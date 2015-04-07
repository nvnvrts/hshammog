import sys
import zmq

from . import cfg


def run():
    context = zmq.Context()
    socket = context.socket(zmq.SUB)

    socket.connect("tcp://%s:%d" % (cfg.mq_servers[0], cfg.mq_outport))
    topicfilter = "5"
    socket.setsockopt(zmq.SUBSCRIBE, topicfilter)

    for update_nbr in range(10):
        string = socket.recv()
        topic, messagedata = string.split()
        print topic, messagedata
