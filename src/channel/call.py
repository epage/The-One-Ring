import logging

import telepathy

import gtk_toolbox
import handle


_moduleLogger = logging.getLogger("channel.call")


class CallChannel(
		telepathy.server.ChannelTypeStreamedMedia,
		telepathy.server.ChannelInterfaceCallState,
		telepathy.server.ChannelInterfaceGroup,
	):

	def __init__(self, connection, manager, props, contactHandle):
		self.__manager = manager
		self.__props = props

		try:
			# HACK Older python-telepathy way
			telepathy.server.ChannelTypeStreamedMedia.__init__(self, connection, None)
			self._requested = props[telepathy.interfaces.CHANNEL_INTERFACE + '.Requested']
			self._implement_property_get(
				telepathy.interfaces.CHANNEL_INTERFACE,
				{"Requested": lambda: self._requested}
			)
		except TypeError:
			# HACK Newer python-telepathy way
			telepathy.server.ChannelTypeStreamedMedia.__init__(self, connection, manager, props)
		telepathy.server.ChannelInterfaceCallState.__init__(self)
		telepathy.server.ChannelInterfaceGroup.__init__(self)
		self.__contactHandle = contactHandle
		self._implement_property_get(
			telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA,
			{
				"InitialAudio": self.initial_audio,
				"InitialVideo": self.initial_video,
			},
		)

	def initial_audio(self):
		return False

	def initial_video(self):
		return False

	def get_props(self):
		# HACK Older python-telepathy doesn't provide this
		_immutable_properties = {
			'ChannelType': telepathy.server.interfaces.CHANNEL_INTERFACE,
			'TargetHandle': telepathy.server.interfaces.CHANNEL_INTERFACE,
			'Interfaces': telepathy.server.interfaces.CHANNEL_INTERFACE,
			'TargetHandleType': telepathy.server.interfaces.CHANNEL_INTERFACE,
			'TargetID': telepathy.server.interfaces.CHANNEL_INTERFACE,
			'Requested': telepathy.server.interfaces.CHANNEL_INTERFACE
		}
		props = dict()
		for prop, iface in _immutable_properties.items():
			props[iface + '.' + prop] = \
				self._prop_getters[iface][prop]()
		return props

	@gtk_toolbox.log_exception(_moduleLogger)
	def Close(self):
		self.close()

	def close(self):
		telepathy.server.ChannelTypeStreamedMedia.Close(self)
		if self.__manager.channel_exists(self.__props):
			# HACK Older python-telepathy requires doing this manually
			self.__manager.remove_channel(self)
		self.remove_from_connection()

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
		contact = self._conn.handle(telepathy.constants.HANDLE_TYPE_CONTACT, contactId)
		assert self.__contactHandle == contact, "%r != %r" % (self.__contactHandle, contact)
		contactId, contactNumber = handle.ContactHandle.from_handle_name(contact.name)

		self.CallStateChanged(self.__contactHandle, telepathy.constants.CHANNEL_CALL_STATE_RINGING)
		self._conn.session.backend.call(contactNumber)
		self.CallStateChanged(self.__contactHandle, telepathy.constants.CHANNEL_CALL_STATE_FORWARDED)

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
