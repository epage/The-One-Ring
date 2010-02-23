#!/usr/bin/env python

import logging

import util.go_utils as gobject_utils
import util.coroutines as coroutines
import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


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

	def reinitialize_state(self):
		pass

	def increment_state(self):
		pass

	@property
	def timeout(self):
		return UpdateStateMachine.INFINITE_PERIOD

	def __repr__(self):
		return "NopStateStrategy()"


class ConstantStateStrategy(object):

	def __init__(self, timeout):
		assert 0 < timeout or timeout == UpdateStateMachine.INFINITE_PERIOD
		self._timeout = timeout

	def initialize_state(self):
		pass

	def reinitialize_state(self):
		pass

	def increment_state(self):
		pass

	@property
	def timeout(self):
		return self._timeout

	def __repr__(self):
		return "ConstantStateStrategy(timeout=%r)" % self._timeout


class NTimesStateStrategy(object):

	def __init__(self, timeouts, postTimeout):
		assert 0 < len(timeouts)
		for timeout in timeouts:
			assert 0 < timeout or timeout == UpdateStateMachine.INFINITE_PERIOD
		assert 0 < postTimeout or postTimeout == UpdateStateMachine.INFINITE_PERIOD
		self._timeouts = timeouts
		self._postTimeout = postTimeout

		self._attemptCount = 0

	def initialize_state(self):
		self._attemptCount = len(self._timeouts)

	def reinitialize_state(self):
		self._attemptCount = 0

	def increment_state(self):
		self._attemptCount += 1

	@property
	def timeout(self):
		try:
			return self._timeouts[self._attemptCount]
		except IndexError:
			return self._postTimeout

	def __str__(self):
		return "NTimesStateStrategy(timeout=%r)" % (
			self.timeout,
		)

	def __repr__(self):
		return "NTimesStateStrategy(timeouts=%r, postTimeout=%r)" % (
			self._timeouts,
			self._postTimeout,
		)


class GeometricStateStrategy(object):

	def __init__(self, init, min, max):
		assert 0 < init and init < max or init == UpdateStateMachine.INFINITE_PERIOD
		assert 0 < min or min == UpdateStateMachine.INFINITE_PERIOD
		assert min < max or max == UpdateStateMachine.INFINITE_PERIOD
		self._min = min
		self._max = max
		self._init = init
		self._current = 0

	def initialize_state(self):
		self._current = self._max

	def reinitialize_state(self):
		self._current = self._min

	def increment_state(self):
		if self._current == UpdateStateMachine.INFINITE_PERIOD:
			pass
		if self._init == UpdateStateMachine.INFINITE_PERIOD:
			self._current = UpdateStateMachine.INFINITE_PERIOD
		elif self._max == UpdateStateMachine.INFINITE_PERIOD:
			self._current *= 2
		else:
			self._current = min(2 * self._current, self._max - self._init)

	@property
	def timeout(self):
		if UpdateStateMachine.INFINITE_PERIOD in (self._init, self._current):
			timeout = UpdateStateMachine.INFINITE_PERIOD
		else:
			timeout = self._init + self._current
		return timeout

	def __str__(self):
		return "GeometricStateStrategy(timeout=%r)" % (
			self.timeout
		)

	def __repr__(self):
		return "GeometricStateStrategy(init=%r, min=%r, max=%r)" % (
			self._init, self._min, self._max
		)


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
	DEFAULT_MAX_TIMEOUT = to_seconds(hours=24)

	_IS_DAEMON = True

	def __init__(self, updateItems, name="", maxTime = DEFAULT_MAX_TIMEOUT):
		self._name = name
		self._updateItems = updateItems
		self._maxTime = maxTime
		self._isActive = False

		self._state = self.STATE_ACTIVE
		self._onTimeout = gobject_utils.Timeout(self._on_timeout)

		self._strategies = {}
		self._callback = coroutines.func_sink(
			coroutines.expand_positional(
				self._request_reset_timers
			)
		)

	def __str__(self):
		return """UpdateStateMachine(
	name=%r,
	strategie=%s,
	isActive=%r,
	isPolling=%r,
)""" % (self._name, self._strategy, self._isActive, self._onTimeout.is_running())

	def __repr__(self):
		return """UpdateStateMachine(
	name=%r,
	strategie=%r,
)""" % (self._name, self._strategies)

	def set_state_strategy(self, state, strategy):
		self._strategies[state] = strategy

	def start(self):
		for strategy in self._strategies.itervalues():
			strategy.initialize_state()
		if self._strategy.timeout != self.INFINITE_PERIOD:
			self._onTimeout.start(seconds=0)
		self._isActive = True
		_moduleLogger.info("%s Starting State Machine" % (self._name, ))

	def stop(self):
		_moduleLogger.info("%s Stopping State Machine" % (self._name, ))
		self._isActive = False
		self._onTimeout.cancel()

	def close(self):
		self._onTimeout.cancel()
		self._callback = None

	def set_state(self, newState):
		if self._state == newState:
			return
		oldState = self._state
		_moduleLogger.info("%s Transitioning from %s to %s" % (self._name, oldState, newState))

		self._state = newState
		self._reset_timers(initialize=True)

	@property
	def state(self):
		return self._state

	def reset_timers(self):
		self._reset_timers()

	@property
	def request_reset_timers(self):
		return self._callback

	@property
	def _strategy(self):
		return self._strategies[self._state]

	@property
	def maxTime(self):
		return self._maxTime

	@misc_utils.log_exception(_moduleLogger)
	def _request_reset_timers(self, *args):
		self._reset_timers()

	def _reset_timers(self, initialize=False):
		if not self._isActive:
			return # not started yet
		_moduleLogger.info("%s Resetting State Machine" % (self._name, ))
		self._onTimeout.cancel()
		if initialize:
			self._strategy.initialize_state()
		else:
			self._strategy.reinitialize_state()
		self._schedule_update()

	def _schedule_update(self):
		self._strategy.increment_state()
		nextTimeout = self._strategy.timeout
		if nextTimeout != self.INFINITE_PERIOD and nextTimeout < self._maxTime:
			assert 0 < nextTimeout
			self._onTimeout.start(seconds=nextTimeout)
			_moduleLogger.info("%s Next update in %s seconds" % (self._name, nextTimeout, ))
		else:
			_moduleLogger.info("%s No further updates (timeout is %s seconds)" % (self._name, nextTimeout, ))

	@misc_utils.log_exception(_moduleLogger)
	def _on_timeout(self):
		self._schedule_update()
		for item in self._updateItems:
			try:
				item.update(force=True)
			except Exception:
				_moduleLogger.exception("Update failed for %r" % item)
