import uuid
import zlib
import ctypes
from twisted.internet import protocol, reactor
import txzmq
from kazoo.client import KazooClient
import config


class AbstractClient(protocol.Protocol):
    """ Abstract Client """

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


class AbstractFactory(protocol.ClientFactory):
    """ Abstract Factory """

    def __init__(self, hanlder):
        self.handler = hanlder

    def buildProtocol(self, addr):
        return AbstractClient(self.handler)


class AbstractServer():
    """ Abstract Server """

    def __init__(self, prefix, zk_hosts, zk_path):
        # use random uuid as a new server id
        self.id = "%s-%x" % (prefix, ctypes.c_uint(hash(zlib.adler32(uuid.uuid4().hex))).value)

        self.factory = txzmq.ZmqFactory()

        # zookeeper setup
        self.zk_client = KazooClient(hosts=zk_hosts)
        self.zk_client.start()

        self.zk_gateway_servers_path = config.ZK_ROOT + zk_path + config.ZK_GATEWAY_SERVER_PATH
        self.zk_client.ensure_path(self.zk_gateway_servers_path)

        self.zk_room_servers_path = config.ZK_ROOT + zk_path + config.ZK_ROOM_SERVER_PATH
        self.zk_client.ensure_path(self.zk_room_servers_path)

        self.zk_room_rooms_path = config.ZK_ROOT + zk_path + config.ZK_ROOM_ROOMS_PATH
        self.zk_client.ensure_path(self.zk_room_rooms_path)

    def listen_client(self, port):
        print "listening tcp %d..." % port
        reactor.listenTCP(port, AbstractFactory(self))

    def on_client_connect(self, client):
        pass

    def on_client_close(self, client, reason):
        pass

    def on_client_received(self, client, message):
        pass

    def connect_mq(self, host, pub_port, sub_port, *args):
        # publish
        mq_pub_addr = "tcp://%s:%d" % (host, pub_port)
        mq_pub_endpoint = txzmq.ZmqEndpoint("connect", mq_pub_addr)
        self.mq_pub = txzmq.ZmqPubConnection(self.factory, mq_pub_endpoint)

        # subscribe
        mq_sub_addr = "tcp://%s:%d" % (host, sub_port)
        mq_sub_endpoint = txzmq.ZmqEndpoint("connect", mq_sub_addr)
        self.mq_sub = txzmq.ZmqSubConnection(self.factory, mq_sub_endpoint)

        for tag in args:
            self.mq_sub.subscribe(tag)

            def on_sub(data, tag):
                self.on_mq_data_received(tag, data)

            self.mq_sub.gotMessage = on_sub

        print "mq pubsub connected to", mq_pub_addr, mq_sub_addr, args

    def publish_mq(self, tag, data):
        if self.mq_pub:
            self.mq_pub.publish(data, tag)
        else:
            pass

    def on_mq_data_received(self, tag, data):
        pass

    def run(self):
        print self.id, "running..."
        reactor.run()
