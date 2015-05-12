import sys
import getopt
import logging
import json
import core.config as config
import core.server as server

logger = logging.getLogger(__name__)


class Monitor(server.AbstractServer):
    """ Monitor """

    def __init__(self, zk_hosts, zk_path):
        server.AbstractServer.__init__(self, "monitor", zk_hosts, zk_path)

        logger.info("monitor %s initializing..." % self.id)

        self.watch_zk_gateways()
        self.watch_zk_roomservers()

        logger.info("monitor %s initialized." % self.id)

    def on_zk_gateway_added(self, gateways):
        logger.info("gateways are now: %s" % self.get_zk_gateways())

        # add data watcher to new gateways
        for gateway in gateways:
            @self.zk_client.DataWatch(self.zk_gateway_servers_path + gateway)
            def watch_gateway(data, stat):
                self.on_zk_gateway_data_changed(gateway, data)

    def on_zk_gateway_data_changed(self, gateway, data):
        logger.info("%s: %s" % (gateway, json.loads(data)))

    def on_zk_roomserver_added(self, roomservers):
        logger.info("roomservers are now: %s" % self.get_zk_roomservers())

        # add data watcher to new roomservers
        for roomserver in roomservers:
            @self.zk_client.DataWatch(self.zk_room_servers_path + roomserver)
            def watch_roomserver(data, stat):
                self.on_zk_roomserver_data_changed(roomserver, data)

    def on_zk_roomserver_data_changed(self, roomserver, data):
        number_total_rooms = 0
        number_empty_rooms = 0
        number_full_rooms = 0
        number_available_rooms = 0

        for rid, values in json.loads(data).iteritems():
            number_total_rooms += 1
            if values['count'] == 0:
                number_empty_rooms += 1
                number_available_rooms += 1
            elif values['count'] == values['max']:
                number_full_rooms += 1
            else:
                number_available_rooms += 1

        logger.info("%s: available(%d), empty(%d), full(%d), total(%d)" % (roomserver,
                                                                           number_available_rooms,
                                                                           number_empty_rooms,
                                                                           number_full_rooms,
                                                                           number_total_rooms))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:z:", ["--zk_path="])
    except getopt.GetoptError:
        print "usage: monitor.py -z <zookeeper path>"
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print "usage: monitor.py -z <zookeeper path>"
        elif opt in ("-z", "--zk_path"):
            zk_path = arg

    # start a monitor
    server = Monitor("192.168.0.16:2181", zk_path)
    server.run()