import logging
import weakref

import telepathy


_moduleLogger = logging.getLogger("handle")


class MetaMemoize(type):
	"""
	Allows a class to cache off instances for reuse
	"""

	def __call__(cls, connection, *args):
		obj, newlyCreated = cls.__new__(cls, connection, *args)
		if newlyCreated:
			obj.__init__(connection, connection.get_handle_id(), *args)
			_moduleLogger.info("New Handle %r" % obj)
		return obj


class TheOneRingHandle(telepathy.server.Handle):
	"""
	Instances are memoized
	"""

	__metaclass__ = MetaMemoize

	_instances = weakref.WeakValueDictionary()

	def __new__(cls, connection, *args):
		key = cls, connection.username, args
		if key in cls._instances.keys():
			return cls._instances[key], False
		else:
			instance = object.__new__(cls, connection, *args)
			cls._instances[key] = instance # TRICKY: instances is a weakdict
			return instance, True

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

	instance = None

	def __init__(self, connection, id):
		handleType = telepathy.HANDLE_TYPE_CONTACT
		handleName = connection.username
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)

		self.profile = connection.username


def field_join(fields):
	"""
	>>> field_join("1", "First Name")
	'1#First Name'
	"""
	return "#".join(fields)


def field_split(fields):
	"""
	>>> field_split('1#First Name')
	['1', 'First Name']
	"""
	return fields.split("#")


class ContactHandle(TheOneRingHandle):

	def __init__(self, connection, id, contactId, contactAccount):
		handleType = telepathy.HANDLE_TYPE_CONTACT
		handleName = field_join(contactId, contactAccount)
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)

		self.account = contactAccount
		self._id = contactId

	@property
	def contact(self):
		return self._conn.gvoice_client.get_contact_details(self._id)


class ListHandle(TheOneRingHandle):

	def __init__(self, connection, id, listName):
		handleType = telepathy.HANDLE_TYPE_LIST
		handleName = listName
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)


class GroupHandle(TheOneRingHandle):

	def __init__(self, connection, id, groupName):
		handleType = telepathy.HANDLE_TYPE_GROUP
		handleName = groupName
		TheOneRingHandle.__init__(self, connection, id, handleType, handleName)


_HANDLE_TYPE_MAPPING = {
	'connection': ConnectionHandle,
	'contact': ContactHandle,
	'list': ListHandle,
	'group': GroupHandle,
}


def create_handle(connection, type, *args):
	handle = _HANDLE_TYPE_MAPPING[type](connection, *args)
	connection._handles[handle.get_type(), handle.get_id()] = handle
	return handle
