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

	def is_same(self, handleType, handleName):
		return self.get_name() == handleName and self.get_type() == handleType

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

	def __init__(self, connection, id, contactId, phoneNumber):
		handleType = telepathy.HANDLE_TYPE_CONTACT
		handleName = self.to_handle_name(contactId, phoneNumber)
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)

		self._contactId = contactId
		self._phoneNumber = util_misc.strip_number(phoneNumber)

	@staticmethod
	def from_handle_name(handleName):
		parts = handleName.split("#", 1)
		if len(parts) == 2:
			contactId, contactNumber = parts[0:2]
		elif len(parts) == 1:
			contactId, contactNumber = "", handleName
		else:
			raise RuntimeError("Invalid handle: %s" % handleName)

		contactNumber = util_misc.strip_number(contactNumber)
		return contactId, contactNumber

	@staticmethod
	def to_handle_name(contactId, contactNumber):
		handleName = "#".join((contactId, util_misc.strip_number(contactNumber)))
		return handleName

	@classmethod
	def normalize_handle_name(cls, name):
		if "#" in name:
			# Already a properly formatted name, run through the ringer just in case
			return cls.to_handle_name(*cls.from_handle_name(name))
			return name
		else:
			return cls.to_handle_name("", name)

	def is_same(self, handleType, handleName):
		handleName = self.normalize_handle_name(handleName)
		_moduleLogger.info("%r == %r %r?" % (self, handleType, handleName))
		return self.get_name() == handleName and self.get_type() == handleType

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
		if False:
			handleStatus = "Is New!" if isNewHandle else "From Cache"
			_moduleLogger.info("Created Handle: %r (%s)" % (handle, handleStatus))
		return handle

	return create_handle


create_handle = create_handle_factory()
