import core.server as server


class EchoServer(server.AbstractServer):
    """ Echo Server """

    def __init__(self, mq_host, mq_pub_port, mq_sub_port):
        server.AbstractServer.__init__(self)

        # connect to mq as a echo server
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, "echoserver")

    def on_mq_received(self, message):
        print "received from mq: ", message
        tag = "gateway"
        print "pub to mq: ", message, tag
        self.publish_mq(message, tag)


if __name__ == '__main__':
    server = EchoServer('127.0.0.1', 5561, 5562)
    server.run()