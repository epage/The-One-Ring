#!/usr/bin/env python

import logging

import backend
import addressbook
import conversations
import state_machine


_moduleLogger = logging.getLogger("gvoice.session")


class Session(object):

	def __init__(self, cookiePath = None):
		self._username = None
		self._password = None

		self._backend = backend.GVoiceBackend(cookiePath)
		self._addressbook = addressbook.Addressbook(self._backend)
		self._conversations = conversations.Conversations(self._backend)
		self._stateMachine = state_machine.StateMachine([self.addressbook], [self.conversations])

		self._conversations.updateSignalHandler.register_sink(
			self._stateMachine.request_reset_timers
		)

	def login(self, username, password):
		self._username = username
		self._password = password
		if not self._backend.is_authed():
			self._backend.login(self._username, self._password)

		self._stateMachine.start()

	def logout(self):
		self._loggedIn = False
		self._stateMachine.stop()
		self._backend.logout()

		self._username = None
		self._password = None

	def is_logged_in(self):
		if self._username is None and self._password is None:
			_moduleLogger.info("Hasn't even attempted to login yet")
			return False
		elif self._backend.is_authed():
			return True
		else:
			try:
				loggedIn = self._backend.login(self._username, self._password)
			except RuntimeError, e:
				_moduleLogger.exception("Re-authenticating and erroring")
				loggedIn = False
			if loggedIn:
				return True
			else:
				_moduleLogger.info("Login failed")
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
		return self._addressbook

	@property
	def conversations(self):
		"""
		Delay initialized addressbook
		"""
		return self._conversations
