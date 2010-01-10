#!/usr/bin/python

from __future__ import with_statement

import os
import errno
import time
import functools
import contextlib
import logging
import threading
import Queue


_moduleLogger = logging.getLogger("gtk_toolbox")


@contextlib.contextmanager
def flock(path, timeout=-1):
	WAIT_FOREVER = -1
	DELAY = 0.1
	timeSpent = 0

	acquired = False

	while timeSpent <= timeout or timeout == WAIT_FOREVER:
		try:
			fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_RDWR)
			acquired = True
			break
		except OSError, e:
			if e.errno != errno.EEXIST:
				raise
		time.sleep(DELAY)
		timeSpent += DELAY

	assert acquired, "Failed to grab file-lock %s within timeout %d" % (path, timeout)

	try:
		yield fd
	finally:
		os.unlink(path)


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


def autostart(func):
	"""
	>>> @autostart
	... def grep_sink(pattern):
	... 	print "Looking for %s" % pattern
	... 	while True:
	... 		line = yield
	... 		if pattern in line:
	... 			print line,
	>>> g = grep_sink("python")
	Looking for python
	>>> g.send("Yeah but no but yeah but no")
	>>> g.send("A series of tubes")
	>>> g.send("python generators rock!")
	python generators rock!
	>>> g.close()
	"""

	@functools.wraps(func)
	def start(*args, **kwargs):
		cr = func(*args, **kwargs)
		cr.next()
		return cr

	return start


@autostart
def printer_sink(format = "%s"):
	"""
	>>> pr = printer_sink("%r")
	>>> pr.send("Hello")
	'Hello'
	>>> pr.send("5")
	'5'
	>>> pr.send(5)
	5
	>>> p = printer_sink()
	>>> p.send("Hello")
	Hello
	>>> p.send("World")
	World
	>>> # p.throw(RuntimeError, "Goodbye")
	>>> # p.send("Meh")
	>>> # p.close()
	"""
	while True:
		item = yield
		print format % (item, )


@autostart
def null_sink():
	"""
	Good for uses like with cochain to pick up any slack
	"""
	while True:
		item = yield


@autostart
def comap(function, target):
	"""
	>>> p = printer_sink()
	>>> cm = comap(lambda x: x+1, p)
	>>> cm.send((0, ))
	1
	>>> cm.send((1.0, ))
	2.0
	>>> cm.send((-2, ))
	-1
	"""
	while True:
		try:
			item = yield
			mappedItem = function(*item)
			target.send(mappedItem)
		except Exception, e:
			_moduleLogger.exception("Forwarding exception!")
			target.throw(e.__class__, str(e))


def _flush_queue(queue):
	while not queue.empty():
		yield queue.get()


@autostart
def queue_sink(queue):
	"""
	>>> q = Queue.Queue()
	>>> qs = queue_sink(q)
	>>> qs.send("Hello")
	>>> qs.send("World")
	>>> qs.throw(RuntimeError, "Goodbye")
	>>> qs.send("Meh")
	>>> qs.close()
	>>> print [i for i in _flush_queue(q)]
	[(None, 'Hello'), (None, 'World'), (<type 'exceptions.RuntimeError'>, 'Goodbye'), (None, 'Meh'), (<type 'exceptions.GeneratorExit'>, None)]
	"""
	while True:
		try:
			item = yield
			queue.put((None, item))
		except Exception, e:
			queue.put((e.__class__, str(e)))
		except GeneratorExit:
			queue.put((GeneratorExit, None))
			raise


def decode_item(item, target):
	if item[0] is None:
		target.send(item[1])
		return False
	elif item[0] is GeneratorExit:
		target.close()
		return True
	else:
		target.throw(item[0], item[1])
		return False


def nonqueue_source(queue, target):
	isDone = False
	while not isDone:
		item = queue.get()
		isDone = decode_item(item, target)
		while not queue.empty():
			queue.get_nowait()


def threaded_stage(target, thread_factory = threading.Thread):
	messages = Queue.Queue()

	run_source = functools.partial(nonqueue_source, messages, target)
	thread = thread_factory(target=run_source)
	thread.setDaemon(True)
	thread.start()

	# Sink running in current thread
	return queue_sink(messages)


def safecall(f, errorDisplay=None, default=None, exception=Exception):
	'''
	Returns modified f. When the modified f is called and throws an
	exception, the default value is returned
	'''
	def _safecall(*args, **argv):
		try:
			return f(*args, **argv)
		except exception, e:
			if errorDisplay is not None:
				errorDisplay.push_exception(e)
			return default
	return _safecall


def log_call(logger):

	def log_call_decorator(func):

		@functools.wraps(func)
		def wrapper(*args, **kwds):
			_moduleLogger.info("-> %s" % (func.__name__, ))
			try:
				return func(*args, **kwds)
			finally:
				_moduleLogger.info("<- %s" % (func.__name__, ))

		return wrapper

	return log_call_decorator


def log_exception(logger):

	def log_exception_decorator(func):

		@functools.wraps(func)
		def wrapper(*args, **kwds):
			try:
				return func(*args, **kwds)
			except Exception:
				logger.exception(func.__name__)
				raise

		return wrapper

	return log_exception_decorator


def trace(logger):

	def trace_decorator(func):

		@functools.wraps(func)
		def wrapper(*args, **kwds):
			try:
				logger.info("> %s" % (func.__name__, ))
				return func(*args, **kwds)
			except Exception:
				logger.exception(func.__name__)
				raise
			finally:
				logger.info("< %s" % (func.__name__, ))

		return wrapper

	return trace_decorator
