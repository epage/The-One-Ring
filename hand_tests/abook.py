#!/usr/bin/python

import sys
sys.path.insert(0,"../src")
import logging
import pprint

import gvoice.backend as backend
import gvoice.addressbook as abook


def print_contacts():
	logging.basicConfig(level=logging.DEBUG)

	args = sys.argv
	username = args[1]
	password = args[2]

	b = backend.GVoiceBackend()
	b.login(username, password)
	assert b.is_authed()

	book = abook.Addressbook(b)
	book.update()
	for number in book.get_numbers():
		#pprint.pprint((number, book.get_contact_name(number), book.get_phone_type(number), book.is_blocked(number)))
		pprint.pprint(book._numbers[number])


def print_blank_names():
	logging.basicConfig(level=logging.DEBUG)

	args = sys.argv
	username = args[1]
	password = args[2]

	b = backend.GVoiceBackend()
	b.login(username, password)
	assert b.is_authed()

	book = abook.Addressbook(b)
	book.update()
	for number in book.get_numbers():
		if not book.get_contact_name(number):
			pprint.pprint(book._numbers[number])


if __name__ == "__main__":
	if True:
		print_contacts()
	else:
		print_blank_names()
