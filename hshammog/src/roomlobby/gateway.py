from core.server import AbstractServer

from lib.protocol import CGwRequest
import lib.gw_helper


class Gateway(AbstractServer):
    """ Gateway """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port):
        AbstractServer.__init__(self)

        # connect to mq as a gateway
        # subscribe tag = 'G'
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, 'G')

        # accept client
        self.listen_client(port)

        # Cid-Client Binding
        self.cid_binding = {}

        # Cid issue number
        self.cid_issue = 0

    # From Room-server
    # rJAccept, rJReject, rBMsg, rBye, rError
    def on_mq_received(self, message):
        print 'received from mq: ', message

        message_split = message.split(',')

        roomserver_dictionary = {
            'rJAccept':
            (lambda message_split:
                on_rjaccept_received(int(message_split[1]),
                                     int(message_split[2]))),
            'rJReject':
            (lambda message_split:
                on_rjreject_received(int(message_split[1]),
                                     int(message_split[2]))),
            'rBMsg':
            (lambda message_split:
                on_rbmsg_received(int(message_split[1]),
                                  int(message_split[2]),
                                  int(message_split[3]),
                                  message_split[4])),
            'rBye':
            (lambda message_split:
                on_rbye_received(int(message_split[1]),
                                 int(message_split[2]))),
            'rError':
            (lambda message_split:
                on_rerror_received(int(message_split[1]),
                                   message_split[2]))
        }

    # From Client
    # sConnect, sExit, rLookup, rJoin, rMsg, rExit
    def on_client_received(self, client, message):
        # parse from message in JSON format
        request = parse_from_json(message)

        client_dictionary = {
            'sConnect':
            (lambda request: on_sconnect_received(client)),
            'sExit':
            (lambda request: on_sexit_received(request.cid)),
            'rLookup':
            (lambda request: on_rlookup_received(request.cid,
                                                 request.nmaxroom)),
            'rJoin':
            (lambda request: on_rjoin_received(request.cid,
                                               request.nmaxroom)),
            'rMsg':
            (lambda request: on_rmsg_received(request.cid,
                                              request.ciddest,
                                              request.rid,
                                              request.msg)),
            'rExit':
            (lambda request: on_rexit_received(request.cid,
                                               request.rid))
        }

        if request.cmd in client_dictionary:
            print 'received valid', request.cmd, 'from client'
            client_dictionary[request.cmd](request)
        else:
            print 'received invalid', request.cmd, 'from client'

    # connect request from client (sConnect)
    def on_sconnect_received(self, client):
        print 'connect request from client'

        try:
            # ask zookeeper for a cid
            ####################################
            print 'ask zookeeper for a cid'
            cid = zk_cid_issue()
            print 'new cid: %d' % cid
            bind_cid(cid, client)

            resp = parse_to_json(CGwRequest(cmd='sAccept',
                                            cid=cid))
            client.transport.write(resp)

        except Exception as e:
            print 'service rejected'
            resp = parse_to_json(CGwRequest(cmd='sReject'))
            client.transport.write(resp)

    # room look up from client (rLookup)
    def on_rlookup_received(self, cid, nmaxroom):
        # ask zookeeper for room number list
        ####################################
        roomList = zk_room_lookup(nmaxroom)
        return roomList

    # room join request from client (rJoin)
    def on_rjoin_received(self, cid, rid):
        # send join request to mq
        print "room join request from client"
        tag = "J"
        msg = cid + "," + rid
        print "pub to mq: ", tag
        self.publish_mq(msg, tag)

    # message request from client (rMsg)
    def on_rmsg_received(self, cid_src, cid_dest, msg):
        # send message request to mq
        print "send message request from client"
        tag = "M"
        msg = cid_src + msg
        print "pub to mq: ", tag
        self.publish_mq(msg, tag)

    # room exit request from client (rExit)
    def on_rexit_received(self, cid, rid):
        # send exit request to mq
        print "room exit request from client"
        tag = "X"
        msg = cid + "," + rid
        print "pub to mq: ", tag
        self.publish_mq(msg, tag)

    # exit request from client (sExit)
    def on_sexit_received(self, cid):
        pass

    # room join accept from roomserver (rJAccept)
    def on_rjaccept_received(self, cid, rid):
        pass

    # room join reject from roomserver (rJReject)
    def on_rjreject_received(self, cid, rid):
        pass

    # room broadcast message from roomserver (rBMsg)
    def on_rbmsg_received(self, cid_src, cid_dest, rid, msg):
        pass

    # room bye from roomserver (rBye)
    def on_rbye_received(self, cid, rid):
        pass

    # room error from roomserver (rError)
    def on_rerror_received(self, cid, msg):
        pass

    # client id issuer
    # TODO: zookeeper issuing system
    def zk_issue_cid(self):
        cid_issue += 1
        return cid_issue

    # client room lookup
    # TODO: zookeeper room lookup
    def zk_room_lookup(self, nmaxroom):
        return {}

    # client id - client session binder
    def bind_cid(self, cid, client):
        cid_binding[cid] = client

if __name__ == '__main__':
    server = Gateway(18888, '127.0.0.1', 5561, 5562)
    server.run()
