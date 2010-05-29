# -*- coding: utf-8 -*-
# Generated from the Telepathy spec
""" Copyright © 2005-2009 Collabora Limited 
 Copyright © 2005-2009 Nokia Corporation 
 Copyright © 2006 INdT 

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


class ChannelTypeStreamedMedia(dbus.service.Interface):
    """\
      A channel that can send and receive streamed media such as audio or video.
    Provides a number of methods for listing and requesting new streams, and
    signals to indicate when streams have been added, removed and changed
    status.

      To make a media call to a contact, clients should call CreateChannel
        with ChannelType
        = StreamedMedia,
        TargetHandleType
        = Contact, and one of TargetHandle
        or TargetID
        (which should yield a channel with the local user in Members,
        and the remote contact as TargetHandle
        but not in any group members list), then call
        RequestStreams to initiate the call (at
        which point the contact should appear in the channel's RemotePendingMembers).

      In the past, several other patterns have been used to place outgoing
        calls; see
        'Requesting StreamedMedia Channels' on the Telepathy wiki
        for the details.

      Incoming calls should be signalled as TargetHandleType
        = Contact, TargetHandle
        set to the remote contact, with the local user in LocalPendingMembers;
        to accept the call, AddMembers
        can be used to move the local user to the group's members.

      When the local user accepts an incoming call, the connection manager
        SHOULD change the direction of any streams with pending local send
        to be sending, without altering whether those streams are
        receiving.

      
        This matches existing practice, and means that a client
          can answer incoming calls and get an unmuted microphone/activated
          webcam without having to take additional action to accept the
          stream directions.

        It does, however, introduce a race condition: a client believing
          that it is accepting an audio-only call by calling AddMembers
          can inadvertantly accept an audio + video call (and hence activate
          sending from a webcam without the user's permission) if a video
          stream is added just before AddMembers is processed. This race
          should be removed when this specification is revised.
      

    In general this should be used in conjunction with the MediaSignalling
    interface to exchange connection candidates and codec choices with
    whichever component is responsible for the streams. However, in certain
    applications where no candidate exchange is necessary (eg the streams are
    handled by specialised hardware which is controlled directly by the
    connection manager), the signalling interface can be omitted and this
    channel type used simply to control the streams.
    """

    @dbus.service.method('org.freedesktop.Telepathy.Channel.Type.StreamedMedia', in_signature='', out_signature='a(uuuuuu)')
    def ListStreams(self):
        """
        Returns an array of structs representing the streams currently active
        within this channel. Each stream is identified by an unsigned integer
        which is unique for each stream within the channel.
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Channel.Type.StreamedMedia', in_signature='au', out_signature='')
    def RemoveStreams(self, Streams):
        """
        Request that the given streams are removed. If all streams are
          removed, the channel MAY close.

        Clients SHOULD NOT attempt to terminate calls by removing all the
          streams; instead, clients SHOULD terminate calls by removing the
          Group.SelfHandle
          from the channel, using either
          RemoveMembers
          or
          RemoveMembersWithReason.
          
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Channel.Type.StreamedMedia', in_signature='uu', out_signature='')
    def RequestStreamDirection(self, Stream_ID, Stream_Direction):
        """
        Request a change in the direction of an existing stream. In particular,
        this might be useful to stop sending media of a particular type,
        or inform the peer that you are no longer using media that is being
        sent to you.

        Depending on the protocol, streams which are no longer sending in
        either direction should be removed and a
        StreamRemoved signal emitted.
        Some direction changes can be enforced locally (for example,
        BIDIRECTIONAL -> RECEIVE can be achieved by merely stopping sending),
        others may not be possible on some protocols, and some need agreement
        from the remote end. In this case, the MEDIA_STREAM_PENDING_REMOTE_SEND
        flag will be set in the
        StreamDirectionChanged signal, and the
        signal
        emitted again without the flag to indicate the resulting direction when
        the remote end has accepted or rejected the change.
      
        """
        raise NotImplementedError
  
    @dbus.service.method('org.freedesktop.Telepathy.Channel.Type.StreamedMedia', in_signature='uau', out_signature='a(uuuuuu)')
    def RequestStreams(self, Contact_Handle, Types):
        """
        Request that streams be established to exchange the given types of
        media with the given member. In general this will try and establish a
        bidirectional stream, but on some protocols it may not be possible to
        indicate to the peer that you would like to receive media, so a
        send-only stream will be created initially. In the cases where the
        stream requires remote agreement (eg you wish to receive media from
        them), the StreamDirectionChanged signal
        will be emitted with the
        MEDIA_STREAM_PENDING_REMOTE_SEND flag set, and the signal emitted again
        with the flag cleared when the remote end has replied.

        If streams of the requested types already exist, calling this
          method results in the creation of additional streams. Accordingly,
          clients wishing to have exactly one audio stream or exactly one
          video stream SHOULD check for the current streams using
          ListStreams before calling this
          method.
      
        """
        raise NotImplementedError
  
    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Type.StreamedMedia', signature='uuu')
    def StreamAdded(self, Stream_ID, Contact_Handle, Stream_Type):
        """
        Emitted when a new stream has been added to this channel.
          Clients SHOULD assume that the stream's
          Media_Stream_State is initially Disconnected.

        If a connection manager needs to represent the addition of a stream
          whose state is already Connecting or Connected, it MUST do this
          by emitting StreamAdded, closely followed by
          StreamStateChanged indicating a
          change to the appropriate state.

        
          Historically, it was not clear from the StreamAdded signal what
            the state of the stream was. telepathy-spec 0.17.22
            clarified this.
        

        Similarly, clients SHOULD assume that the initial
          Media_Stream_Direction of a newly added stream
          is Receive, and that the initial
          Media_Stream_Pending_Send is
          Pending_Local_Send.

        If a connection manager needs to represent the addition of a stream
          whose direction or pending-send differs from those initial values,
          it MUST do so by emitting StreamAdded, closely followed by
          StreamDirectionChanged indicating a
          change to the appropriate direction and pending-send state.

        
          StreamAdded doesn't itself indicate the stream's direction; this
            is unfortunate, but is preserved for compatibility.

          This is the appropriate direction for streams added by a remote
            contact on existing connection managers, and does not violate
            user privacy by automatically sending audio or video (audio streams
            start off muted, video streams start off not sending). For
            streams added by the local user using the client receiving the
            signal, the true direction can also be determined from the return
            value of the RequestStreams
            method.

          Existing clients typically operate by maintaining a separate
            idea of the directions that they would like the streams to have,
            and enforcing these intended directions by calling
            RequestStreamDirection whenever
            needed.
        
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Type.StreamedMedia', signature='uuu')
    def StreamDirectionChanged(self, Stream_ID, Stream_Direction, Pending_Flags):
        """
        Emitted when the direction or pending flags of a stream are
          changed.

        If the MEDIA_STREAM_PENDING_LOCAL_SEND flag is set, the remote user
          has requested that we begin sending on this stream.
          RequestStreamDirection
          should be called to indicate whether or not this change is
          acceptable.

        
          This allows for a MSN-style user interface, "Fred has asked you
            to enable your webcam. (Accept | Reject)", if desired.
        
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Type.StreamedMedia', signature='uus')
    def StreamError(self, Stream_ID, Error_Code, Message):
        """
        Emitted when a stream encounters an error.
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Type.StreamedMedia', signature='u')
    def StreamRemoved(self, Stream_ID):
        """
        Emitted when a stream has been removed from this channel.
      
        """
        pass
  
    @dbus.service.signal('org.freedesktop.Telepathy.Channel.Type.StreamedMedia', signature='uu')
    def StreamStateChanged(self, Stream_ID, Stream_State):
        """
        Emitted when a member's stream's state changes.
      
        """
        pass
  