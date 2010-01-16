#!/usr/bin/python


import logging

import util.coroutines as coroutines
import util.misc as util_misc


_moduleLogger = logging.getLogger("gvoice.addressbook")


class Addressbook(object):

	def __init__(self, backend):
		self._backend = backend
		self._contacts = {}

		self.updateSignalHandler = coroutines.CoTee()

	def update(self, force=False):
		if not force and self._contacts:
			return
		oldContacts = self._contacts
		oldContactIds = set(self.get_contact_ids())

		self._contacts = {}
		self._populate_contacts()
		newContactIds = set(self.get_contact_ids())

		addedContacts = newContactIds - oldContactIds
		removedContacts = oldContactIds - newContactIds
		changedContacts = set(
			contactId
			for contactId in newContactIds.intersection(oldContactIds)
			if self._has_contact_changed(contactId, oldContacts)
		)

		if addedContacts or removedContacts or changedContacts:
			message = self, addedContacts, removedContacts, changedContacts
			self.updateSignalHandler.stage.send(message)

	def get_contact_ids(self):
		return self._contacts.iterkeys()

	def get_contact_name(self, contactId):
		return self._contacts[contactId][0]

	def get_contact_details(self, contactId):
		return iter(self._contacts[contactId][1])

	def find_contacts_with_number(self, queryNumber):
		strippedQueryNumber = util_misc.normalize_number(queryNumber)
		for contactId, (contactName, contactDetails) in self._contacts.iteritems():
			for phoneType, number in contactDetails:
				if number == strippedQueryNumber:
					yield contactId

	def _populate_contacts(self):
		if self._contacts:
			return
		contacts = self._backend.get_contacts()
		for contactId, contactDetails in contacts:
			contactName = contactDetails["name"]
			contactNumbers = [
				(
					numberDetails.get("phoneType", "Mobile"),
					util_misc.normalize_number(numberDetails["phoneNumber"]),
				)
				for numberDetails in contactDetails["numbers"]
			]
			self._contacts[contactId] = (contactName, contactNumbers)

	def _has_contact_changed(self, contactId, oldContacts):
		oldContact = oldContacts[contactId]
		oldContactName = oldContact[0]
		oldContactDetails = oldContact[1]
		if oldContactName != self.get_contact_name(contactId):
			return True
		if not oldContactDetails:
			return False
		# if its already in the old cache, purposefully add it into the new cache
		return oldContactDetails != self.get_contact_details(contactId)
