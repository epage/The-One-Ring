import logging

import gobject
import telepathy

try:
	import conic as _conic
	conic = _conic
except (ImportError, OSError):
	conic = None

import constants
import util.coroutines as coroutines
import util.go_utils as gobject_utils
import util.tp_utils as telepathy_utils
import gtk_toolbox


_moduleLogger = logging.getLogger("autogv")


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
		self._connRef().session.voicemails.updateSignalHandler.unregister_sink(
			self.__callback
		)
		self._connRef().session.texts.updateSignalHandler.unregister_sink(
			self.__callback
		)
		self.__callback = None

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_conversations_updated(self, conv, conversationIds):
		_moduleLogger.debug("Incoming messages from: %r" % (conversationIds, ))
		for phoneNumber in conversationIds:
			h = self._connRef().get_handle_by_name(telepathy.HANDLE_TYPE_CONTACT, phoneNumber)
			# Just let the TextChannel decide whether it should be reported to the user or not
			props = self._connRef().generate_props(telepathy.CHANNEL_TYPE_TEXT, h, False)
			if self._channel_manager.channel_exists(props):
				continue

			# Maemo 4.1's RTComm opens a window for a chat regardless if a
			# message is received or not, so we need to do some filtering here
			mergedConv = conv.get_conversation(phoneNumber)
			unreadConvs = [
				conversation
				for conversation in mergedConv.conversations
				if not conversation.isRead and not conversation.isArchived
			]
			if not unreadConvs:
				continue

			chan = self._channel_manager.channel_for_props(props, signal=True)


class RefreshVoicemail(object):

	def __init__(self, connRef):
		self._connRef = connRef
		self._newChannelSignaller = telepathy_utils.NewChannelSignaller(self._on_new_channel)
		self._outstandingRequests = []

	def start(self):
		self._newChannelSignaller.start()

	def stop(self):
		_moduleLogger.info("Stopping voicemail refresh")
		self._newChannelSignaller.stop()

		# I don't want to trust whether the cancel happens within the current
		# callback or not which could be the deciding factor between invalid
		# iterators or infinite loops
		localRequests = [r for r in self._outstandingRequests]
		for request in localRequests:
			localRequests.cancel()

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_new_channel(self, bus, serviceName, connObjectPath, channelObjectPath, channelType):
		if channelType != telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA:
			return

		cmName = telepathy_utils.cm_from_path(connObjectPath)
		if cmName == constants._telepathy_implementation_name_:
			_moduleLogger.debug("Ignoring channels from self to prevent deadlock")
			return

		conn = telepathy.client.Connection(serviceName, connObjectPath)
		chan = telepathy.client.Channel(serviceName, channelObjectPath)
		missDetection = telepathy_utils.WasMissedCall(
			bus, conn, chan, self._on_missed_call, self._on_error_for_missed
		)
		self._outstandingRequests.append(missDetection)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_missed_call(self, missDetection):
		_moduleLogger.info("Missed a call")
		self._connRef().session.voicemailsStateMachine.reset_timers()
		self._outstandingRequests.remove(missDetection)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_error_for_missed(self, missDetection, reason):
		_moduleLogger.debug("Error: %r claims %r" % (missDetection, reason))
		self._outstandingRequests.remove(missDetection)


class AutoDisconnect(object):

	def __init__(self, connRef):
		self._connRef = connRef
		if conic is not None:
			self.__connection = conic.Connection()
		else:
			self.__connection = None

		self.__connectionEventId = None
		self.__delayedDisconnectEventId = None

	def start(self):
		if self.__connection is not None:
			self.__connectionEventId = self.__connection.connect("connection-event", self._on_connection_change)

	def stop(self):
		self._cancel_delayed_disconnect()

	@gtk_toolbox.log_exception(_moduleLogger)
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
			self.__delayedDisconnectEventId = gobject_utils.timeout_add_seconds(
				5, self._on_delayed_disconnect
			)
		elif status == conic.STATUS_CONNECTED:
			_moduleLogger.info("Connected to network")
			self._cancel_delayed_disconnect()
		else:
			_moduleLogger.info("Other status: %r" % (status, ))

	def _cancel_delayed_disconnect(self):
		if self.__delayedDisconnectEventId is None:
			return
		_moduleLogger.info("Cancelling auto-log off")
		gobject.source_reove(self.__delayedDisconnectEventId)
		self.__delayedDisconnectEventId = None

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_delayed_disconnect(self):
		if not self.session.is_logged_in():
			_moduleLogger.info("Received connection change event when not logged in")
			return
		try:
			self._connRef().disconnect()
		except Exception:
			_moduleLogger.exception("Error durring disconnect")
		self._connRef().StatusChanged(
			telepathy.CONNECTION_STATUS_DISCONNECTED,
			telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR
		)
		self.__delayedDisconnectEventId = None
		return False

