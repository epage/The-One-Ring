#!/usr/bin/env python

import logging

import dbus
import telepathy


_moduleLogger = logging.getLogger(__name__)


DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class AccountManager(telepathy.client.interfacefactory.InterfaceFactory):

	service_name = 'org.freedesktop.Telepathy.AccountManager'
	object_path = '/org/freedesktop/Telepathy/AccountManager'

	# Some versions of Mission Control are only activatable under this
	# name, not under the generic AccountManager name
	MC5_name = 'org.freedesktop.Telepathy.MissionControl5'
	MC5_path = '/org/freedesktop/Telepathy/MissionControl5'

	def __init__(self, bus=None):
		if not bus:
			bus = dbus.Bus()

		try:
			obj = bus.get_object(self.service_name, self.object_path)
		except:
			raise
			# try activating MissionControl5 (ugly work-around)
			mc5 = bus.get_object(self.MC5_name, self.MC5_path)
			import time
			time.sleep(1)
			obj = bus.get_object(self.service_name, self.object_path)
		telepathy.client.interfacefactory.InterfaceFactory.__init__(self, obj, telepathy.interfaces.ACCOUNT_MANAGER)

		self[DBUS_PROPERTIES].Get(
			telepathy.interfaces.ACCOUNT_MANAGER,
			'Interfaces',
			reply_handler=self._on_get,
			error_handler=self._on_error,
		)

	def _on_get(self, stuff):
		self.get_valid_interfaces().update(stuff)

	def _on_error(self, *args):
		_moduleLogger.error(args)


class Account(telepathy.client.interfacefactory.InterfaceFactory):

	def __init__(self, object_path, bus=None):
		if not bus:
			bus = dbus.Bus()
		service_name = 'org.freedesktop.Telepathy.AccountManager'

		obj = bus.get_object(service_name, object_path)
		telepathy.client.interfacefactory.InterfaceFactory.__init__(self, obj, telepathy.interfaces.ACCOUNT)

		self[DBUS_PROPERTIES].Get(
			telepathy.interfaces.ACCOUNT,
			'Interfaces',
			reply_handler=self._on_get,
			error_handler=self._on_error,
		)

	def _on_get(self, stuff):
		self.get_valid_interfaces().update(stuff)

	def _on_error(self, *args):
		_moduleLogger.error(args)


def _process_acct_path(acct_path, target, message):
	print "Account:", acct_path
	acct = Account(acct_path)
	conn = acct[DBUS_PROPERTIES].Get(telepathy.interfaces.ACCOUNT, 'Connection')
	print "Connection:", conn
	if conn == "/":
		return
	conn = telepathy.client.Connection(conn.replace('/', '.')[1:], conn)
	conn.call_when_ready(lambda con: _show_conn(acct, acct_path, con, target, message))


def _show_conn(acct, path, conn, target, message):
	print path
	print "\t", repr(acct)
	print "\t", repr(conn)

	properties = {
		telepathy.interfaces.CHANNEL+".ChannelType": telepathy.interfaces.CHANNEL_TYPE_TEXT,
		telepathy.interfaces.CHANNEL+".TargetHandleType": telepathy.constants.HANDLE_TYPE_CONTACT,
		telepathy.server.CHANNEL_INTERFACE+".TargetID": target,
	}
	conn[telepathy.server.CONNECTION_INTERFACE_REQUESTS].EnsureChannel(
		properties,
		reply_handler =
			lambda isYours, channelObjectPath, properties: _on_ensure(acct, conn, message, isYours, channelObjectPath, properties),
		error_handler = _on_error,
	)


def _on_ensure(acct, conn, message, yours, channelObjectPath, properties):
	channel = telepathy.client.Channel(conn.service_name, channelObjectPath)
	handle = properties[telepathy.server.CHANNEL_INTERFACE+".TargetHandle"]
	channel[telepathy.server.CHANNEL_TYPE_TEXT].Send(
		telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL,
		message,
		reply_handler = lambda: _on_send(acct, conn, channel),
		error_handler = _on_error,
	)


def _on_send(acct, conn, channel):
	print "Message sent"
	loop.quit()


def _on_error(*args):
	print "Command failed:", args
	loop.quit()


if __name__ == '__main__':
	import sys
	import gobject
	from dbus.mainloop.glib import DBusGMainLoop

	target = sys.argv[1]
	message = " ".join(sys.argv[2:])

	DBusGMainLoop(set_as_default=True)

	am = AccountManager()
	for acct_path in am[DBUS_PROPERTIES].Get(telepathy.interfaces.ACCOUNT_MANAGER, 'ValidAccounts'):
		if acct_path.startswith("/org/freedesktop/Telepathy/Account/theonering"):
			_process_acct_path(acct_path, target, message)

	global loop
	loop = gobject.MainLoop()
	loop.run()
