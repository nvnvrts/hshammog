import json
import logging
import psutil

from conf import cfg
from core import logger
from core.protocol import *
from core.room import Room
from core.server import AbstractServer


class RoomServer(AbstractServer):
    ''' Room Server '''

    def __init__(self,
                 mq_host, mq_pub_port, mq_sub_port,
                 zk_hosts, zk_path):
        AbstractServer.__init__(self, 'roomserver', zk_hosts, zk_path)

        logger.info('room server %s initializing...' % self.id)

        # save given configurations
        self.mq_host = mq_host
        self.mq_pub_port = mq_pub_port
        self.mq_sub_port = mq_sub_port
        self.zk_hosts = zk_hosts
        self.zk_path = zk_path

        # initialize local data
        self.rooms = {}

        # mq message handler
        self.mq_handlers = {
            'rJoin': self.on_mq_r_join,
            'rMLookup': self.on_mq_r_m_lookup,
            'rMsg': self.on_mq_r_msg,
            'rExit': self.on_mq_r_exit,
            'rExitAll': self.on_mq_r_exit_all,
        }

        logger.info('room server %s initialized.' % self.id)

    def create_room(self):
        room = Room(cfg.client_per_room)
        self.rooms[room.get_id()] = room

        data = {
            'count': room.count(),
            'max': room.max_members,
            'server_id': self.id
        }

        # create a new node for the room
        self.zk_client.create(path=self.zk_room_rooms_path + room.get_id(),
                              value=json.dumps(data),
                              ephemeral=True,
                              sequence=False)

        # update zookeeper node data
        self.update_zk_node_data()

        return room

    def delete_room(self, room):
        # create node for the room
        self.zk_client.delete(path=self.zk_room_rooms_path + room.get_id())

        del self.rooms[room.get_id()]

        # update zookeeper node data
        self.update_zk_node_data()

    def update_room(self, room):
        data = {
            'count': room.count(),
            'max': room.max_members,
            'server_id': self.id
        }

        self.zk_client.set(self.zk_room_rooms_path + room.get_id(),
                           json.dumps(data))

    def update_zk_node_data(self):
        path = self.zk_room_servers_path + self.id
        data = {
            'cpu_usage': psutil.cpu_percent(interval=None, percpu=True),
            'mem_usage': psutil.virtual_memory().percent,
            'rooms': {}
        }

        for rid, room in self.rooms.iteritems():
            data['rooms'][rid] = {'count': room.count(),
                                  'max': room.max_members}

        # set node data with room id list
        logger.debug('updating node %s data %s' % (path, json.dumps(data)))
        self.zk_client.set(path, json.dumps(data))

    def publish_message(self, tag, message):
        data = '%s|%s|%d' % (self.id, message.dumps(), message.timestamp)
        logger.debug('PUB %s %s %d' % (tag, data, message.timestamp))

        self.publish_mq(tag, data)

    def on_mq_data_received(self, tag, data):
        logger.debug('SUB %s %s' % (tag, data))

        # parse message from mq
        server_id, payload, timestamp = data.split('|', 2)
        message = MessageHelper.load_message(payload)
        message.timestamp = int(timestamp)

        # invoke mq message handler
        self.mq_handlers[message.cmd](server_id, message)

    def on_mq_r_join(self, server_id, message):
        room_id = None
        reason = 'unknown error'

        if message.rid == 'room':
            # find a non-full room
            for rid, room in self.rooms.iteritems():
                if not room.is_full():
                    room.join(message.cid, server_id)
                    self.update_room(room)
                    room_id = rid
                    break

            # if not found, create a new room
            if not room_id:
                room = self.create_room()
                room.join(message.cid, server_id)
                self.update_room(room)
                room_id = room.get_id()
        else:
            room = self.rooms.get(message.rid)
            if room:
                if room.is_full():
                    reason = 'room is full'
                else:
                    room.join(message.cid, server_id)
                    self.update_room(room)
                    room_id = room.get_id()
            else:
                reason = 'room not found'
                logger.info('room %s not found' % message.rid)

        if room_id:
            self.update_zk_node_data()

            self.publish_message(server_id,
                                 Message(cmd='rJAccept', cid=message.cid,
                                         rid=room_id,
                                         timestamp=message.timestamp))
        else:
            self.publish_message(server_id,
                                 Message(cmd='rJReject', cid=message.cid,
                                         rid=message.rid, msg=reason,
                                         timestamp=message.timestamp))

    def on_mq_r_m_lookup(self, server_id, message):
        room = self.rooms.get(message.rid)
        if room:
            self.publish_message(server_id,
                                 Message(cmd='rMList',
                                         cid=message.cid,
                                         rid=message.rid,
                                         clientlist=room.get_all_member(),
                                         timestamp=message.timestamp))
        else:
            self.publish_message(server_id,
                                 Message(cmd='rError', cid=message.cid,
                                         msg='Not a member of the room',
                                         timestamp=message.timestamp))

    def on_mq_r_msg(self, _, message):
        room = self.rooms.get(message.rid)
        if room:
            def func(client_id, server_id):
                self.publish_message(server_id,
                                     Message(cmd='rBMsg',
                                             cid=message.cid,
                                             ciddest=client_id,
                                             rid=room.get_id(),
                                             msg=message.msg,
                                             timestamp=message.timestamp))
            room.foreach(func)
        else:
            logger.debug('room %s for rMsg not found' % message.rid)

    def on_mq_r_exit(self, server_id, message):
        room = self.rooms.get(message.rid)
        if room:
            room.leave(message.cid)

            if room.is_empty() and len(self.rooms) > cfg.initial_room_count:
                self.delete_room(room)
            else:
                self.update_room(room)

            self.publish_message(server_id,
                                 Message(cmd='rBye', cid=message.cid,
                                         rid=message.rid,
                                         timestamp=message.timestamp))
        else:
            logger.debug('room %s for rExit not found' % message.rid)

    def on_mq_r_exit_all(self, server_id, message):
        for rid in self.rooms.keys():
            room = self.rooms.get(rid)
            if room and room.get_member(message.cid):
                room.leave(message.cid)
                if room.is_empty() \
                   and len(self.rooms) > cfg.initial_room_count:
                    self.delete_room(room)
                else:
                    self.update_room(room)

    def run(self):
        try:
            zk_success = self.initialize_zk()

            if zk_success is not None:
                raise RoomServerError(zk_success)

            zk_room_server_path = self.zk_room_servers_path + self.id

            data = {
                'cpu_usage': psutil.cpu_percent(interval=None, percpu=True),
                'mem_usage': psutil.virtual_memory().percent,
                'rooms': {}
            }

            # zookeeper setup
            node = self.zk_client.create(path=zk_room_server_path,
                                         value=json.dumps(data),
                                         ephemeral=True, sequence=False)

            # connect to mq as a echo server
            self.connect_mq(self.mq_host, self.mq_pub_port, self.mq_sub_port,
                            'roomserver-allserver', self.id)

            # start initial setting
            for i in range(0, cfg.initial_room_count):
                self.create_room()

            # register monitoring
            self.add_timed_call(self.update_zk_node_data, 5)

            AbstractServer.run(self)

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            logger.info('Shutting down %s' % self.id)
            self.close_zk()
