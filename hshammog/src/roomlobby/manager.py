from core import cfg
from roomlobby.pubsubmq import PubSubMQ


def run(server):
    if server == 'mq':
        PubSubMQ(cfg.mq_outport, cfg.mq_inport).run()
