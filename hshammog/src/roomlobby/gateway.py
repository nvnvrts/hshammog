__author__ = 'wonjin'

from core.server import AbstractServer

from lib.protocol import CGwRequest
import lib.gw_helper


class Gateway(AbstractServer):
    """ Gateway """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port):
        AbstractServer.__init__(self)

        # connect to mq as a gateway (tag = "G")
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, "G")

        # accept client
        self.listen_client(port)

    def on_mq_received(self, message):
        print "received from mq: ", message
        msg_type = message.split(',')[0]
        if msg_type == "J":
            # parse success flag and playlist
            pass

    def on_client_received(self, client, message):
        print "received from client"

        # parse from message in JSON format
        request = parse_from_json(message)

        # TODO: message processing
        ############################
        if message.cmd == "sConnect":
            self.connect()
        elif message.cmd == "rLookup":
            self.rlookup(message.cid, message.nmaxroom)
        elif message.cmd == "rJoin":
            self.rjoin(message.cid, message.rid)
        elif message.cmd == "rMsg":
            self.rmsg(message.cid, message.ciddest, message.msg)
        elif message.cmd == "rExit":
            self.rexit(message.cid, message.rid)
        elif message.cmd == "sExit":
            self.exit()

    # connect request from client
    def connect(self):
        print "connect request from client"
        # ask zookeeper for a cid
        ####################################
        print "ask zookeeper for a cid"
        cid = 0
        print "your cid is %d" % cid

    # room look up from client
    def rlookup(self, c_id, n_max_room):
        # ask zookeeper for room number list
        ####################################
        roomList = ()
        return roomList

    # room join request from client
    def rjoin(self, cid, rid):
        # send join request to mq
        print "room join request from client"
        tag = "J"
        msg = cid + "," + rid
        print "pub to mq: ", tag
        self.publist_mq(msg, tag)

    # message request from client
    def rmsg(self, cid_src, cid_dest, msg):
        # send message request to mq
        print "send message request from client"
        tag = "M"
        msg = cid_src + msg
        print "pub to mq: ", tag
        self.publist_mq(msg, tag)

    # room exit request from client
    def rexit(self, cid, rid):
        # send exit request to mq
        print "room exit request from client"
        tag = "X"
        msg = cid + "," + rid
        print "pub to mq: ", tag
        self.publist_mq(msg, tag)

    # exit request from client
    def exit(self):
        pass


if __name__ == '__main__':
    server = Gateway(18888, '127.0.0.1', 5561, 5562)
    server.run()
