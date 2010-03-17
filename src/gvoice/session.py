#!/usr/bin/env python

import os
import time
import logging

import backend
import addressbook
import conversations
import state_machine

import util.go_utils as gobject_utils


_moduleLogger = logging.getLogger(__name__)


class Session(object):

	_DEFAULTS = {
		"contacts": (12, "hours"),
		"voicemail": (120, "minutes"),
		"texts": (10, "minutes"),
	}

	_MINIMUM_MESSAGE_PERIOD = state_machine.to_seconds(minutes=30)

	def __init__(self, cookiePath = None, defaults = None):
		if defaults is None:
			defaults = self._DEFAULTS
		else:
			for key, (quant, unit) in defaults.iteritems():
				if quant == 0:
					defaults[key] = (self._DEFAULTS[key], unit)
				elif quant < 0:
					defaults[key] = (state_machine.UpdateStateMachine.INFINITE_PERIOD, unit)
		self._username = None
		self._password = None

		self._asyncPool = gobject_utils.AsyncPool()
		self._backend = backend.GVoiceBackend(cookiePath)

		if defaults["contacts"][0] == state_machine.UpdateStateMachine.INFINITE_PERIOD:
			contactsPeriodInSeconds = state_machine.UpdateStateMachine.INFINITE_PERIOD
		else:
			contactsPeriodInSeconds = state_machine.to_seconds(
				**{defaults["contacts"][1]: defaults["contacts"][0],}
			)
		self._addressbook = addressbook.Addressbook(self._backend, self._asyncPool)
		self._addressbookStateMachine = state_machine.UpdateStateMachine([self.addressbook], "Addressbook")
		self._addressbookStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_DND,
			state_machine.NopStateStrategy()
		)
		self._addressbookStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_IDLE,
			state_machine.NopStateStrategy()
		)
		self._addressbookStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_ACTIVE,
			state_machine.ConstantStateStrategy(contactsPeriodInSeconds)
		)

		if defaults["voicemail"][0] == state_machine.UpdateStateMachine.INFINITE_PERIOD:
			voicemailPeriodInSeconds = state_machine.UpdateStateMachine.INFINITE_PERIOD
			idleVoicemailPeriodInSeconds = state_machine.UpdateStateMachine.INFINITE_PERIOD
		else:
			voicemailPeriodInSeconds = state_machine.to_seconds(
				**{defaults["voicemail"][1]: defaults["voicemail"][0],}
			)
			idleVoicemailPeriodInSeconds = max(voicemailPeriodInSeconds * 4, self._MINIMUM_MESSAGE_PERIOD)
		self._voicemails = conversations.Conversations(self._backend.get_voicemails, self._asyncPool)
		self._voicemailsStateMachine = state_machine.UpdateStateMachine([self.voicemails], "Voicemail")
		self._voicemailsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_DND,
			state_machine.NopStateStrategy()
		)
		self._voicemailsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_IDLE,
			state_machine.ConstantStateStrategy(idleVoicemailPeriodInSeconds)
		)
		self._voicemailsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_ACTIVE,
			state_machine.NTimesStateStrategy(
				3 * [state_machine.to_seconds(minutes=1)], voicemailPeriodInSeconds
			)
		)
		self._voicemails.updateSignalHandler.register_sink(
			self._voicemailsStateMachine.request_reset_timers
		)

		if defaults["texts"][0] == state_machine.UpdateStateMachine.INFINITE_PERIOD:
			initTextsPeriodInSeconds = state_machine.UpdateStateMachine.INFINITE_PERIOD
			minTextsPeriodInSeconds = state_machine.UpdateStateMachine.INFINITE_PERIOD
			textsPeriodInSeconds = state_machine.UpdateStateMachine.INFINITE_PERIOD
			idleTextsPeriodInSeconds = state_machine.UpdateStateMachine.INFINITE_PERIOD
		else:
			initTextsPeriodInSeconds = state_machine.to_seconds(seconds=20)
			minTextsPeriodInSeconds = state_machine.to_seconds(seconds=1)
			textsPeriodInSeconds = state_machine.to_seconds(
				**{defaults["texts"][1]: defaults["texts"][0],}
			)
			idleTextsPeriodInSeconds = max(textsPeriodInSeconds * 4, self._MINIMUM_MESSAGE_PERIOD)
		self._texts = conversations.Conversations(self._backend.get_texts, self._asyncPool)
		self._textsStateMachine = state_machine.UpdateStateMachine([self.texts], "Texting")
		self._textsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_DND,
			state_machine.NopStateStrategy()
		)
		self._textsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_IDLE,
			state_machine.ConstantStateStrategy(idleTextsPeriodInSeconds)
		)
		self._textsStateMachine.set_state_strategy(
			state_machine.StateMachine.STATE_ACTIVE,
			state_machine.GeometricStateStrategy(
				initTextsPeriodInSeconds,
				minTextsPeriodInSeconds,
				textsPeriodInSeconds,
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

	def login(self, username, password, on_success, on_error):
		self._username = username
		self._password = password
		self._asyncPool.start()
		self._asyncPool.add_task(
			self._backend.login,
			(self._username, self._password),
			{},
			self.__on_login_success(on_success),
			on_error
		)

	def __on_login_success(self, user_success):

		def _actual_success(self, *args, **kwds):
			self._masterStateMachine.start()
			user_success(*args, **kwds)

		return _actual_success

	def logout(self):
		self._asyncPool.stop()
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
			self._lastDndCheck = newTime
			self._cachedIsDnd = self._backend.is_dnd()
		return self._cachedIsDnd

	@property
	def backend(self):
		return self._backend

	@property
	def pool(self):
		return self._asyncPool

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
