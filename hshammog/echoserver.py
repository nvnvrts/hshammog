import core.server as server


class EchoServer(server.AbstractServer):
    """ Echo Server """

    def __init__(self, mq_host, mq_pub_port, mq_sub_port):
        server.AbstractServer.__init__(self)

        # connect to mq as a echo server
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, "echoserver")

    def on_mq_received(self, message):
        print "received from mq: ", message

        # parse message from mq
        id, payload = message.split(" ", 1)

        # publish message to gateway via mq
        print "pub to mq: ", message
        self.publish_mq(message, "gateway")


if __name__ == '__main__':
    server = EchoServer('127.0.0.1', 5561, 5562)
    server.run()