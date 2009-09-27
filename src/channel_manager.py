import weakref
import logging

import telepathy

import channel


class ChannelManager(object):

	def __init__(self, connection):
		self._connRef = weakref.ref(connection)
		self._listChannels = weakref.WeakValueDictionary()
		self._textChannels = weakref.WeakValueDictionary()
		self._callChannels = weakref.WeakValueDictionary()

	def close(self):
		for chan in self._listChannels.values():
			chan.remove_from_connection()# so that dbus lets it die.
		for chan in self._textChannels.values():
			chan.Close()
		for chan in self._callChannels.values():
			chan.Close()

	def channel_for_list(self, handle, suppress_handler=False):
		if handle in self._listChannels:
			chan = self._listChannels[handle]
		else:
			if handle.get_type() == telepathy.HANDLE_TYPE_GROUP:
				chan = channel.contact_list.GroupChannel(self._connRef(), handle)
			elif handle.get_type() == telepathy.HANDLE_TYPE_CONTACT:
				chan = channel.contact_list.creat_contact_list_channel(self._connRef(), handle)
			else:
				logging.warn("Unknown channel type %r" % handle.get_type())
			self._listChannels[handle] = chan
			self._connRef().add_channel(chan, handle, suppress_handler)
		return chan

	def channel_for_text(self, handle, conversation=None, suppress_handler=False):
		if handle in self._textChannels:
			chan = self._textChannels[handle]
		else:
			logging.debug("Requesting new text channel")
			contact = handle.contact

			if conversation is None:
				client = self._connRef().msn_client
				conversation = None
			chan = channel.text.TextChannel(self._connRef(), conversation)
			self._textChannels[handle] = chan
			self._connRef().add_channel(chan, handle, suppress_handler)
		return chan

	def channel_forcall(self, handle, conversation=None, suppress_handler=False):
		if handle in self._callChannels:
			chan = self._callChannels[handle]
		else:
			logging.debug("Requesting new call channel")
			contact = handle.contact

			if conversation is None:
				client = self._connRef().msn_client
				conversation = None
			chan = channel.call.CallChannel(self._connRef(), conversation)
			self._callChannels[handle] = chan
			self._connRef().add_channel(chan, handle, suppress_handler)
		return chan
