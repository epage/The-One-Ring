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

	def handle(self, handleType, handleId):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract function called")

	def GetSelfHandle(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract function called")

	@gtk_toolbox.log_exception(_moduleLogger)
	def GetCapabilities(self, handleIds):
		"""
		@todo HACK Remove this once we are building against a fixed version of python-telepathy
		"""
		ret = []
		for handleId in handleIds:
			h = self.handle(telepathy.HANDLE_TYPE_CONTACT, handleId)
			if handleId != 0 and (telepathy.HANDLE_TYPE_CONTACT, handleId) not in self._handles:
				raise telepathy.errors.InvalidHandle
			elif h in self._caps:
				types = self._caps[h]
				for type in types:
					for ctype, specs in types.iteritems():
						ret.append([handleId, type, specs[0], specs[1]])
			else:
				# No caps, so just default to the connection's caps
				types = self._caps[self.GetSelfHandle()]
				for type in types:
					for ctype, specs in types.iteritems():
						ret.append([handleId, type, specs[0], specs[1]])
		return ret

	@gtk_toolbox.log_exception(_moduleLogger)
	def AdvertiseCapabilities(self, add, remove):
		"""
		@todo HACK Remove this once we are building against a fixed version of python-telepathy
		"""
		my_caps = self._caps.setdefault(self.GetSelfHandle(), {})

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
				caps.append((self.GetSelfHandle(), ctype, gen_old, gen_new,
							spec_old, spec_new))

		self.CapabilitiesChanged(caps)
		_moduleLogger.info("CapsChanged %r" % self._caps)

		# return all my capabilities
		ret = [(ctype, caps[1]) for ctype, caps in my_caps.iteritems()]
		return ret
