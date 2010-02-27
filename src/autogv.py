import logging

import dbus
import telepathy

try:
	import conic as _conic
	conic = _conic
except (ImportError, OSError):
	conic = None

try:
	import osso as _osso
	osso = _osso
except (ImportError, OSError):
	osso = None

import constants
import util.coroutines as coroutines
import util.go_utils as gobject_utils
import util.tp_utils as telepathy_utils
import util.misc as misc_utils
import gvoice


_moduleLogger = logging.getLogger(__name__)


class NewGVConversations(object):

	def __init__(self, connRef):
		self._connRef = connRef
		self.__callback = None

	def start(self):
		self.__callback = coroutines.func_sink(
			coroutines.expand_positional(
				self._on_conversations_updated
			)
		)
		self._connRef().session.voicemails.updateSignalHandler.register_sink(
			self.__callback
		)
		self._connRef().session.texts.updateSignalHandler.register_sink(
			self.__callback
		)

	def stop(self):
		if self.__callback is None:
			_moduleLogger.info("New conversation monitor stopped without starting")
			return
		self._connRef().session.voicemails.updateSignalHandler.unregister_sink(
			self.__callback
		)
		self._connRef().session.texts.updateSignalHandler.unregister_sink(
			self.__callback
		)
		self.__callback = None

	@misc_utils.log_exception(_moduleLogger)
	def _on_conversations_updated(self, conv, conversationIds):
		_moduleLogger.debug("Incoming messages from: %r" % (conversationIds, ))
		for phoneNumber in conversationIds:
			h = self._connRef().get_handle_by_name(telepathy.HANDLE_TYPE_CONTACT, phoneNumber)
			# Just let the TextChannel decide whether it should be reported to the user or not
			props = self._connRef().generate_props(telepathy.CHANNEL_TYPE_TEXT, h, False)
			if self._connRef()._channel_manager.channel_exists(props):
				continue

			# Maemo 4.1's RTComm opens a window for a chat regardless if a
			# message is received or not, so we need to do some filtering here
			mergedConv = conv.get_conversation(phoneNumber)
			newConversations = mergedConv.conversations
			newConversations = gvoice.conversations.filter_out_read(newConversations)
			newConversations = gvoice.conversations.filter_out_self(newConversations)
			newConversations = list(newConversations)
			if not newConversations:
				continue

			chan = self._connRef()._channel_manager.channel_for_props(props, signal=True)


class RefreshVoicemail(object):

	def __init__(self, connRef):
		self._connRef = connRef
		self._newChannelSignaller = telepathy_utils.NewChannelSignaller(self._on_new_channel)
		self._outstandingRequests = []
		self._isStarted = False

	def start(self):
		self._newChannelSignaller.start()
		self._isStarted = True

	def stop(self):
		if not self._isStarted:
			_moduleLogger.info("voicemail monitor stopped without starting")
			return
		_moduleLogger.info("Stopping voicemail refresh")
		self._newChannelSignaller.stop()

		# I don't want to trust whether the cancel happens within the current
		# callback or not which could be the deciding factor between invalid
		# iterators or infinite loops
		localRequests = [r for r in self._outstandingRequests]
		for request in localRequests:
			localRequests.cancel()

		self._isStarted = False

	def _on_new_channel(self, bus, serviceName, connObjectPath, channelObjectPath, channelType):
		if channelType != telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA:
			return

		cmName = telepathy_utils.cm_from_path(connObjectPath)
		if cmName == constants._telepathy_implementation_name_:
			_moduleLogger.debug("Ignoring channels from self to prevent deadlock")
			return

		conn = telepathy.client.Connection(serviceName, connObjectPath)
		try:
			chan = telepathy.client.Channel(serviceName, channelObjectPath)
		except dbus.exceptions.UnknownMethodException:
			_moduleLogger.exception("Client might not have implemented a deprecated method")
			return
		missDetection = telepathy_utils.WasMissedCall(
			bus, conn, chan, self._on_missed_call, self._on_error_for_missed
		)
		self._outstandingRequests.append(missDetection)

	@misc_utils.log_exception(_moduleLogger)
	def _on_missed_call(self, missDetection):
		_moduleLogger.info("Missed a call")
		self._connRef().session.voicemailsStateMachine.reset_timers()
		self._outstandingRequests.remove(missDetection)

	@misc_utils.log_exception(_moduleLogger)
	def _on_error_for_missed(self, missDetection, reason):
		_moduleLogger.debug("Error: %r claims %r" % (missDetection, reason))
		self._outstandingRequests.remove(missDetection)


