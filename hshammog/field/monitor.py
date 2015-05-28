# python generic libraries
import sys
import getopt
import logging
import json

# hshammog
from core import logger
from core.server import AbstractServer


class Monitor(AbstractServer):
    ''' Monitor '''

    def __init__(self, client_websocket_port, zk_hosts, zk_path):
        AbstractServer.__init__(self, 'monitor', zk_hosts, zk_path)

        logger.info('monitor %s initializing...' % self.id)

        self.client_websocket_port = client_websocket_port

        # list of clients to broadcast(push)
        self.clients = {}

        # cached data
        self.zones = {}
        self.gateways = {}
        self.zoneservers = {}

        logger.info('monitor %s initialized.' % self.id)

    def on_client_connect(self, client):
        logger.info('new %s connected' % client.get_id())

        self.clients[client.get_id()] = client

    def on_client_disconnect(self, client):
        logger.info('%s disconnected' % client.get_id())

        del self.clients[client.get_id()]

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
            if gateway in self.gateways:
                del self.gateways[gateway]

    def on_zk_gateway_data_changed(self, gateway, data):
        parsed_data = json.loads(data)

        logger.info('%s: cpu_usage(%s), mem_usage(%f)' %
                    (gateway, parsed_data['cpu_usage'],
                     parsed_data['mem_usage']))
        logger.info('%s: num_client(%d)' %
                    (gateway, parsed_data['num_client']))

        self.gateways[gateway] = parsed_data

    def on_zk_zoneserver_added(self, zoneservers):
        logger.info('zoneservers are now: %s' % self.get_zk_zoneservers())

        # add data watcher to new zoneservers
        for zoneserver in zoneservers:
            @self.zk_client.DataWatch(self.zk_zone_servers_path + zoneserver)
            def watch_zoneserver(data, stat):
                logger.debug(data)
                if data is not None:
                    self.on_zk_zoneserver_data_changed(zoneserver, data)

    def on_zk_zoneserver_removed(self, zoneservers):
        logger.info('zoneservers are now: %s' % self.get_zk_zoneservers())

        for zoneserver in zoneservers:
            if zoneserver in self.zoneservers:
                del self.zoneservers[zoneserver]

    def on_zk_zoneserver_data_changed(self, zoneserver, data):
        parsed_data = json.loads(data)

        logger.info('%s: cpu_usage(%s), mem_usage(%f)' %
                    (zoneserver, parsed_data['cpu_usage'],
                     parsed_data['mem_usage']))

        self.zoneservers[zoneserver] = parsed_data

    def on_zk_zone_added(self, zones):
        logger.info('zones are now: %s' % self.get_zk_zones())

        # add data watcher to new zones
        for zone in zones:
            @self.zk_client.DataWatch(self.zk_zone_zones_path + zone)
            def watch_zone(data, stat):
                logger.debug(data)

                if data is not None:
                    self.on_zk_zone_data_changed(zone, data)

    def on_zk_zone_removed(self, zones):
        logger.info('zone are now: %s' % self.get_zk_zones())

        # remove zones from cache
        for zone in zones:
            if zone in self.zones:
                del self.zones[zone]

    def on_zk_zone_data_changed(self, zone, data):
        parsed_data = json.loads(data)

        logger.info('%s: num_client(%d)' %
                    (zone, parsed_data['clients']['num_client']))

        self.zones[zone] = parsed_data

    def update_client(self):
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
                'num_zone': len(self.zones),
                'list_zone': []
            }
        }

        for gw, gw_data in self.gateways.iteritems():
            gw_obj = {
                'gateway_id': gw,
                'cpu_usage': gw_data['cpu_usage'],
                'mem_usage': gw_data['mem_usage'],
                'num_client': gw_data['num_client']
            }
            data['gateway']['list_gateway'].append(gw_obj)

        for zs, zs_data in self.zoneservers.iteritems():
            zs_obj = {
                'zoneserver_id': zs,
                'cpu_usage': zs_data['cpu_usage'],
                'mem_usage': zs_data['mem_usage'],
                'list_zone': zs_data['list_zone'],
                'num_zone': zs_data['num_zone']
            }
            data['zoneserver']['list_zoneserver'].append(zs_obj)

        for z, z_data in self.zones.iteritems():
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
        logger.debug('updating clients with %s' % dump)

        for client in self.clients.keys():
            self.clients[client].send_data(dump)

    def run(self):
        try:
            zk_success = self.initialize_zk()

            if zk_success is not None:
                raise MonitorError(zk_success)

            self.watch_zk_gateways()
            self.watch_zk_zoneservers()
            self.watch_zk_zones()

            self.listen_websocket_client(self.client_websocket_port)

            self.add_timed_call(self.update_client, 5)

            AbstractServer.run(self)

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            logger.info('Shutting down %s' % self.id)
            self.close_zk()
