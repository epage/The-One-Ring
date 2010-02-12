#!/usr/bin/env python

from __future__ import with_statement

import time
import functools
import logging

import gobject

import misc


_moduleLogger = logging.getLogger("go_utils")


def make_idler(func):
	"""
	Decorator that makes a generator-function into a function that will continue execution on next call
	"""
	a = []

	@functools.wraps(func)
	def decorated_func(*args, **kwds):
		if not a:
			a.append(func(*args, **kwds))
		try:
			a[0].next()
			return True
		except StopIteration:
			del a[:]
			return False

	return decorated_func


def async(func):
	"""
	Make a function mainloop friendly. the function will be called at the
	next mainloop idle state.

	>>> import misc
	>>> misc.validate_decorator(async)
	"""

	@functools.wraps(func)
	def new_function(*args, **kwargs):

		def async_function():
			func(*args, **kwargs)
			return False

		gobject.idle_add(async_function)

	return new_function


class Async(object):

	def __init__(self, func, once = True):
		self.__func = func
		self.__idleId = None
		self.__once = once

	def start(self):
		assert self.__idleId is None
		if self.__once:
			self.__idleId = gobject.idle_add(self._on_once)
		else:
			self.__idleId = gobject.idle_add(self.__func)

	def cancel(self):
		if self.__idleId is not None:
			gobject.source_remove(self.__idleId)
			self.__idleId = None

	def __call__(self):
		return self.start()

	@misc.log_exception(_moduleLogger)
	def _on_once(self):
		self.cancel()
		try:
			self.__func()
		finally:
			return False


class Timeout(object):

	def __init__(self, func):
		self.__func = func
		self.__timeoutId = None

	def start(self, **kwds):
		assert self.__timeoutId is None

		assert len(kwds) == 1
		timeoutInSeconds = kwds["seconds"]
		assert 0 <= timeoutInSeconds
		if timeoutInSeconds == 0:
			self.__timeoutId = gobject.idle_add(self._on_once)
		else:
			timeout_add_seconds(timeoutInSeconds, self._on_once)

	def cancel(self):
		if self.__timeoutId is not None:
			gobject.source_remove(self.__timeoutId)
			self.__timeoutId = None

	def __call__(self, **kwds):
		return self.start(**kwds)

	@misc.log_exception(_moduleLogger)
	def _on_once(self):
		self.cancel()
		try:
			self.__func()
		finally:
			return False


def throttled(minDelay, queue):
	"""
	Throttle the calls to a function by queueing all the calls that happen
	before the minimum delay

	>>> import misc
	>>> import Queue
	>>> misc.validate_decorator(throttled(0, Queue.Queue()))
	"""

	def actual_decorator(func):

		lastCallTime = [None]

		def process_queue():
			if 0 < len(queue):
				func, args, kwargs = queue.pop(0)
				lastCallTime[0] = time.time() * 1000
				func(*args, **kwargs)
			return False

		@functools.wraps(func)
		def new_function(*args, **kwargs):
			now = time.time() * 1000
			if (
				lastCallTime[0] is None or
				(now - lastCallTime >= minDelay)
			):
				lastCallTime[0] = now
				func(*args, **kwargs)
			else:
				queue.append((func, args, kwargs))
				lastCallDelta = now - lastCallTime[0]
				processQueueTimeout = int(minDelay * len(queue) - lastCallDelta)
				gobject.timeout_add(processQueueTimeout, process_queue)

		return new_function

	return actual_decorator


def _old_timeout_add_seconds(timeout, callback):
	return gobject.timeout_add(timeout * 1000, callback)


def _timeout_add_seconds(timeout, callback):
	return gobject.timeout_add_seconds(timeout, callback)


try:
	gobject.timeout_add_seconds
	timeout_add_seconds = _timeout_add_seconds
except AttributeError:
	timeout_add_seconds = _old_timeout_add_seconds
