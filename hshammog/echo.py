import core.server as server


class EchoServer(server.AbstractServer):
    """ Echo Server """
    # TDDO:

    def __init__(self, port):
        server.AbstractServer.__init__(self, port)

    def on_connect(self):
        print "connected"

    def on_close(self, reason):
        print "closed", reason

    def on_received(self, data):
        print "received", data


if __name__ == '__main__':
    server = EchoServer(18651)
    server.run()