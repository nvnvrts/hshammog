from core.server import AbstractServer
class Room():

    def __init__(self):
        self.cid_list = []

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

        self.rid_issue = 0
        self.room_list = {}

        #room,room_list 초기 생성, 후에 변경
        self.mk_room()

    def mk_room(self):
        r = Room()
        self.rid_issue = self.rid_issue + 1
        self.room_list[self.rid_issue] = r
    '''
    def rid_to_room(self,rid): #rid로 room instance 찾아주는 함수
        for i in range(len(self.room_list) - 1):
            if self.room_list[i].rid == rid:
                return self.room_list[i]
            else:
                continue
    '''
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
        cmd = message_split[0]
        if cmd in roomserver_dictionary:
            print 'received valid', cmd, ' from gateway'
            roomserver_dictionary[cmd](message_split)
        else:
            print 'received invalid ', cmd, ' from gateway'

    def make_message(self, cmd, cid, cid_dest, rid, msg):
        return str(cmd) + "|" + str(cid) + "|" + str(cid_dest) + "|" + str(rid) + "|" + str(msg)

    def on_rjoin_received(self,cid,rid): #room(rid)에 client(cid)를 넣는다
        room = self.room_list[rid]
        if len(room.cid_list) < cfg.client_per_room: #room에 빈자리가 있을때
            room.add(cid)
            tag = 'G'
            msg = self.make_message(cmd='rJAccept',cid=cid,cid_dest='',rid=rid,msg='')
            self.publish_mq(msg,tag)
        else: #room에 빈자리가 없을때
            tag = 'G'
            msg = self.make_message(cmd='rJReject',cid=cid,cid_dest='',rid=rid,msg="can't enter this room")
            self.publish_mq(msg,tag)

    def on_rmsg_received(self,cidSrc,cidDest,rid,msg): #한 client(cidSrc)에서 다른 client(cidDest)로 msg 전송
        room = self.room_list[rid]
        if cidDest == -1: #room에 있는 전체 client에 msg 전송
            for i in room.cid_list:
                tag = 'G'
                msg = self.make_message(cmd='rBMsg',cid=cidSrc,cid_dest=i,rid='',msg=msg)
                self.publish_mq(msg,tag)
        else: #room에 있는 하나의 client(cidDest)에 msg 전송
            tag = 'G'
            msg = self.make_message(cmd='rBMsg',cid=cidSrc,cid_dest=cidDest,rid='',msg=msg)
            self.publish_mq(msg,tag)

    def on_rexit_received(self,cid,rid): #room(rid)에서 client(cid)를 제거
        room = self.room_list[rid]
        room.delete(cid)
        tag = 'G'
        msg = self.make_message(cmd='rBye',cid=cid,cid_dest='',rid=rid,msg='')
        self.publish_mq(msg,tag)

    def get_empty_room(self,maxroom): #room list에 있는 empty room을 maxroom개 만큼 return
        emptylist = []
        roomcount = maxroom
        for r in self.room_list:
            if roomcount == 0:
                return emptylist
            else:
                if len(r.cid_list) < cfg.client_per_room:
                    emptylist.append(r)
                    roomcount = roomcount - 1
                else:
                    continue
        return emptylist

    # For future use
    def on_client_received(self, client, message):
        pass

if __name__ == '__main__':
    server = RoomServer()
    server.run()