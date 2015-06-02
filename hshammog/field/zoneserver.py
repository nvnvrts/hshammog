# generic python libraries
import json
import logging
import psutil

# hahammog
from conf import cfg
from core import logger
from core.protocol import *
from core.field import *
from core.server import AbstractServer


class ZoneServer(AbstractServer):
    ''' Zone Server '''

    def __init__(self,
                 mq_host, mq_pub_port, mq_sub_port,
                 zk_hosts, zk_path):
        AbstractServer.__init__(self, 'zoneserver', zk_hosts, zk_path)

        logger.info('zone server %s initializing...' % self.id)

        # save given configurations
        self.mq_host = mq_host
        self.mq_pub_port = mq_pub_port
        self.mq_sub_port = mq_sub_port
        self.zk_hosts = zk_hosts
        self.zk_path = zk_path

        # initialize local data
        self.zones = {}

        # mq message handler
        self.mq_handlers = {
            'fStart': self.on_mq_f_start,
            'fMove': self.on_mq_f_move,
            'fLookup': self.on_mq_f_lookup,
            'fMsg': self.on_mq_f_msg,
            'fExit': self.on_mq_f_exit,
            'zAdd': self.on_mq_z_add,
            'zVSplit': self.on_mq_z_vsplit,
            'zHSplit': self.on_mq_z_hsplit,
            'zDestroy': self.on_mq_z_destroy,
            'zMerge': self.on_mq_z_merge
        }

        logger.info('zone server %s initialized.' % self.id)

    # create a new zone
    def create_zone(self, lt_x, lt_y, rb_x, rb_y, max_mem, border, global_size, sid):
        #zone = Zone(0, 0, 511, 511, 5, 4, 512, self.id)
        zone = Zone(lt_x, lt_y, rb_x, rb_y, max_mem, border, global_size, sid)
        self.zones[zone.get_id()] = zone

        # create a new node for the zone
        self.zk_client.create(path=self.zk_zone_zones_path + zone.get_id(),
                              value=zone.dumps(),
                              ephemeral=True,
                              sequence=False)

        # update zookeeper node data
        self.update_zk_node_data()

        return zone

    # delete the zone
    def delete_zone(self, zone):
        
        del self.zones[zone.get_id()]
        self.zk_client.delete(path=self.zk_zone_zones_path + zone.get_id())

    # update zone data
    def update_zone(self, zone):
        self.zk_client.set(self.zk_zone_zones_path + zone.get_id(),
                           zone.dumps())

    # update cellserver's data to zookeeper
    def update_zk_node_data(self):
        path = self.zk_zone_servers_path + self.id
        data = self.dumps()

        # set node data with zone id list
        logger.debug('update zone %s data %s' % (path, data))
        self.zk_client.set(path, data)

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

    # on_mq_f_start
    def on_mq_f_start(self, server_id, message):
        check = False
        for zone_id, zone in self.zones.iteritems():
            if zone.add_member(message.cid, message.x, message.y):
                check = True
                self.update_zone(zone)

        if check:
            self.publish_message(server_id,
                                 Message(cmd='fLoc', cid=message.cid,
                                         x=message.x, y=message.y,
                                         timestamp=message.timestamp))

    # on_mq_f_move: TODO
    def on_mq_f_move(self, server_id, message):
        check = False

        for zone_id, zone in self.zones.iteritems():
            member = zone.update_member(message.cid, message.x, message.y)
            if member is not None:
                self.update_zone(zone)

                if not check:
                    check = True
                    self.publish_message(server_id,
                                         Message(cmd='fLoc', cid=message.cid,
                                                 x=member.x, y=member.y,
                                                 timestamp=message.timestamp))

    # on_mq_f_lookup
    def on_mq_f_lookup(self, server_id, message):
        for zone_id, zone in self.zones.iteritems():
            member = zone.get_member(message.cid)

            if member is not None and \
               (member.is_at_inner_zone() or member.is_at_perimeter_zone()):

                grid = zone.grid
                width = grid['rb_x'] - grid['lt_x'] + 1
                height = grid['rb_y'] - grid['lt_y'] + 1
                self.publish_message(server_id,
                                     Message(cmd='fList', cid=message.cid,
                                             clientlist=zone.get_all_members(),
                                             zid1=zone_id,
                                             x=grid['lt_x'],
                                             y=grid['lt_y'],
                                             width=width,
                                             height=height,
                                             timestamp=message.timestamp))

    # on_mq_f_msg: TODO
    def on_mq_f_msg(self, server_id, message):
        pass

    # on_mq_f_exit:
    def on_mq_f_exit(self, server_id, message):
        for zone_id, zone in self.zones.iteritems():
            if zone.drop_member(message.cid):
                self.update_zone(zone)

    # on_mq_z_add: TODO
    def on_mq_z_add(self, server_id, message):

        lt_x = int(message.x)
        lt_y = int(message.y)
        width = int(message.width)
        height = int(message.height)

        self.create_zone(lt_x, lt_y, lt_x + width, lt_y + height, 5, 4, 512, self.id)
        

    # on_mq_z_vsplit: TODO
    def on_mq_z_vsplit(self, server_id, message):

        zId = message.zid1
        zone = self.zones[zId]

        rb_y1 = (zone.grid['rb_y'] + zone.grid['lt_y'])/2
        lt_y2 = rb_y1 + 1

        self.create_zone(zone.grid['lt_x'], zone.grid['lt_y'],
                     zone.grid['rb_x'], rb_y1,
                     zone.max_members, zone.grid['border_width'],
                     zone.grid['global_size'], self.id)

        self.create_zone(zone.grid['lt_x'], lt_y2,
                     zone.grid['rb_x'], zone.grid['rb_y'],
                     zone.max_members, zone.grid['border_width'],
                     zone.grid['global_size'], self.id)
        self.delete_zone(zone)

    # on_mq_z_hsplit: TODO
    def on_mq_z_hsplit(self, server_id, message):
        
        zId = message.zid1
        zone = self.zones[zId]

        rb_x1 = (zone.grid['rb_x'] + zone.grid['lt_x'])/2
        lt_x2 = rb_x1 + 1

        self.create_zone(zone.grid['lt_x'], zone.grid['lt_y'],
                     rb_x1, zone.grid['rb_y'],
                     zone.max_members, zone.grid['border_width'],
                     zone.grid['global_size'], self.id)
        self.create_zone(lt_x2, self.grid['lt_y'],
                     zone.grid['rb_x'], zone.grid['rb_y'],
                     zone.max_members, zone.grid['border_width'],
                     zone.grid['global_size'], self.id)
        self.delete_zone(zone)

    # on_mq_z_destroy: TODO
    def on_mq_z_destroy(self, server_id, message):

        self.delete_zone(self.zones[message.zId])

    # on_mq_z_merge: TODO
    def on_mq_z_merge(self, server_id, message):
        
        zId1 = message.zid1
        zId2 = message.zid2
        zone1 = self.zones[zId1]
        zone2 = self.zones[zId2]

        lt_x = min(zone1.grid['lt_x'], zone2.grid['lt_x'])
        lt_y = min(zone1.grid['lt_y'], zone2.grid['lt_y'])
        rb_x = max(zone1.grid['rb_x'], zone2.grid['rb_x'])
        rb_y = max(zone1.grid['rb_y'], zone2.grid['rb_y'])

        zone = self.create_zone(lt_x, lt_y, rb_x, rb_y, 
                     5, 4, 511, self.id)

        self.delete_zone(zone1)
        self.delete_zone(zone2)

    def dumps(self):
        data = {
            'cpu_usage': psutil.cpu_percent(interval=None, percpu=True),
            'mem_usage': psutil.virtual_memory().percent,
            'list_zone': [],
            'num_zone': len(self.zones)
        }

        for zid, zone in self.zones.iteritems():
            zone_data = {
                'zone_id': zid,
                'num_client': zone.count()
            }

            data['list_zone'].append(zone_data)

        return json.dumps(data)

    def run(self):
        try:
            zk_success = self.initialize_zk()

            if zk_success is not None:
                raise ZoneServerError(zk_success)

            zk_zone_server_path = self.zk_zone_servers_path + self.id

            data = {
                'cpu_usage': psutil.cpu_percent(interval=None, percpu=True),
                'mem_usage': psutil.virtual_memory().percent,
                'list_zone': {},
                'num_zone': 0
            }

            # zookeeper setup
            node = self.zk_client.create(path=zk_zone_server_path,
                                         value=json.dumps(data),
                                         ephemeral=True, sequence=False)

            # connect to mq as a echo server
            self.connect_mq(self.mq_host, self.mq_pub_port, self.mq_sub_port,
                            'zoneserver-allserver', self.id)

            # register monitoring
            self.add_timed_call(self.update_zk_node_data, 5)

            zone = self.create_zone(0, 0, 511, 511, 5, 4, 512, self.id)

            AbstractServer.run(self)

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            logger.info('Shutting down %s' % self.id)
            self.close_zk()
