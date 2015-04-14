from core.server import AbstractServer
class Room():

    def __init__(self):
        self.cid_list = []
        self.rid = 0

    def set_rid(self,rid):
        self.rid = rid

    def add(self,cid):
        self.cid_list.append(cid)

    def delete(self,cid):
        self.cid_list.remove(cid)




class RoomServer(AbstractServer):
    """ RoomServer """

    def __init__(self, port, mq_host, mq_pub_port, mq_sub_port):
        AbstractServer.__init__(self)

        # connect to mq as a room server
        # subscribe tag = 'R'
        self.connect_mq(mq_host, mq_pub_port, mq_sub_port, 'R')

        # For future use
        # Wait for TCP connection
        self.listen_client(port)
        r1=Room()
        r1.set_rid(1)


    def rid_to_room(self,rid): #rid로 room instance 찾아주는 함수
        for i in range(len(self.room_list) - 1)
            if self.room_list[i].rid == rid:
                return self.room_list[i]
            else:
                continue

    # From Gateway
    def on_mq_received(self, message):
        print 'received from mq: ', message

        message_split = message.split('|')

        roomserver_dictionary = {
            'rJoin': #cid,rid
                (lambda message_split:
                    self.on_rjoin_received(int(message_split[1]),int(message_split[3]))),
            'rMsg':  #cidSrc,cidDest,rid,msg
                (lambda message_split:
                    self.on_rmsg_received(int(message_split[1]),int(message_split[2]),int(message_split[3]),message_split[4])),
            'rExit':  #cid,rid
                (lambda message_split:
                    self.on_rexit_received(int(message_split[1]),int(message_split[3])))
        }
    def make_message(self, cmd, cid, cid_dest, rid, msg):
        return cmd + "|" + cid + "|" + cid_dest + "|" + rid + "|" + msg

    def on_rjoin_received(self,cid,rid):
        room = self.rid_to_room(self,rid)
        if len(room.cid_list) < 6:
            room.add(cid)
            tag = 'G'
            msg = self.make_message(cmd='rJAccept',cid=cid,cid_dest='',rid=rid,msg='')
            self.publish_mq(msg,tag)
        else:
            tag = 'G'
            msg = self.make_message(cmd='rJReject',cid=cid,cid_dest='',rid=rid,msg="can't enter this room")
            self.publish_mq(msg,tag)

    def on_rmsg_received(self,cidSrc,cidDest,rid,msg):
        room = self.rid_to_room(self,rid)
        if cidDest == -1:
            for i in room.cid_list:
                tag = 'G'
                msg = self.make_message(cmd='rBMsg',cid=cidSrc,cid_dest=i,msg=msg)
                self.publish_mq(msg,tag)
        else:
            tag = 'G'
            msg = self.make_message(cmd='rBMsg',cid=cidSrc,cid_dest=cidDest,msg=msg)
            self.publish_mq(msg,tag)

    def on_rexit_received(self,cid,rid):
        room = self.rid_to_room(self,rid)
        room.delete(cid)
        tag = 'G'
        msg = self.make_message(cmd='rBye',cid=cid,cid_dest='',msg='')
        self.publish_mq(msg,tag)


    # For future use
    def on_client_received(self, client, message):
        pass

    def run():
        pass
