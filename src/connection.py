
"""
@todo Add params for different state machines update times
@todo Add option to use screen name as callback
@todo Get a callback for missed calls to force an update of the voicemail state machine
@todo Get a callback on an incoming call and if its from GV, auto-pickup
@todo Observe when connected/disconnected to disconnect CM
"""


import weakref
import logging

import telepathy

try:
	import conic as _conic
	conic = _conic
except (ImportError, OSError):
	conic = None

import constants
import util.coroutines as coroutines
import gtk_toolbox

import gvoice
import handle

import requests
import contacts
import aliasing
import simple_presence
import presence
import capabilities

import channel_manager


_moduleLogger = logging.getLogger("connection")


class TheOneRingConnection(
	telepathy.server.Connection,
	requests.RequestsMixin,
	contacts.ContactsMixin,
	aliasing.AliasingMixin,
	simple_presence.SimplePresenceMixin,
	presence.PresenceMixin,
	capabilities.CapabilitiesMixin,
):

	# Overriding a base class variable
	# Should the forwarding number be handled by the alias or by an option?
	_mandatory_parameters = {
		'account' : 's',
		'password' : 's',
		'forward' : 's',
	}
	# Overriding a base class variable
	_optional_parameters = {
	}
	_parameter_defaults = {
	}

	@gtk_toolbox.log_exception(_moduleLogger)
	def __init__(self, manager, parameters):
		self.check_parameters(parameters)
		account = unicode(parameters['account'])
		encodedAccount = parameters['account'].encode('utf-8')
		encodedPassword = parameters['password'].encode('utf-8')
		encodedCallback = parameters['forward'].encode('utf-8')
		if not encodedCallback:
			raise telepathy.errors.InvalidArgument("User must specify what number GV forwards calls to")

		# Connection init must come first
		telepathy.server.Connection.__init__(
			self,
			constants._telepathy_protocol_name_,
			account,
			constants._telepathy_implementation_name_
		)
		#telepathy.server.ConnectionInterfaceRequests.__init__(self)
		requests.RequestsMixin.__init__(self)
		contacts.ContactsMixin.__init__(self)
		aliasing.AliasingMixin.__init__(self)
		simple_presence.SimplePresenceMixin.__init__(self)
		presence.PresenceMixin.__init__(self)
		capabilities.CapabilitiesMixin.__init__(self)

		self.__manager = weakref.proxy(manager)
		self.__credentials = (
			encodedAccount,
			encodedPassword,
		)
		self.__callbackNumber = encodedCallback
		self.__channelManager = channel_manager.ChannelManager(self)

		self.__session = gvoice.session.Session(None)
		if conic is not None:
			self.__connection = conic.Connection()
			self.__connectionEventId = None
		else:
			self.__connection = None
			self.__connectionEventId = None

		self.set_self_handle(handle.create_handle(self, 'connection'))

		self.__callback = None
		_moduleLogger.info("Connection to the account %s created" % account)

	@property
	def manager(self):
		return self.__manager

	@property
	def session(self):
		return self.__session

	@property
	def username(self):
		return self.__credentials[0]

	@property
	def userAliasType(self):
		return self.USER_ALIAS_ACCOUNT

	def handle(self, handleType, handleId):
		self.check_handle(handleType, handleId)
		return self._handles[handleType, handleId]

	@property
	def _channel_manager(self):
		return self.__channelManager

	@gtk_toolbox.log_exception(_moduleLogger)
	def Connect(self):
		"""
		For org.freedesktop.telepathy.Connection
		"""
		_moduleLogger.info("Connecting...")
		self.StatusChanged(
			telepathy.CONNECTION_STATUS_CONNECTING,
			telepathy.CONNECTION_STATUS_REASON_REQUESTED
		)
		try:
			cookieFilePath = None
			self.__session = gvoice.session.Session(cookieFilePath)

			self.__callback = coroutines.func_sink(
				coroutines.expand_positional(
					self._on_conversations_updated
				)
			)
			self.session.voicemails.updateSignalHandler.register_sink(
				self.__callback
			)
			self.session.texts.updateSignalHandler.register_sink(
				self.__callback
			)
			self.session.login(*self.__credentials)
			self.session.backend.set_callback_number(self.__callbackNumber)
		except gvoice.backend.NetworkError, e:
			_moduleLogger.exception("Connection Failed")
			self.StatusChanged(
				telepathy.CONNECTION_STATUS_DISCONNECTED,
				telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR
			)
			return
		except Exception, e:
			_moduleLogger.exception("Connection Failed")
			self.StatusChanged(
				telepathy.CONNECTION_STATUS_DISCONNECTED,
				telepathy.CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED
			)
			return

		_moduleLogger.info("Connected")
		self.StatusChanged(
			telepathy.CONNECTION_STATUS_CONNECTED,
			telepathy.CONNECTION_STATUS_REASON_REQUESTED
		)
		if self.__connection is not None:
			self.__connectionEventId = self.__connection.connect("connection-event", self._on_connection_change)

	@gtk_toolbox.log_exception(_moduleLogger)
	def Disconnect(self):
		"""
		For org.freedesktop.telepathy.Connection
		@bug Not properly logging out.  Cookie files need to be per connection and removed
		"""
		self.StatusChanged(
			telepathy.CONNECTION_STATUS_DISCONNECTED,
			telepathy.CONNECTION_STATUS_REASON_REQUESTED
		)
		try:
			self._disconnect()
		except Exception:
			_moduleLogger.exception("Error durring disconnect")

	@gtk_toolbox.log_exception(_moduleLogger)
	def RequestChannel(self, type, handleType, handleId, suppressHandler):
		"""
		For org.freedesktop.telepathy.Connection

		@param type DBus interface name for base channel type
		@param handleId represents a contact, list, etc according to handleType

		@returns DBus object path for the channel created or retrieved
		"""
		self.check_connected()
		self.check_handle(handleType, handleId)

		h = self.handle(handleType, handleId) if handleId != 0 else None
		props = self._generate_props(type, h, suppressHandler)
		if hasattr(self, "_validate_handle"):
			# HACK Newer python-telepathy
			self._validate_handle(props)

		chan = self.__channelManager.channel_for_props(props, signal=True)
		path = chan._object_path
		_moduleLogger.info("RequestChannel Object Path: %s" % path)
		return path

	@gtk_toolbox.log_exception(_moduleLogger)
	def RequestHandles(self, handleType, names, sender):
		"""
		For org.freedesktop.telepathy.Connection
		Overiding telepathy.server.Connecton to allow custom handles
		"""
		self.check_connected()
		self.check_handle_type(handleType)

		handles = []
		for name in names:
			requestedHandleName = name.encode('utf-8')
			if handleType == telepathy.HANDLE_TYPE_CONTACT:
				_moduleLogger.info("RequestHandles Contact: %s" % requestedHandleName)
				requestedContactId, requestedContactNumber = handle.ContactHandle.from_handle_name(
					requestedHandleName
				)
				h = handle.create_handle(self, 'contact', requestedContactId, requestedContactNumber)
			elif handleType == telepathy.HANDLE_TYPE_LIST:
				# Support only server side (immutable) lists
				_moduleLogger.info("RequestHandles List: %s" % requestedHandleName)
				h = handle.create_handle(self, 'list', requestedHandleName)
			else:
				raise telepathy.errors.NotAvailable('Handle type unsupported %d' % handleType)
			handles.append(h.id)
			self.add_client_handle(h, sender)
		return handles

	def _generate_props(self, channelType, handle, suppressHandler, initiatorHandle=None):
		targetHandle = 0 if handle is None else handle.get_id()
		targetHandleType = telepathy.HANDLE_TYPE_NONE if handle is None else handle.get_type()
		props = {
			telepathy.CHANNEL_INTERFACE + '.ChannelType': channelType,
			telepathy.CHANNEL_INTERFACE + '.TargetHandle': targetHandle,
			telepathy.CHANNEL_INTERFACE + '.TargetHandleType': targetHandleType,
			telepathy.CHANNEL_INTERFACE + '.Requested': suppressHandler
		}

		if initiatorHandle is not None:
			props[telepathy.CHANNEL_INTERFACE + '.InitiatorHandle'] = initiatorHandle.id

		return props

	def _disconnect(self):
		_moduleLogger.info("Disconnecting")
		self.session.voicemails.updateSignalHandler.unregister_sink(
			self.__callback
		)
		self.session.texts.updateSignalHandler.unregister_sink(
			self.__callback
		)
		self.__callback = None

		self.__channelManager.close()
		self.session.logout()
		self.session.close()
		self.__session = None
		if self.__connection is not None:
			self.__connection.disconnect(self.__connectionEventId)
			self.__connectionEventId = None

		self.manager.disconnected(self)
		_moduleLogger.info("Disconnected")

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_conversations_updated(self, conv, conversationIds):
		_moduleLogger.debug("Incoming messages from: %r" % (conversationIds, ))
		for contactId, phoneNumber in conversationIds:
			h = handle.create_handle(self, 'contact', contactId, phoneNumber)
			# Just let the TextChannel decide whether it should be reported to the user or not
			props = self._generate_props(telepathy.CHANNEL_TYPE_TEXT, h, False)
			channel = self.__channelManager.channel_for_props(props, signal=True)

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_connection_change(self, connection, event):
		"""
		@note Maemo specific
		"""
		status = event.get_status()
		error = event.get_error()
		iap_id = event.get_iap_id()
		bearer = event.get_bearer_type()

		if status == conic.STATUS_DISCONNECTED:
			_moduleLogger.info("Disconnecting due to loss of network connection")
			self.StatusChanged(
				telepathy.CONNECTION_STATUS_DISCONNECTED,
				telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR
			)
			try:
				self._disconnect()
			except Exception:
				_moduleLogger.exception("Error durring disconnect")
