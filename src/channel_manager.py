import logging

import dbus
import telepathy

import tp
import channel
import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class ChannelManager(tp.ChannelManager):

	def __init__(self, connection):
		tp.ChannelManager.__init__(self, connection)

		classes = [
			(
				{
					telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_CONTACT_LIST,
					telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_LIST),
				},
				[
					telepathy.CHANNEL_INTERFACE + '.TargetHandle',
					telepathy.CHANNEL_INTERFACE + '.TargetID',
				],
			),
		]
		self.implement_channel_classes(
			telepathy.CHANNEL_TYPE_CONTACT_LIST,
			self._get_list_channel,
			classes,
		)

		classes = [
			(
				{
					telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_TEXT,
					telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT)
				},
				[
					telepathy.CHANNEL_INTERFACE + '.TargetHandle',
					telepathy.CHANNEL_INTERFACE + '.TargetID',
				],
			),
		]
		self.implement_channel_classes(
			telepathy.CHANNEL_TYPE_TEXT,
			self._get_text_channel,
			classes,
		)

		classes = [
			(
				{
					telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_FILE_TRANSFER,
					telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT)
				},
				[
					telepathy.CHANNEL_INTERFACE + '.TargetHandle',
					telepathy.CHANNEL_INTERFACE + '.TargetID',
				],
			),
		]
		self.implement_channel_classes(
			telepathy.CHANNEL_TYPE_FILE_TRANSFER,
			self._get_file_transfer_channel,
			classes,
		)

		classes = [
			(
				{
					telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
					telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT)
				},
				[
					telepathy.CHANNEL_INTERFACE + '.TargetHandle',
					telepathy.CHANNEL_INTERFACE + '.TargetID',
					telepathy.CHANNEL_TYPE_STREAMED_MEDIA + '.InitialAudio',
					telepathy.CHANNEL_TYPE_STREAMED_MEDIA + '.InitialVideo',
				],
			),
		]
		self.implement_channel_classes(
			telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
			self._get_media_channel,
			classes,
		)

	def _get_list_channel(self, props):
		_, surpress_handler, h = self._get_type_requested_handle(props)

		_moduleLogger.debug('New contact list channel')
		chan = channel.contact_list.create_contact_list_channel(self._conn, self, props, h)
		return chan

	def _get_text_channel(self, props):
		_, surpress_handler, h = self._get_type_requested_handle(props)

		accountNumber = misc_utils.normalize_number(self._conn.session.backend.get_account_number())
		if h.phoneNumber == accountNumber:
			_moduleLogger.debug('New Debug channel')
			chan = channel.debug_prompt.DebugPromptChannel(self._conn, self, props, h)
		else:
			_moduleLogger.debug('New text channel')
			chan = channel.text.TextChannel(self._conn, self, props, h)
		return chan

	def _get_file_transfer_channel(self, props):
		_, surpress_handler, h = self._get_type_requested_handle(props)

		_moduleLogger.debug('New file transfer channel')
		chan = channel.debug_log.DebugLogChannel(self._conn, self, props, h)
		return chan

	def _get_media_channel(self, props):
		_, surpress_handler, h = self._get_type_requested_handle(props)

		_moduleLogger.debug('New media channel')
		chan = channel.call.CallChannel(self._conn, self, props, h)
		return chan
