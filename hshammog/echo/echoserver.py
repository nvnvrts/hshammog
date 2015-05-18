from core.server as AbstractServer


class EchoServer(AbstractServer):
    ''' Echo Server '''

    def __init__(self, mq_host, mq_pub_port, mq_sub_port):
        server.AbstractServer.__init__(self)

        # connect to mq as a echo server
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, 'server')

    def on_mq_received(self, message):
        print 'received from mq: ', message

        # parse message from mq
        id, payload = message.split(' ', 1)

        # publish message to gateway via mq
        print 'pub to mq: ', message
        self.publish_mq(message, 'gateway')
