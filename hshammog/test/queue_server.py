import zmq
import time
import sys
import random

port = "5560"
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://localhost:%s" % port)
server_id = random.randrange(1,10005)
while True:
    message = socket.recv()
    print "Received request: ",message
    time.sleep (1)
    socket.send("world from server %s" % server_id)