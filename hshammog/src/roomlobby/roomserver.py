# -*- coding: utf-8 -*-
__all__ = ['RoomServer']

from core.server import AbstractServer
from core import cfg

from roomlobby.lib.field import Room


class RoomServer(AbstractServer):
    """ RoomServer """

    def __init__(self, mq_host, mq_pub_port, mq_sub_port):
        AbstractServer.__init__(self)

        self.mq_host = mq_host
        self.mq_pub_port = mq_pub_port
        self.mq_sub_port = mq_sub_port

        # TODO: zookeeper-based rid issuing
        self.rid_issue = 0

        # roomlist dictionary (key: rid, value: Room instances)
        self.room_list = {}

        for cnt in range(1, cfg.initial_room_count):
            self.create_room()

    # Create a new room with a new rid
    def create_room(self):
        new_rid = self.zk_rid_issue()
        self.room_list[new_rid] = Room(new_rid, cfg.client_per_room)

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

    # Zookeeper-based room number issuing
    # TODO:
    def zk_rid_issue(self):
        self.rid_issue += 1
        return self.rid_issue

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

            # start reactor
            AbstractServer.run(self)

        except (Exception, KeyboardInterrupt) as e:
            print e

        finally:
            print 'Shutting down roomserver'
