# -*- coding: utf-8 -*-
__all__ = ['RoomServer']

import struct
import ast

from kazoo.client import KazooClient
from kazoo.client import KazooState

from core.server import AbstractServer
from core import cfg

from roomlobby.lib.field import Room


class RoomServer(AbstractServer):
    """ RoomServer """

    def __init__(self, mq_host, mq_pub_port, mq_sub_port,
                 zk_host, zk_port):
        AbstractServer.__init__(self)

        self.mq_host = mq_host
        self.mq_pub_port = mq_pub_port
        self.mq_sub_port = mq_sub_port
        self.zk_host = zk_host
        self.zk_port = zk_port

        # roomlist dictionary (key: rid, value: Room instances)
        self.room_list = {}

        self.zk_client = None
        self.rsid = None

    def __str__(self):
        str_list = dict(map((lambda (key, value): (key, str(value))),
                            self.room_list.iteritems()))
        return str(str_list)

    # Create a new room with a new rid
    def create_room(self):
        new_rid = self.zk_rid_issue()
        self.room_list[new_rid] = Room(new_rid, cfg.client_per_room)

        # record current status @ zookeeper
        self.zk_client.set('/room/roomservers/%d' % self.rsid,
                           self.__str__())

    # From Gateway
    def on_mq_received(self, message):
        message_split = message.split('|')

        roomserver_dictionary = {
            'rJoin':
            (lambda message_split:
                self.on_rjoin_received(int(message_split[1]),
                                       int(message_split[3]))),
            'rMsg':
            (lambda message_split:
                self.on_rmsg_received(int(message_split[1]),
                                      int(message_split[2]),
                                      int(message_split[3]),
                                      message_split[4])),
            'rExit':
            (lambda message_split:
                self.on_rexit_received(int(message_split[1]),
                                       int(message_split[3])))
        }

        cmd = message_split[0]

        if cmd in roomserver_dictionary:
            print '[RECV][GW] Valid', cmd
            roomserver_dictionary[cmd](message_split)
        else:
            print '[RECV][GW] Invalid ', cmd

    def make_message(self, cmd, cid, cid_dest, rid, msg):
        new_msg = str(cmd) + "|" + str(cid) + "|" + str(cid_dest) + "|"
        new_msg += str(rid) + "|" + str(msg)

        return new_msg

    # Join a client(cid) into a room(rid)
    def on_rjoin_received(self, cid, rid):
        if rid in self.room_list:

            msg = self.room_list[rid].add_player(cid)

            # adding player successful
            if msg is None:
                self.zk_client.set('/room/roomservers/%d' % self.rsid,
                                   self.__str__())

                self.publish_mq(self.make_message(cmd='rJAccept',
                                                  cid=cid,
                                                  cid_dest='',
                                                  rid=rid,
                                                  msg=''),
                                'G')
            # adding player unsuccessful
            else:
                self.publish_mq(self.make_message(cmd='rJReject',
                                                  cid=cid,
                                                  cid_dest='',
                                                  rid=rid,
                                                  msg=msg),
                                'G')

    # Msg transmission from cid_src to cid_dest
    def on_rmsg_received(self, cid_src, cid_dest, rid, msg):
        if rid in self.room_list:

            room = self.room_list[rid]

            # Check if client(cid_src) is in room(rid)
            if cid_src in room.players:
                # broadcasting message in room
                if cid_dest < 0:
                    for i in room.players:
                        self.publish_mq(self.make_message(cmd='rBMsg',
                                                          cid=cid_src,
                                                          cid_dest=i,
                                                          rid=rid,
                                                          msg=msg),
                                        'G')
                # sending message to cid_dest
                elif cid_dest in room.players:
                    self.publish_mq(self.make_message(cmd='rBMsg',
                                                      cid=cid_src,
                                                      cid_dest=cid_dest,
                                                      rid=rid,
                                                      msg=msg),
                                    'G')
                else:
                    self.publish_mq(self.make_message(cmd='rError',
                                                      msg=('Client Id (%d)'
                                                           'not found' %
                                                           cid_dest),
                                                      cid=cid_src,
                                                      cid_dest='',
                                                      rid=rid),
                                    'G')
            else:
                self.publish_mq(self.make_message(cmd='rError',
                                                  msg=('Client Id (%d) not '
                                                       'in room Id (%d)' %
                                                       (cid_src, rid)),
                                                  cid=cid_src,
                                                  cid_dest=cid_dest,
                                                  rid=rid),
                                'G')

    # delete player cid from rid
    def on_rexit_received(self, cid, rid):
        if rid in self.room_list:

            msg = self.room_list[rid].delete_player(cid)

            self.zk_client.set('/room/roomservers/%d' % self.rsid,
                               self.__str__())

            # deleting player successful
            if msg is None:
                self.publish_mq(self.make_message(cmd='rBye',
                                                  cid=cid,
                                                  rid=rid,
                                                  cid_dest='',
                                                  msg=''),
                                'G')

            # deleting player unsuccessful
            else:
                self.publish_mq(self.make_message(cmd='rError',
                                                  cid=cid,
                                                  msg=msg,
                                                  cid_dest='',
                                                  rid=rid),
                                'G')

    # For future use
    def on_client_received(self, client, message):
        pass

    # establish Zookeeper connection
    def zk_start(self):
        address = str(self.zk_host) + ':' + str(self.zk_port)
        self.zk_client = KazooClient(hosts=address)

        self.zk_client.start()

        def zk_listen_state(state):
            if state == KazooState.LOST:
                print '[ZK] Lost connection'
            elif state == KazooState.SUSPENDED:
                print '[ZK] Suspended connection'
            else:
                print '[ZK] Established connection'

        self.zk_client.add_listener(zk_listen_state)

        self.zk_initialize()

    def zk_initialize(self):
        if not self.zk_client.exists('/room/rId'):
            self.zk_client.ensure_path('/room/rId')
            self.zk_client.set('/room/rId', struct.pack('>I', 0))

        if not self.zk_client.exists('/room/rsId'):
            self.zk_client.ensure_path('/room/rsId')
            self.zk_client.set('/room/rsId', struct.pack('>I', 0))

        if not self.zk_client.exists('/room/roomservers'):
            self.zk_client.ensure_path('/room/roomservers')

    # terminate Zookeeper connection
    def zk_stop(self):
        if self.zk_client is not None:
            self.zk_client.stop()

    # Zookeeper-based room number issuing
    def zk_rid_issue(self):
        lock = self.zk_client.Lock('/lockpath', 'newRId')

        with lock:
            data, stat = self.zk_client.get('/room/rId')
            new_rid = struct.unpack('>I', data)[0] + 1
            self.zk_client.set('/room/rId', struct.pack('>I', new_rid))

        return new_rid

    # Zookeeper-based room server number issuing
    def zk_rsid_issue(self):
        lock = self.zk_client.Lock('/lockpath', 'newRSId')

        with lock:
            data, stat = self.zk_client.get('/room/rsId')
            new_rsid = struct.unpack('>I', data)[0] + 1
            self.zk_client.set('/room/rsId', struct.pack('>I', new_rsid))

        return new_rsid

    def zk_initialize_roomserver(self):
        self.rsid = self.zk_rsid_issue()

        print 'Assigned RSID(RoomServer ID) :', self.rsid

        self.zk_client.ensure_path('/room/roomservers/%d' % self.rsid)

        for cnt in range(0, cfg.initial_room_count):
            self.create_room()

    def run(self):
        try:
            print 'Starting roomserver with'
            print 'subscribing mq (', self.mq_host, ') with port (', \
                  self.mq_sub_port, ')'
            print 'publishing mq (', self.mq_host, ') with port (', \
                  self.mq_pub_port, ')'

            # connect to mq as a gateway
            # subscribe tag = 'R'
            self.connect_mq(self.mq_host, self.mq_pub_port,
                            self.mq_sub_port, 'R')

            # start Zookeeper
            self.zk_start()

            # initialize roomserver
            self.zk_initialize_roomserver()

            # start reactor
            AbstractServer.run(self)

        except (Exception, KeyboardInterrupt) as e:
            print e

        finally:
            print 'Shutting down roomserver'

            # terminate Zookeeper connection
            if self.zk_client is not None:
                self.zk_stop()
