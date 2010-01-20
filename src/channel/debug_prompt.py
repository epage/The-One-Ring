import cmd
import StringIO
import time
import datetime
import logging

import telepathy

import tp
import gtk_toolbox


_moduleLogger = logging.getLogger("channel.text")


class DebugPromptChannel(tp.ChannelTypeText, cmd.Cmd):
	"""
	Look into implementing ChannelInterfaceMessages for rich text formatting
	"""

	def __init__(self, connection, manager, props, contactHandle):
		self.__manager = manager
		self.__props = props

		cmd.Cmd.__init__(self, "Debug Prompt")
		self.use_rawinput = False
		tp.ChannelTypeText.__init__(self, connection, manager, props)
		self.__nextRecievedId = 0
		self.__lastMessageTimestamp = datetime.datetime(1, 1, 1)

		self.__otherHandle = contactHandle

	@gtk_toolbox.log_exception(_moduleLogger)
	def Send(self, messageType, text):
		if messageType != telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL:
			raise telepathy.errors.NotImplemented("Unhandled message type: %r" % messageType)

		self.Sent(int(time.time()), messageType, text)

		oldStdin, oldStdout = self.stdin, self.stdout
		try:
			self.stdin = currentStdin = StringIO.StringIO()
			self.stdout = currentStdout = StringIO.StringIO()
			self.onecmd(text)
		finally:
			self.stdin, self.stdout = oldStdin, oldStdout

		self._report_new_message(currentStdout.getvalue())

	@gtk_toolbox.log_exception(_moduleLogger)
	def Close(self):
		self.close()

	def close(self):
		_moduleLogger.debug("Closing debug")
		tp.ChannelTypeText.Close(self)
		self.remove_from_connection()

	def _report_new_message(self, message):
		currentReceivedId = self.__nextRecievedId

		timestamp = int(time.time())
		type = telepathy.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL

		self.Received(currentReceivedId, timestamp, self.__otherHandle, type, 0, message.strip())

		self.__nextRecievedId += 1

	def do_reset_state_machine(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			for machine in self._conn.session.stateMachine._machines:
				machine.reset_timers()
		except Exception, e:
			self._report_new_message(str(e))

	def do_get_state(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			state = self._conn.session.stateMachine.state
			self._report_new_message(str(state))
		except Exception, e:
			self._report_new_message(str(e))

	def do_is_authed(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			isAuthed = self._conn.session.backend.is_authed()
			self._report_new_message(str(isAuthed))
		except Exception, e:
			self._report_new_message(str(e))

	def do_is_dnd(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			isDnd = self._conn.session.backend.is_dnd()
			self._report_new_message(str(isDnd))
		except Exception, e:
			self._report_new_message(str(e))

	def do_get_account_number(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			number = self._conn.session.backend.get_account_number()
			self._report_new_message(number)
		except Exception, e:
			self._report_new_message(str(e))

	def do_get_callback_numbers(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			numbers = self._conn.session.backend.get_callback_numbers()
			numbersDisplay = "\n".join(
				"%s: %s" % (name, number)
				for (number, name) in numbers.iteritems()
			)
			self._report_new_message(numbersDisplay)
		except Exception, e:
			self._report_new_message(str(e))

	def do_get_callback_number(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			number = self._conn.session.backend.get_callback_number()
			self._report_new_message(number)
		except Exception, e:
			self._report_new_message(str(e))

	def do_call(self, args):
		if len(args) != 1:
			self._report_new_message("Must specify the phone number and only the phone nunber")
			return

		try:
			number = args[0]
			self._conn.session.backend.call(number)
		except Exception, e:
			self._report_new_message(str(e))

	def do_send_sms(self, args):
		if 1 < len(args):
			self._report_new_message("Must specify the phone number and then message")
			return

		try:
			number = args[0]
			message = " ".join(args[1:])
			self._conn.session.backend.send_sms(number, message)
		except Exception, e:
			self._report_new_message(str(e))
