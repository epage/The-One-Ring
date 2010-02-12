import logging
import weakref

import telepathy

import tp
import util.misc as misc_utils


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

	def __init__(self, connection, id, phoneNumber):
		self._phoneNumber = misc_utils.normalize_number(phoneNumber)

		handleType = telepathy.HANDLE_TYPE_CONTACT
		handleName = self._phoneNumber
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)

	@property
	def phoneNumber(self):
		return self._phoneNumber


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

	def _create_handle(connection, type, *args):
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

	return _create_handle


create_handle = create_handle_factory()
