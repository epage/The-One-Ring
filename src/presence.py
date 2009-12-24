import logging

import telepathy

import gtk_toolbox
import simple_presence
import gvoice.state_machine as state_machine


_moduleLogger = logging.getLogger('presence')


class PresenceMixin(telepathy.server.ConnectionInterfacePresence, simple_presence.TheOneRingPresence):

	def __init__(self):
		telepathy.server.ConnectionInterfacePresence.__init__(self)
		simple_presence.TheOneRingPresence.__init__(self)

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetStatuses(self):
		# the arguments are in common to all on-line presences
		arguments = {}

		return dict(
			(localType, (telepathyType, True, True, arguments))
			for (localType, telepathyType) in self.TO_PRESENCE_TYPE.iteritems()
		)

	@gtk_toolbox.log_exception(_moduleLogger)
	def RequestPresence(self, contactIds):
		presences = self.__get_presences(contactIds)
		self.PresenceUpdate(presences)

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetPresence(self, contactIds):
		return self.__get_presences(contactIds)

	@gtk_toolbox.log_exception(_moduleLogger)
	def SetStatus(self, statuses):
		assert len(statuses) == 1
		status, arguments = statuses.items()[0]
		assert len(arguments) == 0
		self.set_presence(status)

	def __get_presences(self, contacts):
		arguments = {}
		return dict(
			(h, (0, {presence: arguments}))
			for (h, (presenceType, presence)) in self.get_presences(contacts).iteritems()
		)
