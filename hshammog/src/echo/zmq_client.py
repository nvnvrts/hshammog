__author__ = 'wonjin'

import zmq
import os, sys
import random

port = "5559"
context = zmq.Context()
print "Connecting to server ... "
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:%s" % port)
client_id = random.randrange(1, 10000)

for i in range(1, 100):

    # Send a message
    print "Sending request %d ..." % i
    socket.send("I am %s" % client_id)

    # Receive a message
    message = socket.recv()
    print "Received reply %d : [%s]" % (i, message)