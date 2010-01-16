import logging
import weakref

import telepathy

import tp
import util.misc as util_misc


_moduleLogger = logging.getLogger("handle")


class TheOneRingHandle(tp.Handle):
	"""
	Instances are memoized
	"""

	def __init__(self, connection, id, handleType, name):
		tp.Handle.__init__(self, id, handleType, name)
		self._conn = weakref.proxy(connection)

	def __repr__(self):
		return "<%s id=%u name='%s'>" % (
			type(self).__name__, self.id, self.name
		)

	id = property(tp.Handle.get_id)
	type = property(tp.Handle.get_type)
	name = property(tp.Handle.get_name)


class ConnectionHandle(TheOneRingHandle):

	def __init__(self, connection, id):
		handleType = telepathy.HANDLE_TYPE_CONTACT
		handleName = connection.username
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)

		self.profile = connection.username


class ContactHandle(TheOneRingHandle):

	_DELIMETER = "|"

	def __init__(self, connection, id, contactId, phoneNumber):
		handleType = telepathy.HANDLE_TYPE_CONTACT
		handleName = self.to_handle_name(contactId, phoneNumber)
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)

		self._contactId = contactId
		self._phoneNumber = util_misc.normalize_number(phoneNumber)

	@classmethod
	def from_handle_name(cls, handleName):
		"""
		>>> ContactHandle.from_handle_name("+1 555 123-1234")
		('', '+15551231234')
		>>> ContactHandle.from_handle_name("+15551231234")
		('', '+15551231234')
		>>> ContactHandle.from_handle_name("123456|+15551231234")
		('123456', '+15551231234')
		"""
		parts = handleName.split(cls._DELIMETER, 1)
		if len(parts) == 2:
			contactId, contactNumber = parts[0:2]
		elif len(parts) == 1:
			contactId, contactNumber = "", handleName
		else:
			raise RuntimeError("Invalid handle: %s" % handleName)

		contactNumber = util_misc.normalize_number(contactNumber)
		return contactId, contactNumber

	@classmethod
	def to_handle_name(cls, contactId, contactNumber):
		"""
		>>> ContactHandle.to_handle_name('', "+1 555 123-1234")
		'+15551231234'
		>>> ContactHandle.to_handle_name('', "+15551231234")
		'+15551231234'
		>>> ContactHandle.to_handle_name('123456', "+15551231234")
		'123456|+15551231234'
		"""
		contactNumber = util_misc.normalize_number(contactNumber)
		if contactId:
			handleName = cls._DELIMETER.join((contactId, contactNumber))
		else:
			handleName = contactNumber
		return handleName

	@property
	def contactID(self):
		return self._contactId

	@property
	def phoneNumber(self):
		return self._phoneNumber

	@property
	def contactDetails(self):
		return self._conn.addressbook.get_contact_details(self._id)


class ListHandle(TheOneRingHandle):

	def __init__(self, connection, id, listName):
		handleType = telepathy.HANDLE_TYPE_LIST
		handleName = listName
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)


_HANDLE_TYPE_MAPPING = {
	'connection': ConnectionHandle,
	'contact': ContactHandle,
	'list': ListHandle,
}


def create_handle_factory():

	cache = weakref.WeakValueDictionary()

	def create_handle(connection, type, *args):
		Handle = _HANDLE_TYPE_MAPPING[type]
		key = Handle, connection.username, args
		try:
			handle = cache[key]
			isNewHandle = False
		except KeyError:
			# The misnamed get_handle_id requests a new handle id
			handle = Handle(connection, connection.get_handle_id(), *args)
			cache[key] = handle
			isNewHandle = True
		connection._handles[handle.get_type(), handle.get_id()] = handle
		handleStatus = "Is New!" if isNewHandle else "From Cache"
		_moduleLogger.debug("Created Handle: %r (%s)" % (handle, handleStatus))
		return handle

	return create_handle


create_handle = create_handle_factory()
