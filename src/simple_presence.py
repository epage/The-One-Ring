import logging

import telepathy

import gtk_toolbox


_moduleLogger = logging.getLogger("simple_presence")


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
	def session(self):
		"""
		@abstract
		"""
		raise NotImplementedError()

	@property
	def handle(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetPresences(self, contacts):
		"""
		@todo Copy Aliasing's approach to knowing if self and get whether busy or not

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

	@gtk_toolbox.log_exception(_moduleLogger)
	def SetPresence(self, status, message):
		if message:
			raise telepathy.errors.InvalidArgument("Messages aren't supported")


		if status == TheOneRingPresence.ONLINE:
			# @todo Implement dnd
			#self.gvoice_backend.mark_dnd(True)
			pass
		elif status == TheOneRingPresence.BUSY:
			# @todo Implement dnd
			#self.gvoice_backend.mark_dnd(False)
			raise telepathy.errors.NotAvailable("DnD support not yet added to TheOneRing")
		else:
			raise telepathy.errors.InvalidArgument("Unsupported status: %r" % status)
		_moduleLogger.info("Setting Presence to '%s'" % status)


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

