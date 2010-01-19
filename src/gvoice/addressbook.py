#!/usr/bin/python


import logging

import util.coroutines as coroutines
import util.misc as util_misc


_moduleLogger = logging.getLogger("gvoice.addressbook")


class Addressbook(object):

	def __init__(self, backend):
		self._backend = backend
		self._numbers = {}

		self.updateSignalHandler = coroutines.CoTee()

	def update(self, force=False):
		if not force and self._numbers:
			return
		oldContacts = self._numbers
		oldContactNumbers = set(self.get_numbers())

		self._numbers = {}
		self._populate_contacts()
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
		return self._numbers[strippedNumber][0]

	def get_phone_type(self, strippedNumber):
		return self._numbers[strippedNumber][1]

	def _populate_contacts(self):
		if self._numbers:
			return
		contacts = self._backend.get_contacts()
		for contactId, contactDetails in contacts:
			contactName = contactDetails["name"]
			contactNumbers = (
				(
					numberDetails.get("phoneType", "Mobile"),
					util_misc.normalize_number(numberDetails["phoneNumber"]),
				)
				for numberDetails in contactDetails["numbers"]
			)
			self._numbers.update(
				(number, (contactName, phoneType))
				for (phoneType, number) in contactNumbers
			)
