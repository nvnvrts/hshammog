__all__ = ['Message', 'MessageHelper']

import json


class Message:
    ''' Message '''

    def __init__(self, cmd=None, cid=None, ciddest=None, nmaxroom=None,
                 msg=None, rid=None, roomlist=None, clientlist=None,
                 x=None, y=None, width=None, height=None,
                 zid1=None, zid2=None, timestamp=-1):
        self.cmd = cmd
        self.cid = cid
        self.ciddest = ciddest
        self.nmaxroom = nmaxroom
        self.msg = msg
        self.rid = rid
        self.roomlist = roomlist
        self.clientlist = clientlist
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.zid1 = zid1
        self.zid2 = zid2
        self.timestamp = timestamp

    def dumps(self):
        return MessageHelper.dump_message(self)


class MessageHelper(object):
    ''' Message Helper Class '''

    encode_functions = {
        'sConnect':
        (lambda message: {'cmd': 'sConnect'}),
        'sAccept':
        (lambda message: {'cmd': 'sAccept', 'cId': message.cid}),
        'sReject':
        (lambda message: {'cmd': 'sReject'}),
        'sExit':
        (lambda message: {'cmd': 'sExit', 'cId': message.cid}),
        'sBye':
        (lambda message: {'cmd': 'sBye', 'cId': message.cid}),
        'sError':
        (lambda message: {'cmd': 'sError', 'eMsg': message.msg}),
        'rLookup':
        (lambda message: {'cmd': 'rLookup', 'cId': message.cid,
                          'nMaxRoom': message.nmaxroom}),
        'rList':
        (lambda message: {'cmd': 'rList', 'cId': message.cid,
                          'roomList': message.roomlist}),
        'rJoin':
        (lambda message: {'cmd': 'rJoin', 'cId': message.cid,
                          'rId': message.rid}),
        'rJAccept':
        (lambda message: {'cmd': 'rJAccept', 'cId': message.cid,
                          'rId': message.rid}),
        'rJReject':
        (lambda message: {'cmd': 'rJReject', 'cId': message.cid,
                          'rId': message.rid, 'msg': message.msg}),
        'rMsg':
        (lambda message: {'cmd': 'rMsg', 'cIdSrc': message.cid,
                          'cIdDest': message.ciddest, 'rId': message.rid,
                          'msg': message.msg}),
        'rBMsg':
        (lambda message: {'cmd': 'rBMsg', 'cIdSrc': message.cid,
                          'cIdDest': message.ciddest, 'rId': message.rid,
                          'msg': message.msg}),
        'rExit':
        (lambda message: {'cmd': 'rExit', 'cId': message.cid,
                          'rId': message.rid}),
        'rBye':
        (lambda message: {'cmd': 'rBye', 'cId': message.cid,
                          'rId': message.rid}),
        'rExitAll':
        (lambda message: {'cmd': 'rExitAll', 'cId': message.cid}),
        'rError':
        (lambda message: {'cmd': 'rError', 'eMsg': message.msg}),
        'fStart':
        (lambda message: {'cmd': 'fStart', 'cId': message.cid,
                          'xCoordinate': message.x,
                          'yCoordinate': message.y}),
        'fMove':
        (lambda message: {'cmd': 'fMove', 'cId': message.cid,
                          'xDelta': message.x, 'yDelta': message.y}),
        'fLookup':
        (lambda message: {'cmd': 'fLookup', 'cId': message.cid}),
        'fLoc':
        (lambda message: {'cmd': 'fLoc', 'cId': message.cid,
                          'xCoordinate': message.x,
                          'yCoordinate': message.y}),
        'fList':
        (lambda message: {'cmd': 'fList', 'cId': message.cid,
                          'clientList': message.clientlist,
                          'zId': message.zid1,
                          'zone_lt_x': message.x,
                          'zone_lt_y': message.y,
                          'zone_width': message.width,
                          'zone_height': message.height,
                          'clientList': message.clientlist}),
        'fMsg':
        (lambda message: {'cmd': 'fMsg', 'cId': message.cid,
                          'msg': message.msg}),
        'fBMsg':
        (lambda message: {'cmd': 'fBMsg', 'cIdSrc': message.cid,
                          'cIdDest': message.ciddest, 'msg': message.msg}),
        'fError':
        (lambda message: {'cmd': 'fError', 'cId': message.cid,
                          'eMsg': message.msg}),
        'fExit':
        (lambda message: {'cmd': 'fExit', 'cId': message.cid}),
        'zAdd':
        (lambda message: {'cmd': 'zAdd',
                          'lt_x': message.x, 'lt_y': message.y,
                          'width': message.width, 'height': message.height}),
        'zVSplit':
        (lambda message: {'cmd': 'zVSplit', 'zId': message.zid1}),
        'zHSplit':
        (lambda message: {'cmd': 'zHSplit', 'zId': message.zid1}),
        'zDestroy':
        (lambda message: {'cmd': 'zDestroy', 'zId': message.zid1}),
        'zMerge':
        (lambda message: {'cmd': 'zMerge', 'zId1': message.zid1,
                          'zId2': message.zid2})
    }

    decode_functions = {
        'sConnect':
        (lambda message: Message(cmd='sConnect')),
        'sAccept':
        (lambda message: Message(cmd='sAccept', cid=message['cId'])),
        'sReject':
        (lambda message: Message(cmd='sReject')),
        'sExit':
        (lambda message: Message(cmd='sExit', cid=message['cId'])),
        'sBye':
        (lambda message: Message(cmd='sBye', cid=message['cId'])),
        'sError':
        (lambda message: Message(cmd='sError', msg=message['eMsg'])),
        'rLookup':
        (lambda message: Message(cmd='rLookup', cid=message['cId'],
                                 nmaxroom=message['nMaxRoom'])),
        'rList':
        (lambda message: Message(cmd='rList', cid=message['cId'],
                                 roomlist=message['roomList'])),
        'rJoin':
        (lambda message: Message(cmd='rJoin', cid=message['cId'],
                                 rid=message['rId'])),
        'rJAccept':
        (lambda message: Message(cmd='rJAccept', cid=message['cId'],
                                 rid=message['rId'])),
        'rJReject':
        (lambda message: Message(cmd='rJReject', cid=message['cId'],
                                 rid=message['rId'], msg=message['msg'])),
        'rMsg':
        (lambda message: Message(cmd='rMsg', cid=message['cIdSrc'],
                                 ciddest=message['cIdDest'],
                                 rid=message['rId'], msg=message['msg'])),
        'rBMsg':
        (lambda message: Message(cmd='rBMsg', cid=message['cIdSrc'],
                                 ciddest=message['cIdDest'],
                                 rid=message['rId'],  msg=message['msg'])),
        'rExit':
        (lambda message: Message(cmd='rExit', cid=message['cId'],
                                 rid=message['rId'])),
        'rBye':
        (lambda message: Message(cmd='rBye', cid=message['cId'],
                                 rid=message['rId'])),
        'rExitAll':
        (lambda message: Message(cmd='rExitAll', cid=message['cId'])),
        'rError':
        (lambda message: Message(cmd='rError', cid=message['cId'],
                                 msg=message['eMsg'])),
        'fStart':
        (lambda message: Message(cmd='fStart', cid=message['cId'],
                                 x=message['xCoordinate'],
                                 y=message['yCoordinate'])),
        'fMove':
        (lambda message: Message(cmd='fMove', cid=message['cId'],
                                 x=message['xDelta'], y=message['yDelta'])),
        'fLookup':
        (lambda message: Message(cmd='fLookup', cid=message['cId'])),
        'fLoc':
        (lambda message: Message(cmd='fLoc', cid=message['cId'],
                                 x=message['xCoordinate'],
                                 y=message['yCoordinate'])),
        'fList':
        (lambda message: Message(cmd='fList', cid=message['cId'],
                                 clientlist=message['clientList'],
                                 zid1=message['zId'],
                                 x=message['zone_lt_x'],
                                 y=message['zone_lt_y'],
                                 width=message['zone_width'],
                                 height=message['zone_height'])),
        'fMsg':
        (lambda message: Message(cmd='fMsg', cid=message['cId'],
                                 msg=message['msg'])),
        'fBMsg':
        (lambda message: Message(cmd='fBMsg', cid=message['cIdSrc'],
                                 ciddest=message['cIdDest'],
                                 msg=message['msg'])),
        'fError':
        (lambda message: Message(cmd='fError', cid=message['cId'],
                                 msg=message['eMsg'])),
        'fExit':
        (lambda message: Message(cmd='fExit', cid=message['cId'])),
        'zAdd':
        (lambda message: Message(cmd='zAdd',
                                 x=message['lt_x'],
                                 y=message['lt_y'],
                                 width=message['width'],
                                 height=message['height'])),
        'zVSplit':
        (lambda message: Message(cmd='zVSplit',
                                 zid1=message['zId'])),
        'zHSplit':
        (lambda message: Message(cmd='zHSplit',
                                 zid1=message['zId'])),
        'zDestroy':
        (lambda message: Message(cmd='zDestroy',
                                 zid1=message['zId'])),
        'zMerge':
        (lambda message: Message(cmd='zMerge',
                                 zid1=message['zId1'],
                                 zid2=message['zId2']))
    }

    @staticmethod
    def load_message(data):
        ''' load message '''
        # load json object from string
        obj = json.loads(data)

        # decode object to message
        try:
            return MessageHelper.decode_functions[(obj['cmd'])](obj)
        except Exception as e:
            return Message(cmd='sError', msg=e.__str__())

    @staticmethod
    def dump_message(message, timestamp=None):
        # get json object from message
        obj = MessageHelper.encode_functions[message.cmd](message)

        # dumps json object to data
        try:
            return json.dumps(obj)
        except Exception as e:
            return json.dumps(
                MessageHelper.encode_functions['sError'](
                    Message(cmd='sError', msg=e.__str__())))
