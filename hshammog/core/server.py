from twisted.internet import protocol, reactor


class AbstractClient(protocol.Protocol):
    """ Abstract Client """

    def __init__(self, handler):
        self.handler = handler

    def connectionMade(self):
        self.handler.on_connect(self)

    def connectionLost(self, reason):
        self.handler.on_close(self, reason)

    def dataReceived(self, data):
        self.handler.on_received(self, data)

    def send(self, data):
        self.transport.write(data)


class AbstractFactory(protocol.ClientFactory):
    """ Abstract Factory """

    def __init__(self, hanlder):
        self.handler = hanlder

    def buildProtocol(self, addr):
        return AbstractClient(self.handler)


class AbstractServer():
    """ Abstract Server """
    # TODO:

    def __init__(self, port):
        self.port = port

    def on_connect(self, client):
        pass

    def on_close(self, client, reason):
        pass

    def on_received(self, client, data):
        pass

    def run(self):
        reactor.listenTCP(self.port, AbstractFactory(self))
        reactor.run()
