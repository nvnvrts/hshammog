from time import sleep
from twisted.internet import protocol, reactor


class TestClient(protocol.Protocol):
    def connectionMade(self):
        self.seq = 1
        self.transport.write("%s %s\n" % ("ECHO", str(self.seq)))
        self.recv_buffer = ""

    def dataReceived(self, data):
        self.recv_buffer += data
        while self.recv_buffer:
            list = self.recv_buffer.split("\n", 1)
            if len(list) == 1:
                break
            message = list[0]
            self.recv_buffer = list[1]
            print "received from server:", message

        self.seq += 1
        self.transport.write("%s %s\n" % ("ECHO", str(self.seq)))


class TestClientFactory(protocol.ClientFactory):
    def buildProtocol(self, addr):
        return TestClient()

if __name__ == '__main__':
    reactor.connectTCP("127.0.0.1", 18888, TestClientFactory())
    reactor.run()
