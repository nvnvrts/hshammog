from conf import cfg


def run(server_mode):
    server = None
    print 'TODO: field_manager', server_mode
    if server_mode == 'mq':
        pass
    elif server_mode == 'gateway':
        pass
    elif server_mode == 'server':
        pass
    elif server_mode == 'monitor':
        from field.monitor import Monitor
        Monitor(cfg.ws_port, cfg.zk_servers[0], cfg.zk_path).run()
