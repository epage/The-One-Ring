#!/usr/bin/env python

"""
@todo Look into switching from POLL_TIME = min(F * 2^n, MAX) to POLL_TIME = min(CONST + F * 2^n, MAX)
@todo Look into supporting more states that have a different F and MAX
"""

import Queue
import threading
import logging

import gobject

import util.algorithms as algorithms
import util.coroutines as coroutines


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

	STATE_ACTIVE = "active"
	STATE_IDLE = "idle"
	STATE_DND = "dnd"

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

		self._actions = Queue.Queue()
		self._state = self.STATE_ACTIVE
		self._timeoutId = None
		self._thread = None
		self._currentPeriod = self._INITIAL_ACTIVE_PERIOD
		self._set_initial_period()

	def start(self):
		assert self._thread is None
		self._thread = threading.Thread(target=self._run)
		self._thread.setDaemon(self._IS_DAEMON)
		self._thread.start()

	def stop(self):
		if self._thread is not None:
			self._actions.put(self._ACTION_STOP)
			self._thread = None
		else:
			_moduleLogger.info("Stopping an already stopped state machine")

	def set_state(self, state):
		self._state = state
		self.reset_timers()

	def get_state(self):
		return self._state

	def reset_timers(self):
		self._actions.put(self._ACTION_RESET)

	@coroutines.func_sink
	def request_reset_timers(self, args):
		self.reset_timers()

	def _run(self):
		logging.basicConfig(level=logging.DEBUG)
		_moduleLogger.info("Starting State Machine")
		for item in self._initItems:
			try:
				item.update()
			except Exception:
				_moduleLogger.exception("Initial update failed for %r" % item)

		# empty the task queue
		actions = list(algorithms.itr_available(self._actions, initiallyBlock = False))
		self._schedule_update()
		if len(self._updateItems) == 0:
			self.stop()

		while True:
			# block till we get a task, or get all the tasks if we were late 
			actions = list(algorithms.itr_available(self._actions, initiallyBlock = True))

			if self._ACTION_STOP in actions:
				_moduleLogger.info("Requested to stop")
				self._stop_update()
				break
			elif self._ACTION_RESET in actions:
				_moduleLogger.info("Reseting timers")
				self._reset_timers()
			elif self._ACTION_UPDATE in actions:
				_moduleLogger.info("Update")
				for item in self._updateItems:
					try:
						item.update(force=True)
					except Exception:
						_moduleLogger.exception("Update failed for %r" % item)
				self._schedule_update()

	def _set_initial_period(self):
		self._currentPeriod = self._INITIAL_ACTIVE_PERIOD / 2 # We will double it later

	def _reset_timers(self):
		self._stop_update()
		self._set_initial_period()
		self._schedule_update()

	def _schedule_update(self):
		nextTimeout = self._calculate_step(self._state, self._currentPeriod)
		nextTimeout = int(nextTimeout)
		if nextTimeout != self._INFINITE_PERIOD:
			self._timeoutId = gobject.timeout_add(nextTimeout, self._on_timeout)
		self._currentPeriod = nextTimeout

	def _stop_update(self):
		if self._timeoutId is None:
			return
		gobject.source_remove(self._timeoutId)
		self._timeoutId = None

	def _on_timeout(self):
		self._actions.put(self._ACTION_UPDATE)
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
