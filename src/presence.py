import logging

import tp
import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class PresenceMixin(tp.ConnectionInterfacePresence):

	def __init__(self, torPresence):
		tp.ConnectionInterfacePresence.__init__(self)
		self.__torPresence = torPresence

	@misc_utils.log_exception(_moduleLogger)
	def GetStatuses(self):
		# the arguments are in common to all on-line presences
		arguments = {}

		return dict(
			(localType, (telepathyType, True, True, arguments))
			for (localType, telepathyType) in self.__torPresence.TO_PRESENCE_TYPE.iteritems()
		)

	@misc_utils.log_exception(_moduleLogger)
	def RequestPresence(self, contactIds):
		presences = self.__get_presences(contactIds)
		self.PresenceUpdate(presences)

	@misc_utils.log_exception(_moduleLogger)
	def GetPresence(self, contactIds):
		return self.__get_presences(contactIds)

	@misc_utils.log_exception(_moduleLogger)
	def SetStatus(self, statuses):
		assert len(statuses) == 1
		status, arguments = statuses.items()[0]
		assert len(arguments) == 0
		self.__torPresence.set_presence(status)

	def __get_presences(self, contacts):
		arguments = {}
		return dict(
			(h, (0, {presence: arguments}))
			for (h, (presenceType, presence)) in self.__torPresence.get_presences(contacts).iteritems()
		)
