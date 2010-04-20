from __future__ import with_statement

import os
import cmd
import StringIO
import time
import datetime
import logging

import telepathy

import constants
import tp
import util.misc as misc_utils
import util.go_utils as gobject_utils
import gvoice


_moduleLogger = logging.getLogger(__name__)


class DebugPromptChannel(tp.ChannelTypeText, cmd.Cmd):

	def __init__(self, connection, manager, props, contactHandle):
		self.__manager = manager
		self.__props = props

		cmd.Cmd.__init__(self, "Debug Prompt")
		self.use_rawinput = False
		tp.ChannelTypeText.__init__(self, connection, manager, props)
		self.__nextRecievedId = 0
		self.__lastMessageTimestamp = datetime.datetime(1, 1, 1)

		self.__otherHandle = contactHandle

	@misc_utils.log_exception(_moduleLogger)
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

		stdoutData = currentStdout.getvalue().strip()
		if stdoutData:
			self._report_new_message(stdoutData)

	@misc_utils.log_exception(_moduleLogger)
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
		try:
			args = args.strip().lower()
			if not args:
				args  = "all"
			if args == "all":
				for machine in self._conn.session.stateMachine._machines:
					machine.reset_timers()
			elif args == "contacts":
				self._conn.session.addressbookStateMachine.reset_timers()
			elif args == "voicemail":
				self._conn.session.voicemailsStateMachine.reset_timers()
			elif args == "texts":
				self._conn.session.textsStateMachine.reset_timers()
			else:
				self._report_new_message('Unknown machine "%s"' % (args, ))
		except Exception, e:
			self._report_new_message(str(e))

	def help_reset_state_machine(self):
		self._report_new_message("""Reset the refreshing state machine.
"reset_state_machine" - resets all
"reset_state_machine all"
"reset_state_machine contacts"
"reset_state_machine voicemail"
"reset_state_machine texts"
""")

	def do_get_state(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			state = self._conn.session.stateMachine.state
			self._report_new_message(str(state))
		except Exception, e:
			self._report_new_message(str(e))

	def help_get_state(self):
		self._report_new_message("Print the current state the refreshing state machine is in")

	def do_get_polling(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return
		self._report_new_message("\n".join((
			"Contacts:", repr(self._conn.session.addressbookStateMachine)
		)))
		self._report_new_message("\n".join((
			"Voicemail:", repr(self._conn.session.voicemailsStateMachine)
		)))
		self._report_new_message("\n".join((
			"Texts:", repr(self._conn.session.textsStateMachine)
		)))

	def help_get_polling(self):
		self._report_new_message("Prints the frequency each of the state machines updates")

	def do_get_state_status(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return
		self._report_new_message("\n".join((
			"Contacts:", str(self._conn.session.addressbookStateMachine)
		)))
		self._report_new_message("\n".join((
			"Voicemail:", str(self._conn.session.voicemailsStateMachine)
		)))
		self._report_new_message("\n".join((
			"Texts:", str(self._conn.session.textsStateMachine)
		)))

	def help_get_state_status(self):
		self._report_new_message("Prints the current setting for the state machines")

	def do_is_authed(self, args):
		le = gobject_utils.AsyncLinearExecution(self._conn.session.pool, self._is_authed)
		le.start(args)

	@misc_utils.log_exception(_moduleLogger)
	def _is_authed(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			isAuthed = yield (
				self._conn.session.backend.is_authed,
				(),
				{}
			)
			self._report_new_message(str(isAuthed))
		except Exception, e:
			self._report_new_message(str(e))
			return

	def help_is_authed(self):
		self._report_new_message("Print whether logged in to Google Voice")

	def do_is_dnd(self, args):
		le = gobject_utils.AsyncLinearExecution(self._conn.session.pool, self._is_dnd)
		le.start(args)

	@misc_utils.log_exception(_moduleLogger)
	def _is_dnd(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			isDnd = yield (
				self._conn.session.backend.is_dnd,
				(),
				{}
			)
			self._report_new_message(str(isDnd))
		except Exception, e:
			self._report_new_message(str(e))
			return

	def help_is_dnd(self):
		self._report_new_message("Print whether Do-Not-Disturb mode enabled on the Google Voice account")

	def do_get_account_number(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			number = self._conn.session.backend.get_account_number()
			self._report_new_message(number)
		except Exception, e:
			self._report_new_message(str(e))

	def help_get_account_number(self):
		self._report_new_message("Print the Google Voice account number")

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

	def help_get_callback_numbers(self):
		self._report_new_message("Print a list of all configured callback numbers")

	def do_get_sane_callback_number(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			number = gvoice.backend.get_sane_callback(self._conn.session.backend)
			self._report_new_message(number)
		except Exception, e:
			self._report_new_message(str(e))

	def help_get_sane_callback_number(self):
		self._report_new_message("Print the best guess of callback numbers to use")

	def do_get_callback_number(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			number = self._conn.session.backend.get_callback_number()
			self._report_new_message(number)
		except Exception, e:
			self._report_new_message(str(e))

	def help_get_callback_number(self):
		self._report_new_message("Print the callback number currently enabled")

	def do_call(self, args):
		le = gobject_utils.AsyncLinearExecution(self._conn.session.pool, self._call)
		le.start(args)

	@misc_utils.log_exception(_moduleLogger)
	def _call(self, args):
		if not args:
			self._report_new_message("Must specify the phone number and only the phone nunber")
			return

		try:
			number = args
			yield (
				self._conn.session.backend.call,
				(number),
				{}
			)
		except Exception, e:
			self._report_new_message(str(e))

	def help_call(self):
		self._report_new_message("\n".join(["call NUMBER", "Initiate a callback, Google forwarding the call to the callback number"]))

	def do_send_sms(self, args):
		le = gobject_utils.AsyncLinearExecution(self._conn.session.pool, self._send_sms)
		le.start(args)

	@misc_utils.log_exception(_moduleLogger)
	def _send_sms(self, args):
		args = args.split(" ")
		if 1 < len(args):
			self._report_new_message("Must specify the phone number and then message")
			return

		try:
			number = args[0]
			message = " ".join(args[1:])
			yield (
				self._conn.session.backend.send_sms,
				([number], message),
				{},
			)
		except Exception, e:
			self._report_new_message(str(e))

	def help_send_sms(self):
		self._report_new_message("\n".join(["send_sms NUMBER MESSAGE0 MESSAGE1 ...", "Send an sms to number NUMBER"]))

	def do_version(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return
		self._report_new_message("%s-%s" % (constants.__version__, constants.__build__))

	def help_version(self):
		self._report_new_message("Prints the version (hint: %s-%s)" % (constants.__version__, constants.__build__))

	def do_grab_log(self, args):
		if args:
			self._report_new_message("No arguments supported")
			return

		try:
			publishProps = self._conn.generate_props(telepathy.CHANNEL_TYPE_FILE_TRANSFER, self.__otherHandle, False)
			self._conn._channel_manager.channel_for_props(publishProps, signal=True)
		except Exception, e:
			self._report_new_message(str(e))

	def help_grab_log(self):
		self._report_new_message("Download the debug log for including with bug report")
		self._report_new_message("Warning: this may contain sensitive information")

	def do_save_log(self, args):
		if not args:
			self._report_new_message("Must specify a filename to save the log to")
			return

		try:
			filename = os.path.expanduser(args)
			with open(constants._user_logpath_, "r") as f:
				logLines = f.xreadlines()
				log = "".join(logLines)
			with open(filename, "w") as f:
				f.write(log)
		except Exception, e:
			self._report_new_message(str(e))

	def help_save_log(self):
		self._report_new_message("Save the log to a specified location")
