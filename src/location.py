import logging

import telepathy

import gtk_toolbox


_moduleLogger = logging.getLogger('location')


#class LocationMixin(telepathy.server.ConnectionInterfaceLocation):
class LocationMixin(object):

	def __init__(self):
		#telepathy.server.ConnectionInterfaceLocation.__init__(self)
		pass

	@property
	def session(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetLocations(self, contacts):
		"""
		@returns {Contact: {Location Type: Location}}
		"""
		raise telepathy.errors.NotImplemented("Yet")

	@gtk_toolbox.log_exception(_moduleLogger)
	def RequestLocation(self, contact):
		"""
		@returns {Location Type: Location}
		"""
		raise telepathy.errors.NotImplemented("Yet")

	@gtk_toolbox.log_exception(_moduleLogger)
	def SetLocation(self, location):
		"""
		Since presence is based off of phone numbers, not allowing the client to change it
		"""
		raise telepathy.errors.PermissionDenied()
