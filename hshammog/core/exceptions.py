class Error(Exception):
    """ Base class for exceptions """
    pass


class ServerError(Error):
    """ Exception raised for errors in Server """
    pass

class MessageParseError(ServerError):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.value)

class RoomServerNotFoundError(ServerError):
    def __init__(self, rid):
        self.rid = rid
