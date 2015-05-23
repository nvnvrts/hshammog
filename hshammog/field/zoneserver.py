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
            'fMsg': self.on_mq_f_msg
        }

        logger.info('zone server %s initialized.' % self.id)

    # create a new zone
    def create_zone(self):
        zone = Zone(0, 0, 511, 511, 5, 4, 512, self.id)
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
        pass

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

    # on_mq_fstart: TODO
    def on_mq_f_start(self):
        pass

    # on_mq_fmove: TODO
    def on_mq_f_move(self):
        pass

    # on_mq_flookup: TODO
    def on_mq_f_lookup(self):
        pass

    # on_mq_fmsg: TODO
    def on_mq_f_msg(self):
        pass

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

            self.create_zone()

            AbstractServer.run(self)

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            logger.info('Shutting down %s' % self.id)
            self.close_zk()
