import string
import core.server as server
from core.protocol import *

class Gateway(server.AbstractServer):
    """ Gateway """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port):
        server.AbstractServer.__init__(self)

        # connect to mq as a gateway
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, "gateway")

        # start accepting client
        self.clients = {}
        self.listen_client(port)

    def on_mq_received(self, message):
        print "received from mq: ", message

        # parse message from mq
        id, payload = message.split(" ", 1)

        # get client by id
        client = self.clients[id]
        if client:
            client.send(payload)
            print "sent to client", id, payload
        else:
            print "client not found", id

    def on_client_connect(self, client):
        print "new client connected", client.get_id()

        # add client to hash
        self.clients[client.get_id()] = client

    def on_client_close(self, client, reason):
        print "client disconnected", client.get_id()

        # remove client from hash
        del self.clients[client.get_id()]

    def on_client_received(self, client, message):
        print "received from client: ", message

        # publish message to echoserver via mq
        msg = "%s %s" % (client.get_id(), message)
        self.publish_mq(msg, "echoserver")

if __name__ == '__main__':
    server = Gateway(18888, '127.0.0.1', 5561, 5562)
    server.run()
