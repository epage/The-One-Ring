#!/usr/bin/env python

import gobject
import dbus
import dbus.mainloop.glib
import telepathy


DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class AutoAcceptCall(object):

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


class NewChannelSignaller(object):

	def __init__(self, on_new_channel):
		self._sessionBus = dbus.SessionBus()
		self._on_new_channel = on_new_channel

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

	def _on_new_channel(
		self, channelObjectPath, channelType, handleType, handle, supressHandler
	):
		connObjectPath = channelObjectPath.rsplit("/", 1)[0][1:]
		serviceName = connObjectPath.replace("/", ".")
		conn = telepathy.client.Channel(serviceName, connObjectPath)
		chan = telepathy.client.Channel(serviceName, channelObjectPath)
		self._on_new_channel(self._sessionBus, conn, chan, channelType)


class Manager(object):

	def __init__(self):
		self._newChannelSignaller = NewChannelSignaller(self._on_new_channel)
		self._activeAttempts = []

	def _on_new_channel(self, bus, conn, chan, channelType):
		if channelType != telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA:
			return

		# @bug does not distinguish between preferred CMs
		# @todo Need a way to be notified on error, ignored, or if picked up
		attemptPickup = AutoAcceptCall(bus, conn, chan)
		self._activeAttempts.append(attemptPickup)


if __name__ == "__main__":
	l = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	autoaccept = Manager()

	gobject.threads_init()
	gobject.idle_add(autoaccept.start)

	mainloop = gobject.MainLoop(is_running=True)
	mainloop.run()
