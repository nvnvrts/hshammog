import sys
import getopt
import logging
from kazoo.client import KazooClient
import core.config as config
import core.server as server
import core.room as core_room
from core.protocol import *


class RoomServer(server.AbstractServer):
    """ Room Server """

    def __init__(self, mq_host, mq_pub_port, mq_sub_port, zk_node, zk_hosts):
        server.AbstractServer.__init__(self, "roomserver")

        self.rooms = {}

        # connect to mq as a echo server
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, "server")

        # zookeeper client setup
        self.zk_client = KazooClient(hosts=zk_hosts)
        self.zk_client.start()

        self.zk_gateway_servers_path = config.ZK_ROOT + zk_node + config.ZK_GATEWAY_SERVER_PATH
        self.zk_client.ensure_path(self.zk_gateway_servers_path)

        self.zk_room_servers_path = config.ZK_ROOT + zk_node + config.ZK_ROOM_SERVER_PATH
        self.zk_client.ensure_path(self.zk_room_servers_path)

        node = self.zk_client.create(path=self.zk_room_servers_path + self.id,
                                     value=b"[]", ephemeral=True, sequence=False)
        print "zk node %s created." % node

        # mq message handler
        self.mq_handlers = {
            'rJoin': self.on_mq_r_join,
            'rMsg': self.on_mq_r_msg,
            'rExit': self.on_mq_r_exit,
            'rExitAll': self.on_mq_r_exit_all,
        }

    def create_room(self):
        room = core_room.Room(2)
        self.rooms[room.get_id()] = room

        # update zookeeper node data
        self.update_zk_node_data()

        return room

    def delete_room(self, room):
        del self.rooms[room.get_id()]

        # update zookeeper node data
        self.update_zk_node_data()

    def update_zk_node_data(self):
        path = self.zk_room_servers_path + self.id
        data = []

        for rid, room in self.rooms.iteritems():
            if not room.is_full():
                data.append(rid)

        # set node data with room id list
        #print json.dumps(data)
        self.zk_client.set(path, json.dumps(data))

    def publish_message(self, tag, message):
        data = "%s|%s" % (self.id, message.dumps())
        self.publish_mq(tag, data)
        #print "PUB", tag, data

    def on_mq_data_received(self, tag, data):
        #print "SUB", tag, data

        # parse message from mq
        server_id, payload = data.split("|", 1)
        message = MessageHelper.load_message(payload)

        # invoke mq message handler
        self.mq_handlers[message.cmd](server_id, message)

    def on_mq_r_join(self, server_id, message):
        room_id = None
        reason = 'unknown error'

        if message.rid == 0:
            # find a non-full room
            for rid, room in self.rooms.iteritems():
                if not room.is_full():
                    room.join(message.cid, server_id)
                    room_id = rid
                    break

            # if not found, create a new room
            if not room_id:
                room = self.create_room()
                room.join(message.cid, server_id)
                room_id = room.get_id()
        else:
            room = self.rooms.get(message.rid)
            if room:
                if room.is_full():
                    reason = 'room is full'
                else:
                    room.join(message.cid, server_id)
                    room_id = room.get_id()
            else:
                reason = 'room not found'
                print "room %s not found" % message.rid

        if room_id:
            self.update_zk_node_data()

            self.publish_message(server_id,
                                 Message(cmd='rJAccept', cid=message.cid, rid=room_id))
        else:
            self.publish_message(server_id,
                                 Message(cmd='rJReject', cid=message.cid, rid=message.rid, msg=reason))

    def on_mq_r_msg(self, _, message):
        room = self.rooms.get(message.rid)
        if room:
            def func(client_id, server_id):
                self.publish_message(server_id,
                                     Message(cmd='rBMsg',
                                             cid=message.cid,
                                             ciddest=client_id,
                                             rid=room.get_id(),
                                             msg=message.msg))
            room.foreach(func)
        else:
            print "room %s for rMsg not found" % message.rid
            pass

    def on_mq_r_exit(self, server_id, message):
        room = self.rooms.get(message.rid)
        if room:
            room.leave(message.cid)
            if room.is_empty():
                self.delete_room(room)

            self.publish_message(server_id,
                                 Message(cmd='rBye', cid=message.cid, rid=message.rid))
        else:
            print "room %s for rExit not found" % message.rid
            pass

    def on_mq_r_exit_all(self, server_id, message):
        for rid in self.rooms.keys():
            room = self.rooms.get(rid)
            if room and room.get_member(message.cid):
                room.leave(message.cid)
                if room.is_empty():
                    self.delete_room(room)


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:z:", ["--zk_node="])
    except getopt.GetoptError:
        print "usage: roomserver.py -z <zookeeper node>"
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print "usage: roomserver.py -z <zookeeper node>"
        elif opt in ("-z", "--zk_node"):
            zk_node = arg

    # start a roomserver
    server = RoomServer('127.0.0.1', 5561, 5562, zk_node, "192.168.0.16:2181")
    server.run()