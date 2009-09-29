import time
import weakref

import telepathy


class TextChannel(telepathy.server.ChannelTypeText):
	"""
	Look into implementing ChannelInterfaceMessages for rich text formatting
	"""

	def __init__(self, connection):
		self._recv_id = 0
		self._connRef = weakref.ref(connection)

		telepathy.server.ChannelTypeText.__init__(self, connection, None)

		self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD, 0)
		self.__add_initial_participants()

	def Send(self, messageType, text):
		if messageType == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
			pass
		else:
			raise telepathy.NotImplemented("Unhandled message type")
		self.Sent(int(time.time()), messageType, text)

	def Close(self):
		self._conversation.leave()
		telepathy.server.ChannelTypeText.Close(self)
		self.remove_from_connection()
