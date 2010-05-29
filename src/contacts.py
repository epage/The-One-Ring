import logging

import dbus
import telepathy

import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class ContactsMixin(telepathy.server.ConnectionInterfaceContacts):

	ATTRIBUTES = {
		telepathy.CONNECTION : 'contact-id',
		telepathy.CONNECTION_INTERFACE_SIMPLE_PRESENCE : 'presence',
		telepathy.CONNECTION_INTERFACE_ALIASING : 'alias',
		telepathy.CONNECTION_INTERFACE_AVATARS : 'token',
		telepathy.CONNECTION_INTERFACE_CAPABILITIES : 'caps',
		telepathy.CONNECTION_INTERFACE_CONTACT_CAPABILITIES : 'capabilities'
	}

	def __init__(self):
		telepathy.server.ConnectionInterfaceContacts.__init__(self)

		dbus_interface = telepathy.CONNECTION_INTERFACE_CONTACTS
		self._implement_property_get(
			dbus_interface,
			{'ContactAttributeInterfaces' : self.get_contact_attribute_interfaces}
		)

	def HoldHandles(self, *args):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract function called")

	# Overwrite the dbus attribute to get the sender argument
	@misc_utils.log_exception(_moduleLogger)
	@dbus.service.method(telepathy.CONNECTION_INTERFACE_CONTACTS, in_signature='auasb',
							out_signature='a{ua{sv}}', sender_keyword='sender')
	def GetContactAttributes(self, handles, interfaces, hold, sender):
		#InspectHandle already checks we're connected, the handles and handle type.
		supportedInterfaces = set()
		for interface in interfaces:
			if interface in self.ATTRIBUTES:
				supportedInterfaces.add(interface)
			else:
				_moduleLogger.debug("Ignoring unsupported interface %s" % interface)

		handle_type = telepathy.HANDLE_TYPE_CONTACT
		ret = dbus.Dictionary(signature='ua{sv}')
		for handle in handles:
			ret[handle] = dbus.Dictionary(signature='sv')

		functions = {
			telepathy.CONNECTION:
				lambda x: zip(x, self.InspectHandles(handle_type, x)),
			telepathy.CONNECTION_INTERFACE_SIMPLE_PRESENCE:
				lambda x: self.GetPresences(x).items(),
			telepathy.CONNECTION_INTERFACE_ALIASING:
				lambda x: self.GetAliases(x).items(),
			telepathy.CONNECTION_INTERFACE_AVATARS :
				lambda x: self.GetKnownAvatarTokens(x).items(),
			telepathy.CONNECTION_INTERFACE_CAPABILITIES:
				lambda x: self.GetCapabilities(x).items(),
			telepathy.CONNECTION_INTERFACE_CONTACT_CAPABILITIES :
				lambda x: self.GetContactCapabilities(x).items()
		}

		#Hold handles if needed
		if hold:
			self.HoldHandles(handle_type, handles, sender)

		# Attributes from the interface org.freedesktop.Telepathy.Connection
		# are always returned, and need not be requested explicitly.
		supportedInterfaces.add(telepathy.CONNECTION)

		for interface in supportedInterfaces:
			interface_attribute = interface + '/' + self.ATTRIBUTES[interface]
			results = functions[interface](handles)
			for handle, value in results:
				ret[int(handle)][interface_attribute] = value
		return ret

	def get_contact_attribute_interfaces(self):
		return self.ATTRIBUTES.keys()
