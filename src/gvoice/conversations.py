#!/usr/bin/python


import logging

import util.coroutines as coroutines


_moduleLogger = logging.getLogger("gvoice.conversations")


class Conversations(object):

	def __init__(self, backend):
		self._backend = backend
		self._conversations = {}

		self.updateSignalHandler = coroutines.CoTee()

	def update(self, force=False):
		if not force and self._conversations:
			return

		oldConversationIds = set(self._conversations.iterkeys())

		updateConversationIds = set()
		conversations = list(self._backend.get_conversations())
		conversations.sort()
		for conversation in conversations:
			key = conversation.contactId, conversation.number
			try:
				mergedConversations = self._conversations[key]
			except KeyError:
				mergedConversations = MergedConversations()
				self._conversations[key] = mergedConversations

			try:
				mergedConversations.append_conversation(conversation)
				isConversationUpdated = True
			except RuntimeError:
				isConversationUpdated = False

			if isConversationUpdated:
				updateConversationIds.add(key)

		if updateConversationIds:
			message = (self, updateConversationIds, )
			self.updateSignalHandler.stage.send(message)

	def get_conversations(self):
		return self._conversations.iterkeys()

	def get_conversation(self, key):
		return self._conversations[key]

	def clear_conversation(self, key):
		try:
			del self._conversations[key]
		except KeyError:
			_moduleLogger.info("Conversation never existed for %r" % (key,))

	def clear_all(self):
		self._conversations.clear()


class MergedConversations(object):

	def __init__(self):
		self._conversations = []

	def append_conversation(self, newConversation):
		self._validate(newConversation)
		self._remove_repeats(newConversation)
		self._conversations.append(newConversation)

	@property
	def conversations(self):
		return self._conversations

	def _validate(self, newConversation):
		if not self._conversations:
			return

		for constantField in ("contactId", "number"):
			assert getattr(self._conversations[0], constantField) == getattr(newConversation, constantField), "Constant field changed, soemthing is seriously messed up: %r v %r" % (
				getattr(self._conversations[0], constantField),
				getattr(newConversation, constantField),
			)

		if newConversation.time <= self._conversations[-1].time:
			raise RuntimeError("Conversations got out of order")

	def _remove_repeats(self, newConversation):
		similarConversations = [
			conversation
			for conversation in self._conversations
			if conversation.id == newConversation.id
		]

		for similarConversation in similarConversations:
			for commonField in ("isRead", "isSpam", "isTrash", "isArchived"):
				newValue = getattr(newConversation, commonField)
				setattr(similarConversation, commonField, newValue)

			newConversation.messages = [
				newMessage
				for newMessage in newConversation.messages
				if newMessage not in similarConversation.messages
			]
			assert 0 < len(newConversation.messages), "Everything shouldn't have been removed"
