from conf import cfg


def run(server_mode):
    server = None

    if server_mode == 'mq':
        from field.pubsubmq import PubSubMQ
        PubSubMQ(cfg.mq_outport, cfg.mq_inport).run()
    elif server_mode == 'gateway':
        from field.gateway import Gateway
        Gateway(cfg.gw_port, cfg.ws_port,
                cfg.mq_servers[0], cfg.mq_outport, cfg.mq_inport,
                cfg.zk_servers[0], cfg.zk_path).run()
    elif server_mode == 'server':
        from field.zoneserver import ZoneServer
        ZoneServer(cfg.mq_servers[0], cfg.mq_outport,
                   cfg.mq_inport, cfg.zk_servers[0], cfg.zk_path).run()
    elif server_mode == 'monitor':
        from field.monitor import Monitor
        Monitor(cfg.mon_port, cfg.mq_servers[0], cfg.mq_outport,
                cfg.mq_inport, cfg.zk_servers[0], cfg.zk_path).run()
