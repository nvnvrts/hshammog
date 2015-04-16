# -*- coding: utf-8 -*-

import zmq

from core.messagequeue import AbstractMQ


class PubSubMQ(AbstractMQ):
    """ Publish-Subscribe using ZMQ """

    def __init__(self, out_port, in_port):
        AbstractMQ.__init__(self, out_port, in_port)

    def run(self):
        pub = None
        sub = None
        context = None

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

            print 'Starting pub-sub mq with subport(', self.in_port, \
                  ') and pubport(', self.out_port, ')'

            # Start device
            zmq.device(zmq.FORWARDER, sub, pub)

        except (KeyboardInterrupt, Exception) as e:
            print e

        finally:
            print 'Shutting down pub-sub mq'

            if pub is not None:
                pub.close()
            if sub is not None:
                sub.close()
            if context is not None:
                context.term()
