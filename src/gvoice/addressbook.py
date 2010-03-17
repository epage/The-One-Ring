#!/usr/bin/python


import logging

import util.coroutines as coroutines
import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class Addressbook(object):

	_RESPONSE_GOOD = 0
	_RESPONSE_BLOCKED = 3

	def __init__(self, backend, asyncPool):
		self._backend = backend
		self._numbers = {}
		self._asyncPool = asyncPool

		self.updateSignalHandler = coroutines.CoTee()

	def update(self, force=False):
		if not force and self._numbers:
			return
		self._asyncPool.add_task(
			self._backend.get_contacts,
			(),
			{},
			self._on_get_contacts,
			self._on_get_contacts_failed,
		)

	def _on_get_contacts(self, contacts):
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

	@misc_utils.log_exception(_moduleLogger)
	def _on_get_contacts_failed(self, error):
		_moduleLogger.error(error)

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
