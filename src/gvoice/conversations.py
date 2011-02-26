#!/usr/bin/python

from __future__ import with_statement

import datetime
import logging

try:
	import cPickle
	pickle = cPickle
except ImportError:
	import pickle

import constants
import util.coroutines as coroutines
import util.misc as misc_utils
import util.go_utils as gobject_utils


_moduleLogger = logging.getLogger(__name__)


class ConversationError(RuntimeError):

	pass


class Conversations(object):

	OLDEST_COMPATIBLE_FORMAT_VERSION = misc_utils.parse_version("0.8.0")

	def __init__(self, getter, asyncPool):
		self._get_raw_conversations = getter
		self._asyncPool = asyncPool
		self._conversations = {}
		self._loadedFromCache = False
		self._hasDoneUpdate = False

		self.updateSignalHandler = coroutines.CoTee()

	@property
	def _name(self):
		return repr(self._get_raw_conversations.__name__)

	def load(self, path):
		_moduleLogger.debug("%s Loading cache" % (self._name, ))
		assert not self._conversations
		try:
			with open(path, "rb") as f:
				fileVersion, fileBuild, convs = pickle.load(f)
		except (pickle.PickleError, IOError, EOFError, ValueError, Exception):
			_moduleLogger.exception("While loading for %s" % self._name)
			return

		if convs and misc_utils.compare_versions(
			self.OLDEST_COMPATIBLE_FORMAT_VERSION,
			misc_utils.parse_version(fileVersion),
		) <= 0:
			_moduleLogger.info("%s Loaded cache" % (self._name, ))
			self._conversations = convs
			self._loadedFromCache = True
		else:
			_moduleLogger.debug(
				"%s Skipping cache due to version mismatch (%s-%s)" % (
					self._name, fileVersion, fileBuild
				)
			)

	def save(self, path):
		_moduleLogger.info("%s Saving cache" % (self._name, ))
		if not self._conversations:
			_moduleLogger.info("%s Odd, no conversations to cache.  Did we never load the cache?" % (self._name, ))
			return

		try:
			dataToDump = (constants.__version__, constants.__build__, self._conversations)
			with open(path, "wb") as f:
				pickle.dump(dataToDump, f, pickle.HIGHEST_PROTOCOL)
		except (pickle.PickleError, IOError):
			_moduleLogger.exception("While saving for %s" % self._name)
		_moduleLogger.info("%s Cache saved" % (self._name, ))

	def update(self, force=False):
		if not force and self._conversations:
			return

		le = gobject_utils.AsyncLinearExecution(self._asyncPool, self._update)
		le.start()

	@misc_utils.log_exception(_moduleLogger)
	def _update(self):
		try:
			conversationResult = yield (
				self._get_raw_conversations,
				(),
				{},
			)
		except Exception:
			_moduleLogger.exception("%s While updating conversations" % (self._name, ))
			return

		oldConversationIds = set(self._conversations.iterkeys())

		updateConversationIds = set()
		conversations = list(conversationResult)
		conversations.sort()
		for conversation in conversations:
			key = misc_utils.normalize_number(conversation.number)
			try:
				mergedConversations = self._conversations[key]
			except KeyError:
				mergedConversations = MergedConversations()
				self._conversations[key] = mergedConversations

			if self._loadedFromCache or self._hasDoneUpdate:
				markAllAsRead = False
			else:
				markAllAsRead = True

			try:
				mergedConversations.append_conversation(conversation, markAllAsRead)
				isConversationUpdated = True
			except ConversationError, e:
				isConversationUpdated = False
			except AssertionError, e:
				_moduleLogger.debug("%s Skipping conversation for %r because '%s'" % (self._name, key, e))
				isConversationUpdated = False
			except RuntimeError, e:
				_moduleLogger.debug("%s Skipping conversation for %r because '%s'" % (self._name, key, e))
				isConversationUpdated = False

			if isConversationUpdated:
				updateConversationIds.add(key)

		for key in updateConversationIds:
			mergedConv = self._conversations[key]
			_moduleLogger.debug("%s \tUpdated %s" % (self._name, key))
			for conv in mergedConv.conversations:
				message = "%s \t\tUpdated %s (%r) %r %r %r" % (
					self._name, conv.id, conv.time, conv.isRead, conv.isArchived, len(conv.messages)
				)
				_moduleLogger.debug(message)

		if updateConversationIds:
			message = (self, updateConversationIds, )
			self.updateSignalHandler.stage.send(message)
		self._hasDoneUpdate = True

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

	def append_conversation(self, newConversation, markAllAsRead):
		self._validate(newConversation)
		for similarConversation in self._find_related_conversation(newConversation.id):
			self._update_previous_related_conversation(similarConversation, newConversation)
			self._remove_repeats(similarConversation, newConversation)

		# HACK: Because GV marks all messages as read when you reply it has
		# the following race:
		# 1. Get all messages
		# 2. Contact sends a text
		# 3. User sends a text marking contacts text as read
		# 4. Get all messages not returning text from step 2
		# This isn't a problem for voicemails but we don't know(?( enough.
		# So we hack around this by:
		# * We cache to disk the history of messages sent/received
		# * On first run we mark all server messages as read due to no cache
		# * If not first load or from cache (disk or in-memory) then it must be unread
		if newConversation.type != newConversation.TYPE_VOICEMAIL:
			if markAllAsRead:
				newConversation.isRead = True
			else:
				newConversation.isRead = False

		if newConversation.messages:
			# must not have had all items removed due to duplicates
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
			raise ConversationError("Conversations got out of order")

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


def filter_out_read(conversations):
	return (
		conversation
		for conversation in conversations
		if not conversation.isRead and not conversation.isArchived
	)


def is_message_from_self(message):
	return message.whoFrom == "Me:"


def filter_out_self(conversations):
	return (
		newConversation
		for newConversation in conversations
		if len(newConversation.messages) and any(
			not is_message_from_self(message)
			for message in newConversation.messages
		)
	)


class FilterOutReported(object):

	NULL_TIMESTAMP = datetime.datetime(1, 1, 1)

	def __init__(self):
		self._lastMessageTimestamp = self.NULL_TIMESTAMP

	def get_last_timestamp(self):
		return self._lastMessageTimestamp

	def __call__(self, conversations):
		filteredConversations = [
			conversation
			for conversation in conversations
			if self._lastMessageTimestamp < conversation.time
		]
		if filteredConversations and self._lastMessageTimestamp < filteredConversations[0].time:
			self._lastMessageTimestamp = filteredConversations[0].time
		return filteredConversations


def print_conversations(path):
	import pprint

	try:
		with open(path, "rb") as f:
			fileVersion, fileBuild, convs = pickle.load(f)
	except (pickle.PickleError, IOError, EOFError, ValueError):
		_moduleLogger.exception("")
	else:
		for key, value in convs.iteritems():
			convs[key] = value.to_dict()
		pprint.pprint((fileVersion, fileBuild))
		pprint.pprint(convs)
