import core.server as server
from core.protocol import *


class Gateway(server.AbstractServer):
    """ Gateway """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port):
        server.AbstractServer.__init__(self, "gateway")

        # connect to mq as a gateway
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, self.id)

        # handler
        self.mq_hanlders = {
            'rJAccept': self.on_mq_r_j_accept,
            'rJReject': self.on_mq_r_j_reject,
            'rBMsg': self.on_mq_r_b_msg,
            'rBye': self.on_mq_r_bye,
        }

        # handler
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
        self.listen_client(port)

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

    def on_client_close(self, client, reason):
        print client.get_id(), "disconnected"

        # remove client from hash
        del self.clients[client.get_id()]

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
        # TODO: get room list from manager
        room_list = {}

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
    server = Gateway(18888, '127.0.0.1', 5561, 5562)
    server.run()
