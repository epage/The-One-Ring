import logging

import telepathy

import util.misc as misc_utils
import handle


_moduleLogger = logging.getLogger(__name__)


#class LocationMixin(tp.ConnectionInterfaceLocation):
class LocationMixin(object):

	def __init__(self):
		#tp.ConnectionInterfaceLocation.__init__(self)
		pass

	@property
	def session(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	@misc_utils.log_exception(_moduleLogger)
	def GetLocations(self, contacts):
		"""
		@returns {Contact: {Location Type: Location}}
		"""
		contactLocation = (
			(contact, self._get_location(contact))
			for contact in contacts
		)
		return dict(
			(contact, location)
			for (contact, location) in contactLocation
			if location
		)

	@misc_utils.log_exception(_moduleLogger)
	def RequestLocation(self, contact):
		"""
		@returns {Location Type: Location}
		"""
		return self._get_location(contact)

	@misc_utils.log_exception(_moduleLogger)
	def SetLocation(self, location):
		"""
		Since presence is based off of phone numbers, not allowing the client to change it
		"""
		raise telepathy.errors.PermissionDenied()

	def _get_location(self, contact):
		h = self.get_handle_by_id(telepathy.HANDLE_TYPE_CONTACT, contact)
		if isinstance(h, handle.ConnectionHandle):
			number = self.session.backend.get_callback_number()
		else:
			number = h.phoneNumber

		rawData = self.session.location.request_location(number)
		if rawData is None:
			return {}

		data = {
			"country": rawData["country"],
			"city": rawData["city"],
			"region": rawData["region"],
		}
