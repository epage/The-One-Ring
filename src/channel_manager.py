import logging

import dbus
import telepathy

import channel
import util.misc as util_misc


_moduleLogger = logging.getLogger("channel_manager")


class TelepathyChannelManager(object):

	def __init__(self, connection):
		self._conn = connection

		self._requestable_channel_classes = dict()
		self._channels = dict()
		self._fixed_properties = dict()
		self._available_properties = dict()

	def close(self):
		for channel_type in self._requestable_channel_classes:
			for chan in self._channels[channel_type].values():
				try:
					_moduleLogger.info("Closing %s %s" % (channel_type, chan._object_path))
					chan.Close()
				except Exception:
					_moduleLogger.exception("Shutting down %r" % (chan, ))

	def remove_channel(self, chan):
		for channel_type in self._requestable_channel_classes:
			for handle, ichan in self._channels[channel_type].items():
				if chan == ichan:
					del self._channels[channel_type][handle]

	def _get_type_requested_handle(self, props):
		type = props[telepathy.interfaces.CHANNEL_INTERFACE + '.ChannelType']
		requested = props[telepathy.interfaces.CHANNEL_INTERFACE + '.Requested']
		target_handle = props[telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandle']
		target_handle_type = props[telepathy.interfaces.CHANNEL_INTERFACE + '.TargetHandleType']

		handle = self._conn._handles[target_handle_type, target_handle]

		return (type, requested, handle)

	def channel_exists(self, props):
		type, _, handle = self._get_type_requested_handle(props)

		if type in self._channels:
			if handle in self._channels[type]:
				return True

		return False

	def channel_for_props(self, props, signal=True, **args):
		type, suppress_handler, handle = self._get_type_requested_handle(props)

		if type not in self._requestable_channel_classes:
			raise NotImplemented('Unknown channel type "%s"' % type)

		if self.channel_exists(props):
			return self._channels[type][handle]

		chan = self._requestable_channel_classes[type](props, **args)

		if hasattr(self._conn, "add_channels"):
			# HACK Newer python-telepathy
			self._conn.add_channels([chan], signal=signal)
		elif hasattr(self._conn, "add_channel"):
			# HACK Older python-telepathy
			self._conn.add_channel(chan, handle, suppress_handler)
		else:
			raise RuntimeError("Uhh, what just happened with the connection")
		self._channels[type][handle] = chan

		return chan

	def _implement_channel_class(self, type, make_channel, fixed, available):
		self._requestable_channel_classes[type] = make_channel
		self._channels.setdefault(type, {})

		self._fixed_properties[type] = fixed
		self._available_properties[type] = available

	def get_requestable_channel_classes(self):
		retval = []

		for channel_type in self._requestable_channel_classes:
			retval.append((self._fixed_properties[channel_type],
				self._available_properties[channel_type]))

		return retval


class ChannelManager(TelepathyChannelManager):

	def __init__(self, connection):
		TelepathyChannelManager.__init__(self, connection)

		fixed = {
			telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_TEXT,
			telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT)
		}
		self._implement_channel_class(
			telepathy.CHANNEL_TYPE_TEXT,
			self._get_text_channel,
			fixed,
			[]
		)

		fixed = {
			telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_CONTACT_LIST
		}
		self._implement_channel_class(
			telepathy.CHANNEL_TYPE_CONTACT_LIST,
			self._get_list_channel,
			fixed,
			[]
		)

		fixed = {
			telepathy.CHANNEL_INTERFACE + '.ChannelType': telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
			telepathy.CHANNEL_INTERFACE + '.TargetHandleType': dbus.UInt32(telepathy.HANDLE_TYPE_CONTACT)
		}
		self._implement_channel_class(
			telepathy.CHANNEL_TYPE_STREAMED_MEDIA,
			self._get_media_channel,
			fixed,
			[telepathy.CHANNEL_INTERFACE + '.TargetHandle']
		)

	def _get_list_channel(self, props):
		_, surpress_handler, h = self._get_type_requested_handle(props)

		_moduleLogger.debug('New contact list channel')
		chan = channel.contact_list.create_contact_list_channel(self._conn, self, props, h)
		return chan

	def _get_text_channel(self, props):
		_, surpress_handler, h = self._get_type_requested_handle(props)

		accountNumber = util_misc.strip_number(self._conn.session.backend.get_account_number())
		if h.phoneNumber == accountNumber:
			_moduleLogger.debug('New Debug channel')
			chan = channel.debug_prompt.DebugPromptChannel(self._conn, self, props, h)
		else:
			_moduleLogger.debug('New text channel')
			chan = channel.text.TextChannel(self._conn, self, props, h)
		return chan

	def _get_media_channel(self, props):
		_, surpress_handler, h = self._get_type_requested_handle(props)

		_moduleLogger.debug('New media channel')
		chan = channel.call.CallChannel(self._conn, self, props, h)
		return chan
