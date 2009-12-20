import time
import datetime
import logging

import telepathy

import util.go_utils as gobject_utils
import util.coroutines as coroutines
import gtk_toolbox


_moduleLogger = logging.getLogger("channel.text")


class TextChannel(telepathy.server.ChannelTypeText):
	"""
	Look into implementing ChannelInterfaceMessages for rich text formatting
	"""

	def __init__(self, connection, h):
		telepathy.server.ChannelTypeText.__init__(self, connection, h)
		self._nextRecievedId = 0
		self._lastMessageTimestamp = datetime.datetime(1, 1, 1)

		self._otherHandle = h

		self._callback = coroutines.func_sink(
			coroutines.expand_positional(
				self._on_conversations_updated
			)
		)
		self._conn.session.conversations.updateSignalHandler.register_sink(
			self._callback
		)

		# The only reason there should be anything in the conversation is if
		# its new, so report it all
		try:
			mergedConversations = self._conn.session.conversations.get_conversation(self._contactKey)
		except KeyError:
			pass
		else:
			self._report_conversation(mergedConversations)

	@gtk_toolbox.log_exception(_moduleLogger)
	def Send(self, messageType, text):
		if messageType != telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
			raise telepathy.errors.NotImplemented("Unhandled message type: %r" % messageType)

		self._conn.session.backend.send_sms(self._otherHandle.phoneNumber, text)

		self.Sent(int(time.time()), messageType, text)

	@gtk_toolbox.log_exception(_moduleLogger)
	def Close(self):
		try:
			# Clear since the user has seen it all and it should start a new conversation
			self._conn.session.conversations.clear_conversation(self._contactKey)

			self._conn.session.conversations.updateSignalHandler.unregister_sink(
				self._callback
			)
		finally:
			telepathy.server.ChannelTypeText.Close(self)
			self.remove_from_connection()

	@property
	def _contactKey(self):
		contactKey = self._otherHandle.contactID, self._otherHandle.phoneNumber
		return contactKey

	@gobject_utils.async
	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_conversations_updated(self, conv, conversationIds):
		if self._contactKey not in conversationIds:
			return
		_moduleLogger.info("Incoming messages from %r for existing conversation" % (self._contactKey, ))
		mergedConversations = self._conn.session.conversations.get_conversation(self._contactKey)
		self._report_conversation(mergedConversations)

	def _report_conversation(self, mergedConversations):
		newConversations = mergedConversations.conversations
		newConversations = list(newConversations)
		lenMerged = len(newConversations)
		newConversations = self._filter_out_reported(newConversations)
		newConversations = list(newConversations)
		lenUnreported = len(newConversations)
		newConversations = self._filter_out_read(newConversations)
		newConversations = list(newConversations)
		lenUnread = len(newConversations)
		if not newConversations:
			_moduleLogger.info(
				"New messages for %r have already been read externally" % (self._contactKey, )
			)
			return
		_moduleLogger.debug("%s, %s, %s" % (lenMerged, lenUnreported, lenUnread))
		self._lastMessageTimestamp = newConversations[-1].time

		for newConversation in newConversations:
			for newMessage in newConversations.messages:
				if newMessage.name != "Me:":
					formattedMessage = self._format_message(newMessage)
					self._report_new_message(formattedMessage)

	def _filter_out_reported(self, conversations):
		return (
			conversation
			for conversation in conversations
			if self._lastMessageTimestamp < conversation.time
		)

	def _filter_out_read(self, conversations):
		return (
			conversation
			for conversation in conversations
			if not conversation.isRead and not conversation.isArchived
		)

	def _format_message(self, message):
		return " ".join(part.text.strip() for part in message.body)

	def _report_new_message(self, message):
		currentReceivedId = self._nextRecievedId

		timestamp = int(time.time())
		type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL

		_moduleLogger.info("Received message from User %r" % self._otherHandle)
		self.Received(currentReceivedId, timestamp, self._otherHandle, type, 0, message)

		self._nextRecievedId += 1
