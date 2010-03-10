#!/usr/bin/env python

import logging

import dbus
import telepathy

import util.go_utils as gobject_utils
import misc


_moduleLogger = logging.getLogger("tp_utils")
DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class WasMissedCall(object):

	def __init__(self, bus, conn, chan, on_success, on_error):
		self.__on_success = on_success
		self.__on_error = on_error

		self._requested = None
		self._didMembersChange = False
		self._didClose = False
		self._didReport = False

		self._onTimeout = gobject_utils.Timeout(self._on_timeout)
		self._onTimeout.start(seconds=10)

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
			error_handler = self._on_error,
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
		self._onTimeout.cancel()
		self.__on_success(self)

	def _report_error(self, reason):
		assert not self._didReport
		self._didReport = True
		self._onTimeout.cancel()
		self.__on_error(self, reason)

	@misc.log_exception(_moduleLogger)
	def _on_got_all(self, properties):
		self._requested = properties["Requested"]
		self._report_missed_if_ready()

	@misc.log_exception(_moduleLogger)
	def _on_members_changed(self, message, added, removed, lp, rp, actor, reason):
		if added:
			self._didMembersChange = True
			self._report_missed_if_ready()

	@misc.log_exception(_moduleLogger)
	def _on_closed(self):
		self._didClose = True
		self._report_missed_if_ready()

	@misc.log_exception(_moduleLogger)
	def _on_error(self, *args):
		self._report_error(args)

	@misc.log_exception(_moduleLogger)
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

	@misc.log_exception(_moduleLogger)
	def _on_new_channel(
		self, channelObjectPath, channelType, handleType, handle, supressHandler
	):
		connObjectPath = channel_path_to_conn_path(channelObjectPath)
		serviceName = path_to_service_name(channelObjectPath)
		try:
			self._on_user_new_channel(
				self._sessionBus, serviceName, connObjectPath, channelObjectPath, channelType
			)
		except Exception:
			_moduleLogger.exception("Blocking exception from being passed up")


def channel_path_to_conn_path(channelObjectPath):
	"""
	>>> channel_path_to_conn_path("/org/freedesktop/Telepathy/ConnectionManager/theonering/gv/USERNAME/Channel1")
	'/org/freedesktop/Telepathy/ConnectionManager/theonering/gv/USERNAME'
	"""
	return channelObjectPath.rsplit("/", 1)[0]


def path_to_service_name(path):
	"""
	>>> path_to_service_name("/org/freedesktop/Telepathy/ConnectionManager/theonering/gv/USERNAME/Channel1")
	'org.freedesktop.Telepathy.ConnectionManager.theonering.gv.USERNAME'
	"""
	return ".".join(path[1:].split("/")[0:7])


def cm_from_path(path):
	"""
	>>> cm_from_path("/org/freedesktop/Telepathy/ConnectionManager/theonering/gv/USERNAME/Channel1")
	'theonering'
	"""
	return path[1:].split("/")[4]
