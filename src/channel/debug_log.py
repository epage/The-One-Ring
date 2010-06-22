from __future__ import with_statement

import os
import socket
import logging

import telepathy

import constants
import tp
import util.go_utils as gobject_utils
import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class DebugLogChannel(tp.ChannelTypeFileTransfer):

	def __init__(self, connection, manager, props, contactHandle):
		self.__manager = manager
		self.__props = props
		self.__otherHandle = contactHandle
		self.__socket = None
		self.__socketName = ""
		self.__delayWrite = gobject_utils.Timeout(self._on_write)

		tp.ChannelTypeFileTransfer.__init__(self, connection, manager, props)

		dbus_interface = telepathy.CHANNEL_TYPE_FILE_TRANSFER
		self._implement_property_get(
			dbus_interface,
			{
				'State': self.get_state,
				"ContentType": self.get_content_type,
				"Filename": self.get_filename,
				"Size": self.get_state,
				"Description": self.get_description,
				"AvailableSocketTypes": self.get_available_socket_types,
				"TransferredBytes": self.get_transferred_bytes,
				"InitialOffset": self.get_initial_offset,
			},
		)

		# grab a snapshot of the log so that we are always in a consistent
		# state between calls
		with open(constants._user_logpath_, "r") as f:
			logLines = f.xreadlines()
			self._log = "".join(logLines)
		self._transferredBytes = 0

		self._state = telepathy.constants.FILE_TRANSFER_STATE_PENDING
		self.FileTransferStateChanged(
			self._state,
			telepathy.constants.FILE_TRANSFER_STATE_CHANGE_REASON_NONE,
		)

	def get_state(self):
		return self._state

	def get_content_type(self):
		return "application/octet-stream"

	def get_filename(self):
		return "%s.log" % constants._telepathy_implementation_name_

	def get_size(self):
		return len(self._log)

	def get_description(self):
		return "Debug log for The One Ring"

	def get_available_socket_types(self):
		return {
			telepathy.constants.SOCKET_ADDRESS_TYPE_UNIX: [
				telepathy.constants.SOCKET_ACCESS_CONTROL_LOCALHOST,
				telepathy.constants.SOCKET_ACCESS_CONTROL_CREDENTIALS,
			],
		}

	def get_transferred_bytes(self):
		return self._transferredBytes

	def get_initial_offset(self):
		return 0

	@misc_utils.log_exception(_moduleLogger)
	def AcceptFile(self, addressType, accessControl, accessControlParam, offset):
		# @bug All wrong
		_moduleLogger.info("%r %r %r %r" % (addressType, accessControl, accessControlParam, offset))
		assert not self.__socketName, self.__socketName
		self.__socketName = os.tempnam()

		assert self.__socket is None, self.__socket
		self.__socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
		self.__socket.bind(self.__socketName)

		self._state = telepathy.constants.FILE_TRANSFER_STATE_ACCEPTED
		self.FileTransferStateChanged(
			self._state,
			telepathy.constants.FILE_TRANSFER_STATE_CHANGE_REASON_REQUESTED,
		)

		self.__delayWrite.start(seconds=0)

		return self.__socketName

	@misc_utils.log_exception(_moduleLogger)
	def ProvideFile(self, addressType, accessControl, accessControlParam):
		raise telepathy.errors.NotImplemented("Cannot send outbound files")

	@misc_utils.log_exception(_moduleLogger)
	def Close(self):
		self.close()

	def close(self):
		_moduleLogger.debug("Closing log")
		if self.__socket is not None:
			self.__socket.close()
		tp.ChannelTypeFileTransfer.Close(self)
		self.remove_from_connection()

	@misc_utils.log_exception(_moduleLogger)
	def _on_write(self):
		self.__socket.listen(1)
		conn, addr = self.__socket.accept()

		self.InitialOffsetDefined(0)
		self._state = telepathy.constants.FILE_TRANSFER_STATE_OPEN
		self.FileTransferStateChanged(
			self._state,
			telepathy.constants.FILE_TRANSFER_STATE_CHANGE_REASON_NONE,
		)

		conn.send(self._log)

		self._transferredBytes = len(self._log)
		self.TransferredBytesChanged(self._transferredBytes)

		self._state = telepathy.constants.FILE_TRANSFER_STATE_COMPLETED
		self.FileTransferStateChanged(
			self._state,
			telepathy.constants.FILE_TRANSFER_STATE_CHANGE_REASON_NONE,
		)
