import uuid
import zlib
import ctypes


class Room:
    """ Room """

    def __init__(self, max_members):
        # use random uuid as a new room id
        self.id = "room-%x" % ctypes.c_uint(hash(zlib.adler32(uuid.uuid4().hex))).value

        self.max_members = max_members
        self.members = {}

        print "room %s created" % self.id

    def __del__(self):
        print "room %s deleted" % self.id

    def get_id(self):
        return self.id

    def get_member(self, member_id):
        return self.members.get(member_id)

    def join(self, member_id, value):
        self.members[member_id] = value
        print "%s joins room %s" % (member_id, self.id)

    def leave(self, member_id):
        value = self.members.get(member_id)
        if value:
            del self.members[member_id]
        print "%s leaves room %s" % (member_id, self.id)
        return value

    def count(self):
        return len(self.members)

    def is_empty(self):
        return self.count() == 0

    def is_full(self):
        return self.count() >= self.max_members

    def foreach(self, func):
        for member_id, value in self.members.iteritems():
            func(member_id, value)