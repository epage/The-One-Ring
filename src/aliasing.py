import logging

import dbus
import telepathy

import tp
import util.misc as misc_utils
import handle


_moduleLogger = logging.getLogger(__name__)


def _make_pretty_with_areacode(phonenumber):
	prettynumber = "(%s)" % (phonenumber[0:3], )
	if 3 < len(phonenumber):
		prettynumber += " %s" % (phonenumber[3:6], )
		if 6 < len(phonenumber):
			prettynumber += "-%s" % (phonenumber[6:], )
	return prettynumber


def _make_pretty_local(phonenumber):
	prettynumber = "%s" % (phonenumber[0:3], )
	if 3 < len(phonenumber):
		prettynumber += "-%s" % (phonenumber[3:], )
	return prettynumber


def _make_pretty_international(phonenumber):
	prettynumber = phonenumber
	if phonenumber.startswith("0"):
		prettynumber = "+%s " % (phonenumber[0:3], )
		if 3 < len(phonenumber):
			prettynumber += _make_pretty_with_areacode(phonenumber[3:])
	elif phonenumber.startswith("1"):
		prettynumber = "1 "
		prettynumber += _make_pretty_with_areacode(phonenumber[1:])
	return prettynumber


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
	'+1 (234) 567-8901'
	>>> make_pretty("12345678901")
	'+1 (234) 567-8901'
	>>> make_pretty("01234567890")
	'+012 (345) 678-90'
	>>> make_pretty("+01234567890")
	'+012 (345) 678-90'
	>>> make_pretty("+12")
	'+1 (2)'
	>>> make_pretty("+123")
	'+1 (23)'
	>>> make_pretty("+1234")
	'+1 (234)'
	"""
	if phonenumber is None or phonenumber == "":
		return ""

	phonenumber = misc_utils.normalize_number(phonenumber)

	if phonenumber == "":
		return ""
	elif phonenumber[0] == "+":
		prettynumber = _make_pretty_international(phonenumber[1:])
		if not prettynumber.startswith("+"):
			prettynumber = "+"+prettynumber
	elif 8 < len(phonenumber) and phonenumber[0] in ("0", "1"):
		prettynumber = _make_pretty_international(phonenumber)
	elif 7 < len(phonenumber):
		prettynumber = _make_pretty_with_areacode(phonenumber)
	elif 3 < len(phonenumber):
		prettynumber = _make_pretty_local(phonenumber)
	else:
		prettynumber = phonenumber
	return prettynumber.strip()


class AliasingMixin(tp.ConnectionInterfaceAliasing):

	def __init__(self):
		tp.ConnectionInterfaceAliasing.__init__(self)

	@property
	def session(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	@property
	def callbackNumberParameter(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	def get_handle_by_id(self, handleType, handleId):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract function called")

	@misc_utils.log_exception(_moduleLogger)
	def GetAliasFlags(self):
		return 0

	@misc_utils.log_exception(_moduleLogger)
	def RequestAliases(self, contactHandleIds):
		_moduleLogger.debug("Called RequestAliases")
		return [self._get_alias(handleId) for handleId in contactHandleIds]

	@misc_utils.log_exception(_moduleLogger)
	def GetAliases(self, contactHandleIds):
		_moduleLogger.debug("Called GetAliases")

		idToAlias = dbus.Dictionary(
			(
				(handleId, self._get_alias(handleId))
				for handleId in contactHandleIds
			),
			signature="us",
		)
		return idToAlias

	@misc_utils.log_exception(_moduleLogger)
	def SetAliases(self, aliases):
		_moduleLogger.debug("Called SetAliases")
		# first validate that no other handle types are included
		handleId, alias = None, None
		for handleId, alias in aliases.iteritems():
			h = self.get_handle_by_id(telepathy.HANDLE_TYPE_CONTACT, handleId)
			if isinstance(h, handle.ConnectionHandle):
				break
		else:
			raise telepathy.errors.PermissionDenied("No user customizable aliases")

		uglyNumber = misc_utils.normalize_number(alias)
		if len(uglyNumber) == 0:
			# Reset to the original from login if one was provided
			uglyNumber = self.callbackNumberParameter
		if not misc_utils.is_valid_number(uglyNumber):
			raise telepathy.errors.InvalidArgument("Invalid phone number %r" % (uglyNumber, ))

		# Update callback
		self.session.backend.set_callback_number(uglyNumber)

		# Inform of change
		userAlias = make_pretty(uglyNumber)
		changedAliases = ((handleId, userAlias), )
		self.AliasesChanged(changedAliases)

	def _get_alias(self, handleId):
		h = self.get_handle_by_id(telepathy.HANDLE_TYPE_CONTACT, handleId)
		if isinstance(h, handle.ConnectionHandle):
			aliasNumber = self.session.backend.get_callback_number()
			userAlias = make_pretty(aliasNumber)
			return userAlias
		else:
			number = h.phoneNumber
			try:
				contactAlias = self.session.addressbook.get_contact_name(number)
			except KeyError:
				contactAlias = make_pretty(number)
			return contactAlias
