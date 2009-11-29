import logging

import telepathy

import gtk_toolbox
import handle


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
		@return {ContactHandle: (Status, Presence Type, Message)}
		"""
		presences = {}
		for handleId in contacts:
			h = self.handle(telepathy.HANDLE_TYPE_CONTACT, handleId)
			if isinstance(h, handle.ConnectionHandle):
				isDnd = self.session.backend.is_dnd()
				presence = TheOneRingPresence.BUSY if isDnd else TheOneRingPresence.ONLINE
				personalMessage = u""
				presenceType = TheOneRingPresence.TO_PRESENCE_TYPE[presence]
			else:
				presence = TheOneRingPresence.ONLINE
				personalMessage = u""
				presenceType = TheOneRingPresence.TO_PRESENCE_TYPE[presence]

			presences[h] = (presenceType, presence, personalMessage)
		return presences

	@gtk_toolbox.log_exception(_moduleLogger)
	def SetPresence(self, status, message):
		if message:
			raise telepathy.errors.InvalidArgument("Messages aren't supported")


		if status == TheOneRingPresence.ONLINE:
			self.gvoice_backend.set_dnd(False)
		elif status == TheOneRingPresence.BUSY:
			self.gvoice_backend.set_dnd(True)
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

