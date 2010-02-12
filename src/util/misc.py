#!/usr/bin/env python

from __future__ import with_statement

import sys
import re
import cPickle

import functools
import contextlib
import inspect

import optparse
import traceback
import warnings
import string


_indentationLevel = [0]


def log_call(logger):

	def log_call_decorator(func):

		@functools.wraps(func)
		def wrapper(*args, **kwds):
			logger.debug("%s> %s" % (" " * _indentationLevel[0], func.__name__, ))
			_indentationLevel[0] += 1
			try:
				return func(*args, **kwds)
			finally:
				_indentationLevel[0] -= 1
				logger.debug("%s< %s" % (" " * _indentationLevel[0], func.__name__, ))

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


def printfmt(template):
	"""
	This hides having to create the Template object and call substitute/safe_substitute on it. For example:

	>>> num = 10
	>>> word = "spam"
	>>> printfmt("I would like to order $num units of $word, please") #doctest: +SKIP
	I would like to order 10 units of spam, please
	"""
	frame = inspect.stack()[-1][0]
	try:
		print string.Template(template).safe_substitute(frame.f_locals)
	finally:
		del frame


def is_special(name):
	return name.startswith("__") and name.endswith("__")


def is_private(name):
	return name.startswith("_") and not is_special(name)


def privatize(clsName, attributeName):
	"""
	At runtime, make an attributeName private

	Example:
	>>> class Test(object):
	... 	pass
	...
	>>> try:
	... 	dir(Test).index("_Test__me")
	... 	print dir(Test)
	... except:
	... 	print "Not Found"
	Not Found
	>>> setattr(Test, privatize(Test.__name__, "me"), "Hello World")
	>>> try:
	... 	dir(Test).index("_Test__me")
	... 	print "Found"
	... except:
	... 	print dir(Test)
	0
	Found
	>>> print getattr(Test, obfuscate(Test.__name__, "__me"))
	Hello World
	>>>
	>>> is_private(privatize(Test.__name__, "me"))
	True
	>>> is_special(privatize(Test.__name__, "me"))
	False
	"""
	return "".join(["_", clsName, "__", attributeName])


def obfuscate(clsName, attributeName):
	"""
	At runtime, turn a private name into the obfuscated form

	Example:
	>>> class Test(object):
	... 	__me = "Hello World"
	...
	>>> try:
	... 	dir(Test).index("_Test__me")
	... 	print "Found"
	... except:
	... 	print dir(Test)
	0
	Found
	>>> print getattr(Test, obfuscate(Test.__name__, "__me"))
	Hello World
	>>> is_private(obfuscate(Test.__name__, "__me"))
	True
	>>> is_special(obfuscate(Test.__name__, "__me"))
	False
	"""
	return "".join(["_", clsName, attributeName])


class PAOptionParser(optparse.OptionParser, object):
	"""
	>>> if __name__ == '__main__':
	... 	#parser = PAOptionParser("My usage str")
	... 	parser = PAOptionParser()
	... 	parser.add_posarg("Foo", help="Foo usage")
	... 	parser.add_posarg("Bar", dest="bar_dest")
	... 	parser.add_posarg("Language", dest='tr_type', type="choice", choices=("Python", "Other"))
	... 	parser.add_option('--stocksym', dest='symbol')
	... 	values, args = parser.parse_args()
	... 	print values, args
	...

	python mycp.py  -h
	python mycp.py
	python mycp.py  foo
	python mycp.py  foo bar

	python mycp.py foo bar lava
	Usage: pa.py <Foo> <Bar> <Language> [options]

	Positional Arguments:
	Foo: Foo usage
	Bar:
	Language:

	pa.py: error: option --Language: invalid choice: 'lava' (choose from 'Python', 'Other'
	"""

	def __init__(self, *args, **kw):
		self.posargs = []
		super(PAOptionParser, self).__init__(*args, **kw)

	def add_posarg(self, *args, **kw):
		pa_help = kw.get("help", "")
		kw["help"] = optparse.SUPPRESS_HELP
		o = self.add_option("--%s" % args[0], *args[1:], **kw)
		self.posargs.append((args[0], pa_help))

	def get_usage(self, *args, **kwargs):
		params = (' '.join(["<%s>" % arg[0] for arg in self.posargs]), '\n '.join(["%s: %s" % (arg) for arg in self.posargs]))
		self.usage = "%%prog %s [options]\n\nPositional Arguments:\n %s" % params
		return super(PAOptionParser, self).get_usage(*args, **kwargs)

	def parse_args(self, *args, **kwargs):
		args = sys.argv[1:]
		args0 = []
		for p, v in zip(self.posargs, args):
			args0.append("--%s" % p[0])
			args0.append(v)
		args = args0 + args
		options, args = super(PAOptionParser, self).parse_args(args, **kwargs)
		if len(args) < len(self.posargs):
			msg = 'Missing value(s) for "%s"\n' % ", ".join([arg[0] for arg in self.posargs][len(args):])
			self.error(msg)
		return options, args


