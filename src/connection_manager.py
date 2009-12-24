"""
Empathy Experience:
	Can't call
	When first started, reports all read conversations when some might have been read
	When first started, reports all of an SMS conversation even though some has been reported previously
	Still leaking one of two contact lists
"""

import logging

import gobject
import telepathy

import constants
import gtk_toolbox
import connection


_moduleLogger = logging.getLogger("connection_manager")


class TheOneRingConnectionManager(telepathy.server.ConnectionManager):

	def __init__(self, shutdown_func=None):
		telepathy.server.ConnectionManager.__init__(self, constants._telepathy_implementation_name_)

		# self._protos is from super
		self._protos[constants._telepathy_protocol_name_] = connection.TheOneRingConnection
		self._on_shutdown = shutdown_func
		_moduleLogger.info("Connection manager created")

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetParameters(self, proto):
		"""
		For org.freedesktop.telepathy.ConnectionManager

		@returns the mandatory and optional parameters for creating a connection
		"""
		if proto not in self._protos:
			raise telepathy.errors.NotImplemented('unknown protocol %s' % proto)

		result = []
		ConnectionClass = self._protos[proto]
		mandatoryParameters = ConnectionClass._mandatory_parameters
		optionalParameters = ConnectionClass._optional_parameters
		defaultParameters = ConnectionClass._parameter_defaults

		for parameterName, parameterType in mandatoryParameters.iteritems():
			flags = telepathy.CONN_MGR_PARAM_FLAG_REQUIRED
			if parameterName == "password":
				flags |= telepathy.CONN_MGR_PARAM_FLAG_SECRET
			param = (
				parameterName,
				flags,
				parameterType,
				'',
			)
			result.append(param)

		for parameterName, parameterType in optionalParameters.iteritems():
			if parameterName in defaultParameters:
				flags = telepathy.CONN_MGR_PARAM_FLAG_HAS_DEFAULT
				if parameterName == "password":
					flags |= telepathy.CONN_MGR_PARAM_FLAG_SECRET
				default = defaultParameters[parameterName]
			else:
				flags = 0
				default = ""
			param = (
				parameterName,
				flags,
				parameterName,
				default,
			)
			result.append(param)

		return result

	def disconnected(self, conn):
		"""
		Overrides telepathy.server.ConnectionManager
		"""
		result = telepathy.server.ConnectionManager.disconnected(self, conn)
		gobject.timeout_add(5000, self._shutdown)

	def quit(self):
		"""
		Terminates all connections. Must be called upon quit
		"""
		for connection in self._connections:
			connection.Disconnect()
		_moduleLogger.info("Connection manager quitting")

	@gtk_toolbox.log_exception(_moduleLogger)
	def _shutdown(self):
		if (
			self._on_shutdown is not None and
			len(self._connections) == 0
		):
			self._on_shutdown()
		return False
