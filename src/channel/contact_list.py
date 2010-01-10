import logging

import telepathy

import util.coroutines as coroutines
import gtk_toolbox
import handle


_moduleLogger = logging.getLogger("channel.contact_list")


class AllContactsListChannel(
		telepathy.server.ChannelTypeContactList,
		telepathy.server.ChannelInterfaceGroup,
	):
	"""
	The group of contacts for whom you receive presence
	"""

	def __init__(self, connection, manager, props, h):
		try:
			# HACK Older python-telepathy way
			telepathy.server.ChannelTypeContactList.__init__(self, connection, h)
		except TypeError:
			# HACK Newer python-telepathy way
			telepathy.server.ChannelTypeContactList.__init__(self, connection, manager, props)
		telepathy.server.ChannelInterfaceGroup.__init__(self)

		self.__manager = manager
		self.__props = props
		self.__session = connection.session

		self._callback = coroutines.func_sink(
			coroutines.expand_positional(
				self._on_contacts_refreshed
			)
		)
		self.__session.addressbook.updateSignalHandler.register_sink(
			self._callback
		)

		self.GroupFlagsChanged(0, 0)

		addressbook = connection.session.addressbook
		contacts = addressbook.get_contacts()
		self._process_refresh(addressbook, contacts, [])

	@gtk_toolbox.log_exception(_moduleLogger)
	def Close(self):
		self.close()

	def close(self):
		self.__session.addressbook.updateSignalHandler.unregister_sink(
			self._callback
		)
		self._callback = None

		telepathy.server.ChannelTypeContactList.Close(self)
		if self.__manager.channel_exists(self.__props):
			# HACK Older python-telepathy requires doing this manually
			self.__manager.remove_channel(self)
		self.remove_from_connection()

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_contacts_refreshed(self, addressbook, added, removed, changed):
		self._process_refresh(addressbook, added, removed)

	def _process_refresh(self, addressbook, added, removed):
		connection = self._conn
		handlesAdded = [
			handle.create_handle(connection, "contact", contactId, phoneNumber)
			for contactId in added
			for (phoneType, phoneNumber) in addressbook.get_contact_details(contactId)
		]
		handlesRemoved = [
			handle.create_handle(connection, "contact", contactId, phoneNumber)
			for contactId in removed
			for (phoneType, phoneNumber) in addressbook.get_contact_details(contactId)
		]
		message = ""
		actor = 0
		reason = telepathy.CHANNEL_GROUP_CHANGE_REASON_NONE
		self.MembersChanged(
			message,
			handlesAdded, handlesRemoved,
			(), (),
			actor,
			reason,
		)


def create_contact_list_channel(connection, manager, props, h):
	if h.get_name() == 'subscribe':
		# The group of contacts for whom you receive presence
		ChannelClass = AllContactsListChannel
	elif h.get_name() == 'publish':
		# The group of contacts who may receive your presence
		ChannelClass = AllContactsListChannel
	elif h.get_name() == 'hide':
		# A group of contacts who are on the publish list but are temporarily
		# disallowed from receiving your presence
		# This doesn't make sense to support
		_moduleLogger.warn("Unsuported type %s" % h.get_name())
	elif h.get_name() == 'allow':
		# A group of contacts who may send you messages
		# @todo Allow-List would be cool to support
		_moduleLogger.warn("Unsuported type %s" % h.get_name())
	elif h.get_name() == 'deny':
		# A group of contacts who may not send you messages
		# @todo Deny-List would be cool to support
		_moduleLogger.warn("Unsuported type %s" % h.get_name())
	elif h.get_name() == 'stored':
		# On protocols where the user's contacts are stored, this contact list
		# contains all stored contacts regardless of subscription status.
		ChannelClass = AllContactsListChannel
	else:
		raise TypeError("Unknown list type : " + h.get_name())
	return ChannelClass(connection, manager, props, h)


