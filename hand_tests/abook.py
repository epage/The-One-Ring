#!/usr/bin/python

import sys
sys.path.insert(0,"../src")
import logging

import gvoice.backend as backend
import gvoice.addressbook as abook


def main():
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
		print number, book.get_contact_name(number), book.get_phone_type(number)


if __name__ == "__main__":
	main()

