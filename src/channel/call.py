import logging

import dbus
import telepathy

import tp
import util.go_utils as gobject_utils
import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class CallChannel(
		tp.ChannelTypeStreamedMedia,
		tp.ChannelInterfaceCallState,
		tp.ChannelInterfaceGroup,
	):

	def __init__(self, connection, manager, props, contactHandle):
		self.__manager = manager
		self.__props = props
		self._delayedClose = gobject_utils.Timeout(self._on_close_requested)

		if telepathy.interfaces.CHANNEL_INTERFACE + '.InitiatorHandle' in props:
			self._initiator = connection.get_handle_by_id(
				telepathy.HANDLE_TYPE_CONTACT,
				props[telepathy.interfaces.CHANNEL_INTERFACE + '.InitiatorHandle'],
			)
		elif telepathy.interfaces.CHANNEL_INTERFACE + '.InitiatorID' in props:
			self._initiator = connection.get_handle_by_name(
				telepathy.HANDLE_TYPE_CONTACT,
				props[telepathy.interfaces.CHANNEL_INTERFACE + '.InitiatorHandle'],
			)
		else:
			# Maemo 5 seems to require InitiatorHandle/InitiatorID to be set
			# even though I can't find them in the dbus spec.  I think its
			# generally safe to assume that its locally initiated if not
			# specified.  Specially for The One Ring, its always locally
			# initiated
			_moduleLogger.warning('InitiatorID or InitiatorHandle not set on new channel, assuming locally initiated')
			self._initiator = connection.GetSelfHandle()

		tp.ChannelTypeStreamedMedia.__init__(self, connection, manager, props)
		tp.ChannelInterfaceCallState.__init__(self)
		tp.ChannelInterfaceGroup.__init__(self)
		self.__contactHandle = contactHandle
		self.__calledNumer = None

		self._implement_property_get(
			telepathy.interfaces.CHANNEL_INTERFACE,
			{
				'InitiatorHandle': lambda: dbus.UInt32(self._initiator.id),
				'InitiatorID': lambda: self._initiator.name,
			},
		)
		self._add_immutables({
			'InitiatorHandle': telepathy.interfaces.CHANNEL_INTERFACE,
			'InitiatorID': telepathy.interfaces.CHANNEL_INTERFACE,
		})
		self._implement_property_get(
			telepathy.interfaces.CHANNEL_INTERFACE_GROUP,
			{
				'LocalPendingMembers': lambda: self.GetLocalPendingMembersWithInfo()
			},
		)
		self._implement_property_get(
			telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA,
			{
				"InitialAudio": self.initial_audio,
				"InitialVideo": self.initial_video,
			},
		)
		self._add_immutables({
			'InitialAudio': telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA,
			'InitialVideo': telepathy.interfaces.CHANNEL_TYPE_STREAMED_MEDIA,
		})

		self.GroupFlagsChanged(0, 0)
		self.MembersChanged(
			'', [self._conn.GetSelfHandle()], [], [], [contactHandle],
			0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE
		)

	def initial_audio(self):
		return False

	def initial_video(self):
		return False

	@misc_utils.log_exception(_moduleLogger)
	def Close(self):
		self.close()

	def close(self):
		_moduleLogger.debug("Closing call")
		tp.ChannelTypeStreamedMedia.Close(self)
		self.remove_from_connection()
		if self.__calledNumer is not None:
			self._conn.session.backend.cancel(self.__calledNumer)
		self._delayedClose.cancel()

	@misc_utils.log_exception(_moduleLogger)
	def GetLocalPendingMembersWithInfo(self):
		info = dbus.Array([], signature="(uuus)")
		for member in self._local_pending:
			info.append((member, self._handle, 0, ''))
		return info

	@misc_utils.log_exception(_moduleLogger)
	def AddMembers(self, handles, message):
		_moduleLogger.info("Add members %r: %s" % (handles, message))
		for handle in handles:
			if handle == int(self.GetSelfHandle()) and self.GetSelfHandle() in self._local_pending:
				_moduleLogger.info("Technically the user just accepted the call")

	@misc_utils.log_exception(_moduleLogger)
	def RemoveMembers(self, handles, message):
		_moduleLogger.info("Remove members (no-op) %r: %s" % (handles, message))

	@misc_utils.log_exception(_moduleLogger)
	def RemoveMembersWithReason(self, handles, message, reason):
		_moduleLogger.info("Remove members (no-op) %r: %s (%i)" % (handles, message, reason))

	@misc_utils.log_exception(_moduleLogger)
	def ListStreams(self):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia
		"""
		return ()

	@misc_utils.log_exception(_moduleLogger)
	def RemoveStreams(self, streams):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia
		"""
		raise telepathy.errors.NotImplemented("Cannot remove a stream")

	@misc_utils.log_exception(_moduleLogger)
	def RequestStreamDirection(self, stream, streamDirection):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia

		@note Since streams are short lived, not bothering to implement this
		"""
		_moduleLogger.info("A request was made to change the stream direction")
		raise telepathy.errors.NotImplemented("Cannot change directions")

	@misc_utils.log_exception(_moduleLogger)
	def RequestStreams(self, contactId, streamTypes):
		"""
		For org.freedesktop.Telepathy.Channel.Type.StreamedMedia

		@returns [(Stream ID, contact, stream type, stream state, stream direction, pending send flags)]
		"""
		contact = self._conn.get_handle_by_id(telepathy.constants.HANDLE_TYPE_CONTACT, contactId)
		assert self.__contactHandle == contact, "%r != %r" % (self.__contactHandle, contact)
		contactNumber = contact.phoneNumber

		self.__calledNumer = contactNumber
		self.CallStateChanged(self.__contactHandle, telepathy.constants.CHANNEL_CALL_STATE_RINGING)
		self._conn.session.backend.call(contactNumber)
		self._delayedClose.start(seconds=5)
		self.CallStateChanged(self.__contactHandle, telepathy.constants.CHANNEL_CALL_STATE_FORWARDED)

		streamId = 0
		streamState = telepathy.constants.MEDIA_STREAM_STATE_CONNECTED
		streamDirection = telepathy.constants.MEDIA_STREAM_DIRECTION_BIDIRECTIONAL
		pendingSendFlags = telepathy.constants.MEDIA_STREAM_PENDING_REMOTE_SEND
		return [(streamId, contact, streamTypes[0], streamState, streamDirection, pendingSendFlags)]

	@misc_utils.log_exception(_moduleLogger)
	def GetCallStates(self):
		"""
		For org.freedesktop.Telepathy.Channel.Interface.CallState

		Get the current call states for all contacts involved in this call. 
		@returns {Contact: telepathy.constants.CHANNEL_CALL_STATE_*}
		"""
		return {self.__contactHandle: telepathy.constants.CHANNEL_CALL_STATE_FORWARDED}

	@misc_utils.log_exception(_moduleLogger)
	def _on_close_requested(self, *args):
		_moduleLogger.debug("Cancel now disallowed")
		self.__calledNumer = None
		self.close()
