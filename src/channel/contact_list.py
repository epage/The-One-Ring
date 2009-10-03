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

		self._session = connection.session


class AllContactsListChannel(AbstractListChannel):
	"""
	The group of contacts for whom you receive presence
	"""

	def __init__(self, connection, h):
		AbstractListChannel.__init__(self, connection, h)
		self._session.addressbook.updateSignalHandler.register_sink(
			self._on_contacts_refreshed
		)
		self.GroupFlagsChanged(0, 0)

	@coroutines.func_sink
	@coroutines.expand_positional
	@gobject_utils.async
	def _on_contacts_refreshed(self, addressbook, added, removed, changed):
		"""
		@todo This currently filters out people not yet added to the contact
			list.  Something needs to be done about those
		@todo This currently does not handle people with multiple phone
			numbers, yay that'll be annoying to resolve
		"""
		connection = self._conn
		handlesAdded = [
			handle.create_handle(connection, "contact", contactId)
			for contactId in added
			if contactId
		]
		handlesRemoved = [
			handle.create_handle(connection, "contact", contactId)
			for contactId in removed
			if contactId
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
	return ChannelClass(connection, h)


