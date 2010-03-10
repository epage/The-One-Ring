#!/usr/bin/env python

import sys

import gobject
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)

import telepathy


DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


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

	def get_next_action(self):
		assert self._action is not None
		return self._action

	def _on_done(self):
		if self._action is None:
			return
		self._action.queue_action()

	def _on_error(self, error):
		print error

	def _on_generic_message(self, *args):
		pass


class DummyAction(Action):

	def queue_action(self):
		gobject.idle_add(self._on_done)


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
			'gv',
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, params):
		print "Connection Parameters:"
		for name, flags, signature, default in params:
			print "\t%s (%s)" % (name, signature),

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
		super(DisplayParams, self)._on_done()


class RequestConnection(Action):

	def __init__(self, cm, username, password, forward):
		super(RequestConnection, self).__init__()
		self._cm = cm

		self._conn = None
		self._serviceName = None

		self._username = username
		self._password = password
		self._forward = forward

	@property
	def conn(self):
		return self._conn

	@property
	def serviceName(self):
		return self._serviceName

	def queue_action(self):
		self._cm[telepathy.server.CONNECTION_MANAGER].RequestConnection(
			'gv',
			{
				'account':  self._username,
				'password': self._password,
				'forward':  self._forward,
			},
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, busName, objectPath):
		self._serviceName = busName
		self._conn = telepathy.client.Connection(busName, objectPath)
		super(RequestConnection, self)._on_done()


