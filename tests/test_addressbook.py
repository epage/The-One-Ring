from __future__ import with_statement

import logging

import sys
sys.path.append("../src")

import util.coroutines as coroutines

import gvoice


logging.basicConfig(level=logging.DEBUG)


class MockBackend(object):

	def __init__(self, contactsData):
		self.contactsData = contactsData

	def get_contacts(self):
		return (
			(i, contactData["name"])
			for (i, contactData) in enumerate(self.contactsData)
		)

	def get_contact_details(self, contactId):
		return self.contactsData[contactId]["details"]


def generate_update_callback(callbackData):

	@coroutines.func_sink
	@coroutines.expand_positional
	def callback(book, addedContacts, removedContacts, changedContacts):
		callbackData.append((book, addedContacts, removedContacts, changedContacts))

	return callback


def test_no_contacts():
	callbackData = []
	callback = generate_update_callback(callbackData)

	backend = MockBackend([])
	book = gvoice.addressbook.Addressbook(backend)
	book.updateSignalHandler.register_sink(callback)
	assert len(callbackData) == 0, "%r" % callbackData

	book.update()
	assert len(callbackData) == 0, "%r" % callbackData

	book.update(force=True)
	assert len(callbackData) == 0, "%r" % callbackData

	contacts = list(book.get_contacts())
	assert len(contacts) == 0


def test_one_contact_no_details():
	callbackData = []
	callback = generate_update_callback(callbackData)

	backend = MockBackend([
		{
			"name": "One",
			"details": [],
		},
	])
	book = gvoice.addressbook.Addressbook(backend)
	book.updateSignalHandler.register_sink(callback)
	assert len(callbackData) == 0, "%r" % callbackData

	contacts = list(book.get_contacts())
	assert len(contacts) == 1
	id = contacts[0]
	name = book.get_contact_name(id)
	assert name == backend.contactsData[id]["name"]

	book.update()
	assert len(callbackData) == 0, "%r" % callbackData

	book.update(force=True)
	assert len(callbackData) == 0, "%r" % callbackData

	contacts = list(book.get_contacts())
	assert len(contacts) == 1
	id = contacts[0]
	name = book.get_contact_name(id)
	assert name == backend.contactsData[id]["name"]

	contactDetails = list(book.get_contact_details(id))
	assert len(contactDetails) == 0


def test_one_contact_with_details():
	callbackData = []
	callback = generate_update_callback(callbackData)

	backend = MockBackend([
		{
			"name": "One",
			"details": [("Type A", "123"), ("Type B", "456"), ("Type C", "789")],
		},
	])
	book = gvoice.addressbook.Addressbook(backend)
	book.updateSignalHandler.register_sink(callback)
	assert len(callbackData) == 0, "%r" % callbackData

	contacts = list(book.get_contacts())
	assert len(contacts) == 1
	id = contacts[0]
	name = book.get_contact_name(id)
	assert name == backend.contactsData[id]["name"]

	book.update()
	assert len(callbackData) == 0, "%r" % callbackData

	book.update(force=True)
	assert len(callbackData) == 0, "%r" % callbackData

	contacts = list(book.get_contacts())
	assert len(contacts) == 1
	id = contacts[0]
	name = book.get_contact_name(id)
	assert name == backend.contactsData[id]["name"]

	contactDetails = list(book.get_contact_details(id))
	print "%r" % contactDetails
	assert len(contactDetails) == 3
	assert contactDetails[0][0] == "Type A"
	assert contactDetails[0][1] == "123"
	assert contactDetails[1][0] == "Type B"
	assert contactDetails[1][1] == "456"
	assert contactDetails[2][0] == "Type C"
	assert contactDetails[2][1] == "789"


def test_adding_a_contact():
	callbackData = []
	callback = generate_update_callback(callbackData)

	backend = MockBackend([
		{
			"name": "One",
			"details": [],
		},
	])
	book = gvoice.addressbook.Addressbook(backend)
	book.updateSignalHandler.register_sink(callback)
	assert len(callbackData) == 0, "%r" % callbackData

	book.update()
	assert len(callbackData) == 0, "%r" % callbackData

	book.update(force=True)
	assert len(callbackData) == 0, "%r" % callbackData

	backend.contactsData.append({
		"name": "Two",
		"details": [],
	})

	book.update()
	assert len(callbackData) == 0, "%r" % callbackData

	book.update(force=True)
	assert len(callbackData) == 1, "%r" % callbackData

	callbackBook, addedContacts, removedContacts, changedContacts = callbackData[0]
	assert callbackBook is book
	assert len(addedContacts) == 1
	assert 1 in addedContacts
	assert len(removedContacts) == 0
	assert len(changedContacts) == 0


def test_removing_a_contact():
	callbackData = []
	callback = generate_update_callback(callbackData)

	backend = MockBackend([
		{
			"name": "One",
			"details": [],
		},
	])
	book = gvoice.addressbook.Addressbook(backend)
	book.updateSignalHandler.register_sink(callback)
	assert len(callbackData) == 0, "%r" % callbackData

	book.update()
	assert len(callbackData) == 0, "%r" % callbackData

	book.update(force=True)
	assert len(callbackData) == 0, "%r" % callbackData

	del backend.contactsData[:]

	book.update()
	assert len(callbackData) == 0, "%r" % callbackData

	book.update(force=True)
	assert len(callbackData) == 1, "%r" % callbackData

	callbackBook, addedContacts, removedContacts, changedContacts = callbackData[0]
	assert callbackBook is book
	assert len(addedContacts) == 0
	assert len(removedContacts) == 1
	assert 0 in removedContacts
	assert len(changedContacts) == 0
