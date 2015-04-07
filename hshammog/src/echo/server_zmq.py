import zmq
import random
import sys
import time

from . import cfg


def run():
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.connect("tcp://%s:%d" % (cfg.mq_servers[0], cfg.mq_inport))
    publisher_id = random.randrange(0, 9999)
    while True:
        topic = random.randrange(1, 10)
        messagedata = "server#%s" % publisher_id
        print "Hello %s %s" % (topic, messagedata)
        socket.send("%d %s" % (topic, messagedata))
        time.sleep(1)
