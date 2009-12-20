#!/usr/bin/env python

import threading
import datetime
import time
import logging

import gtk

import sys
sys.path.insert(0,"../src")
import gvoice.state_machine as state_machine


class _I(object):

	def __init__(self, startTime):
		self._startTime = startTime

	def update(self, force = False):
		print "%s\t%r: force=%r" % (datetime.datetime.now() - self._startTime, self, force)


def loop(state):

	def actual():
		while state[0]:
			gtk.main_iteration(block=False)
			time.sleep(0.1)

	return actual


def main():
	logging.basicConfig(level=logging.DEBUG)
	startTime = datetime.datetime.now()

	state = [True]
	mainLoop = threading.Thread(target=loop(state))
	mainLoop.setDaemon(False)
	mainLoop.start()
	try:
		state_machine.StateMachine._IS_DAEMON = False

		initial = _I(startTime)
		print "Initial:", initial
		regular = _I(startTime)
		print "Regular:", regular

		sm = state_machine.StateMachine([initial], [regular])
		print "Starting", datetime.datetime.now() - startTime
		sm.start()
		time.sleep(60.0) # seconds
		print "Reseting timers", datetime.datetime.now() - startTime
		sm.reset_timers()
		time.sleep(60.0) # seconds
		print "Switching to IDLE", datetime.datetime.now() - startTime
		sm.set_state(state_machine.StateMachine.STATE_IDLE)
		time.sleep(10.0) # seconds
		print "Stopping", datetime.datetime.now() - startTime
		sm.stop()
	finally:
		state[0] = False


if __name__ == "__main__":
	print state_machine.StateMachine._INITIAL_ACTIVE_PERIOD
	print state_machine.StateMachine._FINAL_ACTIVE_PERIOD
	print state_machine.StateMachine._IDLE_PERIOD
	main()
