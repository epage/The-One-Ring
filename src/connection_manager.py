import logging

import gobject
import telepathy

import connection


class TheOneRingConnectionManager(telepathy.server.ConnectionManager):

	def __init__(self, shutdown_func=None):
		telepathy.server.ConnectionManager.__init__(self, 'theonering')

		self._protos['gvoice'] = connection.TheOneRingConnection
		self._on_shutdown = shutdown_func
		logging.info("Connection manager created")

	def GetParameters(self, proto):
		"""
		org.freedesktop.telepathy.ConnectionManager

		@returns the mandatory and optional parameters for creating a connection
		"""
		if proto not in self._protos:
			raise telepathy.NotImplemented('unknown protocol %s' % proto)

		result = []
		connection_class = self._protos[proto]
		mandatory_parameters = connection_class._mandatory_parameters
		optional_parameters = connection_class._optional_parameters
		default_parameters = connection_class._parameter_defaults

		for parameter_name, parameter_type in mandatory_parameters.iteritems():
			param = (
				parameter_name,
				telepathy.CONN_MGR_PARAM_FLAG_REQUIRED,
				parameter_type,
				'',
			)
			result.append(param)

		for parameter_name, parameter_type in optional_parameters.iteritems():
			if parameter_name in default_parameters:
				param = (
					parameter_name,
					telepathy.CONN_MGR_PARAM_FLAG_HAS_DEFAULT,
					parameter_name,
					default_parameters[parameter_name],
				)
			else:
				param = (parameter_name, 0, parameter_name, '')
			result.append(param)

		return result

	def disconnected(self, conn):
		result = telepathy.server.ConnectionManager.disconnected(self, conn)
		gobject.timeout_add(5000, self.shutdown)

	def quit(self):
		"""
		Terminates all connections. Must be called upon quit
		"""
		for connection in self._connections:
			connection.Disconnect()
		logging.info("Connection manager quitting")

	def _shutdown(self):
		if (
			self._on_shutdown is not None and
			len(self._connections) == 0
		):
			self._on_shutdown()
		return False
