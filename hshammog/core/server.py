# generic python libraries
import uuid
import zlib
import ctypes
import logging
import socket
import sys

# python packages
import txzmq  # txzmq
from twisted.internet import reactor  # twisted
from twisted.internet.task import LoopingCall  # twisted
from txws import WebSocketFactory  # txws
from kazoo.client import KazooClient  # kazoo
from kazoo.protocol.states import KazooState  # kazoo

from core.factory import TcpFactory
from conf import cfg
from core import logger


class AbstractServer():
    '''
    Abstract Server
    '''

    def __init__(self, prefix, zk_hosts, zk_path):
        # use random uuid as a new server id
        new_hash = hash(zlib.adler32(uuid.uuid4().hex))
        self.id = '%s-%x' % (prefix, ctypes.c_uint(new_hash).value)
        logger.info('server unique id: %s' % self.id)

        # twisted setup
        self.factory = txzmq.ZmqFactory()

        # zookeeper setup
        self.zk_client = None
        self.zk_hosts = zk_hosts
        self.zk_path = zk_path

        # cached lists
        self.gateway_ids = []
        self.roomserver_ids = []
        self.zoneserver_ids = []
        self.zone_ids = []

        # get network configuration
        self.get_ip_address()

    def ensure_path_zk(self, path):
        newpath = ''

        for subpath in path.split('/'):
            if subpath != '':
                newpath = newpath + subpath + '/'
                self.zk_client.ensure_path(newpath)

    def initialize_zk(self):
        zk_success = None

        try:
            def zk_listen_state(state):
                if state == KazooState.LOST:
                    logger.info('Zookeeper@%s: lost connection' % self.id)
                elif state == KazooState.SUSPENDED:
                    logger.info('Zookeeper@%s: suspended connection' % self.id)
                else:
                    logger.info('Zookeeper@%s: established connection' %
                                self.id)

            # zookeeper setup
            self.zk_client = KazooClient(hosts=self.zk_hosts)
            self.zk_client.start()

            self.zk_client.add_listener(zk_listen_state)

            self.zk_gateway_servers_path = \
                cfg.zk_root + cfg.zk_path + cfg.zk_gateway_server_path
            # recursive ensure_path not working
            # self.zk_client.ensure_path(self.zk_gateway_servers_path)
            # instead,
            self.ensure_path_zk(self.zk_gateway_servers_path)

            self.zk_room_servers_path = \
                cfg.zk_root + cfg.zk_path + cfg.zk_room_server_path
            # recursive ensure_path not working
            # self.zk_client.ensure_path(self.zk_room_servers_path)
            # instead,
            self.ensure_path_zk(self.zk_room_servers_path)

            self.zk_room_rooms_path = \
                cfg.zk_root + cfg.zk_path + cfg.zk_room_rooms_path
            # recursive ensure_path not working
            # self.zk_client.ensure_path(self.zk_room_rooms_path)
            # instead,
            self.ensure_path_zk(self.zk_room_rooms_path)

            self.zk_zone_servers_path = \
                cfg.zk_root + cfg.zk_path + cfg.zk_zone_server_path
            # recursive ensure_path not working
            # self.zk_client.ensure_path(self.zk_zone_servers_path)
            self.ensure_path_zk(self.zk_zone_servers_path)

            self.zk_zone_zones_path = \
                cfg.zk_root + cfg.zk_path + cfg.zk_zone_zones_path
            # recursive ensure_path not working
            # self.zk_client.ensure_path(self.zk_zone_zones_path)
            self.ensure_path_zk(self.zk_zone_zones_path)

        except Exception as e:
            zk_success = str(e)

        finally:
            return zk_success

    def close_zk(self):
        if self.zk_client is not None:
            self.zk_client.stop()

    def watch_zk_gateways(self):
        @self.zk_client.ChildrenWatch(self.zk_gateway_servers_path)
        def watch_gateways(gateways):
            # find out gateways changes
            added = [x for x in gateways if x not in self.gateway_ids]
            removed = [x for x in self.gateway_ids if x not in gateways]

            # update list before call handlers
            self.gateway_ids = gateways

            if added:
                self.on_zk_gateway_added(added)

            if removed:
                self.on_zk_gateway_removed(removed)

    def get_zk_gateways(self):
        return self.gateway_ids

    def on_zk_gateway_added(self, gateways):
        pass

    def on_zk_gateway_removed(self, gateways):
        pass

    def watch_zk_roomservers(self):
        @self.zk_client.ChildrenWatch(self.zk_room_servers_path)
        def watch_roomservers(roomservers):
            # find out roomservers changes
            added = [x for x in roomservers if x not in self.roomserver_ids]
            removed = [x for x in self.roomserver_ids if x not in roomservers]

            # update list before call handlers
            self.roomservers = roomservers

            if added:
                self.on_zk_roomserver_added(added)

            if removed:
                self.on_zk_roomserver_removed(removed)

    def get_zk_roomservers(self):
        return self.roomserver_ids

    def on_zk_roomserver_added(self, roomservers):
        pass

    def on_zk_roomserver_removed(self, roomservers):
        pass

    def watch_zk_zoneservers(self):
        @self.zk_client.ChildrenWatch(self.zk_zone_servers_path)
        def watch_zoneservers(zoneservers):
            # find out zoneservers changes
            added = [x for x in zoneservers if x not in self.zoneserver_ids]
            removed = [x for x in self.zoneserver_ids if x not in zoneservers]

            # update list before call handlers
            self.zoneservers_ids = zoneservers

            if added:
                self.on_zk_zoneserver_added(added)

            if removed:
                self.on_zk_zoneserver_removed(removed)

    def get_zk_zoneservers(self):
        return self.zoneservers_ids

    def on_zk_zoneserver_added(self, zoneservers):
        pass

    def on_zk_zoneserver_removed(self, zoneservers):
        pass

    def watch_zk_zones(self):
        @self.zk_client.ChildrenWatch(self.zk_zone_zones_path)
        def watch_zoneservers(zones):
            # find out zones changes
            added = [x for x in zones if x not in self.zone_ids]
            removed = [x for x in self.zone_ids if x not in zones]

            # update list before call handlers
            self.zone_ids = zones

            if added:
                self.on_zk_zone_added(added)

            if removed:
                self.on_zk_zone_removed(removed)

    def get_zk_zones(self):
        return self.zone_ids

    def on_zk_zone_added(self, zones):
        pass

    def on_zk_zone_removed(self, zones):
        pass

    def listen_tcp_client(self, port):
        logger.info('listening client on tcp(%d)...' % port)

        reactor.listenTCP(port, TcpFactory(self))

    def listen_websocket_client(self, port):
        logger.info('listening client on websocket(%d)...' % port)

        reactor.listenTCP(port, WebSocketFactory(TcpFactory(self)))

    def on_client_connect(self, client):
        pass

    def on_client_close(self, client, reason):
        pass

    def on_client_received(self, client, message):
        pass

    def connect_mq(self, host, pub_port, sub_port, *args):
        # publish
        mq_pub_addr = 'tcp://%s:%d' % (host, pub_port)
        mq_pub_endpoint = txzmq.ZmqEndpoint('connect', mq_pub_addr)
        self.mq_pub = txzmq.ZmqPubConnection(self.factory, mq_pub_endpoint)

        # subscribe
        mq_sub_addr = 'tcp://%s:%d' % (host, sub_port)
        mq_sub_endpoint = txzmq.ZmqEndpoint('connect', mq_sub_addr)
        self.mq_sub = txzmq.ZmqSubConnection(self.factory, mq_sub_endpoint)

        for tag in args:
            self.mq_sub.subscribe(tag.encode('ascii', 'ignore'))

            def on_sub(data, tag):
                self.on_mq_data_received(tag, data)

            self.mq_sub.gotMessage = on_sub

        logger.info('mq pubsub connected to pub=%s sub=%s tags=%s'
                    % (mq_pub_addr, mq_sub_addr, args))

    def publish_mq(self, tag, data):
        if self.mq_pub:
            self.mq_pub.publish(data, tag)
        else:
            pass

    def on_mq_data_received(self, tag, data):
        pass

    def add_timed_call(self, function, period):
        LoopingCall(function).start(period)

    def get_ip_address(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((cfg.proxy_servers[0], cfg.proxy_port))

        self.ip_address = s.getsockname()[0]

    def run(self):
        try:
            logger.info('starting %s at %s' % (self.id, self.ip_address))
            reactor.run()

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt as e:
            logger.info('Keyboard Interrupt: %s' % self.id)
