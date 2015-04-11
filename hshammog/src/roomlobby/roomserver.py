from core.server import AbstractServer


class RoomServer(AbstractServer):
    """ RoomServer """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port):
        AbstractServer.__init__(self)

        # connect to mq as a room server
        # subscribe tag = 'R'
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, 'R')

        # For future use
        # Wait for TCP connection
        self.listen_client(port)

    # From Gateway
    def on_mq_received(self, message):
        print 'received from mq: ', message

        #TODO: Cmd Processing
        pass

    # For future use
    def on_client_received(self, client, message):
        pass

    def run():
        pass
