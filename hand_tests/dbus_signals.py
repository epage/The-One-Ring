#!/usr/bin/env python

import sys
sys.path.insert(0,"../src")
import logging
import pprint

import gobject
import dbus
import dbus.mainloop.glib
import telepathy

import util.go_utils as gobject_utils
import gtk_toolbox


_moduleLogger = logging.getLogger("receptionist")
DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class AutoAcceptCall(object):

	def __init__(self, bus, conn, chan, on_success, on_error):
		self._sessionBus = bus
		self._conn = conn
		self._chan = chan
		self._outstandingRequests = []
		self._on_success = on_success
		self._on_error = on_error

		self._initiatorHandle = None
		self._initiatorID = None
		self._targetHandle = None
		self._targetID = None
		self._requested = None
		self._pendingHandles = None

		self._chan[DBUS_PROPERTIES].GetAll(
			telepathy.interfaces.CHANNEL_INTERFACE,
			reply_handler = self._on_got_all,
			error_handler = self._custom_error(self._on_got_all),
		)
		self._outstandingRequests.append(self._on_got_all)

		if False:
			# @bug Unsure why this isn't working
			self._chan[DBUS_PROPERTIES].Get(
				telepathy.interfaces.CHANNEL_INTERFACE_GROUP,
				'LocalPendingMembers',
				reply_handler = self._on_got_pending_members,
				error_handler = self._custom_error(self._on_got_pending_members),
			)
		else:
			self._chan[telepathy.interfaces.CHANNEL_INTERFACE_GROUP].GetLocalPendingMembersWithInfo(
				reply_handler = self._on_got_pending_members,
				error_handler = self._custom_error(self._on_got_pending_members),
			)
		self._outstandingRequests.append(self._on_got_pending_members)

	def is_inbound(self):
		return not self._requested
		isInbound = self._targetHandle == self._initiatorHandle
		return isInbound

	@property
	def initiator(self):
		return self._initiatorID

	@property
	def target(self):
		return self._targetID

	def accept_call(self, on_accepted, on_error):
		self._chan[telepathy.interfaces.CHANNEL_INTERFACE_GROUP].AddMembers(
			self._pendingHandles,
			"",
			reply_handler = self._custom_on_accept(on_accepted),
			error_handler = self._custom_on_accept_error(on_error),
		)

	def _custom_on_accept(self, callback):

		def on_accept(*args):
			callback(self)

		return on_accept

	def _custom_on_accept_error(self, callback):

		def on_error(*args):
			callback(self, *args)

		return on_error

	def _custom_error(self, action):

		def _on_error(*args):
			_moduleLogger.error("Failed for %r (%r)" % (action, args))
			self._outstandingRequests.remove(action)
			if self._outstandingRequests:
				return

			self._on_error(self)

		return _on_error

	def _report_callback_done(self, action):
		_moduleLogger.debug("Succeded with %r" % (action, ))
		self._outstandingRequests.remove(action)
		if self._outstandingRequests:
			return

		assert None not in (
			self._initiatorHandle,
			self._initiatorID,
			self._targetHandle,
			self._targetID,
			self._pendingHandles,
			self._requested,
		)

		self._on_success(self)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_got_all(self, properties):
		self._initiatorID = properties["InitiatorID"]
		self._initiatorHandle = properties["InitiatorHandle"]
		self._targetID = properties["InitiatorID"]
		self._targetHandle = properties["InitiatorHandle"]
		self._requested = properties["Requested"]

		self._report_callback_done(self._on_got_all)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_got_pending_members(self, pendings):
		for pendingHandle, instigatorHandle, reason, message in pendings:
			print pendingHandle, instigatorHandle, reason, message

		self._pendingHandles = [pendingWithInfo[0] for pendingWithInfo in pendings]

		self._report_callback_done(self._on_got_pending_members)


