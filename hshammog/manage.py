# generic python libraries
import logging

# python packages
import argparse  # argparse


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
    def run_echo(server_mode):
        from echo.manager import run
        run(server_mode)

    def run_roomlobby(server_mode):
        from roomlobby.manager import run
        run(server_mode)

    def run_field(server_mode):
        from field.manager import run
        run(server_mode)

    logging_level = {
        'critical': logging.CRITICAL,
        'error': logging.ERROR,
        'warning': logging.WARNING,
        'info': logging.INFO,
        'debug': logging.DEBUG,
        'notset': logging.NOTSET
    }

    app_modes = {
        'echo': run_echo,
        'roomlobby': run_roomlobby,
        'field': run_field
    }

    logging.basicConfig(level=logging_level[args.logging])
    app_modes[args.app_mode](args.server_mode)

if __name__ == '__main__':
    operations = {
        'config': config,
        'run': run
    }

    parser = argparse.ArgumentParser(
        description=('Manage for High Scalability/'
                     'High Availability MMOG Service'),
        add_help=True)

    parser.add_argument('-l', '--logging', type=str,
                        choices=('critical', 'error', 'warning',
                                 'info', 'debug', 'notset'),
                        default='notset',
                        help='set logging level')

    subparsers = parser.add_subparsers(help='manage commands. For additional '
                                            'help, run \"manage.py {command} '
                                            '-h\"',
                                       dest='command')

    subparser_config = subparsers.add_parser('config',
                                             description='print configuration',
                                             help='print configuration.')
    subparser_config.add_argument('config_var',
                                  type=str,
                                  default='all',
                                  help='print given configuration variable. '
                                       '\"all\" prints all variables')

    subparser_run = subparsers.add_parser('run',
                                          help='run server.')
    subparser_run.add_argument('app_mode',
                               choices=('echo', 'roomlobby', 'field'),
                               default='echo',
                               help='application type')
    subparser_run.add_argument('server_mode',
                               choices=('mq', 'server', 'client',
                                        'gateway', 'monitor', 'proxy'),
                               default='mq',
                               help='server type')

    args = parser.parse_args()

    if args.command == 'config':
        config(args)
    else:
        run(args)
