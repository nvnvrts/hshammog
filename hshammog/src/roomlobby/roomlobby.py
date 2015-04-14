from config import  Config
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

class RoomServer():

    def __init__(self):
        self.room_list = []

    def rid_to_room(self,rid): #rid로 room instance 찾아주는 함수
        for i in range(len(self.room_list) - 1)
            if self.room_list[i].rid == rid:
                return self.room_list[i]
            else:
                continue

    def rjoin(self,cid,rid):
        room = self.rid_to_room(self,rid)
        if len(room.cid_list) == client_per_room


