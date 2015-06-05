# generic python libraries
import json
import uuid
import zlib
import ctypes

# python packages
from enum import Enum, unique

# hshammog
from core import logger


@unique
class ZoneMemberState(Enum):
    ''' ZoneMemberState '''
    inner = 0
    outer = 1
    perimeter = 2
    off = 3
    invalid = 4


class ZoneMember:
    ''' ZoneMember '''
    def __init__(self, client_id, x, y, state=ZoneMemberState.invalid):
        self.client_id = client_id
        self.x = x
        self.y = y
        self.state = state

    def update(self, delta_x, delta_y):
        self.x += delta_x
        self.y += delta_y

    def in_grid(self, grid):
        lt_x = grid['lt_x']
        lt_y = grid['lt_y']
        rb_x = grid['rb_x']
        rb_y = grid['rb_y']
        border_width = grid['border_width']
        global_size = grid['global_size']

        inner_lt_x = lt_x + border_width
        inner_lt_y = lt_y + border_width
        inner_rb_x = rb_x - border_width
        inner_rb_y = rb_y - border_width
        outer_lt_x = max(0, lt_x - border_width)
        outer_lt_y = max(0, lt_y - border_width)
        outer_rb_x = min(global_size - 1, rb_x + border_width)
        outer_rb_y = min(global_size - 1, rb_y + border_width)

        if inner_lt_x <= self.x <= inner_rb_x and \
                inner_lt_y <= self.y <= inner_rb_y:
            self.state = ZoneMemberState.inner
        elif lt_x <= self.x <= rb_x and lt_y <= self.y <= rb_y:
            self.state = ZoneMemberState.perimeter
        elif outer_lt_x <= self.x <= outer_rb_x and \
                outer_lt_y <= self.y <= outer_rb_y:
            self.state = ZoneMemberState.outer
        else:
            self.state = ZoneMemberState.off

    def is_at_inner_zone(self):
        return self.state == ZoneMemberState.inner

    def is_at_perimeter_zone(self):
        return self.state == ZoneMemberState.perimeter

    def is_at_outer_zone(self):
        return self.state == ZoneMemberState.outer

    def is_out(self):
        return (self.state == ZoneMemberState.off or
                self.state == ZoneMemberState.invalid)


class Zone:
    ''' Zone '''

    def __init__(self, lt_x, lt_y, rb_x, rb_y,
                 max_members, border_width, global_size, server_id):
        # use random uuid as a new zone id
        new_hash = hash(zlib.adler32(uuid.uuid4().hex))
        self.id = 'zone-%x' % ctypes.c_uint(new_hash).value

        # initial setting
        self.grid = {
            'lt_x': lt_x,
            'lt_y': lt_y,
            'rb_x': rb_x,
            'rb_y': rb_y,
            'border_width': border_width,
            'global_size': global_size
        }
        self.max_members = max_members
        self.members = {}
        self.handover_buffer = {}
        self.server_id = server_id

        self.parent_zone = ""

        logger.info('zone %s created' % self.id)

    def __del__(self):
        logger.info('zone %s deleted' % self.id)

    def get_id(self):
        return self.id

    def get_member(self, member_id):
        return self.members.get(member_id)

    def get_all_members(self):
        members_obj = []

        for mid, member in self.members.iteritems():
            member_obj = {
                'client_id': member.client_id,
                'client_x': member.x,
                'client_y': member.y
            }

            members_obj.append(member_obj)

        return members_obj

    def update_member(self, member_id, delta_x, delta_y):
        if member_id in self.members.keys():
            member = self.get_member(member_id)

            was_at_inner_zone = member.is_at_inner_zone()

            member.update(delta_x, delta_y)
            member.in_grid(self.grid)

            is_at_perimeter_zone = member.is_at_perimeter_zone()

            if member.is_out():
                del self.members[member_id]
            else:
                self.members[member_id] = member
  
            return (member, was_at_inner_zone and is_at_perimeter_zone)
        else:
            return (None, False)

    def add_member(self, member_id, x, y):
        member = ZoneMember(member_id, x, y)
        member.in_grid(self.grid)

        if not member.is_out():
            self.members[member_id] = member
            return True
        else:
            return False

    def drop_member(self, member_id):
        if member_id in self.members.keys():
            del self.members[member_id]
            return True
        else:
            return False

    def count(self):
        return len(self.members)

    def is_empty(self):
        return self.count() == 0

    def foreach(self, func):
        for member_id, value in self.members.iteritems():
            func(member_id, value)

    def update_parent(self, parent_id):
        self.parent_zone = parent_id

    def dumps(self):
        zone_obj = {
            'zone_id': self.id,
            'width': self.grid['rb_x'] - self.grid['lt_x'] + 1,
            'height': self.grid['rb_y'] - self.grid['lt_y'] + 1,
            'lt_x': self.grid['lt_x'],
            'lt_y': self.grid['lt_y'],
            'rb_x': self.grid['rb_x'],
            'rb_y': self.grid['rb_y'],
            'clients': {
                'num_client': len(self.members),
                'list_client': []
            },
            'server_id': self.server_id,
            'parent_zone': self.parent_zone
        }

        for mid, member in self.members.iteritems():
            member_data = {
                'client_id': member.client_id,
                'client_x': member.x,
                'client_y': member.y
            }

            zone_obj['clients']['list_client'].append(member_data)

        return json.dumps(zone_obj)

    def horizontal_split(self):
        rb_y1 = (self.grid['rb_y'] + self.grid['lt_y'])/2
        lt_y2 = rb_y1 + 1

        zone1 = Zone(self.grid['lt_x'], self.grid['lt_y'],
                     self.grid['rb_x'], rb_y1,
                     self.max_members, self.grid['border_width'],
                     self.grid['global_size'])

        zone2 = Zone(self.grid['lt_x'], lt_y2,
                     self.grid['rb_x'], self.grid['rb_y'],
                     self.max_members, self.grid['border_width'],
                     self.grid['global_size'])

        return [zone1, zone2]

    def vertical_split(self):
        rb_x1 = (zone['rb_x'] + zone['lt_x'])/2
        lt_x2 = rb_x1 + 1

        zone1 = Zone(self.grid['lt_x'], self.grid['lt_y'],
                     rb_x1, self.grid['rb_y'],
                     self.max_members, self.grid['border_width'],
                     self.grid['global_size'])
        zone2 = Zone(lt_x2, self.grid['lt_y'],
                     self.grid['rb_x'], self.grid['rb_y'],
                     self.max_members, self.grid['border_width'],
                     self.grid['global_size'])

        return [zone1, zone2]
