import core.server as server


class EchoServer(server.AbstractServer):
    """ Echo Server """
    # TDDO:

    def __init__(self, port):
        server.AbstractServer.__init__(self, port)

    def on_connect(self, client):
        print "connected"

    def on_close(self, client, reason):
        print "closed", reason

    def on_received(self, client, data):
        print "received", data
        client.send(data)


if __name__ == '__main__':
    server = EchoServer(18651)
    server.run()