import itertools
import logging

import telepathy

import tp
import gtk_toolbox
import util.coroutines as coroutines


_moduleLogger = logging.getLogger('capabilities')


class CapabilitiesMixin(tp.ConnectionInterfaceCapabilities):

	def __init__(self):
		tp.ConnectionInterfaceCapabilities.__init__(self)
		self._caps[telepathy.CHANNEL_TYPE_STREAMED_MEDIA] = self._get_capabilities(
			None, telepathy.CHANNEL_TYPE_STREAMED_MEDIA
		)
		self._callback = coroutines.func_sink(
			coroutines.expand_positional(
				self._on_contacts_refreshed
			)
		)
		self.session.addressbook.updateSignalHandler.register_sink(
			self._callback
		)

	@property
	def session(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	def GetSelfHandle():
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract function called")

	def get_handle_by_name(self, handleType, handleName):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract function called")

	@gtk_toolbox.log_exception(_moduleLogger)
	def _on_contacts_refreshed(self, addressbook, added, removed, changed):
		capabilityDifferences = []
		for isAdded, phoneNumber in itertools.chain(
			itertools.izip(itertools.repeat(True), added),
			itertools.izip(itertools.repeat(False), removed),
		):
			handle = self.get_handle_by_name(telepathy.HANDLE_TYPE_CONTACT, phoneNumber)
			ctype = telepathy.CHANNEL_TYPE_STREAMED_MEDIA

			if isAdded:
				new_gen, new_spec = self._get_capabilities(handle, ctype)
			else:
				new_gen, new_spec = 0, 0
			old_gen, old_spec = self._get_old_capabilities(handle, ctype)

			if old_gen == new_gen and old_spec == new_spec:
				continue

			diff = (int(handle), ctype, old_gen, new_gen, old_spec, new_spec)
			capabilityDifferences.append(diff)
		self.CapabilitiesChanged(capabilityDifferences)

	def _get_old_capabilities(self, handle, ctype):
		if handle in self._caps:
			old_gen, old_spec = self._caps[handle][ctype]
		else:
			old_gen = 0
			old_spec = 0
		return old_gen, old_spec

	def _get_capabilities(self, handle, ctype):
		gen_caps = 0
		spec_caps = 0

		gen_caps |= telepathy.CONNECTION_CAPABILITY_FLAG_CREATE
		gen_caps |= telepathy.CONNECTION_CAPABILITY_FLAG_INVITE
		spec_caps |= telepathy.CHANNEL_MEDIA_CAPABILITY_AUDIO

		return gen_caps, spec_caps
