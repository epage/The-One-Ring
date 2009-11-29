import weakref
import logging

import telepathy

import constants
import util.go_utils as gobject_utils
import util.coroutines as coroutines
import gtk_toolbox
import gvoice
import handle
import aliasing
import simple_presence
import channel_manager


_moduleLogger = logging.getLogger("connection")


class TheOneRingConnection(
	telepathy.server.Connection,
	aliasing.AliasingMixin,
	simple_presence.SimplePresenceMixin,
):

	# Overriding a base class variable
	# Should the forwarding number be handled by the alias or by an option?
	_mandatory_parameters = {
		'username' : 's',
		'password' : 's',
		'forward' : 's',
	}
	# Overriding a base class variable
	_optional_parameters = {
	}
	_parameter_defaults = {
	}

	def __init__(self, manager, parameters):
		try:
			self.check_parameters(parameters)
			account = unicode(parameters['username'])

			# Connection init must come first
			telepathy.server.Connection.__init__(
				self,
				constants._telepathy_protocol_name_,
				account,
				constants._telepathy_implementation_name_
			)
			aliasing.AliasingMixin.__init__(self)
			simple_presence.SimplePresenceMixin.__init__(self)

			self._manager = weakref.proxy(manager)
			self._credentials = (
				parameters['username'].encode('utf-8'),
				parameters['password'].encode('utf-8'),
			)
			self._callbackNumber = parameters['forward'].encode('utf-8')
			self._channelManager = channel_manager.ChannelManager(self)

			cookieFilePath = "%s/cookies.txt" % constants._data_path_
			self._session = gvoice.session.Session(cookieFilePath)

			self.set_self_handle(handle.create_handle(self, 'connection'))

			_moduleLogger.info("Connection to the account %s created" % account)
		except Exception, e:
			_moduleLogger.exception("Failed to create Connection")
			raise

	@property
	def manager(self):
		return self._manager

	@property
	def session(self):
		return self._session

	@property
	def username(self):
		return self._credentials[0]

	def handle(self, handleType, handleId):
		self.check_handle(handleType, handleId)
		return self._handles[handleType, handleId]

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
			self.session.login(*self._credentials)
			self.session.backend.set_callback_number(self._callbackNumber)
		except gvoice.backend.NetworkError, e:
			_moduleLogger.exception("Connection Failed")
			self.StatusChanged(
				telepathy.CONNECTION_STATUS_DISCONNECTED,
				telepathy.CONNECTION_STATUS_REASON_NETWORK_ERROR
			)
		except Exception, e:
			_moduleLogger.exception("Connection Failed")
			self.StatusChanged(
				telepathy.CONNECTION_STATUS_DISCONNECTED,
				telepathy.CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED
			)
		else:
			_moduleLogger.info("Connected")
			self.StatusChanged(
				telepathy.CONNECTION_STATUS_CONNECTED,
				telepathy.CONNECTION_STATUS_REASON_REQUESTED
			)

	@gtk_toolbox.log_exception(_moduleLogger)
	def Disconnect(self):
		"""
		For org.freedesktop.telepathy.Connection
		@bug Not properly logging out.  Cookie files need to be per connection and removed
		"""
		_moduleLogger.info("Disconnecting")
		try:
			self.session.logout()
			_moduleLogger.info("Disconnected")
		except Exception:
			_moduleLogger.exception("Disconnecting Failed")
		self.StatusChanged(
			telepathy.CONNECTION_STATUS_DISCONNECTED,
			telepathy.CONNECTION_STATUS_REASON_REQUESTED
		)

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

		channel = None
		channelManager = self._channelManager
		handle = self.handle(handleType, handleId)

		if type == telepathy.CHANNEL_TYPE_CONTACT_LIST:
			_moduleLogger.info("RequestChannel ContactList")
			channel = channelManager.channel_for_list(handle, suppressHandler)
		elif type == telepathy.CHANNEL_TYPE_TEXT:
			_moduleLogger.info("RequestChannel Text")
			channel = channelManager.channel_for_text(handle, suppressHandler)
		elif type == telepathy.CHANNEL_TYPE_STREAMED_MEDIA:
			_moduleLogger.info("RequestChannel Media")
			channel = channelManager.channel_for_call(handle, suppressHandler)
		else:
			raise telepathy.errors.NotImplemented("unknown channel type %s" % type)

		_moduleLogger.info("RequestChannel Object Path: %s" % channel._object_path)
		return channel._object_path

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
			name = name.encode('utf-8')
			if handleType == telepathy.HANDLE_TYPE_CONTACT:
				_moduleLogger.info("RequestHandles Contact: %s" % name)
				h = self._create_contact_handle(name)
			elif handleType == telepathy.HANDLE_TYPE_LIST:
				# Support only server side (immutable) lists
				_moduleLogger.info("RequestHandles List: %s" % name)
				h = handle.create_handle(self, 'list', name)
			else:
				raise telepathy.errors.NotAvailable('Handle type unsupported %d' % handleType)
			handles.append(h.id)
			self.add_client_handle(h, sender)
		return handles

	def _create_contact_handle(self, requestedHandleName):
		requestedContactId, requestedContactNumber = handle.ContactHandle.from_handle_name(
			requestedHandleName
		)
		h = handle.create_handle(self, 'contact', requestedContactId, requestedContactNumber)
		return h

	@coroutines.func_sink
	@coroutines.expand_positional
	@gobject_utils.async
	def _on_conversations_updated(self, conversationIds):
		# @todo get conversations update running
		# @todo test conversatiuons
		channelManager = self._channelManager
		for contactId, phoneNumber in conversationIds:
			h = self._create_contact_handle(contactId, phoneNumber)
			# if its new, __init__ will take care of things
			# if its old, its own update will take care of it
			channel = channelManager.channel_for_text(handle)
