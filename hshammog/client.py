from time import sleep
from twisted.internet import protocol, reactor
from core.protocol import *

class TestClient(protocol.Protocol):
    """ Test Client """

    def __init__(self):
        # client id issued by server
        self.cid = None

        # receive buffer
        self.data_receive_buffer = ""

        # message handlers
        self.handlers = {
            'sAccept': self.on_s_accept,
            'rList': self.on_s_list,
            'rJAccept': self.on_r_j_accept,
            'rJReject': self.on_r_j_reject,
            'rBMsg': self.on_r_b_msg,
            'rBye': self.on_r_bye,
            'sBye': self.on_s_bye,
            'rError': self.on_r_error,
        }

        self.count = 0

    def connectionMade(self):
        # send the first message
        self.send_message(Message(cmd='sConnect'))

    def dataReceived(self, data):
        # attach data to receive buffer
        self.data_receive_buffer += data
        #print "RECV %d byte(s)" % len(data)

        # extract message from the buffer
        while self.data_receive_buffer:
            lines = self.data_receive_buffer.split("\n", 1)
            if len(lines) == 1:
                break
            self.data_receive_buffer = lines[1]
            message = MessageHelper.load_message(lines[0])
            self.on_message_received(message)

    def send_message(self, message):
        data = message.dumps()
        self.transport.write(data + "\n")
        #print "SND", data

    def on_message_received(self, message):
        #print "handling %s..." % message.cmd
        self.handlers[message.cmd](message)

    def on_s_accept(self, message):
        # set client id
        self.cid = message.cid

        # send command to get room list
        self.send_message(Message(cmd='rLookup', cid=self.cid, nmaxroom=4))

    def on_s_list(self, message):
        # TODO: choose a room in the room list
        room_id = 1

        # send command to join the room
        self.send_message(Message(cmd='rJoin', cid=self.cid, rid=room_id))

    def on_r_j_accept(self, message):
        # reset count
        self.count = 0

        text = 'hello ' + self.cid

        # send command to broadcast a message
        self.send_message(Message(cmd='rMsg', cid=self.cid, ciddest=-1, rid=message.rid, msg=text))

    def on_r_j_reject(self, message):
        # send command to get room list
        self.send_message(Message(cmd='rLookup', cid=self.cid, nmaxroom=4))

    def on_r_b_msg(self, message):
        # if received message is from mine,
        # send another message until count limit exceeds
        if message.cid == self.cid:
            if self.count < 1000:
                self.count += 1
                text = "%s %d" % (self.cid, self.count)
                # send command to broadcast a message
                self.send_message(Message(cmd='rMsg',
                                          cid=self.cid, ciddest=-1, rid=message.rid, msg=text))
            else:
                # send command to exit from the room
                self.send_message(Message(cmd='rExit', cid=self.cid, rid=message.rid))
        else:
            print "%s:%s> %s" % (message.rid, self.cid, message.msg)

    def on_r_bye(self, message):
        # send command to exit from the server
        self.send_message(Message(cmd='sExit', cid=self.cid))

    def on_s_bye(self, message):
        # reset client id
        self.cid = None

        # send the first message
        self.send_message(Message(cmd='sConnect'))

    def on_r_error(self, message):
        print "server error %s" % message.msg


class TestClientFactory(protocol.ClientFactory):
    """ Test Client Factory """

    def buildProtocol(self, addr):
        return TestClient()


if __name__ == '__main__':
    reactor.connectTCP("127.0.0.1", 18888, TestClientFactory())
    reactor.run()
