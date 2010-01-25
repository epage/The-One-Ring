import logging

import telepathy

import tp
import util.coroutines as coroutines
import gtk_toolbox
import handle


_moduleLogger = logging.getLogger("channel.contact_list")


class AllContactsListChannel(
		tp.ChannelTypeContactList,
		tp.ChannelInterfaceGroup,
	):
	"""
	The group of contacts for whom you receive presence
	"""

	def __init__(self, connection, manager, props, listHandle):
		tp.ChannelTypeContactList.__init__(self, connection, manager, props)
		tp.ChannelInterfaceGroup.__init__(self)

		self.__manager = manager
		self.__props = props
		self.__session = connection.session
		self.__listHandle = listHandle

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
		contacts = addressbook.get_numbers()
		self._process_refresh(addressbook, set(contacts), set())


	@gtk_toolbox.log_exception(_moduleLogger)
	def Close(self):
		self.close()

	def close(self):
		_moduleLogger.debug("Closing contact list")
		self.__session.addressbook.updateSignalHandler.unregister_sink(
			self._callback
		)
		self._callback = None

		tp.ChannelTypeContactList.Close(self)
		self.remove_from_connection()

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetLocalPendingMembersWithInfo(self):
		return []

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_contacts_refreshed(self, addressbook, added, removed, changed):
		self._process_refresh(addressbook, added, removed)

	def _process_refresh(self, addressbook, added, removed):
		_moduleLogger.info(
			"%s Added: %r, Removed: %r" % (self.__listHandle.get_name(), len(added), len(removed))
		)
		connection = self._conn
		handlesAdded = [
			handle.create_handle(connection, "contact", contactNumber)
			for contactNumber in added
		]
		handlesRemoved = [
			handle.create_handle(connection, "contact", contactNumber)
			for contactNumber in removed
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


_LIST_TO_FACTORY = {
	# The group of contacts for whom you receive presence
	'subscribe': AllContactsListChannel,
	# The group of contacts who may receive your presence
	'publish': AllContactsListChannel,
	# A group of contacts who are on the publish list but are temporarily
	# disallowed from receiving your presence
	# This doesn't make sense to support
	'hide': None,
	# A group of contacts who may send you messages
	'allow': None,
	# A group of contacts who may not send you messages
	'deny': None,
	# On protocols where the user's contacts are stored, this contact list
	# contains all stored contacts regardless of subscription status.
	'stored': AllContactsListChannel,
}


_SUPPORTED_LISTS = frozenset(
	name
	for name in _LIST_TO_FACTORY.iterkeys()
	if name is not None
)


def create_contact_list_channel(connection, manager, props, h):
	factory = _LIST_TO_FACTORY.get(h.get_name(), None)
	if factory is None:
		raise telepathy.errors.NotCapable("Unsuported type %s" % h.get_name())
	return factory(connection, manager, props, h)


def get_spported_lists():
	return _SUPPORTED_LISTS
