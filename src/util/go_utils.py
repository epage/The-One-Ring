#!/usr/bin/env python

from __future__ import with_statement

import time
import functools

import gobject


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
