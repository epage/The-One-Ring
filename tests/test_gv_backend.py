from __future__ import with_statement

import cookielib
import logging

import test_utils

import sys
sys.path.append("../src")

import gvoice


logging.basicConfig(level=logging.DEBUG)


def generate_mock(cookiesSucceed, username, password):

	class MockModule(object):

		class MozillaEmulator(object):

			def __init__(self, trycount = 1):
				self.cookies = cookielib.LWPCookieJar()
				self.trycount = trycount

			def download(self, url,
					postdata = None, extraheaders = None, forbid_redirect = False,
					trycount = None, only_head = False,
				):
				return ""

			def load_cookies(self, *args):
				pass

			def save_cookies(self, *args):
				pass

			def clear_cookies(self, *args):
				pass

	return MockModule


def test_not_logged_in():
	correctUsername, correctPassword = "", ""
	MockBrowserModule = generate_mock(False, correctUsername, correctPassword)
	gvoice.backend.browser_emu, RealBrowser = MockBrowserModule, gvoice.backend.browser_emu
	try:
		backend = gvoice.backend.GVoiceBackend()
		assert not backend.is_authed()
		assert not backend.login("bad_name", "bad_password")
		backend.logout()
		with test_utils.expected(RuntimeError):
			backend.call("5551234567")
		with test_utils.expected(RuntimeError):
			backend.send_sms("5551234567", "Hello World")
		assert backend.get_account_number() == "", "%s" % backend.get_account_number()
		gvoice.backend.set_sane_callback(backend)
		assert backend.get_callback_number() == ""
		with test_utils.expected(Exception):
			recent = list(backend.get_recent())
		with test_utils.expected(Exception):
			messages = list(backend.get_messages())
	finally:
		gvoice.backend.browser_emu = RealBrowser
