from core.mq import AbstractMQ


class PubSubMQ(AbstractMQ):
    """ Publish-Subscribe using ZMQ """

    def __init__(self, out_port, in_port):
        AbstractMQ.__init__(self, out_port, in_port)

    def run(self):
        try:
            # Context initialization
            context = zmq.Context()

            # Subscribe socket initialization
            sub = context.socket(zmq.SUB)
            sub.bind('tcp://*:%d' % self.in_port)
            sub.setsockopt(zmq.SUBSCRIBE, "")

            # Publish socket initialization
            pub = context.socket(zmq.PUB)
            pub.bind('tcp://*:%d' % self.out_port)

            # Start device
            zmq.device(zmq.FORWARDER, sub, pub)

        except Exception as e:
            print e

        finally:
            pass
            pub.close()
            sub.close()
            context.term()
