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
			object = bus.get_object(self.service_name, self.object_path)
		except:
			raise
			# try activating MissionControl5 (ugly work-around)
			mc5 = bus.get_object(self.MC5_name, self.MC5_path)
			import time
			time.sleep(1)
			object = bus.get_object(self.service_name, self.object_path)
		telepathy.client.interfacefactory.InterfaceFactory.__init__(self, object, telepathy.interfaces.ACCOUNT_MANAGER)

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


if __name__ == '__main__':
	import gobject
	from dbus.mainloop.glib import DBusGMainLoop
	DBusGMainLoop(set_as_default=True)

	am = AccountManager()
	print am[DBUS_PROPERTIES].Get(telepathy.interfaces.ACCOUNT_MANAGER, 'ValidAccounts')

	gobject.MainLoop().run()
