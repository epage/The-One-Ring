import logging

import gobject
import telepathy

import tp
import gtk_toolbox


_moduleLogger = logging.getLogger("channel.call")


class CallChannel(
		tp.ChannelTypeStreamedMedia,
		tp.ChannelInterfaceCallState,
		tp.ChannelInterfaceGroup,
	):
	# @bug On Maemo 5 this is having some kind of "General" error, possibly due to an issue with "GetAll" DBusProperties stuff
	# @bug broke again on Empathy

	def __init__(self, connection, manager, props, contactHandle):
		self.__manager = manager
		self.__props = props
		self.__cancelId = None

		tp.ChannelTypeStreamedMedia.__init__(self, connection, manager, props)
		tp.ChannelInterfaceCallState.__init__(self)
		tp.ChannelInterfaceGroup.__init__(self)
		self.__contactHandle = contactHandle
		self._implement_property_get(
			telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA,
			{
				"InitialAudio": self.initial_audio,
				"InitialVideo": self.initial_video,
			},
		)

		self.GroupFlagsChanged(0, 0)
		self.MembersChanged(
			'', [self._conn.GetSelfHandle()], [], [], [contactHandle],
			0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE
		)

	def initial_audio(self):
		return False

	def initial_video(self):
		return False

	@gtk_toolbox.log_exception(_moduleLogger)
	def Close(self):
		self.close()

	def close(self):
		tp.ChannelTypeStreamedMedia.Close(self)
		self.remove_from_connection()
		if self.__cancelId is not None:
			gobject.source_remove(self.__cancelId)
			self.__cancelId = None

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
		contact = self._conn.get_handle_by_id(telepathy.constants.HANDLE_TYPE_CONTACT, contactId)
		assert self.__contactHandle == contact, "%r != %r" % (self.__contactHandle, contact)
		contactNumber = contact.phoneNumber

		self.CallStateChanged(self.__contactHandle, telepathy.constants.CHANNEL_CALL_STATE_RINGING)
		self.__cancelId = gobject.idle_add(self._on_cancel)
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
		return {self.__contactHandle: telepathy.constants.CHANNEL_CALL_STATE_FORWARDED}

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_cancel(self, *args):
		self.CallStateChanged(self.__contactHandle, telepathy.constants.CHANNEL_CALL_STATE_FORWARDED)
		self.close()
		self.__cancelId = None
		return False
