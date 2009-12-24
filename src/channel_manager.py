import weakref
import itertools
import logging

import telepathy

import channel


_moduleLogger = logging.getLogger("channel_manager")


class ChannelManager(object):

	def __init__(self, connection):
		self._connRef = weakref.ref(connection)
		self._listChannels = weakref.WeakValueDictionary()
		self._textChannels = weakref.WeakValueDictionary()
		self._callChannels = weakref.WeakValueDictionary()

	def close(self):
		for chan in itertools.chain(
			self._listChannels.values(), self._textChannels.values(), self._callChannels.values()
		):
			try:
				chan.close()
			except Exception:
				_moduleLogger.exception("Shutting down %r" % (chan, ))

	def channel_for_list(self, handle, suppress_handler=False):
		try:
			chan = self._listChannels[handle]
		except KeyError, e:
			if handle.get_type() != telepathy.HANDLE_TYPE_LIST:
				raise telepathy.errors.NotImplemented("Only server lists are allowed")
			_moduleLogger.debug("Requesting new contact list channel")

			chan = channel.contact_list.create_contact_list_channel(self._connRef(), handle)
			self._listChannels[handle] = chan
			self._connRef().add_channel(chan, handle, suppress_handler)
		return chan

	def channel_for_text(self, handle, suppress_handler=False):
		try:
			chan = self._textChannels[handle]
		except KeyError, e:
			if handle.get_type() != telepathy.HANDLE_TYPE_CONTACT:
				raise telepathy.errors.NotImplemented("Only Contacts are allowed")
			_moduleLogger.debug("Requesting new text channel")

			chan = channel.text.TextChannel(self._connRef(), handle)
			self._textChannels[handle] = chan
			self._connRef().add_channel(chan, handle, suppress_handler)
		return chan

	def channel_for_call(self, handle, suppress_handler=False):
		try:
			chan = self._callChannels[handle]
		except KeyError, e:
			if handle.get_type() != telepathy.HANDLE_TYPE_CONTACT:
				_moduleLogger.warning("Using deprecated means to create a call")
				raise telepathy.errors.NotImplemented("Not implementing depcrecated means")
			_moduleLogger.debug("Requesting new call channel")

			chan = channel.call.CallChannel(self._connRef(), handle)
			self._callChannels[handle] = chan
			self._connRef().add_channel(chan, handle, suppress_handler)
		return chan
