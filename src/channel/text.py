import time
import logger

import telepathy

import handle


_moduleLogger = logger.getLogger("channel.text")


class TextChannel(telepathy.server.ChannelTypeText):
	"""
	Look into implementing ChannelInterfaceMessages for rich text formatting
	"""

	def __init__(self, connection):
		h = None
		telepathy.server.ChannelTypeText.__init__(self, connection, h)
		self._nextRecievedId = 0

		handles = []
		# @todo Populate participants
		self.MembersChanged('', handles, [], [], [],
				0, telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE)

	def Send(self, messageType, text):
		if messageType != telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
			raise telepathy.NotImplemented("Unhandled message type")
		# @todo implement sending message
		self.Sent(int(time.time()), messageType, text)

	def Close(self):
		telepathy.server.ChannelTypeText.Close(self)
		self.remove_from_connection()

	def _on_message_received(self, sender, message):
		"""
		@todo Attatch this to receiving a message
		"""
		currentReceivedId = self._nextRecievedId

		timestamp = int(time.time())
		h = handle.create_handle(self._conn, "contact", sender.account)
		type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
		message = message.content

		_moduleLogger.info("Received message from User %r" % h)
		self.Received(id, timestamp, h, type, 0, message)

		self._nextRecievedId += 1
