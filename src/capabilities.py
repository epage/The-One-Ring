import logging

import telepathy

import gtk_toolbox


_moduleLogger = logging.getLogger('capabilities')


class CapabilitiesMixin(telepathy.server.ConnectionInterfaceCapabilities):

	def __init__(self):
		telepathy.server.ConnectionInterfaceCapabilities.__init__(self)
		self._implement_property_get(
			telepathy.interfaces.CONN_INTERFACE_CAPABILITIES,
			{"caps": self.GetCapabilities},
		)

	@property
	def session(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	@property
	def handle(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetCapabilities(self, handles):
		"""
		@todo HACK Remove this once we are building against a fixed version of python-telepathy
		"""
		ret = []
		for handle in handles:
			if handle != 0 and (telepathy.HANDLE_TYPE_CONTACT, handle) not in self._handles:
				raise telepathy.errors.InvalidHandle
			elif handle in self._caps:
				theirs = self._caps[handle]
				for type in theirs:
					ret.append([handle, type, theirs[0], theirs[1]])
		_moduleLogger.info("GetCaps %r" % ret)
		return ret

	@gtk_toolbox.log_exception(_moduleLogger)
	def AdvertiseCapabilities(self, add, remove):
		"""
		@todo HACK Remove this once we are building against a fixed version of python-telepathy
		"""
		my_caps = self._caps.setdefault(self._self_handle, {})

		changed = {}
		for ctype, spec_caps in add:
			changed[ctype] = spec_caps
		for ctype in remove:
			changed[ctype] = None

		caps = []
		for ctype, spec_caps in changed.iteritems():
			gen_old, spec_old = my_caps.get(ctype, (0, 0))
			if spec_caps is None:
				# channel type no longer supported (provider has gone away)
				gen_new, spec_new = 0, 0
			else:
				# channel type supports new capabilities
				gen_new, spec_new = gen_old, spec_old | spec_caps
			if spec_old != spec_new or gen_old != gen_new:
				caps.append((self._self_handle, ctype, gen_old, gen_new,
							spec_old, spec_new))

		_moduleLogger.info("CapsChanged %r" % caps)
		self.CapabilitiesChanged(caps)

		# return all my capabilities
		ret = [(ctype, caps[1]) for ctype, caps in my_caps.iteritems()]
		_moduleLogger.info("Adv %r" % ret)
		return ret
