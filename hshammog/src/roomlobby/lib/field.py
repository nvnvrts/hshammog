# -*- coding: utf-8 -*-


class Room:
    """ Room """

    def __init__(self, rid, nmaxplayer):
        self.rid = rid
        self.nmaxplayer = nmaxplayer
        self.players = []

    def add_player(self, cid):
        if len(self.players) < self.nmaxplayer:
            self.players.append(cid)
            return None
        else:
            return 'player join failed: room(%d) is full' % self.rid

    def delete_player(self, cid):
        if cid in self.players:
            self.players.remove(cid)
            return None
        else:
            return ('player exit failed: room(%d) does not have client(%d)' %
                    (self.rid, cid))
