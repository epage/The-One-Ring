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

	outgoingNumber = args[3]
	forward = args[4]
	subscriber = args[5] # Number or "undefined"
	phoneType = args[6] # See PHONE_TYPE_*
	remember = args[7] # "1" or "0"
	if len(args) == 9:
		cookiePath = args[8]
	else:
		cookiePath = None

	b = backend.GVoiceBackend(cookiePath)
	b.login(username, password)
	assert b.is_authed()

	callData = {
			'outgoingNumber': outgoingNumber,
			'forwardingNumber': forward,
			'subscriberNumber': subscriber,
			'phoneType': phoneType,
			'remember': remember,
	}
	logging.info("%r" % callData)

	page = b._get_page_with_token(
		b._callUrl,
		callData,
	)
	print page


if __name__ == "__main__":
	main()
