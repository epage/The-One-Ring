import logging

import dbus
import telepathy

import tp
from tp._generated import Connection_Interface_Contact_Capabilities
import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class CapabilitiesMixin(
	tp.ConnectionInterfaceCapabilities,
	Connection_Interface_Contact_Capabilities.ConnectionInterfaceContactCapabilities,
):

	_CAPABILITIES = {
		telepathy.CHANNEL_TYPE_TEXT: (
			telepathy.CONNECTION_CAPABILITY_FLAG_CREATE,
			0,
		),
		telepathy.CHANNEL_TYPE_STREAMED_MEDIA: (
			telepathy.CONNECTION_CAPABILITY_FLAG_CREATE |
				telepathy.CONNECTION_CAPABILITY_FLAG_INVITE,
			telepathy.CHANNEL_MEDIA_CAPABILITY_AUDIO,
		),
	}

	text_chat_class = (
		{
			telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_TEXT,
			telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT),
		},
		[
			telepathy.CHANNEL_INTERFACE + '.TargetHandle',
			telepathy.CHANNEL_INTERFACE + '.TargetID',
		],
	)

	audio_chat_class = (
		{
			telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
			telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT),
		},
		[
			telepathy.CHANNEL_INTERFACE + '.TargetHandle',
			telepathy.CHANNEL_INTERFACE + '.TargetID',
			telepathy.CHANNEL_TYPE_STREAMED_MEDIA + '.InitialAudio',
		],
	)

	av_chat_class = (
		{
			telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
			telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT),
		},
		[
			telepathy.CHANNEL_INTERFACE + '.TargetHandle',
			telepathy.CHANNEL_INTERFACE + '.TargetID',
			telepathy.CHANNEL_TYPE_STREAMED_MEDIA + '.InitialAudio',
			telepathy.CHANNEL_TYPE_STREAMED_MEDIA + '.InitialVideo',
		],
	)

	def __init__(self):
		tp.ConnectionInterfaceCapabilities.__init__(self)
		Connection_Interface_Contact_Capabilities.ConnectionInterfaceContactCapabilities.__init__(self)

	def get_handle_by_id(self, handleType, handleId):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract function called")

	@misc_utils.log_exception(_moduleLogger)
	def GetCapabilities(self, handleIds):
		ret = []
		for handleId in handleIds:
			if handleId != 0 and (telepathy.HANDLE_TYPE_CONTACT, handleId) not in self._handles:
				raise telepathy.errors.InvalidHandle

			h = self.get_handle_by_id(telepathy.HANDLE_TYPE_CONTACT, handleId)
			for type, (gen, spec) in self._CAPABILITIES.iteritems():
				ret.append([handleId, type, gen, spec])
		return ret

	def GetContactCapabilities(self, handles):
		if 0 in handles:
			raise telepathy.InvalidHandle('Contact handle list contains zero')

		ret = dbus.Dictionary({}, signature='ua(a{sv}as)')
		for i in handles:
			handle = self.get_handle_by_id(telepathy.HANDLE_TYPE_CONTACT, i)
			contactCapabilities = (self.text_chat_class, self.audio_chat_class)
			ret[handle] = dbus.Array(contactCapabilities, signature='(a{sv}as)')

		return ret

	def UpdateCapabilities(self, caps):
		_moduleLogger.info("Ignoring updating contact capabilities")
