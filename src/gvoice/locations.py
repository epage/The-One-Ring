#!/usr/bin/python

from __future__ import with_statement

import re
import logging

try:
	import cPickle
	pickle = cPickle
except ImportError:
	import pickle

try:
	import simplejson as _simplejson
	simplejson = _simplejson
except ImportError:
	simplejson = None

import constants
import util.coroutines as coroutines
import util.misc as misc_utils
import util.go_utils as gobject_utils

import browser_emu


_moduleLogger = logging.getLogger(__name__)


class Locations(object):

	OLDEST_COMPATIBLE_FORMAT_VERSION = misc_utils.parse_version("0.8.0")

	def __init__(self, asyncPool):
		self._asyncPool = asyncPool
		self._locations = {}
		self._browser = browser_emu.MozillaEmulator()

		self.updateSignalHandler = coroutines.CoTee()

	def load(self, path):
		_moduleLogger.debug("Loading cache")
		assert not self._locations
		try:
			with open(path, "rb") as f:
				fileVersion, fileBuild, locs = pickle.load(f)
		except (pickle.PickleError, IOError, EOFError, ValueError, Exception):
			_moduleLogger.exception("While loading for %s" % self._name)
			return

		if misc_utils.compare_versions(
			self.OLDEST_COMPATIBLE_FORMAT_VERSION,
			misc_utils.parse_version(fileVersion),
		) <= 0:
			_moduleLogger.info("Loaded cache")
			self._locations = locs
		else:
			_moduleLogger.debug(
				"Skipping cache due to version mismatch (%s-%s)" % (
					fileVersion, fileBuild
				)
			)

	def save(self, path):
		_moduleLogger.info("Saving cache")
		if not self._locations:
			_moduleLogger.info("Odd, no conversations to cache.  Did we never load the cache?")
			return

		try:
			dataToDump = (constants.__version__, constants.__build__, self._locations)
			with open(path, "wb") as f:
				pickle.dump(dataToDump, f, pickle.HIGHEST_PROTOCOL)
		except (pickle.PickleError, IOError):
			_moduleLogger.exception("While saving for %s" % self._name)
		_moduleLogger.info("%s Cache saved" % (self._name, ))

	def request_location(self, number):
		try:
			return self._locations[number]
		except KeyError:
			le = gobject_utils.AsyncLinearExecution(self._asyncPool, self._request_location)
			le.start(number)
			return None

	def _download_location(self, number):
		numberURL = "http://digits.cloudvox.com/%s.json" % number
		page = self._browser.download(numberURL)
		data = parse_json(page)
		return data

	@misc_utils.log_exception(_moduleLogger)
	def _request_location(self, number):
		try:
			locationData = yield (
				self._download_location,
				(number, ),
				{},
			)
		except Exception:
			_moduleLogger.exception("%s While updating conversations" % (self._name, ))
			return

		self._locations[number] = locationData
		message = (locationData, )
		self.updateSignalHandler.stage.send(message)


def safe_eval(s):
	_TRUE_REGEX = re.compile("true")
	_FALSE_REGEX = re.compile("false")
	s = _TRUE_REGEX.sub("True", s)
	s = _FALSE_REGEX.sub("False", s)
	return eval(s, {}, {})


def _fake_parse_json(flattened):
	return safe_eval(flattened)


def _actual_parse_json(flattened):
	return simplejson.loads(flattened)


if simplejson is None:
	parse_json = _fake_parse_json
else:
	parse_json = _actual_parse_json
