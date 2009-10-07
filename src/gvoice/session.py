#!/usr/bin/env python

import logging

import backend
import addressbook
import conversations


_moduleLogger = logging.getLogger("gvoice.session")


class Session(object):

	def __init__(self, cookiePath):
		self._cookiePath = cookiePath
		self._username = None
		self._password = None
		self._backend = None
		self._addressbook = None
		self._conversations = None

	def login(self, username, password):
		self._username = username
		self._password = password
		self._backend = backend.GVoiceBackend(self._cookiePath)
		if not self._backend.is_authed():
			self._backend.login(self._username, self._password)

	def logout(self):
		self._username = None
		self._password = None
		self._backend = None
		self._addressbook = None
		self._conversations = None

	def is_logged_in(self):
		if self._backend is None:
			return False
		elif self._backend.is_authed():
			return True
		else:
			try:
				loggedIn = self._backend.login(self._username, self._password)
			except RuntimeError:
				loggedIn = False
			if loggedIn:
				return True
			else:
				self.logout()
				return False

	@property
	def backend(self):
		"""
		Login enforcing backend
		"""
		assert self.is_logged_in(), "User not logged in"
		return self._backend

	@property
	def addressbook(self):
		"""
		Delay initialized addressbook
		"""
		if self._addressbook is None:
			_moduleLogger.info("Initializing addressbook")
			self._addressbook = addressbook.Addressbook(self.backend)
		return self._addressbook

	@property
	def conversations(self):
		"""
		Delay initialized addressbook
		"""
		if self._conversations is None:
			_moduleLogger.info("Initializing conversations")
			self._conversations = conversations.Conversationst(self.backend)
		return self._conversations
