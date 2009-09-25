import logging

import telepathy

import simple_presence


class ButterflyPresence(telepathy.server.ConnectionInterfacePresence):

	def __init__(self):
		telepathy.server.ConnectionInterfacePresence.__init__(self)

	def GetStatuses(self):
		# the arguments are in common to all on-line presences
		arguments = {'message' : 's'}

		# you get one of these for each status
		# {name:(type, self, exclusive, {argument:types}}
		return {
			simple_presence.ButterflyPresenceMapping.ONLINE:(
				telepathy.CONNECTION_PRESENCE_TYPE_AVAILABLE,
				True, True, arguments),
			simple_presence.ButterflyPresenceMapping.AWAY:(
				telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
				True, True, arguments),
			simple_presence.ButterflyPresenceMapping.BUSY:(
				telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
				True, True, arguments),
			simple_presence.ButterflyPresenceMapping.IDLE:(
				telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
				True, True, arguments),
			simple_presence.ButterflyPresenceMapping.BRB:(
				telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
				True, True, arguments),
			simple_presence.ButterflyPresenceMapping.PHONE:(
				telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
				True, True, arguments),
			simple_presence.ButterflyPresenceMapping.LUNCH:(
				telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
				True, True, arguments),
			simple_presence.ButterflyPresenceMapping.INVISIBLE:(
				telepathy.CONNECTION_PRESENCE_TYPE_HIDDEN,
				True, True, {}),
			simple_presence.ButterflyPresenceMapping.OFFLINE:(
				telepathy.CONNECTION_PRESENCE_TYPE_OFFLINE,
				True, True, {})
		}

	def RequestPresence(self, contacts):
		presences = self.get_presences(contacts)
		self.PresenceUpdate(presences)

	def GetPresence(self, contacts):
		return self.get_presences(contacts)

	def SetStatus(self, statuses):
		status, arguments = statuses.items()[0]
		if status == simple_presence.ButterflyPresenceMapping.OFFLINE:
			self.Disconnect()

		presence = simple_presence.ButterflyPresenceMapping.to_pymsn[status]
		message = arguments.get('message', u'').encode("utf-8")

		logging.info("Setting Presence to '%s'" % presence)
		logging.info("Setting Personal message to '%s'" % message)

		if self._status != telepathy.CONNECTION_STATUS_CONNECTED:
			self._initial_presence = presence
			self._initial_personal_message = message
		else:
			self.msn_client.profile.personal_message = message
			self.msn_client.profile.presence = presence

	def get_presences(self, contacts):
		presences = {}
		for handleId in contacts:
			h = self.handle(telepathy.HANDLE_TYPE_CONTACT, handleId)
			try:
				contact = h.contact
			except AttributeError:
				contact = h.profile

			if contact is not None:
				presence = simple_presence.ButterflyPresenceMapping.to_telepathy[contact.presence]
				personal_message = unicode(contact.personal_message, "utf-8")
			else:
				presence = simple_presence.ButterflyPresenceMapping.OFFLINE
				personal_message = u""

			arguments = {}
			if personal_message:
				arguments = {'message' : personal_message}

			presences[h] = (0, {presence : arguments}) # TODO: Timestamp
		return presences
