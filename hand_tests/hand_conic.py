#!/usr/bin/env python

import gtk
import conic


def on_connection_change(connection, event):
	status = event.get_status()
	error = event.get_error()
	iap_id = event.get_iap_id()
	bearer = event.get_bearer_type()
	if status == conic.STATUS_DISCONNECTED:
		print "Disconnected"
	elif status == conic.STATUS_DISCONNECTING:
		print "Disconnecting"
	elif status == conic.STATUS_CONNECTED:
		print "Connected"
	elif status == conic.STATUS_NETWORK_UP:
		print "Network Up"


if __name__ == "__main__":
	connection = conic.Connection()
	connectionEventId = connection.connect("connection-event", on_connection_change)
	print connectionEventId
	try:
		gtk.main()
	except:
		connection.disconnect()
		raise
