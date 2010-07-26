#!/usr/bin/env python

import gvoice


def main(args):
	if args[0] == "messages":
		gvoice.conversations.print_conversations(args[1])
	elif args[0] == "contacts":
		gvoice.addressbook.print_addressbook(args[1])
	else:
		print "Huh?"


if __name__ == "__main__":
	import sys
	main(sys.argv[1:])
