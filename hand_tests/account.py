#!/usr/bin/env python

import logging

import dbus
import telepathy


_moduleLogger = logging.getLogger(__name__)


DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class Account(telepathy.client.interfacefactory.InterfaceFactory):

	def __init__(self, object_path, bus=None):
		if not bus:
			bus = dbus.Bus()
		service_name = 'org.freedesktop.Telepathy.AccountManager'
		#service_name = object_path.replace('/', '.')[1:]

		object = bus.get_object(service_name, object_path)
		telepathy.client.interfacefactory.InterfaceFactory.__init__(self, object, telepathy.interfaces.ACCOUNT)

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


def _process_acct_path(acct_path):
	print "Account:", acct_path
	acct = Account(acct_path)
	conn = acct[DBUS_PROPERTIES].Get(telepathy.interfaces.ACCOUNT, 'Connection')
	print "Connection:", conn
	if conn == "/":
		return
	conn = telepathy.client.Connection(conn.replace('/', '.')[1:], conn)
	conn.call_when_ready(lambda con: _show_conn(acct, acct_path, con))


def _show_conn(acct, path, conn):
	print path
	print "\t", repr(acct)
	print "\t", repr(conn)
	acct["com.nokia.Account.Interface.ChannelRequests"].EnsureChannel(
		{
			telepathy.interfaces.CHANNEL+".ChannelType": telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA,
			telepathy.interfaces.CHANNEL+".TargetHandleType": telepathy.constants.HANDLE_TYPE_CONTACT,
			telepathy.interfaces.CHANNEL+".TargetID": "512-961-6001",
		},
		0,
		"",
		reply_handler=lambda *args: _on_ensure("good", path, *args),
		error_handler=lambda *args: _on_ensure("bad", path, *args),
	)


def _on_ensure(state, acct_path, *args):
	print state
	print "\t", acct_path
	print "\tEnsure:", args


if __name__ == '__main__':
	import gobject
	from dbus.mainloop.glib import DBusGMainLoop
	import accountmgr

	DBusGMainLoop(set_as_default=True)

	am = accountmgr.AccountManager()
	for acct_path in am[DBUS_PROPERTIES].Get(telepathy.interfaces.ACCOUNT_MANAGER, 'ValidAccounts'):
		_process_acct_path(acct_path)

	gobject.MainLoop().run()
