import zmq

from core import logger
from core.messagequeue import AbstractMQ


class PubSubMQ(AbstractMQ):
    ''' PubSubMQ using ZMQ '''

    def __init__(self, pub_port, sub_port):
        AbstractMQ.__init__(self, pub_port, sub_port)

    def run(self):
        context = None
        pub = None
        sub = None

        try:
            context = zmq.Context()

            pub = context.socket(zmq.XSUB)
            pub.bind('tcp://*:%d' % self.pub_port)

            sub = context.socket(zmq.XPUB)
            sub.bind('tcp://*:%d' % self.sub_port)

            logger.debug('mq pub port: %d, sub port: %d'
                         % (self.pub_port, self.sub_port))

            zmq.device(zmq.QUEUE, pub, sub)

        except Exception as e:
            logger.error('Exception: %s' % e.message)

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            if pub is not None:
                pub.close()

            if sub is not None:
                sub.close()

            if context is not None:
                context.term()

        logger.info('Shutting down PubSubMQ')

if __name__ == '__main__':
    mq = PubSubMQ(5561, 5562)
    mq.run()
