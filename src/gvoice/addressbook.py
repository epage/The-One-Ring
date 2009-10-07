#!/usr/bin/python


import logging

import util.coroutines as coroutines


_moduleLogger = logging.getLogger("gvoice.addressbook")


class Addressbook(object):

	def __init__(self, backend):
		self._backend = backend
		self._contacts = {}
		self._addedContacts = set()
		self._removedContacts = set()
		self._changedContacts = set()

		self.updateSignalHandler = coroutines.CoTee()
		self.update()

	def update(self, force=False):
		if not force and self._contacts:
			return
		oldContacts = self._contacts
		oldContactIds = set(self.get_contacts())

		self._contacts = {}
		self._populate_contacts()
		newContactIds = set(self.get_contacts())

		self._addedContacts = newContactIds - oldContactIds
		self._removedContacts = oldContactIds - newContactIds
		self._changedContacts = set(
			contactId
			for contactId in newContactIds.intersection(oldContactIds)
			if self._has_contact_changed(contactId, oldContacts)
		)

		if self._addedContacts or self._removedContacts or self._changedContacts:
			message = self, self._addedContacts, self._removedContacts, self._changedContacts
			self.updateSignalHandler.stage.send(message)

	def get_contacts(self):
		return self._contacts.iterkeys()

	def get_contact_name(self, contactId):
		return self._contacts[contactId][0]

	def get_contact_details(self, contactId):
		self._populate_contact_details(contactId)
		return self._get_contact_details(contactId)

	def _populate_contacts(self):
		if self._contacts:
			return
		contacts = self._backend.get_contacts()
		for contactId, contactName in contacts:
			self._contacts[contactId] = (contactName, [])

	def _populate_contact_details(self, contactId):
		if self._get_contact_details(contactId):
			return
		self._get_contact_details(contactId).extend(
			self._backend.get_contact_details(contactId)
		)

	def _get_contact_details(self, contactId):
		return self._contacts[contactId][1]

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
