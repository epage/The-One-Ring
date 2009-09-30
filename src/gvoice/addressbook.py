#!/usr/bin/python


import logging


_moduleLogger = logging.getLogger("gvoice.addressbook")


class Addressbook(object):

	def __init__(self, backend):
		self._backend = backend
		self._contacts = {}

	def clear_cache(self):
		self._contacts.clear()

	def get_contacts(self):
		self._populate_contacts()
		return self._contacts.iterkeys()

	def get_contact_details(self, contactId):
		self._populate_contacts()
		self._populate_contact_details(contactId)
		return self._contacts[contactId]

	def _populate_contacts(self):
		if self._contacts:
			return
		contacts = self._backend.get_contacts()
		for contactId, contactName in contacts:
			self._contacts[contactId] = None

	def _populate_contact_details(self, contactId):
		if self._contacts[contactId] is not None:
			return
		self._contacts[contactId] = self._backend.get_contact_details(contactId)
