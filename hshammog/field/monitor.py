# python generic libraries
import sys
import logging
import json
import random
import threading

# hshammog
from core import logger
from conf import cfg
from core.exceptions import *
from core.protocol import *
from core.field import *
from core.server import AbstractServer


class Monitor(AbstractServer):
    ''' Monitor '''

    def __init__(self, client_websocket_port, mq_host,
                 mq_pub_port, mq_sub_port, zk_hosts, zk_path):
        AbstractServer.__init__(self, 'monitor', zk_hosts, zk_path)

        logger.info('monitor %s initializing...' % self.id)

        self.client_websocket_port = client_websocket_port

        # save given configurations
        self.mq_host = mq_host
        self.mq_pub_port = mq_pub_port
        self.mq_sub_port = mq_sub_port

        # list of clients to broadcast(push)
        self.clients = {}

        # cached data
        self.zone_lock = threading.Lock()
        self.zones = {}
        self.gateways = {}
        self.zoneservers = {}

        # zone request
        self.zone_last_requested = 0
        self.zone_last_completed = 0
        self.zone_tree = {}

        # mq handlerd
        self.mq_handlers = {
            'zAddDone': self.on_mq_z_add_done,
            'zSplitDone': self.on_mq_z_split_done,
            'zMergeDone': self.on_mq_z_merge_done
        }

        logger.info('monitor %s initialized.' % self.id)

    def on_client_connect(self, client):
        logger.info('new %s connected' % client.get_id())

        self.clients[client.get_id()] = client

    def on_client_disconnect(self, client):
        logger.info('%s disconnected' % client.get_id())

        del self.clients[client.get_id()]

    def on_client_data_received(self, client, data):
        dump_id, dump, op = data.split('|', 2)

        if 'gateway' in dump_id:
            parsed_data = json.loads(dump)
            self.gateways[dump_id] = parsed_data
        elif 'zoneserver' in dump_id:
            parsed_data = json.loads(dump)
            self.zoneservers[dump_id] = parsed_data
        elif 'zone' in dump_id:
            if 'd' in op:
                del self.zones[dump_id]
            else:
                parsed_data = json.loads(dump)
                self.zones[dump_id] = parsed_data

    def on_zk_gateway_added(self, gateways):
        logger.info('gateways are now: %s' % self.get_zk_gateways())

        # add data watcher to new gateways
        for gateway in gateways:
            @self.zk_client.DataWatch(self.zk_gateway_servers_path + gateway)
            def watch_gateway(data, stat):
                if data is not None:
                    self.on_zk_gateway_data_changed(gateway, data)

    def on_zk_gateway_removed(self, gateways):
        logger.info('gateways are now: %s' % self.get_zk_gateways())

        for gateway in gateways:
            if gateway in self.gateways.keys():
                del self.gateways[gateway]

    def on_zk_gateway_data_changed(self, gateway, data):
        parsed_data = json.loads(data)

        self.gateways[gateway] = parsed_data

    def on_zk_zoneserver_added(self, zoneservers):
        logger.info('zoneservers are now: %s' % self.get_zk_zoneservers())

        # add data watcher to new zoneservers
        for zoneserver in zoneservers:
            @self.zk_client.DataWatch(self.zk_zone_servers_path + zoneserver)
            def watch_zoneserver(data, stat):
                if data is not None:
                    self.on_zk_zoneserver_data_changed(zoneserver, data)

    def on_zk_zoneserver_removed(self, zoneservers):
        logger.info('zoneservers are now: %s' % self.get_zk_zoneservers())

        for zoneserver in zoneservers:
            if zoneserver in self.zoneservers.keys():
                del self.zoneservers[zoneserver]

    def on_zk_zoneserver_data_changed(self, zoneserver, data):
        parsed_data = json.loads(data)

        self.zoneservers[zoneserver] = parsed_data

    def on_zk_zone_added(self, zones):
        logger.info('zones are now: %s' % self.get_zk_zones())

        # add data watcher to new zones
        for zone in zones:
            @self.zk_client.DataWatch(self.zk_zone_zones_path + zone)
            def watch_zone(data, stat):
                if data is not None:
                    self.on_zk_zone_data_changed(zone, data)

    def on_zk_zone_removed(self, zones):
        logger.info('zone are now: %s' % self.get_zk_zones())

        if self.zone_lock.acquire(True):
            # remove zones from cache
            for zone in zones:
                if zone in self.zones.keys():
                    del self.zones[zone]
            self.zone_lock.release()

    def on_zk_zone_data_changed(self, zone, data):
        parsed_data = json.loads(data)

        if self.zone_lock.acquire(True):
            self.zones[zone] = parsed_data
            self.zone_lock.release()

    def update_client(self):
        if self.zone_lock.acquire(True):
            zones = self.zones
            self.zone_lock.release()

        data = {
            'gateway': {
                'num_gateway': len(self.gateways),
                'list_gateway': []
            },
            'zoneserver': {
                'num_zoneserver': len(self.zoneservers),
                'list_zoneserver': []
            },
            'zone': {
                'num_zone': len(zones),
                'list_zone': []
            }
        }

        for gw, gw_data in self.gateways.iteritems():
            gw_obj = {
                'gateway_id': gw,
                'cpu_usage': gw_data['cpu_usage'],
                'mem_usage': gw_data['mem_usage'],
                'num_client': gw_data['num_client'],
                'address': gw_data['ip_address']
            }
            data['gateway']['list_gateway'].append(gw_obj)

        for zs, zs_data in self.zoneservers.iteritems():
            zs_obj = {
                'zoneserver_id': zs,
                'cpu_usage': zs_data['cpu_usage'],
                'mem_usage': zs_data['mem_usage'],
                'list_zone': zs_data['list_zone'],
                'num_zone': zs_data['num_zone'],
                'address': zs_data['ip_address']
            }
            data['zoneserver']['list_zoneserver'].append(zs_obj)

        for z, z_data in zones.iteritems():
            z_obj = {
                'zone_id': z,
                'width': z_data['width'],
                'height': z_data['height'],
                'lt_x': z_data['lt_x'],
                'lt_y': z_data['lt_y'],
                'rb_x': z_data['rb_x'],
                'rb_y': z_data['rb_y'],
                'clients': z_data['clients']
            }
            data['zone']['list_zone'].append(z_obj)

        dump = json.dumps(data)
        #logger.debug('updating clients with %s' % dump)

        for client in self.clients.keys():
            self.clients[client].send_data(dump)

    def update_zone(self):
        if len(self.zones) == 0 and len(self.zoneservers) == 1:
            zs = random.choice(self.zoneservers.keys())
            self.zone_last_requested += 1
            self.publish_message(zs,
                                 Message(cmd='zAdd', width=512, height=512,
                                         x=0, y=0,
                                         timestamp=self.zone_last_requested))
        elif len(self.zones) == 0 and len(self.zoneservers) > 1:
            new_zone = Zone(0, 0, 511, 511, cfg.max_client_per_zone,
                            cfg.zone_border_width, 512, self.id)
            new_zones = [new_zone]
            new_zone_idx = [0]

            for i in range(0, len(self.zoneservers)-1):
                split_zone = new_zones[0]
                split_zone_idx = new_zone_idx[0]
                del new_zones[0]

                nz1, nz2 = (random.choice([split_zone.horizontal_split,
                                           split_zone.vertical_split]))()

                new_zones.append(nz1)
                new_zones.append(nz2)

            for i in range(0, len(self.zoneservers)):
                width = new_zones[i].grid['rb_x'] - \
                        new_zones[i].grid['lt_x'] + 1
                height = new_zones[i].grid['rb_y'] \
                        - new_zones[i].grid['lt_y'] + 1
                self.publish_message(self.zoneservers.keys()[i],
                                     Message(cmd='zAdd',
                                             width=width,
                                             height=height,
                                             x=new_zones[i].grid['lt_x'],
                                             y=new_zones[i].grid['lt_y'],
                                             timestamp=self.zone_last_requested))

        elif (len(self.zones) > 0 and
              self.zone_last_requested == self.zone_last_completed):
            max_member = cfg.max_client_per_zone
            min_member = cfg.min_client_per_zone

            def exists(idx, zone_tree):
                return idx in zone_tree.keys()

            def has_left(idx, zone_tree):
                return ((idx*2) in zone_tree.keys())

            def has_right(idx, zone_tree):
                return ((idx*2+1) in zone_tree.keys())

            def is_leaf(idx, zone_tree):
                return not (has_left(idx, zone_tree) or has_right(idx, zone_tree))

            def traverse(idx, zone_tree):
                if not exists(idx, zone_tree):
                    return

                zone_id = zone_tree[idx]
                zone = self.zones.get(zone_id)

                # split
                if zone is not None and is_leaf(idx, zone_tree):
                    if zone['clients']['num_client'] > max_member:
                        direction = random.choice(['zVSplit', 'zHSplit'])
