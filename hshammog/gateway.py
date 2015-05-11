import sys
import getopt
import logging
from kazoo.client import KazooClient
import core.config as config
from core.protocol import *
import core.server as server

logging.basicConfig()

class Gateway(server.AbstractServer):
    """ Gateway """

    def __init__(self, client_listen_port, mq_host, mq_pub_port, mq_sub_port, zk_node, zk_hosts):
        server.AbstractServer.__init__(self, "gateway")

        # connect to mq as a gateway
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, self.id)

        # zookeeper client setup
        self.zk_client = KazooClient(hosts=zk_hosts)
        self.zk_client.start()

        self.zk_gateway_servers_path = config.ZK_ROOT + zk_node + config.ZK_GATEWAY_SERVER_PATH
        self.zk_client.ensure_path(self.zk_gateway_servers_path)

        self.zk_room_servers_path = config.ZK_ROOT + zk_node + config.ZK_ROOM_SERVER_PATH
        self.zk_client.ensure_path(self.zk_room_servers_path)

        node = self.zk_client.create(path=self.zk_gateway_servers_path + self.id,
                                     value=b"{}", ephemeral=True, sequence=False)
        print "zk node %s created." % node

        # mq message handlers
        self.mq_hanlders = {
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

    def update_zk_node_data(self):
        path = self.zk_gateway_servers_path + self.id

        data = {}
        data['num_clients'] = len(self.clients)

        # set node data
        self.zk_client.set(path, json.dumps(data))

    def publish_message(self, tag, message):
        data = "%s|%s" % (self.id, message.dumps())
        self.publish_mq(tag, data)
        #print "PUB", tag, data

    def send_message(self, client, message):
        data = message.dumps()
        client.send_data(data)
        #print "SND", "client %s" % client.get_id(), data

    def on_mq_data_received(self, tag, data):
        #print "SUB", tag, data

        # parse message from mq
        server_id, payload = data.split("|", 1)
        message = MessageHelper.load_message(payload)

        # invoke mq message handler
        self.mq_hanlders[message.cmd](message)

    def on_mq_r_j_accept(self, message):
        client = self.clients.get(message.cid)
        if client:
            self.send_message(client, message)
        else:
            pass

    def on_mq_r_j_reject(self, message):
        client = self.clients.get(message.cid)
        if client:
            self.send_message(client, message)
        else:
            pass

    def on_mq_r_b_msg(self, message):
        client = self.clients.get(message.ciddest)
        if client:
            self.send_message(client, message)
        else:
            pass

    def on_mq_r_bye(self, message):
        client = self.clients.get(message.cid)
        if client:
            self.send_message(client, message)
        else:
            pass

    def on_client_connect(self, client):
        print "new", client.get_id(), "connected"

        # add client to hash
        self.clients[client.get_id()] = client

        self.update_zk_node_data()

    def on_client_close(self, client, reason):
        print client.get_id(), "disconnected"

        # remove client from hash
        del self.clients[client.get_id()]

        self.update_zk_node_data()
        self.publish_message("server", Message(cmd='rExitAll', cid=client.get_id()))


    def on_client_data_received(self, client, data):
        #print "RCV", "client %s" % client.get_id(), data

        # get message from data,
        message = MessageHelper.load_message(data)

        # invoke client message handler
        self.client_handlers[message.cmd](client, message)

    def on_client_s_connect(self, client, message):
        self.send_message(client, Message(cmd='sAccept', cid=client.get_id()))

    def on_client_r_lookup(self, client, message):
        room_list = []

        # gather room list from zk node data
        for room_server in self.zk_client.get_children(self.zk_room_servers_path):
            path = self.zk_room_servers_path + room_server
            data, stat = self.zk_client.get(path)
            for rid, values in json.loads(data).iteritems():
                if values['count'] == values['max']:
                    pass
                else:
                    room_list.append(rid)

        self.send_message(client, Message(cmd='rList', roomlist=room_list, cid=client.get_id()))

    def on_client_r_join(self, client, message):
        self.publish_message("server", message)

    def on_client_r_msg(self, client, message):
        self.publish_message("server", message)

    def on_client_r_exit(self, client, message):
        self.publish_message("server", message)

    def on_client_s_exit(self, client, message):
        self.send_message(client, Message(cmd='sBye', cid=client.get_id()))

    def on_client_s_error(self, client, message):
        print "client %s error %s" % (client.get_id(), message.msg)


if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h:z:", ["--zk_node="])
    except getopt.GetoptError:
        print "usage: gateway.py -z <zookeeper node>"
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print "usage: gateway.py -z <zookeeper node>"
        elif opt in ("-z", "--zk_node"):
            zk_node = arg

    # start a gateway
    server = Gateway(18888, '127.0.0.1', 5561, 5562, zk_node, "192.168.0.16:2181")
    server.run()
