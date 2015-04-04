import zmq


class PubSub():
    """ PubSub using ZMQ """

    def __init__(self, pub_port, sub_port):
        self.pub_port = pub_port
        self.sub_port = sub_port

    def run(self):
        context = zmq.Context()

        pub = context.socket(zmq.XPUB)
        pub.bind("tcp://*:%d" % self.pub_port)

        sub = context.socket(zmq.XSUB)
        sub.bind("tcp://*:%d" % self.sub_port)

        print "pub %d sub %d" % (self.pub_port, self.sub_port)
        zmq.device(zmq.QUEUE, pub, sub)



