#!/usr/bin/env python

import logging

import gobject
import dbus
import dbus.mainloop.glib


_moduleLogger = logging.getLogger(__name__)


class SetSecondaryVCardFields(object):

	ACCOUNT_MGR_NAME = "org.freedesktop.Telepathy.AccountManager"
	ACCOUNT_MGR_PATH = "/org/freedesktop/Telepathy/AccountManager"
	ACCOUNT_MGR_IFACE_QUERY = "com.nokia.AccountManager.Interface.Query"
	ACCOUNT_IFACE_COMPAT = "com.nokia.Account.Interface.Compat"
	ACCOUNT_IFACE_COMPAT_PROFILE = "com.nokia.Account.Interface.Compat.Profile"
	DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'

	def __init__(self, profileName):
		self._bus = dbus.SessionBus()
		self._profileName = profileName

	def start(self):
		self._accountManager = self._bus.get_object(
			self.ACCOUNT_MGR_NAME,
			self.ACCOUNT_MGR_PATH,
		)
		self._accountManagerQuery = dbus.Interface(
			self._accountManager,
			dbus_interface=self.ACCOUNT_MGR_IFACE_QUERY,
		)

		self._accountManagerQuery.FindAccounts(
			{
				self.ACCOUNT_IFACE_COMPAT_PROFILE: self._profileName,
			},
			reply_handler = self._on_found_accounts_reply,
			error_handler = self._on_error,
		)

	def _on_found_accounts_reply(self, accountObjectPaths):
		for accountObjectPath in accountObjectPaths:
			print accountObjectPath
			account = self._bus.get_object(
				self.ACCOUNT_MGR_NAME,
				accountObjectPath,
			)
			accountProperties = dbus.Interface(
				account,
				self.DBUS_PROPERTIES,
			)
			accountProperties.Set(
				self.ACCOUNT_IFACE_COMPAT,
				"SecondaryVCardFields",
				["TEL"],
				reply_handler = self._on_field_set,
				error_handler = self._on_error,
			)

	def _on_field_set(self):
		_moduleLogger.info("Field set")

	def _on_error(self, error):
		_moduleLogger.error("%r" % (error, ))


if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)
	l = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
	manager = SetSecondaryVCardFields("theonering")

	gobject.threads_init()
	gobject.idle_add(manager.start)

	mainloop = gobject.MainLoop(is_running=True)
	mainloop.run()
