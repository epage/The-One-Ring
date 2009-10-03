import logging
import weakref

import telepathy


_moduleLogger = logging.getLogger("handle")


class TheOneRingHandle(telepathy.server.Handle):
	"""
	Instances are memoized
	"""

	def __init__(self, connection, id, handleType, name):
		telepathy.server.Handle.__init__(self, id, handleType, name)
		self._conn = weakref.proxy(connection)

	def __repr__(self):
		return "<%s id=%u name='%s'>" % (
			type(self).__name__, self.id, self.name
		)

	id = property(telepathy.server.Handle.get_id)
	type = property(telepathy.server.Handle.get_type)
	name = property(telepathy.server.Handle.get_name)


class ConnectionHandle(TheOneRingHandle):

	def __init__(self, connection, id):
		handleType = telepathy.HANDLE_TYPE_CONTACT
		handleName = connection.username
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)

		self.profile = connection.username


class ContactHandle(TheOneRingHandle):

	def __init__(self, connection, id, contactId):
		handleType = telepathy.HANDLE_TYPE_CONTACT
		handleName = contactId
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)

		self._id = contactId

	@property
	def contactID(self):
		return self._id

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
			handle = Handle(connection, connection.get_handle_id(), *args)
			cache[key] = handle
			isNewHandle = True
		connection._handles[handle.get_type(), handle.get_id()] = handle
		handleStatus = "Is New!" if isNewHandle else "From Cache"
		_moduleLogger.info("Created Handle: %r (%s)" % (handle, handleStatus))
		return handle

	return create_handle


create_handle = create_handle_factory()
