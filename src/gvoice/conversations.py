#!/usr/bin/python


import logging

import util.coroutines as coroutines

import backend


_moduleLogger = logging.getLogger("gvoice.conversations")


class Conversations(object):

	def __init__(self, backend):
		self._backend = backend
		self._conversations = {}

		self.updateSignalHandler = coroutines.CoTee()
		self.update()

	def update(self, force=False):
		if not force and self._conversations:
			return

		oldConversationIds = set(self._conversations.iterkeys())

		updateConversationIds = set()
		messages = self._backend.get_messages()
		sortedMessages = backend.sort_messages(messages)
		for messageData in sortedMessages:
			key = messageData["contactId"], messageData["number"]
			try:
				conversation = self._conversations[key]
				isNewConversation = False
			except KeyError:
				conversation = Conversation(self._backend, messageData)
				self._conversations[key] = conversation
				isNewConversation = True

			if isNewConversation:
				# @todo see if this has issues with a user marking a item as unread/unarchive?
				isConversationUpdated = True
			else:
				isConversationUpdated = conversation.merge_conversation(messageData)

			if isConversationUpdated:
				updateConversationIds.add(key)

		if updateConversationIds:
			message = (self, updateConversationIds, )
			self.updateSignalHandler.stage.send(message)

	def get_conversations(self):
		return self._conversations.iterkeys()

	def get_conversation(self, key):
		return self._conversations[key]


class Conversation(object):

	def __init__(self, backend, data):
		self._backend = backend
		self._data = dict((key, value) for (key, value) in data.iteritems())

		# confirm we have a list
		self._data["messageParts"] = list(
			self._append_time(message, self._data["time"])
			for message in self._data["messageParts"]
		)

	def __getitem__(self, key):
		return self._data[key]

	def merge_conversation(self, moreData):
		"""
		@returns True if there was content to merge (new messages arrived
		rather than being a duplicate)

		@warning This assumes merges are done in chronological order
		"""
		for constantField in ("contactId", "number"):
			assert self._data[constantField] == moreData[constantField], "Constant field changed, soemthing is seriously messed up: %r v %r" % (self._data, moreData)

		if moreData["time"] < self._data["time"]:
			# If its older, assuming it has nothing new to report
			return False

		for preferredMoreField in ("id", "name", "time", "relTime", "prettyNumber", "location"):
			preferredFieldValue = moreData[preferredMoreField]
			if preferredFieldValue:
				self._data[preferredMoreField] = preferredFieldValue

		messageAppended = False

		messageParts = self._data["messageParts"]
		for message in moreData["messageParts"]:
			messageWithTimestamp = self._append_time(message, moreData["time"])
			if messageWithTimestamp not in messageParts:
				messageParts.append(messageWithTimestamp)
				messageAppended = True

		return messageAppended

	@staticmethod
	def _append_time(message, exactWhen):
		whoFrom, message, when = message
		return whoFrom, message, when, exactWhen