def explicitly(name, stackadd=0):
	"""
	This is an alias for adding to '__all__'.  Less error-prone than using
	__all__ itself, since setting __all__ directly is prone to stomping on
	things implicitly exported via L{alias}.

	@note Taken from PyExport (which could turn out pretty cool):
	@li @a http://codebrowse.launchpad.net/~glyph/
	@li @a http://glyf.livejournal.com/74356.html
	"""
	packageVars = sys._getframe(1+stackadd).f_locals
	globalAll = packageVars.setdefault('__all__', [])
	globalAll.append(name)


def public(thunk):
	"""
	This is a decorator, for convenience.  Rather than typing the name of your
	function twice, you can decorate a function with this.

	To be real, @public would need to work on methods as well, which gets into
	supporting types...

	@note Taken from PyExport (which could turn out pretty cool):
	@li @a http://codebrowse.launchpad.net/~glyph/
	@li @a http://glyf.livejournal.com/74356.html
	"""
	explicitly(thunk.__name__, 1)
	return thunk


def _append_docstring(obj, message):
	if obj.__doc__ is None:
		obj.__doc__ = message
	else:
		obj.__doc__ += message


def validate_decorator(decorator):

	def simple(x):
		return x

	f = simple
	f.__name__ = "name"
	f.__doc__ = "doc"
	f.__dict__["member"] = True

	g = decorator(f)

	if f.__name__ != g.__name__:
		print f.__name__, "!=", g.__name__

	if g.__doc__ is None:
		print decorator.__name__, "has no doc string"
	elif not g.__doc__.startswith(f.__doc__):
		print g.__doc__, "didn't start with", f.__doc__

	if not ("member" in g.__dict__ and g.__dict__["member"]):
		print "'member' not in ", g.__dict__


def deprecated_api(func):
	"""
	This is a decorator which can be used to mark functions
	as deprecated. It will result in a warning being emitted
	when the function is used.

	>>> validate_decorator(deprecated_api)
	"""

	@functools.wraps(func)
	def newFunc(*args, **kwargs):
		warnings.warn("Call to deprecated function %s." % func.__name__, category=DeprecationWarning)
		return func(*args, **kwargs)

	_append_docstring(newFunc, "\n@deprecated")
	return newFunc


def unstable_api(func):
	"""
	This is a decorator which can be used to mark functions
	as deprecated. It will result in a warning being emitted
	when the function is used.

	>>> validate_decorator(unstable_api)
	"""

	@functools.wraps(func)
	def newFunc(*args, **kwargs):
		warnings.warn("Call to unstable API function %s." % func.__name__, category=FutureWarning)
		return func(*args, **kwargs)
	_append_docstring(newFunc, "\n@unstable")
	return newFunc


def enabled(func):
	"""
	This decorator doesn't add any behavior

	>>> validate_decorator(enabled)
	"""
	return func


def disabled(func):
	"""
	This decorator disables the provided function, and does nothing

	>>> validate_decorator(disabled)
	"""

	@functools.wraps(func)
	def emptyFunc(*args, **kargs):
		pass
	_append_docstring(emptyFunc, "\n@note Temporarily Disabled")
	return emptyFunc


def metadata(document=True, **kwds):
	"""
	>>> validate_decorator(metadata(author="Ed"))
	"""

	def decorate(func):
		for k, v in kwds.iteritems():
			setattr(func, k, v)
			if document:
				_append_docstring(func, "\n@"+k+" "+v)
		return func
	return decorate


def prop(func):
	"""Function decorator for defining property attributes

	The decorated function is expected to return a dictionary
	containing one or more of the following pairs:
		fget - function for getting attribute value
		fset - function for setting attribute value
		fdel - function for deleting attribute
	This can be conveniently constructed by the locals() builtin
	function; see:
	http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/205183
	@author http://kbyanc.blogspot.com/2007/06/python-property-attribute-tricks.html

	Example:
	>>> #Due to transformation from function to property, does not need to be validated
	>>> #validate_decorator(prop)
	>>> class MyExampleClass(object):
	...	@prop
	...	def foo():
	...		"The foo property attribute's doc-string"
	...		def fget(self):
	...			print "GET"
	...			return self._foo
	...		def fset(self, value):
	...			print "SET"
	...			self._foo = value
	...		return locals()
	...
	>>> me = MyExampleClass()
	>>> me.foo = 10
	SET
	>>> print me.foo
	GET
	10
	"""
	return property(doc=func.__doc__, **func())


