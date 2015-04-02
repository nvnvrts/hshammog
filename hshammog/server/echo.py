import hshammog.core.server

class EchoServer(server.AbstractServer):
    """ Echo Server """
    # TDDO:

    def __init__(self, port):
        super(self.__class__, self).__init__(port)

    def on_connect(self):
        print "connected"

    def on_close(self, reason):
        print "closed", reason

    def on_received(self, data):
        print "received", data

