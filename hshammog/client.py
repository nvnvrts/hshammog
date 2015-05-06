from time import sleep
from twisted.internet import protocol, reactor
from core.protocol import *

class TestClient(protocol.Protocol):
    """ Test Client """

    def connectionMade(self):
        self.seq = 1
        self.recv_buffer = ""

        self.handlers = {
            'sConnect': (lambda message : self.on_connected(message)),
        }

        self.send_message(CGwRequest(cmd='sConnect'))

    def dataReceived(self, data):
        # attach received data to recv buffer
        self.recv_buffer += data

        # extract message from recv buffer
        while self.recv_buffer:
            list = self.recv_buffer.split("\n", 1)
            if len(list) == 1:
                break
            self.recv_buffer = list[1]

            message = CGwRequestHelper.parse_from_json(list[0])
            self.on_message_received(message)

    def send_message(self, message):
        data = CGwRequestHelper.parse_to_json(message)
        self.transport.write(data + "\n")
        print "SEND >>> ", data

    def on_message_received(self, message):
        print "RECV <<< ", message.cmd
        self.handlers[message.cmd](message)

    def on_connected(self, message):
        print "CONNECTED", json.dumps(message)
        pass


class TestClientFactory(protocol.ClientFactory):
    def buildProtocol(self, addr):
        return TestClient()

if __name__ == '__main__':
    reactor.connectTCP("127.0.0.1", 18888, TestClientFactory())
    reactor.run()
