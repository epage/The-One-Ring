import telepathy


class Debug(telepathy.server.Debug):

	def __init__(self, connManager):
		telepathy.server.Debug.__init__(self, connManager)
