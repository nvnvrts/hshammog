# -*- coding: utf-8 -*-

from core import cfg
from roomlobby.pubsubmq import PubSubMQ
from roomlobby.gateway import GatewayServer
from roomlobby.roomserver import RoomServer


def run(server):
    if server == 'mq':
        PubSubMQ(cfg.mq_outport, cfg.mq_inport).run()
    elif server == 'gateway':
        GatewayServer(cfg.gw_port, cfg.mq_servers[0],
                      cfg.mq_inport, cfg.mq_outport).run()
    elif server == 'server':
        RoomServer(cfg.mq_servers[0], cfg.mq_inport, cfg.mq_outport).run()
