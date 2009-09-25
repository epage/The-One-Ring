import logging

import telepathy


class ButterflyPresenceMapping(object):
	ONLINE = 'available'
	AWAY = 'away'
	BUSY = 'dnd'
	IDLE = 'xa'
	BRB = 'brb'
	PHONE = 'phone'
	LUNCH = 'lunch'
	INVISIBLE = 'hidden'
	OFFLINE = 'offline'

	to_pymsn = {
		ONLINE: pymsn.Presence.ONLINE,
		AWAY: pymsn.Presence.AWAY,
		BUSY: pymsn.Presence.BUSY,
		IDLE: pymsn.Presence.IDLE,
		BRB: pymsn.Presence.BE_RIGHT_BACK,
		PHONE: pymsn.Presence.ON_THE_PHONE,
		LUNCH: pymsn.Presence.OUT_TO_LUNCH,
		INVISIBLE: pymsn.Presence.INVISIBLE,
		OFFLINE: pymsn.Presence.OFFLINE
	}

	to_telepathy = {
		pymsn.Presence.ONLINE: ONLINE,
		pymsn.Presence.AWAY: AWAY,
		pymsn.Presence.BUSY: BUSY,
		pymsn.Presence.IDLE: IDLE,
		pymsn.Presence.BE_RIGHT_BACK: BRB,
		pymsn.Presence.ON_THE_PHONE: PHONE,
		pymsn.Presence.OUT_TO_LUNCH: LUNCH,
		pymsn.Presence.INVISIBLE: INVISIBLE,
		pymsn.Presence.OFFLINE: OFFLINE
	}

	to_presence_type = {
		ONLINE: telepathy.constants.CONNECTION_PRESENCE_TYPE_AVAILABLE,
		AWAY: telepathy.constants.CONNECTION_PRESENCE_TYPE_AWAY,
		BUSY: telepathy.constants.CONNECTION_PRESENCE_TYPE_BUSY,
		IDLE: telepathy.constants.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
		BRB: telepathy.constants.CONNECTION_PRESENCE_TYPE_AWAY,
		PHONE: telepathy.constants.CONNECTION_PRESENCE_TYPE_BUSY,
		LUNCH: telepathy.constants.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
		INVISIBLE: telepathy.constants.CONNECTION_PRESENCE_TYPE_HIDDEN,
		OFFLINE: telepathy.constants.CONNECTION_PRESENCE_TYPE_OFFLINE
	}


class ButterflySimplePresence(telepathy.server.ConnectionInterfaceSimplePresence):

	def __init__(self):
		telepathy.server.ConnectionInterfaceSimplePresence.__init__(self)

		dbus_interface = 'org.freedesktop.Telepathy.Connection.Interface.SimplePresence'

		self._implement_property_get(dbus_interface, {'Statuses' : self.get_statuses})

	def GetPresences(self, contacts):
		return self.get_simple_presences(contacts)

	def SetPresence(self, status, message):
		if status == ButterflyPresenceMapping.OFFLINE:
			self.Disconnect()

		try:
			presence = ButterflyPresenceMapping.to_pymsn[status]
		except KeyError:
			raise telepathy.errors.InvalidArgument
		message = message.encode("utf-8")

		logging.info("Setting Presence to '%s'" % presence)
		logging.info("Setting Personal message to '%s'" % message)

		if self._status != telepathy.CONNECTION_STATUS_CONNECTED:
			self._initial_presence = presence
			self._initial_personal_message = message
		else:
			self.msn_client.profile.personal_message = message
			self.msn_client.profile.presence = presence

	def get_simple_presences(self, contacts):
		presences = {}
		for handle_id in contacts:
			handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handle_id)
			try:
				contact = handle.contact
			except AttributeError:
				contact = handle.profile

			if contact is not None:
				presence = ButterflyPresenceMapping.to_telepathy[contact.presence]
				personal_message = unicode(contact.personal_message, "utf-8")
			else:
				presence = ButterflyPresenceMapping.OFFLINE
				personal_message = u""

			presence_type = ButterflyPresenceMapping.to_presence_type[presence]

			presences[handle] = (presence_type, presence, personal_message)
		return presences

	def get_statuses(self):
		# you get one of these for each status
		# {name:(Type, May_Set_On_Self, Can_Have_Message}
		return {
			ButterflyPresenceMapping.ONLINE:(
				telepathy.CONNECTION_PRESENCE_TYPE_AVAILABLE,
				True, True),
			ButterflyPresenceMapping.AWAY:(
				telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
				True, True),
			ButterflyPresenceMapping.BUSY:(
				telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
				True, True),
			ButterflyPresenceMapping.IDLE:(
				telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
				True, True),
			ButterflyPresenceMapping.BRB:(
				telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
				True, True),
			ButterflyPresenceMapping.PHONE:(
				telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
				True, True),
			ButterflyPresenceMapping.LUNCH:(
				telepathy.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
				True, True),
			ButterflyPresenceMapping.INVISIBLE:(
				telepathy.CONNECTION_PRESENCE_TYPE_HIDDEN,
				True, False),
			ButterflyPresenceMapping.OFFLINE:(
				telepathy.CONNECTION_PRESENCE_TYPE_OFFLINE,
				True, False)
		}

