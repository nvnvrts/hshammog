import core.server as server
import core.room as core_room
from core.protocol import *


class RoomServer(server.AbstractServer):
    """ Room Server """

    def __init__(self, mq_host, mq_pub_port, mq_sub_port):
        server.AbstractServer.__init__(self, "roomsvr")

        self.rooms = {}

        # connect to mq as a echo server
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, "server")

        # handler
        self.mq_handlers = {
            'rJoin': self.on_mq_r_join,
            'rMsg': self.on_mq_r_msg,
            'rExit': self.on_mq_r_exit,
            'rExitAll': self.on_mq_r_exit_all,
        }

    def create_room(self):
        room = core_room.Room(3)
        self.rooms[room.get_id()] = room
        print "the total number of rooms is %d" % len(self.rooms)
        return room

    def delete_room(self, room):
        del self.rooms[room.get_id()]
        print "the total number of rooms is %d" % len(self.rooms)

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

        # find a non-full room
        for rid, room in self.rooms.iteritems():
            if not room.is_full():
                room.join(message.cid, server_id)
                room_id = rid
                break

        # create a new room
        if not room_id:
            room = self.create_room()
            room.join(message.cid, server_id)
            room_id = room.get_id()

        self.publish_message(server_id,
                             Message(cmd='rJAccept', cid=message.cid, rid=room_id))

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
            #print "room %s not found" % message.rid
            pass

    def on_mq_r_exit(self, server_id, message):
        room = self.rooms.get(message.rid)
        if room:
            room.leave(message.cid)

            self.publish_message(server_id,
                                 Message(cmd='rBye', cid=message.cid, rid=message.rid))
        else:
            #print "room %s not found" % message.rid
            pass

    def on_mq_r_exit_all(self, server_id, message):
        for rid, room in self.rooms.iteritems():
            if room.get_member(message.cid):
                room.leave(message.cid)


if __name__ == '__main__':
    server = RoomServer('127.0.0.1', 5561, 5562)
    server.run()