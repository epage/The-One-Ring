# -*- coding: utf-8 -*-
# Generated from the Telepathy spec
"""Copyright © 2008-2009 Collabora Ltd.
Copyright © 2008-2009 Nokia Corporation

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
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
USA.
  
"""

import dbus.service


class ChannelInterfaceMessages(dbus.service.Interface):
    """\
      This interface extends the Text interface to support more general
        messages, including:

      
        messages with attachments (like MIME multipart/mixed)
        groups of alternatives (like MIME multipart/alternative)
        delivery reports
        any extra types of message we need in future
      

      Although this specification supports formatted (rich-text)
        messages with unformatted alternatives, implementations SHOULD NOT
        attempt to send formatted messages until the Telepathy specification
        has also been extended to cover capability discovery for message
        formatting.

      
        We intend to expose all rich-text messages as XHTML-IM, but on some
        protocols, formatting is an extremely limited subset of that format
        (e.g. there are protocols where foreground/background colours, font
        and size can be set, but only for entire messages).
        Until we can tell UIs what controls to offer to the user, it's
        unfriendly to offer the user controls that may have no effect.
      

      This interface also replaces Text.SendError,
        adding support for
        protocols where the message content is not echoed back to the sender on
        failure, adding support for receiving positive acknowledgements,
        and using the Messages queue for state-recovery
        (ensuring that incoming delivery reports are not lost if there is not
        currently a process handling them).

      If this interface is present, clients that support it SHOULD
        listen for the MessageSent and
        MessageReceived signals, and
        ignore the Sent,
        SendError
        and Received
        signals on the Text interface (which are guaranteed to duplicate
        signals from this interface).
    """

    def __init__(self):
        self._interfaces.add('org.freedesktop.Telepathy.Channel.Interface.Messages')

    @dbus.service.method('org.freedesktop.Telepathy.Channel.Interface.Messages', in_signature='aa{sv}u', out_signature='s')
    def SendMessage(self, Message, Flags):
        """
        Submit a message to the server for sending.
          If this method returns successfully, the message has been submitted
          to the server and the MessageSent
          signal is emitted. A corresponding
          Sent
          signal on the Text interface MUST also be emitted.

        This method MUST return before the MessageSent signal is
          emitted.

        
          This means that the process sending the message is the first
            to see the Sent_Message_Token, and can
            relate the message to the corresponding
            MessageSent signal by comparing
            message tokens (if supported by the protocol).
        

        If this method fails, message submission to the server has failed
          and no signal on this interface (or the Text interface) is
          emitted.
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Channel.Interface.Messages', in_signature='uau', out_signature='a{uv}')
    def GetPendingMessageContent(self, Message_ID, Parts):
        """
        Retrieve the content of one or more parts of a pending message.
        Note that this function may take a considerable amount of time
        to return if the part's 'needs-retrieval' flag is true; consider
        extending the default D-Bus method call timeout. Additional API is
        likely to be added in future, to stream large message parts.
      
        """
        raise NotImplementedError
  
    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Interface.Messages', signature='aa{sv}us')
    def MessageSent(self, Content, Flags, Message_Token):
        """
        Signals that a message has been submitted for sending. This
          MUST be emitted exactly once per emission of the Sent
          signal on the
          Text interface.

        
          This signal allows a process that is not the caller of
            SendMessage to log sent messages. The double signal-emission
            provides compatibility with older clients. Clients supporting
            Messages should listen for Messages.MessageSent only (if the
            channel has the Messages interface) or Text.Sent only
            (otherwise).
        
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Interface.Messages', signature='au')
    def PendingMessagesRemoved(self, Message_IDs):
        """
        The messages with the given IDs have been removed from the
        PendingMessages list. Clients SHOULD NOT
        attempt to acknowledge those messages.

        
          This completes change notification for the PendingMessages property
          (previously, there was change notification when pending messages
          were added, but not when they were removed).
        
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Interface.Messages', signature='aa{sv}')
    def MessageReceived(self, Message):
        """
        Signals that a message has been received and added to the pending
        messages queue. This MUST be emitted exactly once per emission of the
        Received
        signal on the Text interface.

        
          The double signal-emission provides compatibility with older
          clients. Clients supporting Messages should listen for
          Messages.MessageReceived only (if the channel has the Messages
          interface) or Text.Received only (otherwise).
        
      
        """
        pass
  