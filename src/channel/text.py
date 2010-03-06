import time
import logging

import telepathy

import tp
import util.coroutines as coroutines
import util.misc as misc_utils
import gvoice


_moduleLogger = logging.getLogger(__name__)


class TextChannel(tp.ChannelTypeText):

	def __init__(self, connection, manager, props, contactHandle):
		self.__manager = manager
		self.__props = props

		tp.ChannelTypeText.__init__(self, connection, manager, props)
		self.__nextRecievedId = 0
		self.__hasServerBeenPolled = False

		self.__otherHandle = contactHandle

		self.__callback = coroutines.func_sink(
			coroutines.expand_positional(
				self._on_conversations_updated
			)
		)
		self._conn.session.voicemails.updateSignalHandler.register_sink(
			self.__callback
		)
		self._conn.session.texts.updateSignalHandler.register_sink(
			self.__callback
		)

		self._filter_out_reported = gvoice.conversations.FilterOutReported()

		# The only reason there should be anything in the conversation is if
		# its new, so report it all
		try:
			mergedConversations = self._conn.session.voicemails.get_conversation(self._contactKey)
		except KeyError:
			_moduleLogger.debug("No voicemails in the conversation yet for %r" % (self._contactKey, ))
		else:
			self._report_conversation(mergedConversations)
		try:
			mergedConversations = self._conn.session.texts.get_conversation(self._contactKey)
		except KeyError:
			_moduleLogger.debug("No texts conversation yet for %r" % (self._contactKey, ))
		else:
			self._report_conversation(mergedConversations)

	@misc_utils.log_exception(_moduleLogger)
	def Send(self, messageType, text):
		if messageType != telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
			raise telepathy.errors.NotImplemented("Unhandled message type: %r" % messageType)

		if not self.__hasServerBeenPolled:
			# Hack: GV marks messages as read when they are replied to.  If GV
			# marks them as read than we ignore them.  So reduce the window for
			# them being marked as read.  Oh and Conversations already handles
			# it if the message was already part of a thread, so we can limit
			# this to if we are trying to start a thread.  You might say a
			# voicemail could be what is being replied to and that doesn't mean
			# anything.  Oh well.
			try:
				self._conn.session.texts.update(force=True)
			except Exception:
				_moduleLogger.exception(
					"Update failed when proactively checking for texts"
				)

		_moduleLogger.info("Sending message to %r" % (self.__otherHandle, ))
		self._conn.session.backend.send_sms([self.__otherHandle.phoneNumber], text)
		self._conn.session.textsStateMachine.reset_timers()

		self.Sent(int(time.time()), messageType, text)

	@misc_utils.log_exception(_moduleLogger)
	def Close(self):
		self.close()

	def close(self):
		_moduleLogger.debug("Closing text")
		self._conn.session.voicemails.updateSignalHandler.unregister_sink(
			self.__callback
		)
		self._conn.session.texts.updateSignalHandler.unregister_sink(
			self.__callback
		)
		self.__callback = None

		tp.ChannelTypeText.Close(self)
		self.remove_from_connection()

	@property
	def _contactKey(self):
		contactKey = self.__otherHandle.phoneNumber
		return contactKey

	@misc_utils.log_exception(_moduleLogger)
	def _on_conversations_updated(self, conv, conversationIds):
		if self._contactKey not in conversationIds:
			return
		_moduleLogger.debug("Incoming messages from %r for existing conversation" % (self._contactKey, ))
		mergedConversations = conv.get_conversation(self._contactKey)
		self._report_conversation(mergedConversations)

	def _report_conversation(self, mergedConversations):
		newConversations = mergedConversations.conversations
		if not newConversations:
			_moduleLogger.info(
				"No messages ended up existing for %r" % (self._contactKey, )
			)
			return

		# Can't filter out messages in a texting conversation that came in
		# before the last one sent because that creates a race condition of two
		# people sending at about the same time, which happens quite a bit
		newConversations = self._filter_out_reported(newConversations)
		newConversations = gvoice.conversations.filter_out_read(newConversations)
		newConversations = gvoice.conversations.filter_out_self(newConversations)
		newConversations = list(newConversations)
		if not newConversations:
			_moduleLogger.debug(
				"New messages for %r have already been read externally" % (self._contactKey, )
			)
			return

		messages = [
			newMessage
			for newConversation in newConversations
			for newMessage in newConversation.messages
			if not gvoice.conversations.is_message_from_self(newMessage)
		]
		if not messages:
			_moduleLogger.debug(
				"How did this happen for %r?" % (self._contactKey, )
			)
			return
		for newMessage in messages:
			formattedMessage = self._format_message(newMessage)
			self._report_new_message(formattedMessage)

		for conv in newConversations:
			conv.isRead = True
		self.__hasServerBeenPolled = True

	def _format_message(self, message):
		return " ".join(part.text.strip() for part in message.body)

	def _report_new_message(self, message):
		currentReceivedId = self.__nextRecievedId
		timestamp = int(time.time())
		type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL

		_moduleLogger.info("Received message from User %r" % self.__otherHandle)
		self.Received(currentReceivedId, timestamp, self.__otherHandle, type, 0, message)

		self.__nextRecievedId += 1
