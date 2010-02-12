import logging

import telepathy

import tp
import util.misc as misc_utils


_moduleLogger = logging.getLogger('capabilities')


class CapabilitiesMixin(tp.ConnectionInterfaceCapabilities):

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

	def __init__(self):
		tp.ConnectionInterfaceCapabilities.__init__(self)

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
