import weakref
import logging

import telepathy

import util.go_utils as gobject_utils
import util.coroutines as coroutines
import handle


_moduleLogger = logging.getLogger("channel.contact_list")


class AbstractListChannel(
		telepathy.server.ChannelTypeContactList,
		telepathy.server.ChannelInterfaceGroup,
	):
	"Abstract Contact List channels"

	def __init__(self, connection, h):
		telepathy.server.ChannelTypeContactList.__init__(self, connection, h)
		telepathy.server.ChannelInterfaceGroup.__init__(self)

		self._conn_ref = weakref.ref(connection)
		self._session = connection.session


class AllContactsListChannel(AbstractListChannel):
	"""
	The group of contacts for whom you receive presence
	"""

	def __init__(self, connection, h):
		AbstractListChannel.__init__(self, connection, h)
		self._session.addressbook.updateSignalHandle.register_sink(
			self._on_contacts_refreshed
		)

	@coroutines.func_sink
	@coroutines.expand_positional
	@gobject_utils.async
	def _on_contacts_refreshed(self, addressbook, added, removed, changed):
		connection = self._conn_ref()
		handlesAdded = [
			handle.create_handle(connection, "contact", contactId)
			for contactId in added
		]
		handlesRemoved = [
			handle.create_handle(connection, "contact", contactId)
			for contactId in removed
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


def create_contact_list_channel(connection, h):
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
		# @todo This would be cool to support
		_moduleLogger.warn("Unsuported type %s" % h.get_name())
	elif h.get_name() == 'deny':
		# A group of contacts who may not send you messages
		# @todo This would be cool to support
		_moduleLogger.warn("Unsuported type %s" % h.get_name())
	elif h.get_name() == 'stored':
		# On protocols where the user's contacts are stored, this contact list
		# contains all stored contacts regardless of subscription status.
		ChannelClass = AllContactsListChannel
	else:
		raise TypeError("Unknown list type : " + h.get_name())
	return ChannelClass(connection, h)


