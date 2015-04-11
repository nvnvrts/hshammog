import argparse


def config(args):
    print args.config_var


def run(args):
    print args.app_mode, args.server_mode


operations = {
    'config': config,
    'run': run
}

parser = argparse.ArgumentParser(
    description=('Manage for High Scalability/High Availability MMOG Service'))
subparsers = parser.add_subparsers(help='management commands', dest='command')

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
                           choices=('mq', 'server', 'client'),
                           default='mq')

args = parser.parse_args()
operations[args.command](args)

# TODO:
