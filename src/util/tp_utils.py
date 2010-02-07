#!/usr/bin/env python

import logging
import pprint

import gobject
import dbus
import telepathy

import util.go_utils as gobject_utils
import gtk_toolbox


_moduleLogger = logging.getLogger("tp_utils")
DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


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
