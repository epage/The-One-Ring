import logging

import telepathy

import constants
import tp
import util.go_utils as gobject_utils
import util.misc as misc_utils
import connection


_moduleLogger = logging.getLogger(__name__)


class TheOneRingConnectionManager(tp.ConnectionManager):

	IDLE_TIMEOUT = 10

	def __init__(self, shutdown_func=None):
		tp.ConnectionManager.__init__(self, constants._telepathy_implementation_name_)

		# self._protos is from super
		self._protos[constants._telepathy_protocol_name_] = connection.TheOneRingConnection
		self._on_shutdown = shutdown_func
		_moduleLogger.info("Connection manager created")

	@misc_utils.log_exception(_moduleLogger)
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
		secretParameters = ConnectionClass._secret_parameters

		for parameterName, parameterType in mandatoryParameters.iteritems():
			flags = telepathy.CONN_MGR_PARAM_FLAG_REQUIRED
			if parameterName in secretParameters:
				flags |= telepathy.CONN_MGR_PARAM_FLAG_SECRET
			param = (parameterName, flags, parameterType, "")
			result.append(param)

		for parameterName, parameterType in optionalParameters.iteritems():
			flags = 0
			default = ""
			if parameterName in secretParameters:
				flags |= telepathy.CONN_MGR_PARAM_FLAG_SECRET
			if parameterName in defaultParameters:
				flags |= telepathy.CONN_MGR_PARAM_FLAG_HAS_DEFAULT
				default = defaultParameters[parameterName]
			param = (parameterName, flags, parameterType, default)
			result.append(param)

		return result

	def disconnected(self, conn):
		"""
		Overrides tp.ConnectionManager
		"""
		result = tp.ConnectionManager.disconnected(self, conn)
		gobject_utils.timeout_add_seconds(self.IDLE_TIMEOUT, self._shutdown)

	def quit(self):
		"""
		Terminates all connections. Must be called upon quit
		"""
		for conn in self._connections:
			conn.Disconnect()
		_moduleLogger.info("Connection manager quitting")

	@misc_utils.log_exception(_moduleLogger)
	def _shutdown(self):
		if (
			self._on_shutdown is not None and
			len(self._connections) == 0
		):
			self._on_shutdown()
		return False
