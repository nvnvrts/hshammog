import logging
import zmq

logger = logging.getLogger(__name__)


class PubSub():
    """ PubSub using ZMQ """

    def __init__(self, pub_port, sub_port):
        self.pub_port = pub_port
        self.sub_port = sub_port

    def run(self):
        try:
            context = zmq.Context()

            pub = context.socket(zmq.XSUB)
            pub.bind("tcp://*:%d" % self.pub_port)

            sub = context.socket(zmq.XPUB)
            sub.bind("tcp://*:%d" % self.sub_port)

            logger.debug("mq pub port: %d, sub port: %d" % (self.pub_port, self.sub_port))

            zmq.device(zmq.QUEUE, pub, sub)
        except Exception as e:
            logger.error("Exception: %s" % e.message)
        finally:
            pub.close()
            sub.close()
            context.term()
