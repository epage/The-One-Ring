import logging

import telepathy

import gtk_toolbox
import handle


_moduleLogger = logging.getLogger("channel.call")


# @todo Test Calls
class CallChannel(
		telepathy.server.ChannelTypeStreamedMedia,
		telepathy.server.ChannelInterfaceCallState,
	):

	def __init__(self, connection, contactHandle):
		telepathy.server.ChannelTypeStreamedMedia.__init__(self, connection, None)
		telepathy.server.ChannelInterfaceCallState.__init__(self)
		self._contactHandle = contactHandle

	@gtk_toolbox.log_exception(_moduleLogger)
	def Close(self):
		self.close()

	def close(self):
		telepathy.server.ChannelTypeStreamedMedia.Close(self)
		self.remove_from_connection()
		self._prop_getters = None # HACK to get around python-telepathy memory leaks

	@gtk_toolbox.log_exception(_moduleLogger)
	def ListStreams(self):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia
		"""
		return ()

	@gtk_toolbox.log_exception(_moduleLogger)
	def RemoveStreams(self, streams):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia
		"""
		raise telepathy.errors.NotImplemented("Cannot remove a stream")

	@gtk_toolbox.log_exception(_moduleLogger)
	def RequestStreamDirection(self, stream, streamDirection):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia

		@note Since streams are short lived, not bothering to implement this
		"""
		_moduleLogger.info("A request was made to change the stream direction")
		raise telepathy.errors.NotImplemented("Cannot change directions")

	@gtk_toolbox.log_exception(_moduleLogger)
	def RequestStreams(self, contactId, streamTypes):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia

		@returns [(Stream ID, contact, stream type, stream state, stream direction, pending send flags)]
		"""
		for streamType in streamTypes:
			if streamType != telepathy.constants.MEDIA_STREAM_TYPE_AUDIO:
				raise telepathy.errors.NotImplemented("Audio is the only stream type supported")

		contact = self._conn.handle(telepathy.constants.HANDLE_TYPE_CONTACT, contactId)
		assert self._contactHandle == contact, "%r != %r" % (self._contactHandle, contact)
		contactId, contactNumber = handle.ContactHandle.from_handle_name(contact.name)

		self._conn.session.backend.call(contactNumber)

		streamId = 0
		streamState = telepathy.constants.MEDIA_STREAM_STATE_DISCONNECTED
		streamDirection = telepathy.constants.MEDIA_STREAM_DIRECTION_BIDIRECTIONAL
		pendingSendFlags = telepathy.constants.MEDIA_STREAM_PENDING_REMOTE_SEND
		return [(streamId, contact, streamTypes[0], streamState, streamDirection, pendingSendFlags)]

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetCallStates(self):
		"""
		For org.freedesktop.Telepathy.Channel.Interface.CallState

		Get the current call states for all contacts involved in this call. 
		@returns {Contact: telepathy.constants.CHANNEL_CALL_STATE_*}
		"""
		return {}
