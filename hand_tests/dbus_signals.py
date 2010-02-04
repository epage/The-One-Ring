#!/usr/bin/env python

import gobject
import dbus
import dbus.mainloop.glib
import telepathy


DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class AutoAcceptAttempt(object):

	def __init__(self, bus, chan):
		self._sessionBus = bus
		self._chan = chan

		self._selfHandle = None
		self._initiatorHandle = None
		self._initiatorID = None
		self._targetHandle = None
		self._targetID = None
		self._pendingHandles = None

		if False:
			# @bug Unsure why this isn't working
			self._chan[DBUS_PROPERTIES].Get(
				telepathy.interfaces.CONNECTION_INTERFACE,
				'SelfHandle',
				reply_handler = self._on_got_self_handle,
				error_handler = self._on_nothing,
			)
		else:
			self._chan[telepathy.interfaces.CHANNEL_INTERFACE_GROUP].GetSelfHandle(
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

		serviceName = channelObjectPath.rsplit("/", 1)[0][1:].replace("/", ".")
		chan = telepathy.client.Channel(serviceName, channelObjectPath)
		# @bug does not distinguish between preferred CMs
		# @todo Need a way to be notified on error, ignored, or if picked up
		attemptPickup = AutoAcceptAttempt(self._sessionBus, chan)
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
