#!/usr/bin/python

from __future__ import with_statement

import logging

try:
	import cPickle
	pickle = cPickle
except ImportError:
	import pickle

import constants
import util.coroutines as coroutines
import util.misc as util_misc


_moduleLogger = logging.getLogger("gvoice.conversations")


class Conversations(object):

	def __init__(self, getter):
		self._get_raw_conversations = getter
		self._conversations = {}

		self.updateSignalHandler = coroutines.CoTee()

	@property
	def _name(self):
		return repr(self._get_raw_conversations.__name__)

	def load(self, path):
		assert not self._conversations
		try:
			with open(path, "rb") as f:
				fileVersion, fileBuild, convs = pickle.load(f)
		except (pickle.PickleError, IOError):
			_moduleLogger.exception("While loading for %s" % self._name)
			return

		if fileVersion == constants.__version__ and fileBuild == constants.__build__:
			self._conversations = convs
		else:
			_moduleLogger.debug(
				"%s Skipping cache due to version mismatch (%s-%s)" % (self._name, fileVersion, fileBuild)
			)

	def save(self, path):
		try:
			dataToDump = (constants.__version__, constants.__build__, self._conversations)
			with open(path, "wb") as f:
				pickle.dump(dataToDump, f, pickle.HIGHEST_PROTOCOL)
		except (pickle.PickleError, IOError):
			_moduleLogger.exception("While saving for %s" % self._name)

	def update(self, force=False):
		if not force and self._conversations:
			return

		oldConversationIds = set(self._conversations.iterkeys())

		updateConversationIds = set()
		conversations = list(self._get_raw_conversations())
		conversations.sort()
		for conversation in conversations:
			key = util_misc.normalize_number(conversation.number)
			try:
				mergedConversations = self._conversations[key]
			except KeyError:
				mergedConversations = MergedConversations()
				self._conversations[key] = mergedConversations

			try:
				mergedConversations.append_conversation(conversation)
				isConversationUpdated = True
			except RuntimeError, e:
				if False:
					_moduleLogger.debug("%s Skipping conversation for %r because '%s'" % (self._name, key, e))
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
			_moduleLogger.info("%s Conversation never existed for %r" % (self._name, key, ))

	def clear_all(self):
		self._conversations.clear()


class MergedConversations(object):

	def __init__(self):
		self._conversations = []

	def append_conversation(self, newConversation):
		self._validate(newConversation)
		similarExist = False
		for similarConversation in self._find_related_conversation(newConversation.id):
			self._update_previous_related_conversation(similarConversation, newConversation)
			self._remove_repeats(similarConversation, newConversation)
			similarExist = True
		if similarExist:
			# Hack to reduce a race window with GV marking messages as read
			# because it thinks we replied when really we replied to the
			# previous message.  Clients of this code are expected to handle
			# this gracefully.  Other race conditions may exist but clients are
			# responsible for them
			if newConversation.messages:
				newConversation.isRead = False
			else:
				newConversation.isRead = True
		self._conversations.append(newConversation)

	def to_dict(self):
		selfDict = {}
		selfDict["conversations"] = [conv.to_dict() for conv in self._conversations]
		return selfDict

	@property
	def conversations(self):
		return self._conversations

	def _validate(self, newConversation):
		if not self._conversations:
			return

		for constantField in ("number", ):
			assert getattr(self._conversations[0], constantField) == getattr(newConversation, constantField), "Constant field changed, soemthing is seriously messed up: %r v %r" % (
				getattr(self._conversations[0], constantField),
				getattr(newConversation, constantField),
			)

		if newConversation.time <= self._conversations[-1].time:
			raise RuntimeError("Conversations got out of order")

	def _find_related_conversation(self, convId):
		similarConversations = (
			conversation
			for conversation in self._conversations
			if conversation.id == convId
		)
		return similarConversations

	def _update_previous_related_conversation(self, relatedConversation, newConversation):
		for commonField in ("isSpam", "isTrash", "isArchived"):
			newValue = getattr(newConversation, commonField)
			setattr(relatedConversation, commonField, newValue)

	def _remove_repeats(self, relatedConversation, newConversation):
		newConversationMessages = newConversation.messages
		newConversation.messages = [
			newMessage
			for newMessage in newConversationMessages
			if newMessage not in relatedConversation.messages
		]
		_moduleLogger.debug("Found %d new messages in conversation %s (%d/%d)" % (
			len(newConversationMessages) - len(newConversation.messages),
			newConversation.id,
			len(newConversation.messages),
			len(newConversationMessages),
		))
		assert 0 < len(newConversation.messages), "Everything shouldn't have been removed"
