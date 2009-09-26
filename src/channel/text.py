import time
import weakref

import telepathy

import handle


class TheOneRingChannelText(
		telepathy.server.ChannelTypeText,
		telepathy.server.ChannelInterfaceGroup,
		telepathy.server.ChannelInterfaceChatState
	):

	def __init__(self, connection, conversation):
		self._recv_id = 0
		self._conversation = conversation
		self._conn_ref = weakref.ref(connection)

		telepathy.server.ChannelTypeText.__init__(self, connection, None)
		telepathy.server.ChannelInterfaceGroup.__init__(self)
		telepathy.server.ChannelInterfaceChatState.__init__(self)

		self.GroupFlagsChanged(telepathy.CHANNEL_GROUP_FLAG_CAN_ADD, 0)
		self.__add_initial_participants()

	def SetChatState(self, state):
		if state == telepathy.CHANNEL_CHAT_STATE_COMPOSING:
			self._conversation.send_typing_notification()
		h = handle.create_handle(self._conn_ref(), 'self')
		self.ChatStateChanged(h, state)

	def Send(self, messageType, text):
		if messageType == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
			self._conversation.send_text_message(text)
		elif messageType == telepathy.CHANNEL_TEXT_MESSAGE_TYPE_ACTION and text == u"nudge":
			self._conversation.send_nudge()
		else:
			raise telepathy.NotImplemented("Unhandled message type")
		self.Sent(int(time.time()), messageType, text)

	def Close(self):
		self._conversation.leave()
		telepathy.server.ChannelTypeText.Close(self)
		self.remove_from_connection()
