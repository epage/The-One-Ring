# -*- coding: utf-8 -*-
# Generated from the Telepathy spec
"""Copyright (C) 2005, 2006 Collabora Limited
Copyright (C) 2005, 2006 Nokia Corporation
Copyright (C) 2006 INdT

    This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
  
"""

import dbus.service


class ChannelInterfaceDTMF(dbus.service.Interface):
    """\
      An interface that gives a Channel the ability to send DTMF events over
      audio streams which have been established using the StreamedMedia channel
      type. The event codes used are in common with those defined in RFC4733, and are
      listed in the DTMF_Event enumeration.
    """

    def __init__(self):
        self._interfaces.add('org.freedesktop.Telepathy.Channel.Interface.DTMF')

    @dbus.service.method('org.freedesktop.Telepathy.Channel.Interface.DTMF', in_signature='uy', out_signature='')
    def StartTone(self, Stream_ID, Event):
        """
        Start sending a DTMF tone on this stream. Where possible, the tone
        will continue until StopTone is called.
        On certain protocols, it may
        only be possible to send events with a predetermined length. In this
        case, the implementation may emit a fixed-length tone, and the StopTone
        method call should return NotAvailable.
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Channel.Interface.DTMF', in_signature='u', out_signature='')
    def StopTone(self, Stream_ID):
        """
        Stop sending any DTMF tone which has been started using the
        StartTone
        method. If there is no current tone, this method will do nothing.
      
        """
        raise NotImplementedError
  