import weakref
import logging

import telepathy

import handle


def create_contact_list_channel(connection, h):
	if h.get_name() == 'subscribe':
		channel_class = TheOneRingSubscribeListChannel
	elif h.get_name() == 'publish':
		channel_class = TheOneRingPublishListChannel
	elif h.get_name() == 'hide':
		logging.warn("Unsuported type %s" % h.get_name())
	elif h.get_name() == 'allow':
		logging.warn("Unsuported type %s" % h.get_name())
	elif h.get_name() == 'deny':
		logging.warn("Unsuported type %s" % h.get_name())
	else:
		raise TypeError("Unknown list type : " + h.get_name())
	return channel_class(connection, h)


class TheOneRingListChannel(
		telepathy.server.ChannelTypeContactList,
		telepathy.server.ChannelInterfaceGroup,
	):
	"Abstract Contact List channels"

	def __init__(self, connection, h):
		telepathy.server.ChannelTypeContactList.__init__(self, connection, h)
		telepathy.server.ChannelInterfaceGroup.__init__(self)

		self._conn_ref = weakref.ref(connection)

	def GetLocalPendingMembersWithInfo(self):
		return []


class TheOneRingSubscribeListChannel(TheOneRingListChannel):
	"""
	Subscribe List channel.

	This channel contains the list of contact to whom the current used is
	'subscribed', basically this list contains the contact for whom you are
	supposed to receive presence notification.
	"""

	def __init__(self, connection, h):
		TheOneRingListChannel.__init__(self, connection, h)
		self.GroupFlagsChanged(
			telepathy.CHANNEL_GROUP_FLAG_CAN_ADD |
			telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE,
			0,
		)

	def AddMembers(self, contacts, message):
		addressBook = self._conn.gvoice_client
		for h in contacts:
			h = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, h)
			contact = h.contact
			if contact is None:
				account = h.account
			else:
				account = contact.account
			groups = list(h.pending_groups)
			h.pending_groups = set()
			addressBook.add_messenger_contact(account,
					invite_message=message.encode('utf-8'),
					groups=groups)

	def RemoveMembers(self, contacts, message):
		addressBook = self._conn.gvoice_client
		for h in contacts:
			h = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, h)
			contact = h.contact
			addressBook.delete_contact(contact)


class TheOneRingPublishListChannel(TheOneRingListChannel):

	def __init__(self, connection, h):
		TheOneRingListChannel.__init__(self, connection, h)
		self.GroupFlagsChanged(0, 0)

	def AddMembers(self, contacts, message):
		addressBook = self._conn.gvoice_client
		for contactHandleId in contacts:
			contactHandle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT,
						contactHandleId)
			contact = contactHandle.contact
			addressBook.accept_contact_invitation(contact, False)

	def RemoveMembers(self, contacts, message):
		addressBook = self._conn.gvoice_client
		for contactHandleId in contacts:
			contactHandle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT,
						contactHandleId)
			contact = contactHandle.contact

	def GetLocalPendingMembersWithInfo(self):
		addressBook = self._conn.gvoice_client
		result = []
		for contact in addressBook.contacts:
			h = handle.create_handle(self._conn_ref(), 'contact',
					contact.account, contact.network_id)
			result.append((h, h,
					telepathy.CHANNEL_GROUP_CHANGE_REASON_INVITED,
					contact.attributes.get('invite_message', '')))
		return result