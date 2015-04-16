# -*- coding: utf-8 -*-
__all__ = ['GatewayServer']

from core.server import AbstractServer

from roomlobby.lib.protocol import CGwRequest
from roomlobby.lib.gw_helper import *


class GatewayServer(AbstractServer):
    """ Gateway """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port):
        AbstractServer.__init__(self)

        self.port = port
        self.mq_host = mq_host
        self.mq_pub_port = mq_pub_port
        self.mq_sub_port = mq_sub_port

        # Cid-Client Binding
        self.cid_binding = {}

        # Cid issue number
        self.cid_issue = 0

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
        print 'connect request from client'

        try:
            # ask zookeeper for a cid
            print 'ask zookeeper for a cid'
            cid = self.zk_cid_issue()
            print 'new cid: %d' % cid
            self.bind_cid(cid, client)

            resp = parse_to_json(CGwRequest(cmd='sAccept',
                                            cid=cid))
            client.transport.write(resp)

        except Exception as e:
            print 'service rejected: ', e
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
        print 'room join request from client'
        tag = 'R'
        msg = self.make_message(cmd='rJoin', cid=cid, cid_dest='',
                                rid=rid, msg='')
        print 'pub to mq: ', tag
        self.publish_mq(msg, tag)

    # message request from client (rMsg)
    def on_rmsg_received(self, cid_src, cid_dest, rid, msg):
        # send message request to mq
        print 'send message request from client'
        tag = 'R'
        msg = self.make_message(cmd='rMsg', cid=cid_src, cid_dest=cid_dest,
                                rid=rid, msg=msg)
        print 'pub to mq: ', tag
        self.publish_mq(msg, tag)

    # room exit request from client (rExit)
    def on_rexit_received(self, cid, rid):
        # send exit request to mq
        print 'room exit request from client'
        tag = 'R'
        msg = self.make_message(cmd='rExit', cid=cid, cid_dest='', rid=rid,
                                msg='')
        print 'pub to mq: ', tag
        self.publish_mq(msg, tag)

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

    # client id issuer
    # TODO: zookeeper issuing system
    def zk_cid_issue(self):
        self.cid_issue += 1
        return self.cid_issue

    # client room lookup
    # TODO: zookeeper room lookup
    def zk_room_lookup(self, nmaxroom):
        return {}

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

            # start reactor
            AbstractServer.run(self)

        except (Exception, KeyboardInterrupt) as e:
            print e

        finally:
            print 'Shutting down gateway'
