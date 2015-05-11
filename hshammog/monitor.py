import sys
import getopt
import logging
import json
from kazoo.client import KazooClient
import core.config as config
import core.server as server


class Monitor(server.AbstractServer):
    """ Monitor """

    def __init__(self, zk_hosts, zk_path):
        server.AbstractServer.__init__(self, "monitor", zk_hosts, zk_path)

        self.gateways = []
        self.roomservers = []

        # zookeeper client setup
        @self.zk_client.ChildrenWatch(self.zk_gateway_servers_path)
        def watch_gateways(gateways):
            self.on_zk_gateways(gateways)

        @self.zk_client.ChildrenWatch(self.zk_room_servers_path)
        def watch_roomservers(roomservers):
            self.on_zk_roomservers(roomservers)


    def on_zk_gateways(self, gateways):
        # find out new gateways
        new_gateways = [x for x in gateways if x not in self.gateways]
        print "new gateways:", new_gateways

        self.gateways = gateways
        print "gateways are now:", gateways

        # add data watcher to new gateways
        for gateway in new_gateways:
            @self.zk_client.DataWatch(self.zk_gateway_servers_path + gateway)
            def watch_gateway(data, stat):
                print "%s: %s" % (gateway, json.loads(data))

    def on_zk_roomservers(self, roomservers):
        # find out new roomservers
        new_roomservers = [x for x in roomservers if x not in self.roomservers]
        print "new roomservers:", roomservers

        self.roomservers = roomservers
        print "roomservers are now:", roomservers

        # add data watcher to new roomservers
        for roomserver in new_roomservers:
            @self.zk_client.DataWatch(self.zk_room_servers_path + roomserver)
            def watch_roomserver(data, stat):
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

                print "%s: available(%d), empty(%d), full(%d), total(%d)" % (roomserver,
                                                                             number_available_rooms,
                                                                             number_empty_rooms,
                                                                             number_full_rooms,
                                                                             number_total_rooms)


if __name__ == "__main__":
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