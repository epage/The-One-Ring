import time
import logging

import telepathy

import gtk_toolbox
import handle


_moduleLogger = logging.getLogger("channel.text")


class TextChannel(telepathy.server.ChannelTypeText):
	"""
	Look into implementing ChannelInterfaceMessages for rich text formatting
	"""

	def __init__(self, connection, h):
		telepathy.server.ChannelTypeText.__init__(self, connection, h)
		self._nextRecievedId = 0

		self._otherHandle = h

	@gtk_toolbox.log_exception(_moduleLogger)
	def Send(self, messageType, text):
		if messageType != telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
			raise telepathy.errors.NotImplemented("Unhandled message type: %r" % messageType)

		self._conn.session.backend.send_sms(self._otherHandle.phoneNumber, text)

		self.Sent(int(time.time()), messageType, text)

	@gtk_toolbox.log_exception(_moduleLogger)
	def Close(self):
		telepathy.server.ChannelTypeText.Close(self)
		self.remove_from_connection()

	def _on_message_received(self, contactId, contactNumber, message):
		"""
		@todo Attatch this to receiving a message signal
		"""
		currentReceivedId = self._nextRecievedId

		timestamp = int(time.time())
		h = handle.create_handle(self._conn, "contact", contactId, contactNumber)
		type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
		message = message.content

		_moduleLogger.info("Received message from User %r" % h)
		self.Received(id, timestamp, h, type, 0, message)

		self._nextRecievedId += 1
