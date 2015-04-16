# -*- coding: utf-8 -*-


class CGwRequest:
    """ Client-Gateway Request Container """

    def __init__(self,
                 cmd=None,
                 cid=None,
                 ciddest=None,
                 nmaxroom=None,
                 msg=None,
                 rid=None,
                 roomlist=None):
        self.cmd = cmd
        self.cid = cid
        self.ciddest = ciddest
        self.nmaxroom = nmaxroom
        self.msg = msg
        self.rid = rid
        self.roomlist = roomlist
