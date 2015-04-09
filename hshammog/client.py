from twisted.internet import protocol, reactor


class TestClient(protocol.Protocol):
    def connectionMade(self):
        self.transport.write("hello")

    def dataReceived(self, data):
        print data


class TestClientFactory(protocol.ClientFactory):
    def buildProtocol(self, addr):
        return TestClient()

if __name__ == '__main__':
    reactor.connectTCP("127.0.0.1", 18888, TestClientFactory())
    reactor.run()
