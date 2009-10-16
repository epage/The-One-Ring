from __future__ import with_statement

import datetime
import logging

import sys
sys.path.append("../src")

import util.coroutines as coroutines

import gvoice


logging.basicConfig(level=logging.DEBUG)


class MockBackend(object):

	def __init__(self, conversationsData):
		self.conversationsData = conversationsData

	def get_messages(self):
		return self.conversationsData


def generate_update_callback(callbackData):

	@coroutines.func_sink
	@coroutines.expand_positional
	def callback(conversations, updatedIds):
		callbackData.append((conversations, updatedIds))

	return callback


def test_no_conversations():
	callbackData = []
	callback = generate_update_callback(callbackData)

	backend = MockBackend([])
	conversings = gvoice.conversations.Conversations(backend)
	conversings.updateSignalHandler.register_sink(callback)
	assert len(callbackData) == 0, "%r" % callbackData

	conversings.update()
	assert len(callbackData) == 0, "%r" % callbackData

	conversings.update(force=True)
	assert len(callbackData) == 0, "%r" % callbackData

	contacts = list(conversings.get_conversations())
	assert len(contacts) == 0


def test_a_conversation():
	callbackData = []
	callback = generate_update_callback(callbackData)

	backend = MockBackend([
		{
			"id": "conv1",
			"contactId": "con1",
			"name": "Con Man",
			"time": datetime.datetime(2000, 1, 1),
			"relTime": "Sometime back",
			"prettyNumber": "(555) 555-1224",
			"number": "5555551224",
			"location": "",
			"messageParts": [
				("Innocent Man", "Body of Message", "Forever ago")
			],
		},
	])
	conversings = gvoice.conversations.Conversations(backend)
	conversings.updateSignalHandler.register_sink(callback)
	assert len(callbackData) == 0, "%r" % callbackData

	cons = list(conversings.get_conversations())
	assert len(cons) == 1
	assert cons[0] == ("con1", "5555551224"), cons

	conversings.update()
	assert len(callbackData) == 0, "%r" % callbackData

	conversings.update(force=True)
	assert len(callbackData) == 0, "%r" % callbackData


def test_adding_a_conversation():
	callbackData = []
	callback = generate_update_callback(callbackData)

	backend = MockBackend([
		{
			"id": "conv1",
			"contactId": "con1",
			"name": "Con Man",
			"time": datetime.datetime(2000, 1, 1),
			"relTime": "Sometime back",
			"prettyNumber": "(555) 555-1224",
			"number": "5555551224",
			"location": "",
			"messageParts": [
				("Innocent Man", "Body of Message", "Forever ago")
			],
		},
	])
	conversings = gvoice.conversations.Conversations(backend)
	conversings.updateSignalHandler.register_sink(callback)
	assert len(callbackData) == 0, "%r" % callbackData

	cons = list(conversings.get_conversations())
	assert len(cons) == 1
	assert cons[0] == ("con1", "5555551224"), cons

	conversings.update()
	assert len(callbackData) == 0, "%r" % callbackData

	conversings.update(force=True)
	assert len(callbackData) == 0, "%r" % callbackData

	backend.conversationsData.append(
		{
			"id": "conv2",
			"contactId": "con2",
			"name": "Pretty Man",
			"time": datetime.datetime(2003, 1, 1),
			"relTime": "Somewhere over the rainbow",
			"prettyNumber": "(555) 555-2244",
			"number": "5555552244",
			"location": "",
			"messageParts": [
				("Con Man", "Body of Message somewhere", "Maybe")
			],
		},
	)

	conversings.update()
	assert len(callbackData) == 0, "%r" % callbackData

	conversings.update(force=True)
	assert len(callbackData) == 1, "%r" % callbackData
	idsOnly = callbackData[0][1]
	assert ("con2", "5555552244") in idsOnly, idsOnly

	cons = list(conversings.get_conversations())
	assert len(cons) == 2
	assert ("con1", "5555551224") in cons, cons
	assert ("con2", "5555552244") in cons, cons


def test_merging_a_conversation():
	callbackData = []
	callback = generate_update_callback(callbackData)

	backend = MockBackend([
		{
			"id": "conv1",
			"contactId": "con1",
			"name": "Con Man",
			"time": datetime.datetime(2000, 1, 1),
			"relTime": "Sometime back",
			"prettyNumber": "(555) 555-1224",
			"number": "5555551224",
			"location": "",
			"messageParts": [
				("Innocent Man", "Body of Message", "Forever ago")
			],
		},
	])
	conversings = gvoice.conversations.Conversations(backend)
	conversings.updateSignalHandler.register_sink(callback)
	assert len(callbackData) == 0, "%r" % callbackData

	cons = list(conversings.get_conversations())
	assert len(cons) == 1
	assert cons[0] == ("con1", "5555551224"), cons

	conversings.update()
	assert len(callbackData) == 0, "%r" % callbackData

	conversings.update(force=True)
	assert len(callbackData) == 0, "%r" % callbackData

	backend.conversationsData.append(
		{
			"id": "conv1",
			"contactId": "con1",
			"name": "Con Man",
			"time": datetime.datetime(2003, 1, 1),
			"relTime": "Sometime back",
			"prettyNumber": "(555) 555-1224",
			"number": "5555551224",
			"location": "",
			"messageParts": [
				("Innocent Man", "Mwahahaah", "somewhat closer")
			],
		},
	)

	conversings.update()
	assert len(callbackData) == 0, "%r" % callbackData

	conversings.update(force=True)
	assert len(callbackData) == 1, "%r" % callbackData
	idsOnly = callbackData[0][1]
	assert ("con1", "5555551224") in idsOnly, idsOnly
	convseration = conversings.get_conversation(idsOnly.pop())
	assert len(convseration["messageParts"]) == 2, convseration["messageParts"]
