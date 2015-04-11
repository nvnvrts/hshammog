class Room:
  """ Room """

  def __init__(self, rid, nmaxplayer):
    self.rid = rid
    self.nmaxplayer = nmaxplayer
    self.players = []
