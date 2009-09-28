import logging

import gobject
import telepathy

import constants
import connection


_moduleLogger = logging.getLogger("connection_manager")


class TheOneRingConnectionManager(telepathy.server.ConnectionManager):

	def __init__(self, shutdown_func=None):
		telepathy.server.ConnectionManager.__init__(self, constants._telepathy_implementation_name_)

		self._protos[constants._telepathy_protocol_name_] = connection.TheOneRingConnection
		self._on_shutdown = shutdown_func
		_moduleLogger.info("Connection manager created")

	def GetParameters(self, proto):
		"""
		For org.freedesktop.telepathy.ConnectionManager

		@returns the mandatory and optional parameters for creating a connection
		"""
		if proto not in self._protos:
			raise telepathy.NotImplemented('unknown protocol %s' % proto)

		result = []
		ConnectionClass = self._protos[proto]
		mandatoryParameters = ConnectionClass.MANDATORY_PARAMETERS
		optionalParameters = ConnectionClass.OPTIONAL_PARAMETERS
		defaultParameters = ConnectionClass.PARAMETER_DEFAULTS

		for parameterName, parameterType in mandatoryParameters.iteritems():
			param = (
				parameterName,
				telepathy.CONN_MGR_PARAM_FLAG_REQUIRED,
				parameterType,
				'',
			)
			result.append(param)

		for parameterName, parameterType in optionalParameters.iteritems():
			if parameterName in defaultParameters:
				param = (
					parameterName,
					telepathy.CONN_MGR_PARAM_FLAG_HAS_DEFAULT,
					parameterName,
					defaultParameters[parameterName],
				)
			else:
				param = (parameterName, 0, parameterName, '')
			result.append(param)

		return result

	def disconnected(self, conn):
		"""
		Overrides telepathy.server.ConnectionManager
		"""
		result = telepathy.server.ConnectionManager.disconnected(self, conn)
		gobject.timeout_add(5000, self.shutdown)

	def quit(self):
		"""
		Terminates all connections. Must be called upon quit
		"""
		for connection in self._connections:
			connection.Disconnect()
		_moduleLogger.info("Connection manager quitting")

	def _shutdown(self):
		if (
			self._on_shutdown is not None and
			len(self._connections) == 0
		):
			self._on_shutdown()
		return False
