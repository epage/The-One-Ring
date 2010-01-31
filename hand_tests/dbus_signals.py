#!/usr/bin/env python

import gobject
import dbus
import dbus.mainloop.glib
import telepathy


DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class AutoAcceptCall(object):

	def __init__(self):
		self._sessionBus = dbus.SessionBus()
		self._chan = None

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
		self._chan = telepathy.client.Channel(serviceName, channelObjectPath)
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

	def _on_got_pending_members(self, pendings):
		for pendingHandle, instigatorHandle, reason, message in pendings:
			print pendingHandle, instigatorHandle, reason, message

		# @bug does not distinguish between inbound and outbound channels
		# @bug does not distinguish between who the call is from for use for TOR auto-pickup
		pendingHandles = [pendingWithInfo[0] for pendingWithInfo in pendings]
		self._chan[telepathy.interfaces.CHANNEL_INTERFACE_GROUP].AddMembers(
			reply_handler = self._on_members_added,
			error_handler = self._on_nothing,
		)

	def _on_members_added(self):
		print "Should be picked up now"

	def _on_nothing(*args):
		print "ERROR", args


if __name__ == "__main__":
	l = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	autoaccept = AutoAcceptCall()

	gobject.threads_init()
	gobject.idle_add(autoaccept.start)

	mainloop = gobject.MainLoop(is_running=True)
	mainloop.run()
