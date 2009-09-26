#!/usr/bin/python2.5

"""
@bug In update desrcription stuff
"""

import os
import sys

try:
	import py2deb
except ImportError:
	import fake_py2deb as py2deb

import constants


__appname__ = constants.__app_name__
__description__ = "Google Voice Communication Plugin"
__author__ = "Ed Page"
__email__ = "eopage@byu.net"
__version__ = constants.__version__
__build__ = constants.__build__
__changelog__ = """
0.1.0
* Initial release
"""


__postinstall__ = """#!/bin/sh -e

gtk-update-icon-cache -f /usr/share/icons/hicolor
"""

def find_files(path):
	for root, dirs, files in os.walk(path):
		for file in files:
			if file.startswith("src-"):
				fileParts = file.split("-")
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
	p.description = __description__
	p.upgradeDescription = __changelog__.split("\n\n", 1)[0]
	p.author = __author__
	p.mail = __email__
	p.license = "lgpl"
	p.depends = ", ".join([
		"python2.6 | python2.5",
		"python-gtk2 | python2.5-gtk2",
		"python-xml | python2.5-xml",
		"python-dbus | python2.5-dbus",
	])
	maemoSpecificDepends = ", python-osso | python2.5-osso, python-hildon | python2.5-hildon"
	p.depends += {
		"debian": ", python-glade2",
		"chinook": maemoSpecificDepends,
		"diablo": maemoSpecificDepends,
		"fremantle": maemoSpecificDepends + ", python-glade2",
		"mer": maemoSpecificDepends + ", python-glade2",
	}[distribution]
	p.recommends = ", ".join([
	])
	p.section = {
		"debian": "comm",
		"chinook": "communication",
		"diablo": "user/network",
		"fremantle": "user/network",
		"mer": "user/network",
	}[distribution]
	p.arch = "all"
	p.urgency = "low"
	p.distribution = "chinook diablo fremantle mer debian"
	p.repository = "extras"
	p.changelog = __changelog__
	p.postinstall = __postinstall__
	p.icon = {
		"debian": "26x26-theonering.png",
		"chinook": "26x26-theonering.png",
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
	p["/usr/share/dbus-1/services"] = ["org.freedesktop.Telepathy.ConnectionManager.theonering.service.in"]
	p["/usr/share/telepathy/managers"] = ["theonering.manager"]
	p["/usr/share/icons/hicolor/26x26/hildon"] = ["26x26-theonering.png|theonering.png"]
	p["/usr/share/icons/hicolor/64x64/hildon"] = ["64x64-theonering.png|theonering.png"]
	p["/usr/share/icons/hicolor/scalable/hildon"] = ["scale-theonering.png|theonering.png"]

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
