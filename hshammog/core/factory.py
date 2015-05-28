import uuid
import zlib
import ctypes

from twisted.internet import protocol

from core import logger


class TcpProtocol(protocol.Protocol):
    ''' TCP Protocol '''

    def __init__(self, handler):
        # use random uuid as a new client id
        new_hash = hash(zlib.adler32(uuid.uuid4().hex))
        self.id = 'client-%x' % ctypes.c_uint(new_hash).value

        # duplication operation
        self.last_received = 0
        self.last_responsed = 0
        self.data_buffer = {}

        self.handler = handler
        self.recv_buffer = ''

    def get_id(self):
        return self.id

    def get_last_received(self):
        return self.last_received

    def set_last_received(self, last_received):
        self.last_received = last_received

    def get_last_responsed(self):
        return self.last_responsed

    def set_last_responsed(self, last_responsed):
        self.last_responsed = last_responsed

    def send_data(self, data):
        self.transport.write(data + '\n')

    def connectionMade(self):
        self.handler.on_client_connect(self)

    def connectionLost(self, reason):
        self.handler.on_client_close(self, reason)

    def dataReceived(self, data):
        self.recv_buffer += data
        while self.recv_buffer:
            lines = self.recv_buffer.split('\n', 1)
            if len(lines) == 1:
                break
            line = lines[0]
            self.recv_buffer = lines[1]
            self.handler.on_client_data_received(self, line)


class TcpFactory(protocol.ServerFactory):
    ''' TCP Factory '''

    def __init__(self, handler):
        self.handler = handler

    def buildProtocol(self, addr):
        return TcpProtocol(self.handler)
