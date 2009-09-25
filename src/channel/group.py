import logging

import telepathy

import contact_list


class TheOneRingGroupChannel(contact_list.TheOneRingListChannel):

	def __init__(self, connection, h):
		self.__pending_add = []
		self.__pending_remove = []
		contact_list.TheOneRingListChannel.__init__(self, connection, h)
		self.GroupFlagsChanged(
			telepathy.CHANNEL_GROUP_FLAG_CAN_ADD | telepathy.CHANNEL_GROUP_FLAG_CAN_REMOVE,
			0,
		)

	def AddMembers(self, contacts, message):
		addressBook = self._conn.gvoice_client
		if self._handle.group is None:
			for contactHandleId in contacts:
				contactHandle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, contactHandleId)
				logging.info("Adding contact %r to pending group %r" % (contactHandle, self._handle))
				if contactHandleId in self.__pending_remove:
					self.__pending_remove.remove(contactHandleId)
				else:
					self.__pending_add.append(contactHandleId)
			return
		else:
			for contactHandleId in contacts:
				contactHandle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, contactHandleId)
				logging.info("Adding contact %r to group %r" % (contactHandle, self._handle))
				contact = contactHandle.contact
				group = self._handle.group
				if contact is not None:
					addressBook.add_contact_to_group(group, contact)
				else:
					contactHandle.pending_groups.add(group)

	def RemoveMembers(self, contacts, message):
		addressBook = self._conn.gvoice_client
		if self._handle.group is None:
			for contactHandleId in contacts:
				contactHandle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, contactHandleId)
				logging.info("Adding contact %r to pending group %r" % (contactHandle, self._handle))
				if contactHandleId in self.__pending_add:
					self.__pending_add.remove(contactHandleId)
				else:
					self.__pending_remove.append(contactHandleId)
			return
		else:
			for contactHandleId in contacts:
				contactHandle = self._conn.handle(telepathy.HANDLE_TYPE_CONTACT, contactHandleId)
				logging.info("Removing contact %r from pending group %r" % (contactHandle, self._handle))
				contact = contactHandle.contact
				group = self._handle.group
				if contact is not None:
					addressBook.delete_contact_from_group(group, contact)
				else:
					contactHandle.pending_groups.discard(group)

	def Close(self):
		logging.debug("Deleting group %s" % self._handle.name)
		addressBook = self._conn.gvoice_client
		group = self._handle.group
		addressBook.delete_group(group)
