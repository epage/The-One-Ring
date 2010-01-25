#!/usr/bin/python2.5

import os
import sys

try:
	import py2deb
except ImportError:
	import fake_py2deb as py2deb

import constants


__appname__ = constants.__app_name__
__description__ = """Send/receive texts and initiate GV callbacks all through Conversations and Phone
Features:
.
* Send Texts and Receive both Texts and Voicemail through your chat window (buggy on Maemo 4.1)
.
* Initiate Google Voice callbacks from the dialpad or your contacts
.
* Access to all of your Google Voice contacts (Maemo 4.1 only for now)
.
* Reduce battery drain by setting your status to "Away"
.
* Block incoming calls by switching your status to "Hidden"
.
Note: Google and Google Voice are probably trademarks of Google.  This software nor the author has any affiliation with Google
.
Homepage: http://theonering.garage.maemo.org
"""
__author__ = "Ed Page"
__email__ = "eopage@byu.net"
__version__ = constants.__version__
__build__ = constants.__build__
__changelog__ = """
0.7.0
* Initial beta release for Maemo 5
* Late Alpha for Maemo 4.1 with horrible consequences like crashing RTComm

0.1.0
* Pre-Alpha Development Release
"""


__postinstall__ = """#!/bin/sh -e

gtk-update-icon-cache -f /usr/share/icons/hicolor
rm -f ~/.telepathy-theonering/theonering.log
"""

def find_files(path):
	for root, dirs, files in os.walk(path):
		for file in files:
			if file.startswith("src!"):
				fileParts = file.split("!")
				unused, relPathParts, newName = fileParts[0], fileParts[1:-1], fileParts[-1]
				assert unused == "src"
				relPath = os.sep.join(relPathParts)
				yield relPath, file, newName


def unflatten_files(files):
	d = {}
	for relPath, oldName, newName in files:
		if relPath not in d:
			d[relPath] = []
		d[relPath].append((oldName, newName))
	return d


def build_package(distribution):
	try:
		os.chdir(os.path.dirname(sys.argv[0]))
	except:
		pass

	py2deb.Py2deb.SECTIONS = py2deb.SECTIONS_BY_POLICY[distribution]
	p = py2deb.Py2deb(__appname__)
	if distribution == "debian":
		p.prettyName = constants.__pretty_app_name__
	else:
		p.prettyName = "Google Voice plugin for Conversations and Calls"
	p.description = __description__
	p.bugTracker = "https://bugs.maemo.org/enter_bug.cgi?product=The%20One%20Ring"
	#p.upgradeDescription = __changelog__.split("\n\n", 1)[0]
	p.author = __author__
	p.mail = __email__
	p.license = "lgpl"
	p.section = {
		"debian": "comm",
		"diablo": "user/network",
		"fremantle": "user/network",
		"mer": "user/network",
	}[distribution]
	p.depends = ", ".join([
		"python (>= 2.5) | python2.5",
		"python-dbus | python2.5-dbus",
		"python-gobject | python2.5-gobject",
		"python-telepathy | python2.5-telepathy",
	])
	p.depends += {
		"debian": "",
		"chinook": "",
		"diablo": ", python2.5-conic, account-plugin-haze",
		"fremantle": ", account-plugin-haze",
		"mer": "",
	}[distribution]
	p.arch = "all"
	p.urgency = "low"
	p.distribution = "diablo fremantle mer debian"
	p.repository = "extras"
	p.changelog = __changelog__
	p.postinstall = __postinstall__
	p.icon = {
		"debian": "26x26-theonering.png",
		"diablo": "26x26-theonering.png",
		"fremantle": "64x64-theonering.png", # Fremantle natively uses 48x48
		"mer": "64x64-theonering.png",
	}[distribution]
	for relPath, files in unflatten_files(find_files(".")).iteritems():
		fullPath = "/usr/lib/theonering"
		if relPath:
			fullPath += os.sep+relPath
		p[fullPath] = list(
			"|".join((oldName, newName))
			for (oldName, newName) in files
		)
	p["/usr/share/dbus-1/services"] = ["org.freedesktop.Telepathy.ConnectionManager.theonering.service"]
	if distribution in ("debian", ):
		p["/usr/share/mission-control/profiles"] = ["theonering.profile.%s|theonering.profile"% distribution]
	elif distribution in ("diablo", "fremantle", "mer"):
		p["/usr/share/osso-rtcom"] = ["theonering.profile.%s|theonering.profile"% distribution]
	p["/usr/lib/telepathy"] = ["telepathy-theonering"]
	p["/usr/share/telepathy/managers"] = ["theonering.manager"]
	p["/usr/share/icons/hicolor/26x26/hildon"] = ["26x26-theonering.png|im-theonering.png"]

	if distribution == "debian":
		print p
		print p.generate(
			version="%s-%s" % (__version__, __build__),
			changelog=__changelog__,
			build=True,
			tar=False,
			changes=False,
			dsc=False,
		)
		print "Building for %s finished" % distribution
	else:
		print p
		print p.generate(
			version="%s-%s" % (__version__, __build__),
			changelog=__changelog__,
			build=False,
			tar=True,
			changes=True,
			dsc=True,
		)
		print "Building for %s finished" % distribution


if __name__ == "__main__":
	if len(sys.argv) > 1:
		try:
			import optparse
		except ImportError:
			optparse = None

		if optparse is not None:
			parser = optparse.OptionParser()
			(commandOptions, commandArgs) = parser.parse_args()
	else:
		commandArgs = None
		commandArgs = ["diablo"]
	build_package(commandArgs[0])
