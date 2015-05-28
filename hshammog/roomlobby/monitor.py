import sys
import getopt
import logging
import json

from core import logger
from core.server import AbstractServer


class Monitor(AbstractServer):
    ''' Monitor '''

    def __init__(self, zk_hosts, zk_path):
        AbstractServer.__init__(self, 'monitor', zk_hosts, zk_path)

        logger.info('monitor %s initializing...' % self.id)
        logger.info('monitor %s initialized.' % self.id)

    def on_zk_gateway_added(self, gateways):
        logger.info('gateways are now: %s' % self.get_zk_gateways())

        # add data watcher to new gateways
        for gateway in gateways:
            @self.zk_client.DataWatch(self.zk_gateway_servers_path + gateway)
            def watch_gateway(data, stat):
                if data is not None:
                    self.on_zk_gateway_data_changed(gateway, data)

    def on_zk_gateway_data_changed(self, gateway, data):
        parsed_data = json.loads(data)

        logger.info('%s: cpu_usage(%s), mem_usage(%f)' %
                    (gateway, parsed_data['cpu_usage'],
                     parsed_data['mem_usage']))
        logger.info('%s: num_clients(%d)' %
                    (gateway, parsed_data['num_clients']))

    def on_zk_roomserver_added(self, roomservers):
        logger.info('roomservers are now: %s' % self.get_zk_roomservers())

        # add data watcher to new roomservers
        for roomserver in roomservers:
            @self.zk_client.DataWatch(self.zk_room_servers_path + roomserver)
            def watch_roomserver(data, stat):
                logger.debug(data)
                if data is not None:
                    self.on_zk_roomserver_data_changed(roomserver, data)

    def on_zk_roomserver_data_changed(self, roomserver, data):
        number_total_rooms = 0
        number_empty_rooms = 0
        number_full_rooms = 0
        number_available_rooms = 0

        parsed_data = json.loads(data)

        for rid, values in parsed_data['rooms'].iteritems():
            number_total_rooms += 1
            if values['count'] == 0:
                number_empty_rooms += 1
                number_available_rooms += 1
            elif values['count'] == values['max']:
                number_full_rooms += 1
            else:
                number_available_rooms += 1

        logger.info('%s: cpu_usage(%s), mem_usage(%f)' %
                    (roomserver, parsed_data['cpu_usage'],
                     parsed_data['mem_usage']))
        logger.info('%s: available(%d), empty(%d), full(%d), total(%d)' %
                    (roomserver, number_available_rooms, number_empty_rooms,
                     number_full_rooms, number_total_rooms))

    def run(self):
        try:
            zk_success = self.initialize_zk()

            if zk_success is not None:
                raise MonitorError(zk_success)

            self.watch_zk_gateways()
            self.watch_zk_roomservers()

            AbstractServer.run(self)

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            logger.info('Shutting down %s' % self.id)
            self.close_zk()
