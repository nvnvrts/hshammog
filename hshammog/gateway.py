import sys
import getopt
import random
import logging
from kazoo.exceptions import *
from core.protocol import *
from core.exceptions import *
import core.server as server

logger = logging.getLogger(__name__)


class Gateway(server.AbstractServer):
    """ Gateway """

    def __init__(self,
                 client_listen_port,
                 mq_host, mq_pub_port, mq_sub_port,
                 zk_hosts, zk_path):
        server.AbstractServer.__init__(self, "gateway", zk_hosts, zk_path)

        logger.info("gateway %s initializing..." % self.id)

        # connect to mq as a gateway
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, self.id)

        # zookeeper setup
        node = self.zk_client.create(path=self.zk_gateway_servers_path + self.id,
                                     value=b"{}",
                                     ephemeral=True,
                                     sequence=False)

        self.watch_zk_roomservers()

        # mq message handlers
        self.mq_handlers = {
            'rJAccept': self.on_mq_r_j_accept,
            'rJReject': self.on_mq_r_j_reject,
            'rBMsg': self.on_mq_r_b_msg,
            'rBye': self.on_mq_r_bye,
        }

        # client message handlers
        self.client_handlers = {
            'sConnect': self.on_client_s_connect,
            'rLookup': self.on_client_r_lookup,
            'rJoin': self.on_client_r_join,
            'rMsg': self.on_client_r_msg,
            'rExit': self.on_client_r_exit,
            'sExit': self.on_client_s_exit,
            'sError': self.on_client_s_error,
        }

        # start accepting client
        self.clients = {}
        self.listen_client(client_listen_port)

        # cache for mapping room id to room server id
        self.server_id_cache = {}

        logger.info("gateway %s initialized." % self.id)

    def update_zk_node_data(self):
        path = self.zk_gateway_servers_path + self.id
        data = {
            'num_clients': len(self.clients)
        }

        # set node data
        self.zk_client.set(path, json.dumps(data))

    def get_zk_roomserver(self, rid):
        server_id = self.server_id_cache.get(rid)
        if not server_id:
            path = self.zk_room_rooms_path + rid

            try:
                data, stat = self.zk_client.get(path)
            except NoNodeError as e:
                raise RoomServerNotFoundError(rid)

            room_data = json.loads(data)
            server_id = room_data['server_id']
            self.server_id_cache[rid] = server_id

        return server_id

    def on_zk_roomserver_added(self, roomservers):
        logger.info("roomservers added... %s" % roomservers)

    def on_zk_roomserver_removed(self, roomservers):
        logger.info("roomservers removed... %s" % roomservers)

        for roomserver in roomservers:
            for rid in self.server_id_cache.keys():
                server_id = self.server_id_cache.get(rid)
                if server_id == roomserver:
                    del self.server_id_cache[rid]

    def pub_mq_message(self, tag, message):
        data = "%s|%s" % (self.id, message.dumps())

        logger.debug("PUB %s %s" % (tag, data))
        self.publish_mq(str(tag), data)

    def on_mq_data_received(self, tag, data):
        logger.debug("SUB %s %s" % (tag, data))

        # parse message from mq
        server_id, payload = data.split("|", 1)
        message = MessageHelper.load_message(payload)

        # invoke mq message handler
        self.mq_handlers[message.cmd](message)

    def on_mq_r_j_accept(self, message):
        client = self.clients.get(message.cid)
        if client:
            self.send_client_message(client, message)
        else:
            pass

    def on_mq_r_j_reject(self, message):
        client = self.clients.get(message.cid)
        if client:
            self.send_client_message(client, message)
        else:
            pass

    def on_mq_r_b_msg(self, message):
        client = self.clients.get(message.ciddest)
        if client:
            self.send_client_message(client, message)
        else:
            pass

    def on_mq_r_bye(self, message):
        client = self.clients.get(message.cid)
        if client:
            self.send_client_message(client, message)
        else:
            pass

    def send_client_message(self, client, message):
        data = message.dumps()
        client.send_data(data)

        logger.debug("SND client %s %s" % (client.get_id(), data))

    def on_client_connect(self, client):
        logger.info("new %s connected" % client.get_id())

        # add client to hash
        self.clients[client.get_id()] = client

        self.update_zk_node_data()

    def on_client_close(self, client, reason):
        logger.info("%s disconnected" % client.get_id())

        # remove client from hash
        del self.clients[client.get_id()]

        self.update_zk_node_data()

        # send message to all room servers
        self.pub_mq_message("roomserver-allserver", Message(cmd='rExitAll', cid=client.get_id()))

    def on_client_data_received(self, client, data):
        logger.debug("RCV client %s %s" % (client.get_id(), data))

        # get message from data,
        message = MessageHelper.load_message(data)

        # invoke client message handler
        self.client_handlers[message.cmd](client, message)

    def on_client_s_connect(self, client, message):
        self.send_client_message(client, Message(cmd='sAccept', cid=client.get_id()))

    def on_client_r_lookup(self, client, message):
        room_list = []

        # gather room list from zk node data
        for room_server in self.get_zk_roomservers():
            path = self.zk_room_servers_path + room_server
            data, stat = self.zk_client.get(path)
            for rid, values in json.loads(data).iteritems():
                if values['count'] == values['max']:
                    pass
                else:
                    room_list.append(rid)

        self.send_client_message(client,
                                 Message(cmd='rList', roomlist=room_list, cid=client.get_id()))

    def on_client_r_join(self, client, message):
        if message.rid == 0:
            # gateway chooses one
            roomservers = self.get_zk_roomservers()
            if roomservers:
                server_id = random.choice(roomservers)
            else:
                self.send_client_message(client,
                                  Message(cmd='rJReject', cid=message.cid, rid=message.rid, msg='no room servers'))
                return
        else:
            self.get_zk_roomserver(message.rid)
            path = self.zk_room_rooms_path + message.rid
            data, stat = self.zk_client.get(path)
            room_data = json.loads(data)
            server_id = room_data['server_id']

        self.pub_mq_message(server_id, message)

    def on_client_r_msg(self, client, message):
        try:
            server_id = self.get_zk_roomserver(message.rid)
            self.pub_mq_message(server_id, message)
        except RoomServerNotFoundError as e:
            self.send_client_message(client, Message(cmd='rBye', cid=message.cid, rid=message.rid))

    def on_client_r_exit(self, client, message):
        try:
            server_id = self.get_zk_roomserver(message.rid)
            self.pub_mq_message(server_id, message)
        except RoomServerNotFoundError as e:
            self.send_client_message(client, Message(cmd='rBye', cid=message.cid, rid=message.rid))

    def on_client_s_exit(self, client, message):
        self.send_client_message(client, Message(cmd='sBye', cid=client.get_id()))

    def on_client_s_error(self, client, message):
        logger.error("client %s error %s" % (client.get_id(), message.msg))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    zk_path = 'test'

    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:z:", ["--zk_path="])
    except getopt.GetoptError:
        print "usage: gateway.py -z <zookeeper path>"
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print "usage: gateway.py -z <zookeeper path>"
        elif opt in ("-z", "--zk_path"):
            zk_path = arg

    # start a gateway
    server = Gateway(18888, '127.0.0.1', 5561, 5562, "192.168.0.16:2181", zk_path)
    server.run()
