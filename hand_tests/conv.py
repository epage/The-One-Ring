#!/usr/bin/python

import sys
sys.path.insert(0,"../src")
import pprint
import logging

import gvoice.backend as backend
import gvoice.conversations as conversations


def main():
	logging.basicConfig(level=logging.DEBUG)

	args = sys.argv
	username = args[1]
	password = args[2]

	b = backend.GVoiceBackend()
	b.login(username, password)

	c = conversations.Conversations(b)

	c.update(force=True)
	for key in c.get_conversations():
		print "="*50
		print key
		for conv in c.get_conversation(key).conversations:
			pprint.pprint(conv.to_dict())


if __name__ == "__main__":
	main()