#                        self.zone_last_requested += 1
                        last_requested = self.zone_last_requested
                        self.publish_message(zone['server_id'],
                                             Message(cmd=direction,
                                                     zid1=zone['zone_id'],
                                                     timestamp=last_requested))
                        logger.info('Split %s' % zone['zone_id'])
                # merge
                elif (has_left(idx, zone_tree) and is_leaf(idx*2, zone_tree) and
                      has_right(idx, zone_tree) and is_leaf(idx*2+1, zone_tree)):
                    l_zone = self.zones.get(zone_tree[idx*2])
                    r_zone = self.zones.get(zone_tree[idx*2+1])

                    if l_zone is not None and r_zone is not None and \
                       l_zone['clients']['num_client'] < min_member and \
                       r_zone['clients']['num_client'] < min_member:
#                        self.zone_last_requested += 1
                        last_requested = self.zone_last_requested
                        self.publish_message(l_zone['server_id'],
                                             Message(cmd='zMerge',
                                                     zid1=l_zone['zone_id'],
                                                     zid2=r_zone['zone_id'],
                                                     timestamp=last_requested))
                        logger.info('Merge %s and %s' % (l_zone['zone_id'],
                                                         r_zone['zone_id']))
                    else:
                        traverse(idx*2, zone_tree)
                        traverse(idx*2+1, zone_tree)
                else:
                    traverse(idx*2, zone_tree)
                    traverse(idx*2+1, zone_tree)

            for zs in self.zoneservers.keys():
                if zs in self.zone_tree.keys():
                    traverse(1, self.zone_tree[zs])

    def publish_message(self, tag, message):
        data = '%s|%s|%d' % (self.id, message.dumps(), message.timestamp)
        logger.debug('PUB %s %s %d' % (str(tag), data, message.timestamp))

        self.publish_mq(str(tag), str(data))

    def on_mq_data_received(self, tag, data):
        logger.debug('SUB %s %s' % (tag, data))

        server_id, payload, timestamp = data.split('|', 2)
        message = MessageHelper.load_message(payload)
        message.timestamp = int(timestamp)

        self.mq_handlers[message.cmd](server_id, message)

    def on_mq_z_add_done(self, server_id, message):
