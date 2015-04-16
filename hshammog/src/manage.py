# -*- coding: utf-8 -*-
import argparse

from core import cfg


def config(args):
    if args.config_var == 'all':
        for key in cfg.keys():
            print key, ': ', cfg[key]
    else:
        if args.config_var in cfg.keys():
            print args.config_var, ': ', cfg[args.config_var]
        else:
            print 'given key(', args.config_var, ') does not exist in config'


def run(args):
    if args.app_mode == 'echo':
        pass
    elif args.app_mode == 'roomlobby':
        from roomlobby.manager import run
        run(args.server_mode)

if __name__ == '__main__':
    operations = {
        'config': config,
        'run': run
    }

    parser = argparse.ArgumentParser(
        description=('Manage for High Scalability/'
                     'High Availability MMOG Service'))
    subparsers = parser.add_subparsers(help='management commands',
                                       dest='command')

    subparser_config = subparsers.add_parser('config',
                                             help='print configuration')
    subparser_config.add_argument('config_var',
                                  type=str,
                                  default='all')

    subparser_run = subparsers.add_parser('run',
                                          help='run server')
    subparser_run.add_argument('app_mode',
                               choices=('echo', 'roomlobby'),
                               default='echo')
    subparser_run.add_argument('server_mode',
                               choices=('mq', 'server', 'client', 'gateway'),
                               default='mq')

    args = parser.parse_args()

    if args.command == 'config':
        config(args)
    else:
        run(args)
