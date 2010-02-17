#!/usr/bin/python

import sys
sys.path.insert(0,"../src")
import logging

import gvoice.backend as backend


def main():
	logging.basicConfig(level=logging.DEBUG)

	args = sys.argv
	username = args[1]
	password = args[2]

	PHONE_TYPE_HOME = 1
	PHONE_TYPE_MOBILE = 2
	PHONE_TYPE_WORK = 3
	PHONE_TYPE_GIZMO = 7

	outgoingNumber1 = args[3]
	outgoingNumber2 = args[4]

	b = backend.GVoiceBackend(None)
	b.login(username, password)
	assert b.is_authed()

	phoneNumbers = ",".join([outgoingNumber1, outgoingNumber2])
	page = b._get_page_with_token(
		b._sendSmsURL,
		{
			'phoneNumber': phoneNumbers,
			'text': "Broadcast SMS experiment, did it work?",
		},
	)
	print page


if __name__ == "__main__":
	main()
