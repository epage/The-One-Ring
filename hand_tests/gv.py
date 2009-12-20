#!/usr/bin/python

import sys
sys.path.insert(0,"../src")
import pprint
import logging

import gvoice.backend as backend


def main():
	logging.basicConfig(level=logging.DEBUG)

	args = sys.argv
	username = args[1]
	password = args[2]

	b = backend.GVoiceBackend()
	if False:
		print "Authenticated: ", b.is_authed()
		if not b.is_authed():
			print "Login?: ", b.login(username, password)
		print "Authenticated: ", b.is_authed()
	else:
		b.login(username, password)

	if False:
		print "Is Dnd: ", b.is_dnd()
		print "Setting Dnd", b.set_dnd(True)
		print "Is Dnd: ", b.is_dnd()
		print "Setting Dnd", b.set_dnd(False)
		print "Is Dnd: ", b.is_dnd()

	if False:
		print "Token: ", b._token
		print "Account: ", b.get_account_number()
		print "Callback: ", b.get_callback_number()
		print "All Callback: ",
		pprint.pprint(b.get_callback_numbers())

	if False:
		print "Recent: "
		for data in b.get_recent():
			pprint.pprint(data)

	if False:
		print "Contacts: ",
		for contact in b.get_contacts():
			pprint.pprint(contact)

	if True:
		print "Messages: ",
		for message in b.get_conversations():
			pprint.pprint(message.to_dict())

	return b


if __name__ == "__main__":
	main()
