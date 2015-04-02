from twisted.internet import protocol, reactor

class AbstractClient(protocol.Protocol):
    """ Abstract Client """

    def __init__(self, handler):
        self(self.__class__, self).init()
        self.handler = handler

    def connectionMade(self):
        self.handler.on_connect()

    def connectionLost(self, reason):
        self.handler.on_close(reason)

    def dataReceived(self, data):
        self.on_received(data)


class AbstractFactory(protocol.Factory):
    """ Abstract Factory """

    def __init__(self, hanlder):
        self(self.__class__, self).__init__()
        self.handler = hanlder

    def buildProtocol(self, addr):
        return AbstractClient(self.handler)


class AbstractServer():
    """ Abstract Server """
    # TODO:

    def __init__(self, port):
        self.port = port
        self.reactor = reactor

    def on_connect(self):
        pass

    def on_close(self, reason):
        pass

    def on_received(self, data):
        pass

    def run(self):
        self.listenTCP(self.port, AbstractFactory(self))
        self.reactor.run()
