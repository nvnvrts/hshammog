__all__ = ['Error', 'ServerError', 'MessageParseError', 'GatewayError',
           'RoomServerError', 'RoomServerNotFoundError']


class Error(Exception):
    ''' Base class for exceptions '''
    pass


class ServerError(Error):
    ''' Exception raised for errors in Server '''
    pass


class MessageParseError(ServerError):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class GatewayError(ServerError):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class RoomServerError(ServerError):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)


class RoomServerNotFoundError(ServerError):
    def __init__(self, rid):
        self.rid = rid
