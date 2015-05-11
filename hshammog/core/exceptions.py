class Error(Exception):
    """ Base class for exceptions """
    pass


class ServerError(Error):
    """ Exception raised for errors in Server """
    pass


class RoomServerNotFoundError(ServerError):
    def __init__(self, rid):
        self.rid = rid
