import string
import core.server as server


class Gateway(server.AbstractServer):
    """ Gateway """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port):
        server.AbstractServer.__init__(self)

        self.clients = {}

        # connect to mq as a gateway
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, "gateway")

        # accept client
        self.listen_client(port)

    def on_mq_received(self, message):
        print "received from mq: ", message
        #id, message = string.split(message)
        id, payload = message.split(" ", 1)
        client = self.clients[id]
        if client:
            client.send(payload)
            print "sent to client", id, payload
        else:
            print "client not found", id

    def on_client_connect(self, client):
        self.clients[client.get_id()] = client
        print "new client connected", client.get_id()

    def on_client_close(self, client, reason):
        del self.clients[client.get_id()]
        print "client disconnected", client.get_id()

    def on_client_received(self, client, message):
        print "received from client: ", message
        message = "%s %s" % (client.get_id(), message)
        tag = "echoserver"
        print "pub to mq: ", message, tag
        self.publish_mq(message, tag)


if __name__ == '__main__':
    server = Gateway(18888, '127.0.0.1', 5561, 5562)
    server.run()
