#!/usr/bin/env python

import sys

import gobject
# Begin Example 2-1
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default = True)
# End Example 2-1

import telepathy
import telepathy.client
from telepathy.interfaces import CONNECTION_MANAGER, \
								 CONNECTION, \
								 CONNECTION_INTERFACE_REQUESTS, \
								 CONNECTION_INTERFACE_ALIASING, \
								 CONNECTION_INTERFACE_SIMPLE_PRESENCE, \
								 CONNECTION_INTERFACE_CONTACTS, \
								 CHANNEL, \
								 CHANNEL_TYPE_CONTACT_LIST, \
								 CHANNEL_INTERFACE_GROUP
from telepathy.constants import CONNECTION_STATUS_CONNECTED, \
								CONNECTION_STATUS_DISCONNECTED, \
								HANDLE_TYPE_LIST, \
								HANDLE_TYPE_GROUP

DBUS_PROPERTIES = 'org.freedesktop.DBus.Properties'


class Example(object):

	def __init__ (self, account, password, forward):
		"""e.g. account  = 'bob@example.com/test'
				password = 'bigbob'
		"""
		self.conn = None

		reg = telepathy.client.ManagerRegistry()
		reg.LoadManagers()

		# get the gabble Connection Manager
		self.cm = cm = reg.GetManager('theonering')

		# get the parameters required to make a Jabber connection
		# Begin Example 2-3
		cm[CONNECTION_MANAGER].RequestConnection('gv',
			{
				'account':  account,
				'forward':  forward,
				'password': password,
			},
			reply_handler = self.request_connection_cb,
			error_handler = self.error_cb)
		# End Example 2-3

	def run(self):
		self.loop = gobject.MainLoop()
		try:
			self.loop.run()
		except KeyboardInterrupt:
			print "Terminating connection..."
			self.disconnect()
			# reengage the mainloop so that we can disconnect cleanly
			self.loop.run()

	def generic_reply (self, *args): pass

	def error_cb (self, error):
		print "Error:", error
		self.disconnect()

	def disconnect (self):
		if self.conn is None:
			return
		self.conn[CONNECTION].Disconnect(reply_handler = self.generic_reply,
										 error_handler = self.error_cb)

	# Begin Example 2-4
	def request_connection_cb (self, bus_name, object_path):
		print bus_name, object_path
		# End Example 2-4
		self.conn = conn = telepathy.client.Connection(bus_name, object_path)

		conn[CONNECTION].connect_to_signal('StatusChanged',
			self.status_changed_cb)

		print "Establishing connection..."
		conn[CONNECTION].Connect(reply_handler = self.generic_reply,
								 error_handler = self.error_cb)

	def status_changed_cb (self, status, reason):
		conn = self.conn

		if status == CONNECTION_STATUS_DISCONNECTED:
			print "Disconnected!"
			self.loop.quit()

		if status != CONNECTION_STATUS_CONNECTED: return

		print 'Carrier Detected' # remember dialup modems?
		print 'Ctrl-C to disconnect'

		# get a list of interfaces on this connection
		conn[CONNECTION].GetInterfaces(reply_handler = self.get_interfaces_cb,
									   error_handler = self.error_cb)

	def request_contact_list (self, *groups):
		conn = self.conn

		class ensure_channel_cb (object):
			def __init__ (self, parent, group):
				self.parent = parent
				self.group = group

			def __call__ (self, yours, path, properties):
				print "got channel for %s -> %s, yours = %s" % (
					self.group, path, yours)

				channel = telepathy.client.Channel(conn.service_name, path)
				self.channel = channel

				# Begin Example 6-8
				# request the list of members
				channel[DBUS_PROPERTIES].Get(CHANNEL_INTERFACE_GROUP,
										 'Members',
										 reply_handler = self.members_cb,
										 error_handler = self.parent.error_cb)

			def members_cb (self, handles):
				# request information for this list of handles using the
				# Contacts interface
				conn[CONNECTION_INTERFACE_CONTACTS].GetContactAttributes(
					handles, [
						CONNECTION,
						CONNECTION_INTERFACE_ALIASING,
						CONNECTION_INTERFACE_SIMPLE_PRESENCE,
					],
					False,
					reply_handler = self.get_contact_attributes_cb,
					error_handler = self.parent.error_cb)
				# End Example 6-8

			def get_contact_attributes_cb (self, attributes):
				return # DEBUG

				print '-' * 78
				print self.group
				print '-' * 78
				for member in attributes.values():
					for key, value in member.iteritems():
						print '%s: %s' % (key, value)
					print
				print '-' * 78

		def no_channel_available (error):
			print error

		# we can either use TargetID if we know a name, or TargetHandle
		# if we already have a handle
		for group in groups:
			# Begin Example 6-6
			print "Ensuring channel to %s..." % group
			conn[CONNECTION_INTERFACE_REQUESTS].EnsureChannel({
				CHANNEL + '.ChannelType'	 : CHANNEL_TYPE_CONTACT_LIST,
				CHANNEL + '.TargetHandleType': HANDLE_TYPE_LIST,
				CHANNEL + '.TargetID'		: group,
				},
				reply_handler = ensure_channel_cb(self, group),
				error_handler = no_channel_available)
			# End Example 6-6

	def get_interfaces_cb (self, interfaces):
		conn = self.conn

		print "Interfaces:"
		for interface in interfaces:
			print " - %s" % interface

		if CONNECTION_INTERFACE_REQUESTS in interfaces:
			self.request_contact_list('subscribe',
									  'publish',
									  'hide',
									  'allow',
									  'deny',
									  'known')

			# get the open channelsA
			# Begin Example 2-6
			conn[CONNECTION_INTERFACE_REQUESTS].connect_to_signal(
									'NewChannels',
									self.get_channels_cb)
			# End Example 2-6
			# Begin Example 2-5
			conn[DBUS_PROPERTIES].Get(CONNECTION_INTERFACE_REQUESTS,
									'Channels',
									reply_handler = self.get_channels_cb,
									error_handler = self.error_cb)
			# End Example 2-5

		if CONNECTION_INTERFACE_SIMPLE_PRESENCE in interfaces:
			# Begin Example 5-4
			# request the statuses
			print 'Requesting statuses...'
			conn[DBUS_PROPERTIES].Get(CONNECTION_INTERFACE_SIMPLE_PRESENCE,
									'Statuses',
									reply_handler = self.get_statuses_cb,
									error_handler = self.error_cb)

			# set our presence
			#print 'Setting presence...'
			#conn[CONNECTION_INTERFACE_SIMPLE_PRESENCE].SetPresence(
			#						'away',
			#						'At the Movies',
			#						reply_handler = self.generic_reply,
			#						error_handler = self.error_cb)
			# End Example 5-4

		if CONNECTION_INTERFACE_CONTACTS in interfaces:
			print 'Requesting contact attribute interfaces...'
			conn[DBUS_PROPERTIES].Get(CONNECTION_INTERFACE_CONTACTS,
									'ContactAttributeInterfaces',
									reply_handler = self.get_contact_ifaces_cb,
									error_handler = self.error_cb)

	def get_channels_cb (self, channels):
		for channel, props in channels:
			# find the group channels
			if props[CHANNEL + '.ChannelType'] != CHANNEL_TYPE_CONTACT_LIST or \
			   props[CHANNEL + '.TargetHandleType'] != HANDLE_TYPE_GROUP:
				continue

			print 'GROUP: Got channel %s: %s' % (channel, props[CHANNEL + '.TargetID'])

	def get_statuses_cb (self, value):
		print "Statuses:"

		for (key, value) in value.iteritems():
			print " - %s" % key

	def get_contact_ifaces_cb (self, interfaces):
		print "Contact Attribute Interfaces:"
		for interface in interfaces:
			print " - %s" % interface

if __name__ == '__main__':
	username = sys.argv[1]
	password = sys.argv[2]
	forward = sys.argv[3]
	e = Example(username, password, forward)
	e.run()
