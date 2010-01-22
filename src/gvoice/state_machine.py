#!/usr/bin/env python

"""
@todo Look into supporting more states
"""

import logging

import gobject

import util.go_utils as gobject_utils
import util.coroutines as coroutines
import gtk_toolbox


_moduleLogger = logging.getLogger("gvoice.state_machine")


def to_milliseconds(**kwd):
	if "milliseconds" in kwd:
		return kwd["milliseconds"]
	elif "seconds" in kwd:
		return kwd["seconds"] * 1000
	elif "minutes" in kwd:
		return kwd["minutes"] * 1000 * 60
	elif "hours" in kwd:
		return kwd["hours"] * 1000 * 60 * 60
	raise KeyError("Unknown arg: %r" % kwd)


def to_seconds(**kwd):
	if "milliseconds" in kwd:
		return kwd["milliseconds"] / 1000
	elif "seconds" in kwd:
		return kwd["seconds"]
	elif "minutes" in kwd:
		return kwd["minutes"] * 60
	elif "hours" in kwd:
		return kwd["hours"] * 60 * 60
	raise KeyError("Unknown arg: %r" % kwd)


class NopStateStrategy(object):

	def __init__(self):
		pass

	def initialize_state(self):
		pass

	def increment_state(self):
		pass

	@property
	def timeout(self):
		return UpdateStateMachine.INFINITE_PERIOD


class ConstantStateStrategy(object):

	def __init__(self, timeout):
		assert 0 < timeout or timeout == UpdateStateMachine.INFINITE_PERIOD
		self._timeout = timeout

	def initialize_state(self):
		pass

	def increment_state(self):
		pass

	@property
	def timeout(self):
		return self._timeout


class GeometricStateStrategy(object):

	def __init__(self, init, min, max):
		assert 0 < init and init < max and init != UpdateStateMachine.INFINITE_PERIOD
		assert 0 < min and min != UpdateStateMachine.INFINITE_PERIOD
		assert min < max or max == UpdateStateMachine.INFINITE_PERIOD
		self._min = min
		self._max = max
		self._init = init
		self._current = 0

	def initialize_state(self):
		self._current = self._min / 2

	def increment_state(self):
		if self._max == UpdateStateMachine.INFINITE_PERIOD:
			self._current *= 2
		else:
			self._current = min(2 * self._current, self._max - self._init)

	@property
	def timeout(self):
		return self._init + self._current


class StateMachine(object):

	STATE_ACTIVE = 0, "active"
	STATE_IDLE = 1, "idle"
	STATE_DND = 2, "dnd"

	def start(self):
		raise NotImplementedError("Abstract")

	def stop(self):
		raise NotImplementedError("Abstract")

	def close(self):
		raise NotImplementedError("Abstract")

	def set_state(self, state):
		raise NotImplementedError("Abstract")

	@property
	def state(self):
		raise NotImplementedError("Abstract")


class MasterStateMachine(StateMachine):

	def __init__(self):
		self._machines = []
		self._state = self.STATE_ACTIVE

	def append_machine(self, machine):
		self._machines.append(machine)

	def start(self):
		# Confirm we are all on the same page
		for machine in self._machines:
			machine.set_state(self._state)
		for machine in self._machines:
			machine.start()

	def stop(self):
		for machine in self._machines:
			machine.stop()

	def close(self):
		for machine in self._machines:
			machine.close()

	def set_state(self, state):
		self._state = state
		for machine in self._machines:
			machine.set_state(state)

	@property
	def state(self):
		return self._state


class UpdateStateMachine(StateMachine):
	# Making sure the it is initialized is finicky, be careful

	INFINITE_PERIOD = -1

	_IS_DAEMON = True

	def __init__(self, updateItems, name=""):
		self._name = name
		self._updateItems = updateItems

		self._state = self.STATE_ACTIVE
		self._timeoutId = None

		self._strategies = {}
		self._callback = coroutines.func_sink(
			coroutines.expand_positional(
				self._request_reset_timers
			)
		)

	def set_state_strategy(self, state, strategy):
		self._strategies[state] = strategy

	def start(self):
		assert self._timeoutId is None
		for strategy in self._strategies.itervalues():
			strategy.initialize_state()
		if self._strategy.timeout != self.INFINITE_PERIOD:
			self._timeoutId = gobject.idle_add(self._on_timeout)
		_moduleLogger.info("%s Starting State Machine" % (self._name, ))

	def stop(self):
		_moduleLogger.info("%s Stopping State Machine" % (self._name, ))
		self._stop_update()

	def close(self):
		assert self._timeoutId is None
		self._callback = None

	def set_state(self, newState):
		if self._state == newState:
			return
		oldState = self._state
		_moduleLogger.info("%s Transitioning from %s to %s" % (self._name, oldState, newState))

		self._state = newState
		self._reset_timers()

	@property
	def state(self):
		return self._state

	def reset_timers(self):
		_moduleLogger.info("%s Resetting State Machine" % (self._name, ))
		self._reset_timers()

	@property
	def request_reset_timers(self):
		return self._callback

	@property
	def _strategy(self):
		return self._strategies[self._state]

	@gtk_toolbox.log_exception(_moduleLogger)
	def _request_reset_timers(self, *args):
		self._reset_timers()

	def _schedule_update(self):
		assert self._timeoutId is None
		self._strategy.increment_state()
		nextTimeout = self._strategy.timeout
		if nextTimeout != self.INFINITE_PERIOD:
			self._timeoutId = gobject_utils.timeout_add_seconds(nextTimeout, self._on_timeout)
		_moduleLogger.info("%s Next update in %s ms" % (self._name, nextTimeout, ))

	def _stop_update(self):
		if self._timeoutId is None:
			return
		gobject.source_remove(self._timeoutId)
		self._timeoutId = None

	def _reset_timers(self):
		if self._timeoutId is None:
			return # not started yet
		self._stop_update()
		self._strategy.initialize_state()
		self._schedule_update()

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_timeout(self):
		self._timeoutId = None
		self._schedule_update()
		for item in self._updateItems:
			try:
				item.update(force=True)
			except Exception:
				_moduleLogger.exception("Update failed for %r" % item)
		return False # do not continue
