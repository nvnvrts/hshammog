__author__ = 'wonjin'

import zmq
import time
import os, sys
import random

port = "5560"
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://localhost:%s" % port)
server_id = random.randrange(1, 10000)

while True:
    # Get a message from a client
    message = socket.recv()
    print "Received request : %s" % message

    time.sleep(1)
    socket.send("Get message from server : %s" % server_id)