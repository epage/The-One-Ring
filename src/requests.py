import logging

import dbus
import telepathy
import gtk_toolbox


_moduleLogger = logging.getLogger('requests')


class RequestsMixin(
	telepathy._generated.Connection_Interface_Requests.ConnectionInterfaceRequests,
	telepathy.server.properties.DBusProperties
):
	"""
	HACK older python-telepathy doesn't provide an implementation but the new one does, ARGH
	"""

	def __init__(self):
		telepathy._generated.Connection_Interface_Requests.ConnectionInterfaceRequests.__init__(self)
		telepathy.server.properties.DBusProperties.__init__(self)

		self._implement_property_get(telepathy.interfaces.CONNECTION_INTERFACE_REQUESTS,
			{'Channels': lambda: dbus.Array(self._get_channels(),
				signature='(oa{sv})'),
			'RequestableChannelClasses': lambda: dbus.Array(
				self._channel_manager.get_requestable_channel_classes(),
				signature='(a{sv}as)')})

	@property
	def _channel_manager(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	def _get_channels(self):
		return [(c._object_path, c.get_props()) for c in self._channels]

	def _check_basic_properties(self, props):
		# ChannelType must be present and must be a string.
		if telepathy.interfaces.CHANNEL_INTERFACE + '.ChannelType' not in props or \
				not isinstance(props[telepathy.interfaces.CHANNEL_INTERFACE + '.ChannelType'],
					dbus.String):
			raise telepathy.errors.InvalidArgument('ChannelType is required')

		def check_valid_type_if_exists(prop, fun):
			p = telepathy.interfaces.CHANNEL_INTERFACE + '.' + prop
			if p in props and not fun(props[p]):
				raise telepathy.errors.InvalidArgument('Invalid %s' % prop)

		# Allow TargetHandleType to be missing, but not to be otherwise broken.
		check_valid_type_if_exists('TargetHandleType',
			lambda p: p > 0 and p < (2**32)-1)

		# Allow TargetType to be missing, but not to be otherwise broken.
		check_valid_type_if_exists('TargetHandle',
			lambda p: p > 0 and p < (2**32)-1)
		if props.get(telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandle') == 0:
			raise telepathy.errors.InvalidArgument("TargetHandle may not be 0")

		# Allow TargetID to be missing, but not to be otherwise broken.
		check_valid_type_if_exists('TargetID',
			lambda p: isinstance(p, dbus.String))

		# Disallow InitiatorHandle, InitiatorID and Requested.
		check_valid_type_if_exists('InitiatorHandle', lambda p: False)
		check_valid_type_if_exists('InitiatorID', lambda p: False)
		check_valid_type_if_exists('Requested', lambda p: False)

		type = props[telepathy.interfaces.CHANNEL_INTERFACE + '.ChannelType']
		handle_type = props.get(telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandleType',
				telepathy.constants.HANDLE_TYPE_NONE)
		handle = props.get(telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandle', 0)

		return (type, handle_type, handle)

	def _validate_handle(self, props):
		target_handle_type = props.get(telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandleType',
			telepathy.constants.HANDLE_TYPE_NONE)
		target_handle = props.get(telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandle', None)
		target_id = props.get(telepathy.interfaces.CHANNEL_INTERFACE + '.TargetID', None)

		# Handle type 0 cannot have a handle.
		if target_handle_type == telepathy.constants.HANDLE_TYPE_NONE and target_handle != None:
			raise telepathy.errors.InvalidArgument('When TargetHandleType is NONE, ' +
				'TargetHandle must be omitted')

		# Handle type 0 cannot have a TargetID.
		if target_handle_type == telepathy.constants.HANDLE_TYPE_NONE and target_id != None:
			raise telepathy.errors.InvalidArgument('When TargetHandleType is NONE, TargetID ' +
				'must be omitted')

		if target_handle_type != telepathy.constants.HANDLE_TYPE_NONE:
			if target_handle == None and target_id == None:
				raise telepathy.errors.InvalidArgument('When TargetHandleType is not NONE, ' +
					'either TargetHandle or TargetID must also be given')

			if target_handle != None and target_id != None:
				raise telepathy.errors.InvalidArgument('TargetHandle and TargetID must not ' +
					'both be given')

			self.check_handle_type(target_handle_type)


	def _alter_properties(self, props):
		target_handle_type = props.get(telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandleType',
			telepathy.constants.HANDLE_TYPE_NONE)
		target_handle = props.get(telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandle', None)
		target_id = props.get(telepathy.interfaces.CHANNEL_INTERFACE + '.TargetID', None)

		altered_properties = props.copy()

		if target_handle_type != telepathy.constants.HANDLE_TYPE_NONE:
			if target_handle == None:
				# Turn TargetID into TargetHandle.
				for handle in self._handles.itervalues():
					if handle.get_name() == target_id and handle.get_type() == target_handle_type:
						target_handle = handle.get_id()
				if not target_handle:
					raise telepathy.errors.InvalidHandle('TargetID %s not valid for type %d' %
						(target_id, target_handle_type))

				altered_properties[telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandle'] = \
					target_handle
			else:
				# Check the supplied TargetHandle is valid
				self.check_handle(target_handle_type, target_handle)

				target_id = self._handles[target_handle_type,\
											target_handle].get_name()
				altered_properties[telepathy.interfaces.CHANNEL_INTERFACE + '.TargetID'] = \
					target_id

		altered_properties[telepathy.interfaces.CHANNEL_INTERFACE + '.Requested'] = True

		return altered_properties

	@dbus.service.method(telepathy.interfaces.CONNECTION_INTERFACE_REQUESTS,
		in_signature='a{sv}', out_signature='oa{sv}',
		async_callbacks=('_success', '_error'))
	def CreateChannel(self, request, _success, _error):
		_moduleLogger.info("CreateChannel")
		type, handle_type, handle = self._check_basic_properties(request)
		self._validate_handle(request)
		props = self._alter_properties(request)

		channel = self._channel_manager.channel_for_props(props, signal=False)

		# Remove mutable properties
		todel = []
		for prop in props:
			iface, name = prop.rsplit('.', 1) # a bit of a hack
			if name in channel._immutable_properties:
				if channel._immutable_properties[name] != iface:
					todel.append(prop)
			else:
				todel.append(prop)

		for p in todel:
			del props[p]

		_success(channel._object_path, props)

		# CreateChannel MUST return *before* NewChannels is emitted.
		# @bug On older python-telepathy, it doesn't exist
		self.signal_new_channels([channel])

	@dbus.service.method(telepathy.interfaces.CONNECTION_INTERFACE_REQUESTS,
		in_signature='a{sv}', out_signature='boa{sv}',
		async_callbacks=('_success', '_error'))
	def EnsureChannel(self, request, _success, _error):
		_moduleLogger.info("EnsureChannel")
		type, handle_type, handle = self._check_basic_properties(request)
		self._validate_handle(request)
		props = self._alter_properties(request)

		yours = not self._channel_manager.channel_exists(props)

		channel = self._channel_manager.channel_for_props(props, signal=False)

		_success(yours, channel._object_path, props)

		# @bug On older python-telepathy, it doesn't exist
		self.signal_new_channels([channel])
