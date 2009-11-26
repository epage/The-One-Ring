import logging

import telepathy

import gtk_toolbox
import handle


_moduleLogger = logging.getLogger('aliasing')


def make_pretty(phonenumber):
	"""
	Function to take a phone number and return the pretty version
	pretty numbers:
		if phonenumber begins with 0:
			...-(...)-...-....
		if phonenumber begins with 1: ( for gizmo callback numbers )
			1 (...)-...-....
		if phonenumber is 13 digits:
			(...)-...-....
		if phonenumber is 10 digits:
			...-....
	>>> make_pretty("12")
	'12'
	>>> make_pretty("1234567")
	'123-4567'
	>>> make_pretty("2345678901")
	'(234)-567-8901'
	>>> make_pretty("12345678901")
	'1 (234)-567-8901'
	>>> make_pretty("01234567890")
	'+012-(345)-678-90'
	"""
	if phonenumber is None or phonenumber is "":
		return ""

	phonenumber = handle.strip_number(phonenumber)

	if len(phonenumber) < 3:
		return phonenumber

	if phonenumber[0] == "0":
		prettynumber = ""
		prettynumber += "+%s" % phonenumber[0:3]
		if 3 < len(phonenumber):
			prettynumber += "-(%s)" % phonenumber[3:6]
			if 6 < len(phonenumber):
				prettynumber += "-%s" % phonenumber[6:9]
				if 9 < len(phonenumber):
					prettynumber += "-%s" % phonenumber[9:]
		return prettynumber
	elif len(phonenumber) <= 7:
		prettynumber = "%s-%s" % (phonenumber[0:3], phonenumber[3:])
	elif len(phonenumber) > 8 and phonenumber[0] == "1":
		prettynumber = "1 (%s)-%s-%s" % (phonenumber[1:4], phonenumber[4:7], phonenumber[7:])
	elif len(phonenumber) > 7:
		prettynumber = "(%s)-%s-%s" % (phonenumber[0:3], phonenumber[3:6], phonenumber[6:])
	return prettynumber


class AliasingMixin(telepathy.server.ConnectionInterfaceAliasing):

	def __init__(self):
		telepathy.server.ConnectionInterfaceAliasing.__init__(self)

	@property
	def session(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	@property
	def handle(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetAliasFlags(self):
		return 0

	@gtk_toolbox.log_exception(_moduleLogger)
	def RequestAliases(self, contactHandleIds):
		_moduleLogger.debug("Called RequestAliases")
		return [self._get_alias(handleId) for handleId in contactHandleIds]

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetAliases(self, contactHandleIds):
		_moduleLogger.debug("Called GetAliases")

		idToAlias = dict(
			(handleId, self._get_alias(handleId))
			for handleId in contactHandleIds
		)
		return idToAlias

	@gtk_toolbox.log_exception(_moduleLogger)
	def SetAliases(self, aliases):
		# @todo Look into setting callback number through this mechanism
		raise telepathy.PermissionDenied("No user customizable aliases")

	def _get_alias(self, handleId):
		h = self.handle(telepathy.HANDLE_TYPE_CONTACT, handleId)
		if isinstance(h, handle.ConnectionHandle):
			callbackNumber = self.session.backend.get_callback_number()
			userAlias = make_pretty(callbackNumber)
			return userAlias
		else:
			contactAlias = self.session.addressbook.get_contact_name(h.contactID)
			return contactAlias
