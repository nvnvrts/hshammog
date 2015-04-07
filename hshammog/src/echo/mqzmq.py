import zmq
import sys
import time

from . import cfg


def run():
    try:
        print 'starting zero-mq echo device'

        # Context initialization
        context = zmq.Context()

        # Frontend socket initialization for Publishers
        frontend = context.socket(zmq.SUB)
        frontend.bind('tcp://*:%d' % cfg.mq_inport)
        frontend.setsockopt(zmq.SUBSCRIBE, "")

        # Backend socket initialization for Subscribers
        backend = context.socket(zmq.PUB)
        backend.bind('tcp://*:%d' % cfg.mq_outport)

        # Start Device
        zmq.device(zmq.FORWARDER, frontend, backend)

    except Exception as e:
        print e
        print 'shutting down zero-mq echo device'

    finally:
        pass
        frontend.close()
        backend.close()
        context.term()