def print_handler(e):
	"""
	@see ExpHandler
	"""
	print "%s: %s" % (type(e).__name__, e)


def print_ignore(e):
	"""
	@see ExpHandler
	"""
	print 'Ignoring %s exception: %s' % (type(e).__name__, e)


def print_traceback(e):
	"""
	@see ExpHandler
	"""
	#print sys.exc_info()
	traceback.print_exc(file=sys.stdout)


def ExpHandler(handler = print_handler, *exceptions):
	"""
	An exception handling idiom using decorators
	Examples
	Specify exceptions in order, first one is handled first
	last one last.

	>>> validate_decorator(ExpHandler())
	>>> @ExpHandler(print_ignore, ZeroDivisionError)
	... @ExpHandler(None, AttributeError, ValueError)
	... def f1():
	... 	1/0
	>>> @ExpHandler(print_traceback, ZeroDivisionError)
	... def f2():
	... 	1/0
	>>> @ExpHandler()
	... def f3(*pargs):
	...	l = pargs
	... 	return l[10]
	>>> @ExpHandler(print_traceback, ZeroDivisionError)
	... def f4():
	... 	return 1
	>>>
	>>>
	>>> f1()
	Ignoring ZeroDivisionError exception: integer division or modulo by zero
	>>> f2() # doctest: +ELLIPSIS, +NORMALIZE_WHITESPACE
	Traceback (most recent call last):
	...
	ZeroDivisionError: integer division or modulo by zero
	>>> f3()
	IndexError: tuple index out of range
	>>> f4()
	1
	"""

	def wrapper(f):
		localExceptions = exceptions
		if not localExceptions:
			localExceptions = [Exception]
		t = [(ex, handler) for ex in localExceptions]
		t.reverse()

		def newfunc(t, *args, **kwargs):
			ex, handler = t[0]
			try:
				if len(t) == 1:
					return f(*args, **kwargs)
				else:
					#Recurse for embedded try/excepts
					dec_func = functools.partial(newfunc, t[1:])
					dec_func = functools.update_wrapper(dec_func, f)
					return dec_func(*args, **kwargs)
			except ex, e:
				return handler(e)

		dec_func = functools.partial(newfunc, t)
		dec_func = functools.update_wrapper(dec_func, f)
		return dec_func
	return wrapper


def into_debugger(func):
	"""
	>>> validate_decorator(into_debugger)
	"""

	@functools.wraps(func)
	def newFunc(*args, **kwargs):
		try:
			return func(*args, **kwargs)
		except:
			import pdb
			pdb.post_mortem()

	return newFunc


class bindclass(object):
	"""
	>>> validate_decorator(bindclass)
	>>> class Foo(BoundObject):
	...	 @bindclass
	...	 def foo(this_class, self):
	...		 return this_class, self
	...
	>>> class Bar(Foo):
	...	 @bindclass
	...	 def bar(this_class, self):
	...		 return this_class, self
	...
	>>> f = Foo()
	>>> b = Bar()
	>>>
	>>> f.foo() # doctest: +ELLIPSIS
	(<class '...Foo'>, <...Foo object at ...>)
	>>> b.foo() # doctest: +ELLIPSIS
	(<class '...Foo'>, <...Bar object at ...>)
	>>> b.bar() # doctest: +ELLIPSIS
	(<class '...Bar'>, <...Bar object at ...>)
	"""

	def __init__(self, f):
		self.f = f
		self.__name__ = f.__name__
		self.__doc__ = f.__doc__
		self.__dict__.update(f.__dict__)
		self.m = None

	def bind(self, cls, attr):

		def bound_m(*args, **kwargs):
			return self.f(cls, *args, **kwargs)
		bound_m.__name__ = attr
		self.m = bound_m

	def __get__(self, obj, objtype=None):
		return self.m.__get__(obj, objtype)


class ClassBindingSupport(type):
	"@see bindclass"

	def __init__(mcs, name, bases, attrs):
		type.__init__(mcs, name, bases, attrs)
		for attr, val in attrs.iteritems():
			if isinstance(val, bindclass):
				val.bind(mcs, attr)


class BoundObject(object):
	"@see bindclass"
	__metaclass__ = ClassBindingSupport


def bindfunction(f):
	"""
	>>> validate_decorator(bindfunction)
	>>> @bindfunction
	... def factorial(thisfunction, n):
	...	 # Within this function the name 'thisfunction' refers to the factorial
	...	 # function(with only one argument), even after 'factorial' is bound
	...	 # to another object
	...	 if n > 0:
	...		 return n * thisfunction(n - 1)
	...	 else:
	...		 return 1
	...
	>>> factorial(3)
	6
	"""

	@functools.wraps(f)
	def bound_f(*args, **kwargs):
		return f(bound_f, *args, **kwargs)
	return bound_f