class WasMissedCall(object):

	def __init__(self, bus, conn, chan, on_success, on_error):
		self._on_success = on_success
		self._on_error = on_error

		self._requested = None
		self._didMembersChange = False
		self._didClose = False
		self._didReport = False

		self._timeoutId = gobject_utils.timeout_add_seconds(10, self._on_timeout)

		chan[telepathy.interfaces.CHANNEL_INTERFACE_GROUP].connect_to_signal(
			"MembersChanged",
			self._on_members_changed,
		)

		chan[telepathy.interfaces.CHANNEL].connect_to_signal(
			"Closed",
			self._on_closed,
		)

		chan[DBUS_PROPERTIES].GetAll(
			telepathy.interfaces.CHANNEL_INTERFACE,
			reply_handler = self._on_got_all,
			error_handler = self._on_got_all,
		)

	def cancel(self):
		self._report_error("by request")

	def _report_missed_if_ready(self):
		if self._didReport:
			pass
		elif self._requested is not None and (self._didMembersChange or self._didClose):
			if self._requested:
				self._report_error("wrong direction")
			elif self._didClose:
				self._report_success()
			else:
				self._report_error("members added")
		else:
			if self._didClose:
				self._report_error("closed too early")

	def _report_success(self):
		assert not self._didReport
		self._didReport = True
		if self._timeoutId:
			gobject.source_remove(self._timeoutId)
			self._timeoutId = None
		self._on_success(self)

	def _report_error(self, reason):
		assert not self._didReport
		self._didReport = True
		if self._timeoutId:
			gobject.source_remove(self._timeoutId)
			self._timeoutId = None
		self._on_error(self, reason)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_got_all(self, properties):
		self._requested = properties["Requested"]
		self._report_missed_if_ready()

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_members_changed(self, message, added, removed, lp, rp, actor, reason):
		pprint.pprint((message, added, removed, lp, rp, actor, reason))
		if added:
			self._didMembersChange = True
			self._report_missed_if_ready()

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_closed(self):
		self._didClose = True
		self._report_missed_if_ready()

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_error(self, *args):
		self._report_error(args)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_timeout(self):
		self._report_error("timeout")
		return False


class NewChannelSignaller(object):

	def __init__(self, on_new_channel):
		self._sessionBus = dbus.SessionBus()
		self._on_user_new_channel = on_new_channel

	def start(self):
		self._sessionBus.add_signal_receiver(
			self._on_new_channel,
			"NewChannel",
			"org.freedesktop.Telepathy.Connection",
			None,
			None
		)

	def stop(self):
		self._sessionBus.remove_signal_receiver(
			self._on_new_channel,
			"NewChannel",
			"org.freedesktop.Telepathy.Connection",
			None,
			None
		)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_new_channel(
		self, channelObjectPath, channelType, handleType, handle, supressHandler
	):
		connObjectPath = channelObjectPath.rsplit("/", 1)[0]
		serviceName = connObjectPath[1:].replace("/", ".")
		conn = telepathy.client.Connection(serviceName, connObjectPath)
		chan = telepathy.client.Channel(serviceName, channelObjectPath)
		self._on_user_new_channel(self._sessionBus, conn, chan, channelType)


class AutoAcceptManager(object):

	def __init__(self):
		self._newChannelSignaller = NewChannelSignaller(self._on_new_channel)

	def start(self):
		self._newChannelSignaller.start()

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_new_channel(self, bus, conn, chan, channelType):
		pprint.pprint((bus, conn, chan, channelType))
		if channelType != telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA:
			return

		# @todo distinguish between preferred CMs
		attemptPickup = AutoAcceptCall(bus, conn, chan, self._on_inbound_call, self._on_inbound_call_error)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_inbound_call(self, autoAcceptCall):
		# @todo Add a comparison for picking up for only certain contacts
		print autoAcceptCall.initiator, autoAcceptCall.target
		if autoAcceptCall.is_inbound():
			autoAcceptCall.accept_call(self._on_call_pickedup, self._on_pickup_error)
		else:
			_moduleLogger.debug(
				"Not an inbound call (initiator=%r, target=%r)" % (autoAcceptCall.initiator, autoAcceptCall.target)
			)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_inbound_call_error(self, *args):
		_moduleLogger.info("Inbound call error")

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_call_pickedup(self, autoAcceptCall):
		_moduleLogger.info("Call picked up")

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_pickup_error(self, autoAcceptCall, *args):
		_moduleLogger.info("Call failed to pick up (%r)" % (args, ))


class MissedManager(object):

	def __init__(self):
		self._newChannelSignaller = NewChannelSignaller(self._on_new_channel)

	def start(self):
		self._newChannelSignaller.start()

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_new_channel(self, bus, conn, chan, channelType):
		pprint.pprint((bus, conn, chan, channelType))
		if channelType != telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA:
			return

		missDetection = WasMissedCall(
			bus, conn, chan, self._on_missed_call, self._on_error_for_missed
		)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_missed_call(self, missDetection):
		_moduleLogger.info("Missed a call")

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_error_for_missed(self, missDetection, reason):
		_moduleLogger.info("Error: %r claims %r" % (missDetection, reason))


if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	l = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	if False:
		manager = AutoAcceptManager()
	else:
		manager = MissedManager()

	gobject.threads_init()
	gobject.idle_add(manager.start)

	mainloop = gobject.MainLoop(is_running=True)
	mainloop.run()
