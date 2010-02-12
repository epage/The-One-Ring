#!/usr/bin/env python

"""
Telepathy-TheOneRing - Telepathy plugin for GoogleVoice
Copyright (C) 2009  Ed Page eopage AT byu DOT net

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""

import os
import sys
import signal
import logging
import gobject

import dbus.glib
import telepathy.utils as telepathy_utils

import util.linux as linux_utils
import util.go_utils as gobject_utils
import constants
import connection_manager


IDLE_TIMEOUT = 5


def run_theonering(persist):
	linux_utils.set_process_name(constants.__app_name__)

	try:
		os.makedirs(constants._data_path_)
	except OSError, e:
		if e.errno != 17:
			raise

	@gobject_utils.async
	def quit():
		manager.quit()
		mainloop.quit()

	def timeout_cb():
		if len(manager._connections) == 0:
			logging.info('No connection received - quitting')
			quit()
		return False

	if persist:
		shutdown_callback = None
	else:
		gobject_utils.timeout_add_seconds(IDLE_TIMEOUT, timeout_cb)
		shutdown_callback = quit

	signal.signal(signal.SIGTERM, lambda: quit)

	try:
		manager = connection_manager.TheOneRingConnectionManager(shutdown_func=shutdown_callback)
	except dbus.exceptions.NameExistsException:
		logging.warning('Failed to acquire bus name, connection manager already running?')
		sys.exit(1)

	mainloop = gobject.MainLoop(is_running=True)

	while mainloop.is_running():
		try:
			mainloop.run()
		except KeyboardInterrupt:
			quit()


def main(logToFile):
	try:
		os.makedirs(constants._data_path_)
	except OSError, e:
		if e.errno != 17:
			raise

	telepathy_utils.debug_divert_messages(os.getenv('THEONERING_LOGFILE'))
	if logToFile:
		logging.basicConfig(
			level=logging.DEBUG,
			filename=constants._user_logpath_,
			format='(%(asctime)s) %(levelname)s:%(name)s:%(message)s',
			datefmt='%H:%M:%S',
		)
	else:
		logging.basicConfig(
			level=logging.INFO,
			format='(%(asctime)s) %(levelname)s:%(name)s:%(message)s',
			datefmt='%H:%M:%S',
		)
	logging.info("telepathy-theonering %s-%s" % (constants.__version__, constants.__build__))
	logging.debug("OS: %s" % (os.uname()[0], ))
	logging.debug("Kernel: %s (%s) for %s" % os.uname()[2:])
	logging.debug("Hostname: %s" % os.uname()[1])

	persist = 'THEONERING_PERSIST' in os.environ

	try:
		run_theonering(persist)
	finally:
		logging.shutdown()


if __name__ == "__main__":
	main(False)
