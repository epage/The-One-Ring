from __future__ import with_statement

import os
import logging

import telepathy

import tp
import util.misc as misc_utils


_moduleLogger = logging.getLogger(__name__)


class AvatarsMixin(tp.server.ConnectionInterfaceAvatars):

	__SELF_AVATAR = "tor_self"
	__MOBILE_AVATAR = "tor_handset"
	__LANDLINE_AVATAR = "tor_phone"
	__OTHER_AVATAR = "tor_question"

	__LOOKUP_PATHS = (
		"/usr/share/theonering",
		os.path.join(os.path.dirname(__file__), "../support/icons"),
	)

	def __init__(self):
		tp.server.ConnectionInterfaceAvatars.__init__(self)
		self._avatarCache = {}

		self._implement_property_get(
			telepathy.interfaces.CONNECTION_INTERFACE_AVATARS,
			{
				'SupportedAvatarMimeTypes': lambda: ("image/png", ),
				'MinimumAvatarHeight': lambda: 32,
				'MinimumAvatarWidth': lambda: 32,
				'RecommendedAvatarHeight': lambda: 32,
				'RecommendedAvatarWidth': lambda: 32,
				'MaximumAvatarHeight': lambda: 32,
				'MaximumAvatarWidth': lambda: 32,
				'MaximumAvatarBytes': lambda: 500 * 1024,
			},
		)

	@property
	def session(self):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract property called")

	def get_handle_by_id(self, handleType, handleId):
		"""
		@abstract
		"""
		raise NotImplementedError("Abstract function called")

	@misc_utils.log_exception(_moduleLogger)
	def GetAvatarRequirements(self):
		mime_types = ("image/png", )
		return (mime_types, 32, 32, 64, 64, 500 * 1024)

	@misc_utils.log_exception(_moduleLogger)
	def GetAvatarTokens(self, contacts):
		result = {}
		for handleid in contacts:
			imageName = self._select_avatar(handleid)
			result[handleid] = imageName
		return result

	@misc_utils.log_exception(_moduleLogger)
	def GetKnownAvatarTokens(self, contacts):
		result = {}
		for handleid in contacts:
			imageName = self._select_avatar(handleid)
			result[handleid] = imageName
		return result

	@misc_utils.log_exception(_moduleLogger)
	def RequestAvatar(self, contact):
		imageName = self._select_avatar(contact)
		image = self._get_avatar(imageName)
		return image, "image/png"

	@misc_utils.log_exception(_moduleLogger)
	def RequestAvatars(self, contacts):
		for handleid in contacts:
			imageName = self._select_avatar(handleid)
			image = self._get_avatar(imageName)
			self.AvatarRetrieved(handleid, imageName, image, "image/png")

	@misc_utils.log_exception(_moduleLogger)
	def SetAvatar(self, avatar, mime_type):
		raise telepathy.errors.PermissionDenied

	@misc_utils.log_exception(_moduleLogger)
	def ClearAvatar(self):
		pass

	def _select_avatar(self, handleId):
		handle = self.get_handle_by_id(telepathy.HANDLE_TYPE_CONTACT, handleId)

		if handle == self.GetSelfHandle():
			imageName = self.__SELF_AVATAR
		else:
			accountNumber = misc_utils.normalize_number(self.session.backend.get_account_number())
			phoneType = self.session.addressbook.get_phone_type(handle.phoneNumber)
			if handle.phoneNumber == accountNumber:
				imageName = self.__SELF_AVATAR
			elif phoneType in ("mobile", ):
				imageName = self.__MOBILE_AVATAR
			elif phoneType in ("home", "work"):
				imageName = self.__LANDLINE_AVATAR
			else:
				imageName = self.__OTHER_AVATAR

		return imageName

	def _get_avatar(self, imageName):
		try:
			return self._avatarCache[imageName]
		except KeyError:
			image = self._load_avatar(imageName)
			self._avatarCache[imageName] = image
			return image

	def _load_avatar(self, imageName):
		_moduleLogger.debug("Loading avatar %r from file" % (imageName, ))
		try:
			with open(os.sep.join([self.__LOOKUP_PATHS[0], imageName+".png"]), "rb") as f:
				return f.read()
		except IOError:
			with open(os.sep.join([self.__LOOKUP_PATHS[1], "32-"+imageName+".png"]), "rb") as f:
				return f.read()