class Memoize(object):
	"""
	Memoize(fn) - an instance which acts like fn but memoizes its arguments
	Will only work on functions with non-mutable arguments
	@note Source: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52201

	>>> validate_decorator(Memoize)
	"""

	def __init__(self, fn):
		self.fn = fn
		self.__name__ = fn.__name__
		self.__doc__ = fn.__doc__
		self.__dict__.update(fn.__dict__)
		self.memo = {}

	def __call__(self, *args):
		if args not in self.memo:
			self.memo[args] = self.fn(*args)
		return self.memo[args]


class MemoizeMutable(object):
	"""Memoize(fn) - an instance which acts like fn but memoizes its arguments
	Will work on functions with mutable arguments(slower than Memoize)
	@note Source: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52201

	>>> validate_decorator(MemoizeMutable)
	"""

	def __init__(self, fn):
		self.fn = fn
		self.__name__ = fn.__name__
		self.__doc__ = fn.__doc__
		self.__dict__.update(fn.__dict__)
		self.memo = {}

	def __call__(self, *args, **kw):
		text = cPickle.dumps((args, kw))
		if text not in self.memo:
			self.memo[text] = self.fn(*args, **kw)
		return self.memo[text]


callTraceIndentationLevel = 0


def call_trace(f):
	"""
	Synchronization decorator.

	>>> validate_decorator(call_trace)
	>>> @call_trace
	... def a(a, b, c):
	... 	pass
	>>> a(1, 2, c=3)
	Entering a((1, 2), {'c': 3})
	Exiting a((1, 2), {'c': 3})
	"""

	@functools.wraps(f)
	def verboseTrace(*args, **kw):
		global callTraceIndentationLevel

		print "%sEntering %s(%s, %s)" % ("\t"*callTraceIndentationLevel, f.__name__, args, kw)
		callTraceIndentationLevel += 1
		try:
			result = f(*args, **kw)
		except:
			callTraceIndentationLevel -= 1
			print "%sException %s(%s, %s)" % ("\t"*callTraceIndentationLevel, f.__name__, args, kw)
			raise
		callTraceIndentationLevel -= 1
		print "%sExiting %s(%s, %s)" % ("\t"*callTraceIndentationLevel, f.__name__, args, kw)
		return result

	@functools.wraps(f)
	def smallTrace(*args, **kw):
		global callTraceIndentationLevel

		print "%sEntering %s" % ("\t"*callTraceIndentationLevel, f.__name__)
		callTraceIndentationLevel += 1
		try:
			result = f(*args, **kw)
		except:
			callTraceIndentationLevel -= 1
			print "%sException %s" % ("\t"*callTraceIndentationLevel, f.__name__)
			raise
		callTraceIndentationLevel -= 1
		print "%sExiting %s" % ("\t"*callTraceIndentationLevel, f.__name__)
		return result

	#return smallTrace
	return verboseTrace


@contextlib.contextmanager
def lexical_scope(*args):
	"""
	@note Source: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/520586
	Example:
	>>> b = 0
	>>> with lexical_scope(1) as (a):
	... 	print a
	...
	1
	>>> with lexical_scope(1,2,3) as (a,b,c):
	... 	print a,b,c
	...
	1 2 3
	>>> with lexical_scope():
	... 	d = 10
	... 	def foo():
	... 		pass
	...
	>>> print b
	2
	"""

	frame = inspect.currentframe().f_back.f_back
	saved = frame.f_locals.keys()
	try:
		if not args:
			yield
		elif len(args) == 1:
			yield args[0]
		else:
			yield args
	finally:
		f_locals = frame.f_locals
		for key in (x for x in f_locals.keys() if x not in saved):
			del f_locals[key]
		del frame


def normalize_number(prettynumber):
	"""
	function to take a phone number and strip out all non-numeric
	characters

	>>> normalize_number("+012-(345)-678-90")
	'+01234567890'
	>>> normalize_number("1-(345)-678-9000")
	'+13456789000'
	>>> normalize_number("+1-(345)-678-9000")
	'+13456789000'
	"""
	uglynumber = re.sub('[^0-9+]', '', prettynumber)
	if uglynumber.startswith("+"):
		pass
	elif uglynumber.startswith("1") and len(uglynumber) == 11:
		uglynumber = "+"+uglynumber
	elif len(uglynumber) == 10:
		uglynumber = "+1"+uglynumber
	else:
		pass

	#validateRe = re.compile("^\+?[0-9]{10,}$")
	#assert validateRe.match(uglynumber) is not None

	return uglynumber


_VALIDATE_RE = re.compile("^\+?[0-9]{10,}$")


def is_valid_number(number):
	"""
	@returns If This number be called ( syntax validation only )
	"""
	return _VALIDATE_RE.match(number) is not None
