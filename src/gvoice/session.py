#!/usr/bin/env python

import os
import time
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
		self._addressbookStateMachine = state_machine.UpdateStateMachine([self.addressbook], "Addressbook")
		self._addressbookStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_DND,
			state_machine.NopStateStrategy()
		)
		self._addressbookStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_IDLE,
			state_machine.ConstantStateStrategy(state_machine.to_milliseconds(hours=6))
		)
		self._addressbookStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_ACTIVE,
			state_machine.ConstantStateStrategy(state_machine.to_milliseconds(hours=2))
		)

		self._voicemails = conversations.Conversations(self._backend.get_voicemails)
		self._voicemailsStateMachine = state_machine.UpdateStateMachine([self.voicemails], "Voicemail")
		self._voicemailsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_DND,
			state_machine.NopStateStrategy()
		)
		self._voicemailsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_IDLE,
			state_machine.ConstantStateStrategy(state_machine.to_milliseconds(minutes=60))
		)
		self._voicemailsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_ACTIVE,
			state_machine.ConstantStateStrategy(state_machine.to_milliseconds(minutes=10))
		)
		self._voicemails.updateSignalHandler.register_sink(
			self._voicemailsStateMachine.request_reset_timers
		)

		self._texts = conversations.Conversations(self._backend.get_texts)
		self._textsStateMachine = state_machine.UpdateStateMachine([self.texts], "Texting")
		self._textsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_DND,
			state_machine.NopStateStrategy()
		)
		self._textsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_IDLE,
			state_machine.ConstantStateStrategy(state_machine.to_milliseconds(minutes=30))
		)
		self._textsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_ACTIVE,
			state_machine.GeometricStateStrategy(
				state_machine.to_milliseconds(seconds=20),
				state_machine.to_milliseconds(milliseconds=500),
				state_machine.to_milliseconds(minutes=10),
			)
		)
		self._texts.updateSignalHandler.register_sink(
			self._textsStateMachine.request_reset_timers
		)

		self._masterStateMachine = state_machine.MasterStateMachine()
		self._masterStateMachine.append_machine(self._addressbookStateMachine)
		self._masterStateMachine.append_machine(self._voicemailsStateMachine)
		self._masterStateMachine.append_machine(self._textsStateMachine)

		self._lastDndCheck = 0
		self._cachedIsDnd = False

	def load(self, path):
		self._texts.load(os.sep.join((path, "texts.cache")))
		self._voicemails.load(os.sep.join((path, "voicemails.cache")))

	def save(self, path):
		self._texts.save(os.sep.join((path, "texts.cache")))
		self._voicemails.save(os.sep.join((path, "voicemails.cache")))

	def close(self):
		self._voicemails.updateSignalHandler.unregister_sink(
			self._voicemailsStateMachine.request_reset_timers
		)
		self._texts.updateSignalHandler.unregister_sink(
			self._textsStateMachine.request_reset_timers
		)
		self._masterStateMachine.close()

	def login(self, username, password):
		self._username = username
		self._password = password
		self._backend.login(self._username, self._password)

		self._masterStateMachine.start()

	def logout(self):
		self._masterStateMachine.stop()
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

	def set_dnd(self, doNotDisturb):
		self._backend.set_dnd(doNotDisturb)
		self._cachedIsDnd = doNotDisturb

	def is_dnd(self):
		# To throttle checking with the server, use a 30s cache
		newTime = time.time()
		if self._lastDndCheck + 30 < newTime:
			self._lasDndCheck = newTime
			self._cachedIsDnd = self._backend.is_dnd()
		return self._cachedIsDnd

	@property
	def backend(self):
		"""
		Login enforcing backend
		"""
		assert self.is_logged_in(), "User not logged in"
		return self._backend

	@property
	def addressbook(self):
		return self._addressbook

	@property
	def texts(self):
		return self._texts

	@property
	def voicemails(self):
		return self._voicemails

	@property
	def stateMachine(self):
		return self._masterStateMachine

	@property
	def addressbookStateMachine(self):
		return self._addressbookStateMachine

	@property
	def voicemailsStateMachine(self):
		return self._voicemailsStateMachine

	@property
	def textsStateMachine(self):
		return self._textsStateMachine
