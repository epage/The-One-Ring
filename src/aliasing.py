import logging

import telepathy

import handle


class ButterflyAliasing(telepathy.server.ConnectionInterfaceAliasing):

	def __init__(self):
		telepathy.server.ConnectionInterfaceAliasing.__init__(self)

	def GetAliasFlags(self):
		return telepathy.constants.CONNECTION_ALIAS_FLAG_USER_SET

	def RequestAliases(self, contacts):
		logging.debug("Called RequestAliases")
		return [self._get_alias(handleId) for handleId in contacts]

	def GetAliases(self, contacts):
		logging.debug("Called GetAliases")

		result = {}
		for contact in contacts:
			result[contact] = self._get_alias(contact)
		return result

	def SetAliases(self, aliases):
		for handleId, alias in aliases.iteritems():
			h = self.handle(telepathy.HANDLE_TYPE_CONTACT, handleId)
			if h != handle.create_handle(self, 'self'):
				if alias == h.name:
					alias = u""
				contact = h.contact
				if contact is None:
					h.pending_alias = alias
					continue
				infos = {}
				self.gvoice_client.update_contact_infos(contact, infos)
			else:
				self.gvoice_client.profile.display_name = alias.encode('utf-8')
				logging.info("Self alias changed to '%s'" % alias)
				self.AliasesChanged(((handle.create_handle(self, 'self'), alias), ))