class TimedDisconnect(object):

	def __init__(self, connRef):
		self._connRef = connRef
		self.__delayedDisconnect = gobject_utils.Timeout(self._on_delayed_disconnect)

	def start(self):
		self.__delayedDisconnect.start(seconds=5)

	def stop(self):
		self.__delayedDisconnect.cancel()

	def _on_delayed_disconnect(self):
		_moduleLogger.info("Timed disconnect occurred")
		self._connRef().disconnect(telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR)


class AutoDisconnect(object):

	def __init__(self, connRef):
		self._connRef = connRef
		if conic is not None:
			self.__connection = conic.Connection()
		else:
			self.__connection = None

		self.__connectionEventId = None
		self.__delayedDisconnect = gobject_utils.Timeout(self._on_delayed_disconnect)

	def start(self):
		if self.__connection is not None:
			self.__connectionEventId = self.__connection.connect("connection-event", self._on_connection_change)

	def stop(self):
		self._cancel_delayed_disconnect()

	@misc_utils.log_exception(_moduleLogger)
	def _on_connection_change(self, connection, event):
		"""
		@note Maemo specific
		"""
		status = event.get_status()
		error = event.get_error()
		iap_id = event.get_iap_id()
		bearer = event.get_bearer_type()

		if status == conic.STATUS_DISCONNECTED:
			_moduleLogger.info("Disconnected from network, starting countdown to logoff")
			self.__delayedDisconnect.start(seconds=5)
		elif status == conic.STATUS_CONNECTED:
			_moduleLogger.info("Connected to network")
			self._cancel_delayed_disconnect()
		else:
			_moduleLogger.info("Other status: %r" % (status, ))

	def _cancel_delayed_disconnect(self):
		_moduleLogger.info("Cancelling auto-log off")
		self.__delayedDisconnect.cancel()

	@misc_utils.log_exception(_moduleLogger)
	def _on_delayed_disconnect(self):
		if not self._connRef().session.is_logged_in():
			_moduleLogger.info("Received connection change event when not logged in")
			return
		try:
			self._connRef().disconnect(telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR)
		except Exception:
			_moduleLogger.exception("Error durring disconnect")


class DisconnectOnShutdown(object):
	"""
	I'm unsure when I get notified of shutdown or if I have enough time to do
	anything about it, but thought this might help
	"""

	def __init__(self, connRef):
		self._connRef = connRef

		self._osso = None
		self._deviceState = None

	def start(self):
		if osso is not None:
			self._osso = osso.Context(constants.__app_name__, constants.__version__, False)
			self._deviceState = osso.DeviceState(self._osso)
			self._deviceState.set_device_state_callback(self._on_device_state_change, 0)
		else:
			_moduleLogger.warning("No device state support")

	def stop(self):
		try:
			self._deviceState.close()
		except AttributeError:
			pass # Either None or close was removed (in Fremantle)
		self._deviceState = None
		try:
			self._osso.close()
		except AttributeError:
			pass # Either None or close was removed (in Fremantle)
		self._osso = None

	@misc_utils.log_exception(_moduleLogger)
	def _on_device_state_change(self, shutdown, save_unsaved_data, memory_low, system_inactivity, message, userData):
		"""
		@note Hildon specific
		"""
		try:
			self._connRef().disconnect(telepathy.CONNECTION_STATUS_REASON_REQUESTED)
		except Exception:
			_moduleLogger.exception("Error durring disconnect")
