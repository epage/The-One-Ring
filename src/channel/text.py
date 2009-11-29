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

		self._conn.session.conversations.updateSignalHandler.register_sink(
			self._on_message_received
		)

		# The only reason there should be anything in the conversation is if
		# its new, so report it all
		try:
			conversation = self._conn.session.conversations[self._contactKey]
		except KeyError:
			pass
		else:
			self._report_conversation(conversation)

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
			self._conn.session.clear_conversation(self._contactKey)

			self._conn.session.conversations.updateSignalHandler.unregister_sink(
				self._on_message_received
			)
		finally:
			telepathy.server.ChannelTypeText.Close(self)
			self.remove_from_connection()

	@property
	def _contactKey(self):
		contactKey = self._otherHandle.contactID, self._otherHandle.phoneNumber
		return contactKey

	@coroutines.func_sink
	@coroutines.expand_positional
	@gobject_utils.async
	def _on_conversations_updated(self, conversationIds):
		if self._contactKey not in conversationIds:
			return
		conversation = self._conn.session.conversations[self._contactKey]
		self._report_conversation(conversation)

	def _report_conversation(self, conversation):
		completeMessageHistory = conversation["messageParts"]
		messages = self._filter_seen_messages(completeMessageHistory)
		self._lastMessageTimestamp = messages[-1][0]
		formattedMessage = self._format_messages(messages)
		self._report_new_message(formattedMessage)

	def _filter_seen_messages(self, messages):
		return (
			message
			for message in messages
			if self._lastMessageTimestamp < message[0]
		)

	def _format_messages(self, messages):
		return "\n".join(message[1] for message in messages)

	def _report_new_message(self, message):
		currentReceivedId = self._nextRecievedId

		timestamp = int(time.time())
		type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
		message = message.content

		_moduleLogger.info("Received message from User %r" % self._otherHandle)
		self.Received(id, timestamp, self._otherHandle, type, 0, message)

		self._nextRecievedId += 1
