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
import util.misc as misc_utils
import util.go_utils as gobject_utils


_moduleLogger = logging.getLogger(__name__)


class Addressbook(object):

	_RESPONSE_GOOD = 0
	_RESPONSE_BLOCKED = 3

	OLDEST_COMPATIBLE_FORMAT_VERSION = misc_utils.parse_version("0.8.0")

	def __init__(self, backend, asyncPool):
		self._backend = backend
		self._numbers = {}
		self._asyncPool = asyncPool

		self.updateSignalHandler = coroutines.CoTee()

	def load(self, path):
		_moduleLogger.debug("Loading cache")
		assert not self._numbers
		try:
			with open(path, "rb") as f:
				fileVersion, fileBuild, contacts = pickle.load(f)
		except (pickle.PickleError, IOError, EOFError, ValueError, Exception):
			_moduleLogger.exception("While loading")
			return

		if contacts and misc_utils.compare_versions(
			self.OLDEST_COMPATIBLE_FORMAT_VERSION,
			misc_utils.parse_version(fileVersion),
		) <= 0:
			_moduleLogger.info("Loaded cache")
			self._numbers = contacts
			self._loadedFromCache = True
		else:
			_moduleLogger.debug(
				"Skipping cache due to version mismatch (%s-%s)" % (
					fileVersion, fileBuild
				)
			)

	def save(self, path):
		_moduleLogger.info("Saving cache")
		if not self._numbers:
			_moduleLogger.info("Odd, no conversations to cache.  Did we never load the cache?")
			return

		try:
			dataToDump = (constants.__version__, constants.__build__, self._numbers)
			with open(path, "wb") as f:
				pickle.dump(dataToDump, f, pickle.HIGHEST_PROTOCOL)
		except (pickle.PickleError, IOError):
			_moduleLogger.exception("While saving for %s" % self._name)
		_moduleLogger.info("Cache saved")

	def update(self, force=False):
		if not force and self._numbers:
			return

		le = gobject_utils.AsyncLinearExecution(self._asyncPool, self._update)
		le.start()

	@misc_utils.log_exception(_moduleLogger)
	def _update(self):
		try:
			contacts = yield (
				self._backend.get_contacts,
				(),
				{},
			)
		except Exception:
			_moduleLogger.exception("While updating the addressbook")
			return

		oldContacts = self._numbers
		oldContactNumbers = set(self.get_numbers())

		self._numbers = self._populate_contacts(contacts)
		newContactNumbers = set(self.get_numbers())

		addedContacts = newContactNumbers - oldContactNumbers
		removedContacts = oldContactNumbers - newContactNumbers
		changedContacts = set(
			contactNumber
			for contactNumber in newContactNumbers.intersection(oldContactNumbers)
			if self._numbers[contactNumber] != oldContacts[contactNumber]
		)

		if addedContacts or removedContacts or changedContacts:
			message = self, addedContacts, removedContacts, changedContacts
			self.updateSignalHandler.stage.send(message)

	def get_numbers(self):
		return self._numbers.iterkeys()

	def get_contact_name(self, strippedNumber):
		"""
		@throws KeyError if contact not in list (so client can choose what to display)
		"""
		return self._numbers[strippedNumber][0]

	def get_phone_type(self, strippedNumber):
		try:
			return self._numbers[strippedNumber][1]
		except KeyError:
			return "unknown"

	def is_blocked(self, strippedNumber):
		try:
			return self._numbers[strippedNumber][2]["response"] == self._RESPONSE_BLOCKED
		except KeyError:
			return False

	def _populate_contacts(self, contacts):
		numbers = {}
		for contactId, contactDetails in contacts:
			contactName = contactDetails["name"]
			contactNumbers = (
				(
					misc_utils.normalize_number(numberDetails["phoneNumber"]),
					numberDetails.get("phoneType", "Mobile"),
				)
				for numberDetails in contactDetails["numbers"]
			)
			numbers.update(
				(number, (contactName, phoneType, contactDetails))
				for (number, phoneType) in contactNumbers
			)
		return numbers


def print_addressbook(path):
	import pprint

	try:
		with open(path, "rb") as f:
			fileVersion, fileBuild, contacts = pickle.load(f)
	except (pickle.PickleError, IOError, EOFError, ValueError):
		_moduleLogger.exception("")
	else:
		pprint.pprint((fileVersion, fileBuild))
		pprint.pprint(contacts)
