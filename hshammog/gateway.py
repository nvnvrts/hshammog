import core.server as server


class Gateway(server.AbstractServer):
    """ Gateway """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port):
        server.AbstractServer.__init__(self)

        # connect to mq as a gateway
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, "gateway")

        # accept client
        self.listen_client(port)

    def on_mq_received(self, message):
        print "received from mq: ", message

    def on_client_received(self, client, message):
        print "received from client: ", message
        tag = "echoserver"
        print "pub to mq: ", message, tag
        self.publish_mq(message, tag)


if __name__ == '__main__':
    server = Gateway(18888, '127.0.0.1', 5561, 5562)
    server.run()
