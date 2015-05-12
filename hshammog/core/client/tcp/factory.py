import uuid
import zlib
import ctypes
import logging
from twisted.internet import protocol

logger = logging.getLogger(__name__)


class TcpProtocol(protocol.Protocol):
    """ TCP Protocol """

    def __init__(self, handler):
        # use random uuid as a new client id
        self.id = "client-%x" % ctypes.c_uint(hash(zlib.adler32(uuid.uuid4().hex))).value

        self.handler = handler
        self.recv_buffer = ""

    def get_id(self):
        return self.id

    def send_data(self, data):
        self.transport.write(data + "\n")

    def connectionMade(self):
        self.handler.on_client_connect(self)

    def connectionLost(self, reason):
        self.handler.on_client_close(self, reason)

    def dataReceived(self, data):
        self.recv_buffer += data
        while self.recv_buffer:
            lines = self.recv_buffer.split("\n", 1)
            if len(lines) == 1:
                break
            line = lines[0]
            self.recv_buffer = lines[1]
            self.handler.on_client_data_received(self, line)


class TcpFactory(protocol.ServerFactory):
    """ TCP Factory """

    def __init__(self, hanlder):
        self.handler = hanlder

    def buildProtocol(self, addr):
        return TcpProtocol(self.handler)