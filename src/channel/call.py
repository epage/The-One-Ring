import logging

import telepathy


_moduleLogger = logging.getLogger("channel.call")


class CallChannel(
		telepathy.server.ChannelTypeStreamedMedia,
		telepathy.server.ChannelInterfaceCallState,
	):

	def __init__(self, connection):
		h = None
		telepathy.server.ChannelTypeStreamedMedia.__init__(self, connection, h)
		telepathy.server.ChannelInterfaceGroup.__init__(self)
		telepathy.server.ChannelInterfaceChatState.__init__(self)

	def ListStreams(self):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia
		"""
		pass

	def RemoveStreams(self, streams):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia
		"""
		pass

	def RequestStreamDirection(self, stream, streamDirection):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia

		@note Since streams are short lived, not bothering to implement this
		"""
		_moduleLogger.info("A request was made to change the stream direction")

	def RequestStreams(self, contact, streamType):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia

		@returns [(Stream ID, contact, stream type, stream state, stream direction, pending send flags)]
		"""
		pass

	def GetCallStates(self):
		"""
		For org.freedesktop.Telepathy.Channel.Interface.CallState

		Get the current call states for all contacts involved in this call. 
		@returns {Contact: telepathy.constants.CHANNEL_CALL_STATE_*}
		"""
		pass
