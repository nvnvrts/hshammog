# -*- coding: utf-8 -*-
__all__ = ['GatewayServer']

import ast
import struct
import random
import psutil

from datetime import datetime
from twisted.internet.task import LoopingCall

from kazoo.client import KazooClient
from kazoo.client import KazooState

from core.server import AbstractServer
from core import cfg

from roomlobby.lib.protocol import CGwRequest
from roomlobby.lib.gw_helper import *


class GatewayServer(AbstractServer):
    """ Gateway """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port,
                 zk_host, zk_port):
        AbstractServer.__init__(self)

        self.port = port
        self.mq_host = mq_host
        self.mq_pub_port = mq_pub_port
        self.mq_sub_port = mq_sub_port
        self.zk_host = zk_host
        self.zk_port = zk_port

        # Cid-Client Binding
        self.cid_binding = {}

        # Cid issue number
        self.cid_issue = 0

        # Zookeeper client
        self.zk_client = None

    def status_monitor(self):
        pass

    # From Room-server
    # rJAccept, rJReject, rBMsg, rBye, rError
    def on_mq_received(self, message):

        # parse message by "|"
        message_split = message.split('|')

        roomserver_dictionary = {
            'rJAccept':
            (lambda message_split:
                self.on_rjaccept_received(int(message_split[1]),
                                          int(message_split[3]))),
            'rJReject':
            (lambda message_split:
                self.on_rjreject_received(int(message_split[1]),
                                          int(message_split[3]),
                                          message_split[4])),
            'rBMsg':
            (lambda message_split:
                self.on_rbmsg_received(int(message_split[1]),
                                       int(message_split[2]),
                                       message_split[4])),
            'rBye':
            (lambda message_split:
                self.on_rbye_received(int(message_split[1]),
                                      int(message_split[3]))),
            'rError':
            (lambda message_split:
                self.on_rerror_received(int(message_split[1]),
                                        message_split[4]))
        }

        cmd = message_split[0]
        if cmd in roomserver_dictionary:
            print '[SUB][RS] Valid', cmd
            roomserver_dictionary[cmd](message_split)
        else:
            print '[SUB][RS] Invalid ', cmd

    # From Client
    # sConnect, sExit, rLookup, rJoin, rMsg, rExit
    def on_client_received(self, client, message):

        # parse from message in JSON format
        request = parse_from_json(message)

        client_dictionary = {
            'sConnect':
            (lambda request: self.on_sconnect_received(client)),
            'sExit':
            (lambda request: self.on_sexit_received(request.cid)),
            'rLookup':
            (lambda request: self.on_rlookup_received(request.cid,
                                                      request.nmaxroom)),
            'rJoin':
            (lambda request: self.on_rjoin_received(request.cid,
                                                    request.rid)),
            'rMsg':
            (lambda request: self.on_rmsg_received(request.cid,
                                                   request.ciddest,
                                                   request.rid,
                                                   request.msg)),
            'rExit':
            (lambda request: self.on_rexit_received(request.cid,
                                                    request.rid))
        }

        if request.cmd in client_dictionary:
            print '[RECV][CL] Valid ', request.cmd
            client_dictionary[request.cmd](request)
        else:
            print '[RECV][CL] Invalid ', request.cmd

    # connect request from client (sConnect)
    def on_sconnect_received(self, client):
        try:
            # ask zookeeper for a cid
            cid = self.zk_cid_issue()
            self.bind_cid(cid, client)

            resp = parse_to_json(CGwRequest(cmd='sAccept',
                                            cid=cid))
            client.transport.write(resp)

        except Exception as e:
            print '[GW] Service rejected: ', e
            resp = parse_to_json(CGwRequest(cmd='sReject'))
            client.transport.write(resp)

    # room look up from client (rLookup)
    def on_rlookup_received(self, cid, nmaxroom):
        client = self.cid_binding[cid]
        # ask zookeeper for room number list
        roomList = self.zk_room_lookup(nmaxroom)

        resp = parse_to_json(CGwRequest(cmd='rList',
                                        cid=cid,
                                        roomlist=roomList))
        client.transport.write(resp)

    # room join request from client (rJoin)
    def on_rjoin_received(self, cid, rid):
        # send join request to mq
        self.publish_mq(self.make_message(cmd='rJoin',
                                          cid=cid,
                                          cid_dest='',
                                          rid=rid,
                                          msg=''),
                        'R')

    # message request from client (rMsg)
    def on_rmsg_received(self, cid_src, cid_dest, rid, msg):
        # send message request to mq
        self.publish_mq(self.make_message(cmd='rMsg',
                                          cid=cid_src,
                                          cid_dest=cid_dest,
                                          rid=rid,
                                          msg=msg),
                        'R')

    # room exit request from client (rExit)
    def on_rexit_received(self, cid, rid):
        # send exit request to mq
        self.publish_mq(self.make_message(cmd='rExit',
                                          cid=cid,
                                          cid_dest='',
                                          rid=rid,
                                          msg=''),
                        'R')

    # exit request from client (sExit)
    def on_sexit_received(self, cid):
        client = self.cid_binding[cid]
        resp = parse_to_json(CGwRequest(cmd='sBye',
                                        cid=cid))
        client.transport.write(resp)

        # remove form cid_binding
        self.cid_binding.__delitem__(cid)

    # room join accept from roomserver (rJAccept)
    def on_rjaccept_received(self, cid, rid):
        print 'rjaccept'
        client = self.cid_binding[cid]
        resp = parse_to_json(CGwRequest(cmd='rJAccept',
                                        cid=cid,
                                        rid=rid))
        client.transport.write(resp)

    # room join reject from roomserver (rJReject)
    def on_rjreject_received(self, cid, rid, msg):
        client = self.cid_binding[cid]
        resp = parse_to_json(CGwRequest(cmd='rJReject',
                                        cid=cid,
                                        rid=rid,
                                        msg=msg))
        client.transport.write(resp)

    # room broadcast message from roomserver (rBMsg)
    def on_rbmsg_received(self, cid_src, cid_dest, msg):
        client = self.cid_binding[cid_dest]
        resp = parse_to_json(CGwRequest(cmd='rBMsg',
                                        cid=cid_src,
                                        ciddest=cid_dest,
                                        msg=msg))
        client.transport.write(resp)

    # room bye from roomserver (rBye)
    def on_rbye_received(self, cid, rid):
        client = self.cid_binding[cid]
        resp = parse_to_json(CGwRequest(cmd='rBye',
                                        cid=cid,
                                        rid=rid))
        client.transport.write(resp)

    # room error from roomserver (rError)
    def on_rerror_received(self, cid, msg):
        client = self.cid_binding[cid]
        resp = parse_to_json(CGwRequest(cmd='rError',
                                        msg=msg))
        client.transport.write(resp)

    # make message for RoomLobby
    def make_message(self, cmd, cid, cid_dest, rid, msg):
        new_msg = str(cmd) + '|' + str(cid) + '|' + str(cid_dest)
        new_msg += '|' + str(rid) + '|' + str(msg)

        return new_msg

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
        if not self.zk_client.exists('/client/cId'):
            self.zk_client.ensure_path('/client/cId')
            self.zk_client.set('/client/cId', struct.pack('>I', 0))

        if not self.zk_client.exists('/room/roomservers'):
            self.zk_client.ensure_path('/room/roomservers')

    # terminate Zookeeper connection
    def zk_stop(self):
        if self.zk_client is not None:
            self.zk_client.stop()

    # zookeeper-based client id issuer
    def zk_cid_issue(self):
        lock = self.zk_client.Lock('/lockpath', 'newCId')

        with lock:
            data, stat = self.zk_client.get('/client/cId')
            new_cid = struct.unpack('>I', data)[0] + 1
            self.zk_client.set('/client/cId', struct.pack('>I', new_cid))

        return new_cid

    # client room lookup
    def zk_room_lookup(self, nmaxroom):
        roomservers = self.zk_client.get_children('/room/roomservers')

        empty_room_dictionary = {}
        random.shuffle(roomservers)

        for rsid in roomservers:
            if self.zk_client.exists('/room/roomservers/' + rsid):
                data, stat = self.zk_client.get('/room/roomservers/' + rsid)
                rooms = ast.literal_eval(data)
                rids = rooms.keys()

                for rid in rids:
                    players = ast.literal_eval(rooms[rid])
                    if len(players) < cfg.client_per_room:
                        empty_room_dictionary[str(rid)] = len(players)

                    if len(empty_room_dictionary) >= nmaxroom:
                        break

            if len(empty_room_dictionary) >= nmaxroom:
                break

        return empty_room_dictionary

    # client id - client session binder
    def bind_cid(self, cid, client):
        self.cid_binding[cid] = client

    def run(self):
        try:
            print 'Starting gateway with'
            print 'listening port (', self.port, ')'
            print 'subscribing mq (', self.mq_host, ') with port (', \
                  self.mq_sub_port, ')'
            print 'publishing mq (', self.mq_host, ') with port (', \
                  self.mq_pub_port, ')'

            # connect to mq as a gateway
            # subscribe tag = 'G'
            self.connect_mq(self.mq_host, self.mq_pub_port,
                            self.mq_sub_port, 'G')

            # accept client
            self.listen_client(self.port)

            # start Zookeeper
            self.zk_start()

            # start monitoring task
            LoopingCall(self.status_monitor).start(1)

            # start reactor
            AbstractServer.run(self)

        except (Exception, KeyboardInterrupt) as e:
            print e

        finally:
            print 'Shutting down gateway'

            # terminate Zookeeper connection
            if self.zk_client is not None:
                self.zk_stop()
