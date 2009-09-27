import logging

import telepathy


class TheOneRingPresence(object):
	ONLINE = 'available'
	BUSY = 'dnd'

	TO_PRESENCE_TYPE = {
		ONLINE: telepathy.constants.CONNECTION_PRESENCE_TYPE_AVAILABLE,
		BUSY: telepathy.constants.CONNECTION_PRESENCE_TYPE_BUSY,
	}


class SimplePresenceMixin(telepathy.server.ConnectionInterfaceSimplePresence):

	def __init__(self):
		telepathy.server.ConnectionInterfaceSimplePresence.__init__(self)

		dbus_interface = 'org.freedesktop.Telepathy.Connection.Interface.SimplePresence'

		self._implement_property_get(dbus_interface, {'Statuses' : self._get_statuses})

	@property
	def gvoice_backend(self):
		"""
		@abstract
		"""
		raise NotImplementedError()

	def GetPresences(self, contacts):
		"""
		@todo Figure out how to know when its self and get whether busy or not

		@return {ContactHandle: (Status, Presence Type, Message)}
		"""
		presences = {}
		for handleId in contacts:
			handle = self.handle(telepathy.HANDLE_TYPE_CONTACT, handleId)

			presence = TheOneRingPresence.BUSY
			personalMessage = u""
			presenceType = TheOneRingPresence.TO_PRESENCE_TYPE[presence]

			presences[handle] = (presenceType, presence, personalMessage)
		return presences

	def SetPresence(self, status, message):
		if message:
			raise telepathy.errors.InvalidArgument

		if status == TheOneRingPresence.ONLINE:
			self.gvoice_backend.mark_dnd(True)
		elif status == TheOneRingPresence.BUSY:
			self.gvoice_backend.mark_dnd(False)
		else:
			raise telepathy.errors.InvalidArgument
		logging.info("Setting Presence to '%s'" % status)


	def _get_statuses(self):
		"""
		Property mapping presence statuses available to the corresponding presence types

		@returns {Name: (Telepathy Type, May Set On Self, Can Have Message)}
		"""
		return {
			TheOneRingPresence.ONLINE: (
				telepathy.CONNECTION_PRESENCE_TYPE_AVAILABLE,
				True, False
			),
			TheOneRingPresence.BUSY: (
				telepathy.CONNECTION_PRESENCE_TYPE_AWAY,
				True, False
			),
		}

