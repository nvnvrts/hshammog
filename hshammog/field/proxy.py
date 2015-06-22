# python generic libraries
import sys
import json
import logging

# hshammog
from core import logger
from conf import cfg
from core.server import AbstractServer


class Proxy(AbstractServer):
    ''' Proxy '''

    def __init__(self, proxy_port, zk_hosts, zk_path):
        AbstractServer.__init__(self, 'proxy', zk_hosts, zk_path)

        logger.info('proxy %s initializing...' % self.id)

        self.proxy_port = proxy_port
        self.gateways = {}

        logger.info('proxy %s initialized' % self.id)

    def on_client_connect(self, client):
        gateway = min(self.gateways.iteritems(),
                      key=(lambda x: x[1]['num_client']))[0]
        client.send_data(str(self.gateways[gateway]['ip_address']))

    def on_zk_gateway_added(self, gateways):
        logger.info('gateways are now: %s' % self.get_zk_gateways())

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

        gw_data = {
            'gateway_id': gateway,
            'ip_address': parsed_data['ip_address'],
            'num_client': parsed_data['num_client']
        }

        self.gateways[gateway] = gw_data

    def run(self):
        try:
            zk_success = self.initialize_zk()

            if zk_success is not None:
                raise ProxyError(zk_success)

            self.watch_zk_gateways()

            self.listen_tcp_client(self.proxy_port)

            AbstractServer.run(self)

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            logger.info('Shutting down %s' % self.id)
            self.close_zk()
