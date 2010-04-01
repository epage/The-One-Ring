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
0.8.8
* Switching to a non-blocking system so TOR can remain responsive to MC and avoid being leaked in the first place

0.8.7
* Adding some logging to help track down some issues

0.8.6
* Switched to a 10 second timeout without connections before closing TOR
* Reduced the numbr of conversations cached
* Forcing system contacts to be enabled but only calls are working for now
* Bugfix: Reduced windows of hitting "Network Failure" when transitioning between networks

0.8.5
* Bugfix: User's locale differs from google's causes errors
* Bugfix: Reducing the times we ignore the cache of past conversations
* Bugfix: The One Ring does not work on desktop systems with Empathy 2.28

0.8.4
* Reduced time allowed for disconnect due to RTComm not putting TOR on hold, causing miss of callback
* Doubled the timed disconnects time
* Cleaning up things to better match the latest Empathy
* Bugfix: Random "General Error"s when making a call

0.8.3
* "Hold" support for calls, so that initiating a callback does not block incoming calls
* Increased the auto-cleanup timeout from 5 seconds to 10 seconds

0.8.2
* Improved debug logs, removing noise
* Reduced allotted disconnect time from 5 seconds to 2
* Auto-cleanup resources when client only does phase 1 of 2 connection creation phases
* Added 26x26 and 64x64 variants of icons to hopefully fix issues on Maemo 4.1

0.8.1
* Canceling of outbound calls
* Bugfix: Removing race condition with disconnect.  I introduced it expecting it to help but it hurts more than it helps

0.8.0
* Basic avatar support to distinguish phone types
* Tweaks to hopefully improve behavior

0.7.14
* Bugfix: Polling state machines weren't properly resetting (maybe thats why I had such good battery life)
* Bugfix: On Maemo 4.1 there are still some empty windows created
* Bugfix: Obscure alias bug no one should hit with The One Ring
* Bugfix: Another obscure bug causing possibly no negative side-effects

0.7.13
* Bugfix: Cancelling timeouts

0.7.12
* Bugfix: In 0.7.11 I messed up refreshing messages
* Bugfix: DND support has been broken for a while
* Bugfix: Auto-disconnect on Maemo 4.1 couldn't have worked for a while
* Bugfix: Handling missed calls had .. issues
* Bugfix: Issues when making a call introduced in 0.7.11
* Etc with the bug fixes (all too small to list)

0.7.11
* Bugfix: Attempting to improve the behavior of calls by reducing potential RTComm errors
* Bugfix: Issues with weird unexpected disconnect issues
* Bugfix: I guess I made a mistake in registering for system signals, whoops
* Bugfix: Following more closely the Telepathy spec by doing connects and disconnects asynchronously

0.7.10
* Increased the network timeout when connecting to GV
* Bugfix: On connection failure, the connection would be left around, preventing future connections

0.7.9
* Bugfix: Disconnect/Reconnect issues seem to be lessoned for me (What I previously thought was a bugfix turned out to cause several bugs.)

0.7.8
* Bugfix: Issues with checking for new conversations

0.7.7
* On change between available/away, start state_machine at max rather than min, reducing overhead
* Added a check for voicemails on missed/rejected calls (checks 3 times, 1 minute apart each)
* Adjusted default polling times to be more battery cautious for our n8x0 friends who can't change things right now
* Bugfix: Some of the derived polling settings had bugs
* Bugfix: Setting text polling to infinite would still have polling done if one sent a text

0.7.6
* On login, polling now starts at the max time rather than the min, reducing overhead
* Bugfix: Polling configuration wasn't actually hooked up to anything
* Debug Prompt: Made it so you can either reset one or all state machines (Rather than just all)

0.7.5
* Fixing a polling time bug introduced when making polling configurable

0.7.4
* Fixing a bug with deny-lists

0.7.3
* Fixing bug with being able to configure polling times

0.7.2
* Added a Deny list
* Added option to make GV Contacts optional
* Added a limit, where if a state machine period is longer than it, than we set the period to infinite
* Delayed when we say the connection is disconnected to hopefully help random issues
* Tweaked how The One Ring shows up in the addressbook (Maemo 5)
* Made polling configurable
* Delayed auto-disconnect in case the user is just switching network connections (Maemo 4.1)
* Bugfix: Removed superfluous blank message from debug prompt
* Bugfix: Moved some more (very minor, very rarely used) timeouts to second resolution reducing overhead
* Bugfix: debug prompt commands handled command validation poorly
* Debug Prompt: Added a "version" command
* Debug Prompt: Added a "get_polling" command to find out what the actual polling periods are
* Debug Prompt: Added a "grab_log" command which is a broken but means to offer the log file through a file transfer
* Debug Prompt: Added a "save_log" command to help till grab_log works and for where file transfers aren't supported by clients

0.7.1
* Reducing the race window where GV will mark messages as read accidently
* Modified some things blindly "because thats what Butterfly does"
* Modified some support files to mimic other plugins on Maemo 5 PR1.1
* Added link to bug tracker and moved all bugs and enhancements to it
* Switched contacts to being away by default upon user feedback
* Adjusting handling of call states to at least allow the option of clients to provide clearer information to the user
* Fixing some bugs with handling a variety of phone number formats
* Removed a hack that changed the number being called, most likely put in place in a bygone era

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
	p.bugTracker = "https://bugs.maemo.org/enter_bug.cgi?product=The%%20One%%20Ring"
	#p.upgradeDescription = __changelog__.split("\n\n", 1)[0]
	p.author = __author__
	p.mail = __email__
	p.license = "lgpl"
	p.section = {
		"debian": "comm",
		"diablo": "user/network",
		"fremantle": "user/network",
	}[distribution]
	p.depends = ", ".join([
		"python (>= 2.5) | python2.5",
		"python-dbus | python2.5-dbus",
		"python-gobject | python2.5-gobject",
		"python-telepathy | python2.5-telepathy",
	])
	p.depends += {
		"debian": "",
		"diablo": ", python2.5-conic, account-plugin-haze",
		"fremantle": ", account-plugin-haze",
	}[distribution]
	p.arch = "all"
	p.urgency = "low"
	p.distribution = "diablo fremantle debian"
	p.repository = "extras"
	p.changelog = __changelog__
	p.postinstall = __postinstall__
	p.icon = "32-tor_handset.png"
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
	elif distribution in ("diablo", "fremantle"):
		p["/usr/share/osso-rtcom"] = ["theonering.profile.%s|theonering.profile"% distribution]
	p["/usr/lib/telepathy"] = ["telepathy-theonering"]
	p["/usr/share/telepathy/managers"] = ["theonering.manager"]
	if distribution in ("debian", ):
		iconBasePath = "/usr/share/icons/gnome/%s/apps"
	elif distribution in ("diablo", "fremantle"):
		iconBasePath = "/usr/share/icons/hicolor/%s/hildon"
	p[iconBasePath % "26x26"] = ["26-tor_handset.png|im-theonering.png"]
	p[iconBasePath % "32x32"] = ["32-tor_handset.png|im-theonering.png"]
	p[iconBasePath % "64x64"] = ["64-tor_handset.png|im-theonering.png"]
	p["/usr/share/theonering"] = [
		"32-tor_handset.png|tor_handset.png",
		"32-tor_phone.png|tor_phone.png",
		"32-tor_question.png|tor_question.png",
		"32-tor_self.png|tor_self.png",
	]

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
