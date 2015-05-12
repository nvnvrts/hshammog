import uuid
import zlib
import ctypes
import logging
from twisted.internet import protocol, reactor
from txws import WebSocketFactory
import txzmq
from kazoo.client import KazooClient
from client.tcp.factory import TcpFactory
import config

logger = logging.getLogger(__name__)


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

        # cached lists
        self.gateways = []
        self.roomservers = []

    def watch_zk_gateways(self):
        @self.zk_client.ChildrenWatch(self.zk_gateway_servers_path)
        def watch_gateways(gateways):
            # find out gateways changes
            added = [x for x in gateways if x not in self.gateways]
            removed = [x for x in self.gateways if x not in gateways]

            # update list before call handlers
            self.gateways = gateways

            if added:
                self.on_zk_gateway_added(added)

            if removed:
                self.on_zk_gateway_removed(removed)

    def get_zk_gateways(self):
        return self.gateways

    def on_zk_gateway_added(self, gateways):
        pass

    def on_zk_gateway_removed(self, gateways):
        pass

    def watch_zk_roomservers(self):
        @self.zk_client.ChildrenWatch(self.zk_room_servers_path)
        def watch_roomservers(roomservers):
            # find out roomservers changes
            added = [x for x in roomservers if x not in self.roomservers]
            removed = [x for x in self.roomservers if x not in roomservers]

            # update list before call handlers
            self.roomservers = roomservers

            if added:
                self.on_zk_roomserver_added(added)

            if removed:
                self.on_zk_roomserver_removed(removed)

    def get_zk_roomservers(self):
        return self.roomservers

    def on_zk_roomserver_added(self, roomservers):
        pass

    def on_zk_roomserver_removed(self, roomservers):
        pass

    def listen_tcp_client(self, port):
        logger.info("listening client on tcp(%d)..." % port)
        reactor.listenTCP(port, TcpFactory(self))

    def listen_websocket_client(self, port):
        logger.info("listening client on websocket(%d)..." % port)
        reactor.listenTCP(port, WebSocketFactory(TcpFactory(self)))

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

        logger.info("mq pubsub connected to pub=%s sub=%s tags=%s",
                    mq_pub_addr, mq_sub_addr, args)

    def publish_mq(self, tag, data):
        if self.mq_pub:
            self.mq_pub.publish(data, tag)
        else:
            pass

    def on_mq_data_received(self, tag, data):
        pass

    def run(self):
        logger.info("server %s is running...", self.id)
        reactor.run()
