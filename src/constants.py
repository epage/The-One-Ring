import os

__pretty_app_name__ = "Telepathy-TheOneRing"
__app_name__ = "telepathy-theonering"
__version__ = "0.7.6"
__build__ = 0
__app_magic__ = 0xdeadbeef
_data_path_ = os.path.join(os.path.expanduser("~"), ".telepathy-theonering")
_user_settings_ = "%s/settings.ini" % _data_path_
_user_logpath_ = "%s/theonering.log" % _data_path_
_telepathy_protocol_name_ = "sip"
_telepathy_implementation_name_ = "theonering"
