#!/usr/bin/env python

"""
@todo Look into switching from POLL_TIME = min(F * 2^n, MAX) to POLL_TIME = min(CONST + F * 2^n, MAX)
@todo Look into supporting more states that have a different F and MAX
"""

import logging

import gobject

import util.go_utils as gobject_utils
import util.coroutines as coroutines
import gtk_toolbox


_moduleLogger = logging.getLogger("gvoice.state_machine")


def _to_milliseconds(**kwd):
	if "milliseconds" in kwd:
		return kwd["milliseconds"]
	elif "seconds" in kwd:
		return kwd["seconds"] * 1000
	elif "minutes" in kwd:
		return kwd["minutes"] * 1000 * 60
	raise KeyError("Unknown arg: %r" % kwd)


class StateMachine(object):

	STATE_ACTIVE = 0, "active"
	STATE_IDLE = 1, "idle"
	STATE_DND = 2, "dnd"

	_ACTION_UPDATE = "update"
	_ACTION_RESET = "reset"
	_ACTION_STOP = "stop"

	_INITIAL_ACTIVE_PERIOD = int(_to_milliseconds(seconds=5))
	_FINAL_ACTIVE_PERIOD = int(_to_milliseconds(minutes=2))
	_IDLE_PERIOD = int(_to_milliseconds(minutes=10))
	_INFINITE_PERIOD = -1

	_IS_DAEMON = True

	def __init__(self, initItems, updateItems):
		self._initItems = initItems
		self._updateItems = updateItems

		self._state = self.STATE_ACTIVE
		self._timeoutId = None
		self._currentPeriod = self._INITIAL_ACTIVE_PERIOD
		self._set_initial_period()

		self._callback = coroutines.func_sink(
			coroutines.expand_positional(
				self._request_reset_timers
			)
		)

	def close(self):
		self._callback = None

	@gobject_utils.async
	@gtk_toolbox.log_exception(_moduleLogger)
	def start(self):
		_moduleLogger.info("Starting State Machine")
		for item in self._initItems:
			try:
				item.update()
			except Exception:
				_moduleLogger.exception("Initial update failed for %r" % item)
		self._schedule_update()

	def stop(self):
		_moduleLogger.info("Stopping an already stopped state machine")
		self._stop_update()

	def set_state(self, newState):
		oldState = self._state
		_moduleLogger.info("Transitioning from %s to %s" % (oldState, newState))

		self._state = newState
		self.reset_timers()

	def get_state(self):
		return self._state

	def reset_timers(self):
		self._reset_timers()

	@property
	def request_reset_timers(self):
		return self._callback

	@gobject_utils.async
	@gtk_toolbox.log_exception(_moduleLogger)
	def _request_reset_timers(self, *args):
		self.reset_timers()

	def _set_initial_period(self):
		self._currentPeriod = self._INITIAL_ACTIVE_PERIOD / 2 # We will double it later

	def _schedule_update(self):
		nextTimeout = self._calculate_step(self._state, self._currentPeriod)
		nextTimeout = int(nextTimeout)
		if nextTimeout != self._INFINITE_PERIOD:
			self._timeoutId = gobject.timeout_add(nextTimeout, self._on_timeout)
		_moduleLogger.info("Next update in %s ms" % (nextTimeout, ))
		self._currentPeriod = nextTimeout

	def _stop_update(self):
		if self._timeoutId is None:
			return
		gobject.source_remove(self._timeoutId)
		self._timeoutId = None

	def _reset_timers(self):
		self._stop_update()
		self._set_initial_period()
		self._schedule_update()

	def _on_timeout(self):
		_moduleLogger.info("Update")
		for item in self._updateItems:
			try:
				item.update(force=True)
			except Exception:
				_moduleLogger.exception("Update failed for %r" % item)
		self._schedule_update()
		return False # do not continue

	@classmethod
	def _calculate_step(cls, state, period):
		if state == cls.STATE_ACTIVE:
			return min(period * 2, cls._FINAL_ACTIVE_PERIOD)
		elif state == cls.STATE_IDLE:
			return cls._IDLE_PERIOD
		elif state == cls.STATE_DND:
			return cls._INFINITE_PERIOD
		else:
			raise RuntimeError("Unknown state: %r" % (state, ))
