#!/usr/bin/env python

import gobject
import dbus
import dbus.mainloop.glib
import telepathy


DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class AutoAcceptAttempt(object):
	# @todo Make this more composable by just checking for incoming call.  Why
	# incoming rather than just call?  Because it has more demands on what
	# properties to get which we can then get them in parallel.  The callback
	# would then chose to pickup based on the caller's number, wait to see if
	# the call is ignored/rejected, etc

	def __init__(self, bus, conn, chan):
		self._sessionBus = bus
		self._conn = conn
		self._chan = chan

		self._selfHandle = None
		self._initiatorHandle = None
		self._initiatorID = None
		self._targetHandle = None
		self._targetID = None
		self._pendingHandles = None

		if False:
			# @bug Unsure why this isn't working
			self._conn[DBUS_PROPERTIES].Get(
				telepathy.interfaces.CONNECTION_INTERFACE,
				'SelfHandle',
				reply_handler = self._on_got_self_handle,
				error_handler = self._on_nothing,
			)
		else:
			self._conn[telepathy.interfaces.CHANNEL_INTERFACE_GROUP].GetSelfHandle(
				reply_handler = self._on_got_self_handle,
				error_handler = self._on_nothing,
			)

		self._chan[DBUS_PROPERTIES].GetAll(
			telepathy.interfaces.CHANNEL_INTERFACE,
			reply_handler = self._on_got_all,
			error_handler = self._on_nothing,
		)

		if False:
			# @bug Unsure why this isn't working
			self._chan[DBUS_PROPERTIES].Get(
				telepathy.interfaces.CHANNEL_INTERFACE_GROUP,
				'LocalPendingMembers',
				reply_handler = self._on_got_pending_members,
				error_handler = self._on_nothing,
			)
		else:
			self._chan[telepathy.interfaces.CHANNEL_INTERFACE_GROUP].GetLocalPendingMembersWithInfo(
				reply_handler = self._on_got_pending_members,
				error_handler = self._on_nothing,
			)

	def _pickup_if_ready(self):
		if None in (
			self._selfHandle,
			self._initiatorHandle,
			self._initiatorID,
			self._targetHandle,
			self._targetID,
			self._pendingHandles,
		):
			# Note ready yet, still some outstanding requests
			return

		if self._selfHandle != self._targetHandle:
			# Turns out it was an inbound call
			return

		# @bug does not distinguish between who the call is from for use for TOR auto-pickup
		self._chan[telepathy.interfaces.CHANNEL_INTERFACE_GROUP].AddMembers(
			reply_handler = self._on_members_added,
			error_handler = self._on_nothing,
		)

	def _on_got_self_handle(self, selfHandle):
		self._pickup_if_ready()

	def _on_got_all(self, properties):
		self._initiatorID = properties["InitiatorID"]
		self._initiatorHandle = properties["InitiatorHandle"]
		self._targetID = properties["InitiatorID"]
		self._targetHandle = properties["InitiatorHandle"]

		self._pickup_if_ready()

	def _on_got_pending_members(self, pendings):
		for pendingHandle, instigatorHandle, reason, message in pendings:
			print pendingHandle, instigatorHandle, reason, message

		self._pendingHandles = [pendingWithInfo[0] for pendingWithInfo in pendings]
		self._pickup_if_ready()

	def _on_members_added(self):
		print "Should be picked up now"

	def _on_nothing(*args):
		print "ERROR", args


class AutoAcceptCall(object):
	# @todo Make this more composable by switchig it to just handle monitoring
	# for new channels.  Other the callback on a new channel will filter for
	# channel type.

	def __init__(self):
		self._sessionBus = dbus.SessionBus()
		self._activeAttempts = []

	def start(self):
		self._sessionBus.add_signal_receiver(
			self._on_new_channel,
			"NewChannel",
			"org.freedesktop.Telepathy.Connection",
			None,
			None
		)

	def _on_new_channel(self, channelObjectPath, channelType, handleType, handle, supressHandler):
		if channelType != telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA:
			return

		connObjectPath = channelObjectPath.rsplit("/", 1)[0][1:]
		serviceName = connObjectPath.replace("/", ".")
		conn = telepathy.client.Channel(serviceName, connObjectPath)
		chan = telepathy.client.Channel(serviceName, channelObjectPath)
		# @bug does not distinguish between preferred CMs
		# @todo Need a way to be notified on error, ignored, or if picked up
		attemptPickup = AutoAcceptAttempt(self._sessionBus, conn, chan)
		self._activeAttempts.append(attemptPickup)

	def _on_nothing(*args):
		print "ERROR", args


if __name__ == "__main__":
	l = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	autoaccept = AutoAcceptCall()

	gobject.threads_init()
	gobject.idle_add(autoaccept.start)

	mainloop = gobject.MainLoop(is_running=True)
	mainloop.run()
