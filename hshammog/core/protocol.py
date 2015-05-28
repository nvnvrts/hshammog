__all__ = ['Message', 'MessageHelper']

import json


class Message:
    ''' Message '''

    def __init__(self, cmd=None, cid=None, ciddest=None, nmaxroom=None,
                 msg=None, rid=None, roomlist=None, timestamp=-1):
        self.cmd = cmd
        self.cid = cid
        self.ciddest = ciddest
        self.nmaxroom = nmaxroom
        self.msg = msg
        self.rid = rid
        self.roomlist = roomlist
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
        (lambda message: {'cmd': 'rError', 'eMsg': message.msg})
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
                                 msg=message['eMsg']))
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
