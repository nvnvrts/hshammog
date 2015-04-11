import json

from protocol import CGwRequest


class CGwRequestParseError(Exception):
    """ Exception occurred during Client-Gateway Request Parsing """
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.value)


def parse_from_json(json_string):
    request = json.loads(json_string)

    try:
        return decode_functions[(request['cmd'])](request)
    except Exception as e:
        raise CGwRequestParseError(e)


def parse_to_json(request):
    try:
        return json.dumps(encode_functions[request.cmd](request))
    except Exception as e:
        raise CGwRequestParseError(e)


decode_functions = {
    'sConnect': (lambda request: CGwRequest(cmd='sConnect')),
    'sAccept': (lambda request: CGwRequest(cmd='sAccept',
                                           cid=request['cId'])),
    'sReject': (lambda request: CGwRequest(cmd='sReject')),
    'sExit': (lambda request: CGwRequest(cmd='sExit',
                                         cid=request['cId'])),
    'sBye': (lambda request: CGwRequest(cmd='sBye',
                                        cid=request['cId'])),
    'sError': (lambda request: CGwRequest(cmd='sError',
                                          msg=request['eMsg'])),
    'rLookup': (lambda request: CGwRequest(cmd='rLookup',
                                           cid=request['cId'],
                                           nmaxroom=request['nMaxRoom'])),
    'rList': (lambda request: CGwRequest(cmd='rList',
                                         cid=request['cId'],
                                         roomlist=request['roomList'])),
    'rJoin': (lambda request: CGwRequest(cmd='rJoin',
                                         cid=request['cId'],
                                         rid=request['rId'])),
    'rJAccept': (lambda request: CGwRequest(cmd='rJAccept',
                                            cid=request['cId'],
                                            rid=request['rId'])),
    'rJReject': (lambda request: CGwRequest(cmd='rJReject',
                                            cid=request['cId'],
                                            rid=request['rId'])),
    'rMsg': (lambda request: CGwRequest(cmd='rMsg',
                                        cid=request['cIdSrc'],
                                        ciddest=request['cIdDest'],
                                        rid=request['rId'],
                                        msg=request['msg'])),
    'rBMsg': (lambda request: CGwRequest(cmd='rBMsg',
                                         cid=request['cIdSrc'],
                                         ciddest=request['cIdDest'],
                                         msg=request['msg'])),
    'rExit': (lambda request: CGwRequest(cmd='rExit',
                                         cid=request['cId'],
                                         rid=request['rId'])),
    'rBye': (lambda request: CGwRequest(cmd='rBye',
                                        cid=request['cId'],
                                        rid=request['rId'])),
    'rError': (lambda request: CGwRequest(cmd='rError',
                                          cid=request['cId'],
                                          msg=request['eMsg']))
}

encode_functions = {
    'sConnect': (lambda request: {'cmd': 'sConnect'}),
    'sAccept': (lambda request: {'cmd': 'sAccept',
                                 'cId': request.cid}),
    'sReject': (lambda request: {'cmd': 'sReject'}),
    'sExit': (lambda request: {'cmd': 'sExit',
                               'cId': request.cid}),
    'sBye': (lambda request: {'cmd': 'sBye',
                              'cId': request.cid}),
    'sError': (lambda request: {'cmd': 'sError',
                                'eMsg': request.msg}),
    'rLookup': (lambda request: {'cmd': 'rLookup',
                                 'cId': request.cid,
                                 'nMaxRoom': request.nmaxroom}),
    'rList': (lambda request: {'cmd': 'rList',
                               'cId': request.cid,
                               'roomList': request.roomlist}),
    'rJoin': (lambda request: {'cmd': 'rJoin',
                               'cId': request.cid,
                               'rId': request.rid}),
    'rJAccept': (lambda request: {'cmd': 'rJAccept',
                                  'cId': request.cid,
                                  'rId': request.rid}),
    'rJReject': (lambda request: {'cmd': 'rJReject',
                                  'cId': request.cid,
                                  'rId': request.rid,
                                  'msg': request.msg}),
    'rMsg': (lambda request: {'cmd': 'rMsg',
                              'cIdSrc': request.cid,
                              'cIdDest': request.ciddest,
                              'msg': request.msg}),
    'rBMsg': (lambda request: {'cmd': 'rBMsg',
                               'cIdSrc': request.cid,
                               'cIdDest': request.ciddest,
                               'msg': request.msg}),
    'rExit': (lambda request: {'cmd': 'rExit',
                               'cId': request.cid,
                               'rId': request.rid}),
    'rBye': (lambda request: {'cmd': 'rBye',
                              'cId': request.cid,
                              'rId': request.rid}),
    'rError': (lambda request: {'cmd': 'rError',
                                'eMsg': request.msg})
}
