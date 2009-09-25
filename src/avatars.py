import logging

import telepathy


class ButterflyAvatars(telepathy.server.ConnectionInterfaceAvatars):

	def __init__(self):
		self._avatar_known = False
		telepathy.server.ConnectionInterfaceAvatars.__init__(self)

	def GetAvatarRequirements(self):
		mime_types = ("image/png","image/jpeg","image/gif")
		return (mime_types, 96, 96, 192, 192, 500 * 1024)

	def GetKnownAvatarTokens(self, contacts):
		result = {}
		for handle_id in contacts:
			handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
			if handle == self.GetSelfHandle():
				contact = handle.profile
			else:
				contact = handle.contact

			if contact is not None:
				msn_object = contact.msn_object
			else:
				msn_object = None

			if msn_object is not None:
				result[handle] = msn_object._data_sha.encode("hex")
			elif self._avatar_known:
				result[handle] = ""
		return result

	def RequestAvatars(self, contacts):
		for handle_id in contacts:
			handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
			if handle == self.GetSelfHandle():
				msn_object = self.msn_client.profile.msn_object
				self._msn_object_retrieved(msn_object, handle)
			else:
				contact = handle.contact
				if contact is not None:
					msn_object = contact.msn_object
				else:
					msn_object = None
				if msn_object is not None:
					self.msn_client.msn_object_store.request(msn_object,\
							(self._msn_object_retrieved, handle))

	def SetAvatar(self, avatar, mime_type):
		self._avatar_known = True
		if not isinstance(avatar, str):
			avatar = "".join([chr(b) for b in avatar])
		avatarToken = 0
		logging.info("Setting self avatar to %s" % avatarToken)
		return avatarToken

	def ClearAvatar(self):
		self.msn_client.profile.msn_object = None
		self._avatar_known = True
