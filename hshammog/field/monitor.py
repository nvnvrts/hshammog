import sys
import getopt
import logging
import json
import random
import uuid
import zlib
import ctypes

from core import logger
from core.server import AbstractServer


class Monitor(AbstractServer):
    ''' Monitor '''

    def __init__(self, client_websocket_port,
                 zk_hosts, zk_path):

        AbstractServer.__init__(self, 'monitor', zk_hosts, zk_path)

        self.client_websocket_port = client_websocket_port

        logger.info('monitor %s initializing...' % self.id)

        # list of clients to broadcast
        self.clients = {}

        logger.info('monitor %s initialized.' % self.id)

    def on_client_connect(self, client):
        logger.info('new %s connected' % client.get_id())

        # add client to hash
        self.clients[client.get_id()] = client

    def on_client_close(self, client, reason):
        logger.info('%s disconnected' % client.get_id())

        # remove client from dictionary
        del self.clients[client.get_id()]

    def new_hash(self):
        return ctypes.c_uint(hash(zlib.adler32(uuid.uuid4().hex))).value

    def new_zone_id(self):
        return ('zone-%x' % self.new_hash())

    def new_gateway_id(self):
        return ('gateway-%s' % self.new_hash())

    def new_cellserver_id(self):
        return ('cellserver-%s' % self.new_hash())

    def new_client_id(self):
        return ('client-%s' % self.new_hash())

    def random_split_zone(self, zone):
        def horizontal_split(zone):
            rb_y1 = (zone['rb-y'] + zone['lt-y'])/2
            lt_y2 = rb_y1 + 1

            zone1 = {
                'zone_id': self.new_zone_id(),
                'width': zone['width'],
                'height': rb_y1 - zone['lt-y'] + 1,
                'lt-x': zone['lt-x'],
                'lt-y': zone['lt-y'],
                'rb-x': zone['rb-x'],
                'rb-y': rb_y1,
                'clients': {
                    'num_client': 0,
                    'list_client': []
                }
            }

            zone2 = {
                'zone_id': self.new_zone_id(),
                'width': zone['width'],
                'height': zone['rb-y'] - lt_y2 + 1,
                'lt-x': zone['lt-x'],
                'lt-y': lt_y2,
                'rb-x': zone['rb-x'],
                'rb-y': zone['rb-y'],
                'clients': {
                    'num_client': 0,
                    'list_client': []
                }
            }

            for client in zone['clients']['list_client']:
                if client['client_x'] >= zone1['lt-x'] and \
                   client['client_x'] <= zone1['rb-x'] and \
                   client['client_y'] >= zone1['lt-y'] and \
                   client['client_y'] <= zone1['rb-y']:
                    zone1['clients']['list_client'].append(client)
                    zone1['clients']['num_client'] += 1
                else:
                    zone2['clients']['list_client'].append(client)
                    zone2['clients']['num_client'] += 1

            return [zone1, zone2]

        def vertical_split(zone):
            rb_x1 = (zone['rb-x'] + zone['lt-x'])/2
            lt_x2 = rb_x1 + 1

            zone1 = {
                'zone_id': self.new_zone_id(),
                'width': rb_x1 - zone['lt-x'] + 1,
                'height': zone['height'],
                'lt-x': zone['lt-x'],
                'lt-y': zone['lt-y'],
                'rb-x': rb_x1,
                'rb-y': zone['rb-y'],
                'clients': {
                    'num_client': 0,
                    'list_client': []
                }
            }

            zone2 = {
                'zone_id': self.new_zone_id(),
                'width': zone['rb-x'] - lt_x2 + 1,
                'height': zone['height'],
                'lt-x': lt_x2,
                'lt-y': zone['lt-y'],
                'rb-x': zone['rb-x'],
                'rb-y': zone['rb-y'],
                'clients': {
                    'num_client': 0,
                    'list_client': []
                }
            }

            for client in zone['clients']['list_client']:
                if client['client_x'] >= zone1['lt-x'] and \
                   client['client_x'] <= zone1['rb-x'] and \
                   client['client_y'] >= zone1['lt-y'] and \
                   client['client_y'] <= zone1['rb-y']:
                    zone1['clients']['list_client'].append(client)
                    zone1['clients']['num_client'] += 1
                else:
                    zone2['clients']['list_client'].append(client)
                    zone2['clients']['num_client'] += 1

            return [zone1, zone2]

        return random.choice([vertical_split, horizontal_split])(zone)

    def update_clients(self):
        data = {}

        initial_size = 512

        num_client = random.randint(1, 10)
        clients = []

        for i in range(0, num_client):
            new_client = {
                'client_id': self.new_client_id(),
                'client_x': random.randint(0, initial_size-1),
                'client_y': random.randint(0, initial_size-1)
            }
            clients.append(new_client)

        zones = []

        initial_zone = {
            'zone_id': self.new_zone_id(),
            'width': initial_size,
            'height': initial_size,
            'lt-x': 0,
            'lt-y': 0,
            'rb-x': initial_size - 1,
            'rb-y': initial_size - 1,
            'clients': {
                'num_client': num_client,
                'list_client': clients
            }
        }
        zones.append(initial_zone)

        while random.randint(0, 10) > 1:
            random_zone_idx = random.choice(range(0, len(zones)))
            random_zone = zones[random_zone_idx]

            if random_zone['width'] > 1 and random_zone['height'] > 1:
                del zones[random_zone_idx]

                zone1, zone2 = self.random_split_zone(random_zone)

                zones.append(zone1)
                zones.append(zone2)

        num_gateway = random.randint(1, 10)
        gateways = []

        num_cellserver = random.randint(1, 10)
        cellservers = []

        for i in range(0, num_gateway):
            new_gateway = {
                'gateway_id': self.new_gateway_id(),
                'num_client': random.randint(0, 100),
                'cpu_usage': random.random()*100.0,
                'mem_usage': random.random()*100.0
            }
            gateways.append(new_gateway)

        for i in range(0, num_cellserver):
            new_cellserver = {
                'cellserver_id': self.new_cellserver_id(),
                'num_zone': 0,
                'list_zone': [],
                'cpu_usage': random.random()*100.0,
                'mem_usage': random.random()*100.0
            }
            cellservers.append(new_cellserver)

        for zone in zones:
            cs_idx = random.randint(0, len(cellservers) - 1)
            cellservers[cs_idx]['list_zone'].append(zone['zone_id'])
            cellservers[cs_idx]['num_zone'] += 1

        for client in clients:
            c_idx = random.randint(0, len(gateways) - 1)
            gateways[c_idx]['num_client'] += 1

        data['zone'] = {
            'num_zone': len(zones),
            'list_zone': zones
        }
        data['gateway'] = {
            'num_gateway': num_gateway,
            'list_gateway': gateways
        }
        data['cellserver'] = {
            'num_cellserver': num_cellserver,
            'list_cellserver': cellservers
        }

        for client in self.clients.keys():
            self.clients[client].send_data(json.dumps(data))

    def run(self):
        try:
            self.listen_websocket_client(self.client_websocket_port)

            self.add_timed_call(self.update_clients, 5)
            AbstractServer.run(self)

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            logger.info('Shutting down %s' % self.id)
            self.close_zk()
