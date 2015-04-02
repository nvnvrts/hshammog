from twisted.internet import protocol, reactor

class AbstractClient(protocol.Protocol):
    """ Abstract Client """

    def connectionMade(self):
        pass

    def connectionLost(self, reason):
        pass

    def dataReceived(self, data):
        pass


class AbstractFactory(protocol.Factory):
    """ Abstract Factory """

    def buildProtocol(self, addr):
        return AbstractClient()


class AbstractServer():
    """ Abstract Server """
    # TODO:

    def __init__(self, port):
        self.port = port
        self.reactor = reactor

    def run(self):
        self.listenTCP(self.port, AbstractFactory())