class Connect(Action):

	def __init__(self, connAction):
		super(Connect, self).__init__()
		self._connAction = connAction

	def queue_action(self):
		self._connAction.conn[telepathy.server.CONNECTION].connect_to_signal(
			'StatusChanged',
			self._on_change,
		)
		self._connAction.conn[telepathy.server.CONNECTION].Connect(
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
		elif status == telepathy.constants.CONNECTION_STATUS_CONNECTING:
			print "Connecting"
		else:
			print "Status: %r" % status


class SimplePresenceOptions(Action):

	def __init__(self, connAction):
		super(SimplePresenceOptions, self).__init__()
		self._connAction = connAction

	def queue_action(self):
		self._connAction.conn[DBUS_PROPERTIES].Get(
			telepathy.server.CONNECTION_INTERFACE_SIMPLE_PRESENCE,
			'Statuses',
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, statuses):
		print "\tAvailable Statuses"
		for (key, value) in statuses.iteritems():
			print "\t\t - %s" % key
		super(SimplePresenceOptions, self)._on_done()


class NullHandle(object):

	@property
	def handle(self):
		return 0

	@property
	def handles(self):
		return []


class UserHandle(Action):

	def __init__(self, connAction):
		super(UserHandle, self).__init__()
		self._connAction = connAction
		self._handle = None

	@property
	def handle(self):
		return self._handle

	@property
	def handles(self):
		return [self._handle]

	def queue_action(self):
		self._connAction.conn[telepathy.server.CONNECTION].GetSelfHandle(
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, handle):
		self._handle = handle
		super(UserHandle, self)._on_done()


class RequestHandle(Action):

	def __init__(self, connAction, handleType, handleNames):
		super(RequestHandle, self).__init__()
		self._connAction = connAction
		self._handle = None
		self._handleType = handleType
		self._handleNames = handleNames

	@property
	def handle(self):
		return self._handle

	@property
	def handles(self):
		return [self._handle]

	def queue_action(self):
		self._connAction.conn[telepathy.server.CONNECTION].RequestHandles(
			self._handleType,
			self._handleNames,
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, handles):
		self._handle = handles[0]
		super(RequestHandle, self)._on_done()


class RequestChannel(Action):

	def __init__(self, connAction, handleAction, channelType, handleType):
		super(RequestChannel, self).__init__()
		self._connAction = connAction
		self._handleAction = handleAction
		self._channel = None
		self._channelType = channelType
		self._handleType = handleType

	@property
	def channel(self):
		return self._channel

	def queue_action(self):
		self._connAction.conn[telepathy.server.CONNECTION].RequestChannel(
			self._channelType,
			self._handleType,
			self._handleAction.handle,
			True,
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, channelObjectPath):
		self._channel = telepathy.client.Channel(self._connAction.serviceName, channelObjectPath)
		super(RequestChannel, self)._on_done()


class EnsureChannel(Action):

	def __init__(self, connAction, channelType, handleType, handleId):
		super(EnsureChannel, self).__init__()
		self._connAction = connAction
		self._channel = None
		self._channelType = channelType
		self._handleType = handleType
		self._handleId = handleId
		self._handle = None

	@property
	def channel(self):
		return self._channel

	@property
	def handle(self):
		return self._handle

	@property
	def handles(self):
		return [self._handle]

	def queue_action(self):
		properties = {
			telepathy.server.CHANNEL_INTERFACE+".ChannelType": self._channelType,
			telepathy.server.CHANNEL_INTERFACE+".TargetHandleType": self._handleType,
			telepathy.server.CHANNEL_INTERFACE+".TargetID": self._handleId,
		}
		self._connAction.conn[telepathy.server.CONNECTION_INTERFACE_REQUESTS].EnsureChannel(
			properties,
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, yours, channelObjectPath, properties):
		print "Create?", not not yours
		print "Path:", channelObjectPath
		print "Properties:", properties
		self._channel = telepathy.client.Channel(self._connAction.serviceName, channelObjectPath)
		self._handle = properties[telepathy.server.CHANNEL_INTERFACE+".TargetHandle"]
		super(EnsureChannel, self)._on_done()


class CloseChannel(Action):

	def __init__(self, connAction, chanAction):
		super(CloseChannel, self).__init__()
		self._connAction = connAction
		self._chanAction = chanAction
		self._handles = []

	def queue_action(self):
		self._chanAction.channel[telepathy.server.CHANNEL].Close(
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self):
		super(CloseChannel, self)._on_done()


class ContactHandles(Action):

	def __init__(self, connAction, chanAction):
		super(ContactHandles, self).__init__()
		self._connAction = connAction
		self._chanAction = chanAction
		self._handles = []

	@property
	def handles(self):
		return self._handles

	def queue_action(self):
		self._chanAction.channel[DBUS_PROPERTIES].Get(
			telepathy.server.CHANNEL_INTERFACE_GROUP,
			'Members',
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, handles):
		self._handles = list(handles)
		super(ContactHandles, self)._on_done()


class SimplePresenceStatus(Action):

	def __init__(self, connAction, handleAction):
		super(SimplePresenceStatus, self).__init__()
		self._connAction = connAction
		self._handleAction = handleAction

	def queue_action(self):
		self._connAction.conn[telepathy.server.CONNECTION_INTERFACE_SIMPLE_PRESENCE].GetPresences(
			self._handleAction.handles,
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, aliases):
		print "\tPresences:"
		for hid, (presenceType, presence, presenceMessage) in aliases.iteritems():
			print "\t\t%s:" % hid, presenceType, presence, presenceMessage
		super(SimplePresenceStatus, self)._on_done()


class SetSimplePresence(Action):

	def __init__(self, connAction, status, message):
		super(SetSimplePresence, self).__init__()
		self._connAction = connAction
		self._status = status
		self._message = message

	def queue_action(self):
		self._connAction.conn[telepathy.server.CONNECTION_INTERFACE_SIMPLE_PRESENCE].SetPresence(
			self._status,
			self._message,
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self):
		super(SetSimplePresence, self)._on_done()


class Aliases(Action):

	def __init__(self, connAction, handleAction):
		super(Aliases, self).__init__()
		self._connAction = connAction
		self._handleAction = handleAction

	def queue_action(self):
		self._connAction.conn[telepathy.server.CONNECTION_INTERFACE_ALIASING].RequestAliases(
			self._handleAction.handles,
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, aliases):
		print "\tAliases:"
		for h, alias in zip(self._handleAction.handles, aliases):
			print "\t\t", h, alias
		super(Aliases, self)._on_done()


class Call(Action):

	def __init__(self, connAction, chanAction, handleAction):
		super(Call, self).__init__()
		self._connAction = connAction
		self._chanAction = chanAction
		self._handleAction = handleAction

	def queue_action(self):
		self._chanAction.channel[telepathy.server.CHANNEL_TYPE_STREAMED_MEDIA].RequestStreams(
			self._handleAction.handle,
			[telepathy.constants.MEDIA_STREAM_TYPE_AUDIO],
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self, handle):
		print "Call started"
		super(Call, self)._on_done()


class SendText(Action):

	def __init__(self, connAction, chanAction, handleAction, messageType, message):
		super(SendText, self).__init__()
		self._connAction = connAction
		self._chanAction = chanAction
		self._handleAction = handleAction
		self._messageType = messageType
		self._message = message

	def queue_action(self):
		self._chanAction.channel[telepathy.server.CHANNEL_TYPE_TEXT].Send(
			self._messageType,
			self._message,
			reply_handler = self._on_done,
			error_handler = self._on_error,
		)

	def _on_done(self,):
		print "Message sent"
		super(SendText, self)._on_done()


class Sleep(Action):

	def __init__(self, length):
		super(Sleep, self).__init__()
		self._length = length

	def queue_action(self):
		gobject.timeout_add(self._length, self._on_done)


class Block(Action):

	def __init__(self):
		super(Block, self).__init__()

	def queue_action(self):
		print "Blocking"

	def _on_done(self):
		#super(SendText, self)._on_done()
		pass


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

	nullHandle = NullHandle()

	dummy = DummyAction()
	firstAction = dummy
	lastAction = dummy

	if True:
		dp = DisplayParams(cm)
		lastAction.append_action(dp)
		lastAction = lastAction.get_next_action()

	if True:
		username = sys.argv[1]
		password = sys.argv[2]
		forward = sys.argv[3]
		reqcon = RequestConnection(cm, username, password, forward)
		lastAction.append_action(reqcon)
		lastAction = lastAction.get_next_action()

		if False:
			reqcon = RequestConnection(cm, username, password, forward)
			lastAction.append_action(reqcon)
			lastAction = lastAction.get_next_action()

		con = Connect(reqcon)
		lastAction.append_action(con)
		lastAction = lastAction.get_next_action()

		if True:
			spo = SimplePresenceOptions(reqcon)
			lastAction.append_action(spo)
			lastAction = lastAction.get_next_action()

		if True:
			uh = UserHandle(reqcon)
			lastAction.append_action(uh)
			lastAction = lastAction.get_next_action()

			ua = Aliases(reqcon, uh)
			lastAction.append_action(ua)
			lastAction = lastAction.get_next_action()

			sps = SimplePresenceStatus(reqcon, uh)
			lastAction.append_action(sps)
			lastAction = lastAction.get_next_action()

			if False:
				setdnd = SetSimplePresence(reqcon, "dnd", "")
				lastAction.append_action(setdnd)
				lastAction = lastAction.get_next_action()

				sps = SimplePresenceStatus(reqcon, uh)
				lastAction.append_action(sps)
				lastAction = lastAction.get_next_action()

				setdnd = SetSimplePresence(reqcon, "available", "")
				lastAction.append_action(setdnd)
				lastAction = lastAction.get_next_action()

				sps = SimplePresenceStatus(reqcon, uh)
				lastAction.append_action(sps)
				lastAction = lastAction.get_next_action()

		if False:
			sl = Sleep(10 * 1000)
			lastAction.append_action(sl)
			lastAction = lastAction.get_next_action()

		if False:
			rclh = RequestHandle(reqcon, telepathy.HANDLE_TYPE_LIST, ["subscribe"])
			lastAction.append_action(rclh)
			lastAction = lastAction.get_next_action()

			rclc = RequestChannel(
				reqcon,
				rclh,
				telepathy.CHANNEL_TYPE_CONTACT_LIST,
				telepathy.HANDLE_TYPE_LIST,
			)
			lastAction.append_action(rclc)
			lastAction = lastAction.get_next_action()

			ch = ContactHandles(reqcon, rclc)
			lastAction.append_action(ch)
			lastAction = lastAction.get_next_action()

			ca = Aliases(reqcon, ch)
			lastAction.append_action(ca)
			lastAction = lastAction.get_next_action()

		if True:
			accountNumber = sys.argv[4]
			enChan = EnsureChannel(reqcon, telepathy.CHANNEL_TYPE_TEXT, telepathy.HANDLE_TYPE_CONTACT, accountNumber)
			lastAction.append_action(enChan)
			lastAction = lastAction.get_next_action()

			sendDebugtext = SendText(reqcon, enChan, enChan, telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, "Boo!")
			lastAction.append_action(sendDebugtext)
			lastAction = lastAction.get_next_action()

		if False:
			rch = RequestHandle(reqcon, telepathy.HANDLE_TYPE_CONTACT, ["18005558355"]) #(1-800-555-TELL)
			lastAction.append_action(rch)
			lastAction = lastAction.get_next_action()

			# making a phone call
			if True:
				smHandle = rch
				smHandleType = telepathy.HANDLE_TYPE_CONTACT
			else:
				smHandle = nullHandle
				smHandleType = telepathy.HANDLE_TYPE_NONE
			rsmc = RequestChannel(
				reqcon,
				smHandle,
				telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
				smHandleType,
			)
			lastAction.append_action(rsmc)
			lastAction = lastAction.get_next_action()

			if False:
				call = Call(reqcon, rsmc, rch)
				lastAction.append_action(call)
				lastAction = lastAction.get_next_action()

			# sending a text
			rtc = RequestChannel(
				reqcon,
				rch,
				telepathy.CHANNEL_TYPE_TEXT,
				smHandleType,
			)
			lastAction.append_action(rtc)
			lastAction = lastAction.get_next_action()

			if True:
				closechan = CloseChannel(reqcon, rtc)
				lastAction.append_action(closechan)
				lastAction = lastAction.get_next_action()

				rtc = RequestChannel(
					reqcon,
					rch,
					telepathy.CHANNEL_TYPE_TEXT,
					smHandleType,
				)
				lastAction.append_action(rtc)
				lastAction = lastAction.get_next_action()

			if False:
				sendtext = SendText(reqcon, rtc, rch, telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL, "Boo!")
				lastAction.append_action(sendtext)
				lastAction = lastAction.get_next_action()

		if False:
			bl = Block()
			lastAction.append_action(bl)
			lastAction = lastAction.get_next_action()

		if False:
			sl = Sleep(30 * 1000)
			lastAction.append_action(sl)
			lastAction = lastAction.get_next_action()

		dis = Disconnect(reqcon)
		lastAction.append_action(dis)
		lastAction = lastAction.get_next_action()

	quitter = QuitLoop(loop)
	lastAction.append_action(quitter)
	lastAction = lastAction.get_next_action()

	firstAction.queue_action()
	loop.run()
