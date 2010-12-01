#!/usr/bin/env python

from __future__ import with_statement
from __future__ import division

import sys
sys.path.insert(0,"../src")

import csv
import logging

try:
	import cStringIO as StringIO
except ImportError:
	import StringIO

import gvoice.backend as backend


_moduleLogger = logging.getLogger(__name__)


if __name__ == "__main__":
	logging.basicConfig(level=logging.DEBUG)

	args = sys.argv

	if True:
		username = args[1]
		password = args[2]
		b = backend.GVoiceBackend()
		b.login(username, password)
		data = b.get_csv_contacts()
		with open("test.csv", "wb") as f:
			f.write(data)
	else:
		with open("test.csv", "U") as f:
			data = f.read()
	if True:
		if False:
			# used with the official gmail one returned by passing no export params
			data = "".join(c for (i, c) in enumerate(data) if (i%2 == 0))[1:]
		for attr in csv.DictReader(StringIO.StringIO(data)):
			for name in attr.keys():
				if not attr[name] or name is None:
					del attr[name]
			#print attr
			if any(attr[name] for name in attr.keys() if "Phone" in name):
				print attr
