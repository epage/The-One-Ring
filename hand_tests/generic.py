#!/usr/bin/env python

import sys

import gobject
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)

import telepathy


def get_registry():
	reg = telepathy.client.ManagerRegistry()
	reg.LoadManagers()
	return reg


def get_connection_manager(reg):
	cm = reg.GetManager('theonering')
	return cm


class Action(object):

	def __init__(self):
		self._action = None

	def queue_action(self):
		pass

	def append_action(self, action):
		assert self._action is None
		self._action = action

	def _on_done(self):
		if self._action is None:
			return
		self._action.queue_action()

	def _on_error(self, error):
		print error

	def _on_generic_message(self, *args):
		pass


class QuitLoop(Action):

	def __init__(self, loop):
		super(QuitLoop, self).__init__()
		self._loop = loop

	def queue_action(self):
		self._loop.quit()


class DisplayParams(Action):

	def __init__(self, cm):
		super(DisplayParams, self).__init__()
		self._cm = cm

	def queue_action(self):
		self._cm[telepathy.interfaces.CONN_MGR_INTERFACE].GetParameters(
			'sip',
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, params):
		super(DisplayParams, self)._on_done()
		for name, flags, signature, default in params:
			print "%s (%s)" % (name, signature),

			if flags & telepathy.constants.CONN_MGR_PARAM_FLAG_REQUIRED:
				print "required",
			if flags & telepathy.constants.CONN_MGR_PARAM_FLAG_REGISTER:
				print "register",
			if flags & telepathy.constants.CONN_MGR_PARAM_FLAG_SECRET:
				print "secret",
			if flags & telepathy.constants.CONN_MGR_PARAM_FLAG_DBUS_PROPERTY:
				print "dbus-property",
			if flags & telepathy.constants.CONN_MGR_PARAM_FLAG_HAS_DEFAULT:
				print "has-default(%s)" % default,

			print ""


class Connect(Action):

	def __init__(self, cm, username, password, forward):
		super(Connect, self).__init__()
		self._cm = cm
		self._conn = None
		self._username = username
		self._password = password
		self._forward = forward

	@property
	def conn(self):
		return self._conn

	def queue_action(self):
		self._cm[telepathy.server.CONNECTION_MANAGER].RequestConnection(
			'sip',
			{
				'username':  self._username,
				'password': self._password,
				'forward':  self._forward,
			},
			reply_handler = self._on_connection_requested,
			error_handler = self._on_error,
		)

	def _on_connection_requested(self, busName, objectPath):
		self._conn = telepathy.client.Connection(busName, objectPath)
		self._conn[telepathy.server.CONNECTION].connect_to_signal(
			'StatusChanged',
			self._on_change,
		)
		self._conn[telepathy.server.CONNECTION].Connect(
			reply_handler = self._on_generic_message,
			error_handler = self._on_error,
		)

	def _on_done(self):
		super(Connect, self)._on_done()

	def _on_change(self, status, reason):
		if status == telepathy.constants.CONNECTION_STATUS_DISCONNECTED:
			print "Disconnected!"
			self._conn = None
		elif status == telepathy.constants.CONNECTION_STATUS_CONNECTED:
			print "Connected"
			self._on_done()
		else:
			print "Status: %r" % status


class Disconnect(Action):

	def __init__(self, connAction):
		super(Disconnect, self).__init__()
		self._connAction = connAction

	def queue_action(self):
		self._connAction.conn[telepathy.server.CONNECTION].Disconnect(
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)


if __name__ == '__main__':
	loop = gobject.MainLoop()

	reg = get_registry()
	cm = get_connection_manager(reg)

	dummy = Action()
	lastAction = dummy

	dp = DisplayParams(cm)
	lastAction.append_action(dp)
	lastAction = dp

	username = sys.argv[1]
	password = sys.argv[2]
	forward = sys.argv[3]
	con = Connect(cm, username, password, forward)
	lastAction.append_action(con)
	lastAction = con

	dis = Disconnect(con)
	lastAction.append_action(dis)
	lastAction = dis

	quitter = QuitLoop(loop)
	lastAction.append_action(quitter)
	lastAction = quitter

	dp.queue_action()
	loop.run()