#        if message.timestamp == self.zone_last_completed + 1:
#        self.zone_last_completed += 1

        # initialize
        self.zone_tree[server_id] = {1: message.zid1}

    def on_mq_z_split_done(self, server_id, message):
#        if message.timestamp == self.zone_last_completed + 1:
#        self.zone_last_completed += 1

        # make parent
        for key, value in self.zone_tree[server_id].iteritems():
            if value == message.zid1:
                self.zone_tree[server_id][key*2] = message.zid2
                self.zone_tree[server_id][key*2+1] = message.zid3
                break

    def on_mq_z_merge_done(self, server_id, message):
#        if message.timestamp == self.zone_last_completed + 1:
#        self.zone_last_completed += 1

        idx1_ = None
        idx2_ = None

        # idx
        for key, value in self.zone_tree[server_id].iteritems():
            if value == message.zid2:
                idx1_ = key
            elif value == message.zid3:
                idx2_ = key

        if idx1_ is not None and idx2_ is not None:
            idx1 = min(idx1_, idx2_)
            idx2 = max(idx1_, idx2_)

            idx = idx1/2

            del self.zone_tree[server_id][idx1]
            del self.zone_tree[server_id][idx2]

            self.zone_tree[server_id][idx] = message.zid1

    def run(self):
        try:
            zk_success = self.initialize_zk()

            if zk_success is not None:
                raise MonitorError(zk_success)

            self.connect_mq(self.mq_host, self.mq_pub_port, self.mq_sub_port,
                            'monitor-allserver', self.id)

            #self.watch_zk_gateways()
            #self.watch_zk_zoneservers()
            #self.watch_zk_zones()

            self.listen_tcp_client(5902)
            self.listen_websocket_client(self.client_websocket_port)

            self.add_timed_call(self.update_client, 2)
            self.add_timed_call(self.update_zone, 5)

            AbstractServer.run(self)

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            logger.info('Shutting down %s' % self.id)
            self.close_zk()
