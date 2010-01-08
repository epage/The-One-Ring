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
		self._addressbookStateMachine = state_machine.UpdateStateMachine([self.addressbook])
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
			state_machine.ConstantStateStrategy(state_machine.to_milliseconds(hours=1))
		)

		self._conversations = conversations.Conversations(self._backend)
		self._conversationsStateMachine = state_machine.UpdateStateMachine([self.conversations])
		self._conversationsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_DND,
			state_machine.NopStateStrategy()
		)
		self._conversationsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_IDLE,
			state_machine.ConstantStateStrategy(state_machine.to_milliseconds(minutes=30))
		)
		self._conversationsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_ACTIVE,
			state_machine.GeometricStateStrategy(
				state_machine.to_milliseconds(seconds=10),
				state_machine.to_milliseconds(seconds=1),
				state_machine.to_milliseconds(minutes=10),
			)
		)

		self._masterStateMachine = state_machine.MasterStateMachine()
		self._masterStateMachine.append_machine(self._addressbookStateMachine)
		self._masterStateMachine.append_machine(self._conversationsStateMachine)

		self._conversations.updateSignalHandler.register_sink(
			self._conversationsStateMachine.request_reset_timers
		)

	def close(self):
		self._conversations.updateSignalHandler.unregister_sink(
			self._conversationsStateMachine.request_reset_timers
		)
		self._masterStateMachine.close()

	def login(self, username, password):
		self._username = username
		self._password = password
		if not self._backend.is_authed():
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

	@property
	def stateMachine(self):
		return self._masterStateMachine

	@property
	def addressbookStateMachine(self):
		return self._addressbookStateMachine

	@property
	def conversationsStateMachine(self):
		return self._conversationsStateMachine
