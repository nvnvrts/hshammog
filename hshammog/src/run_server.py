import argparse


parser = argparse.ArgumentParser(description='Activate Server')
parser.add_argument('app_mode',
                    choices=('echo', 'roomlobby'),
                    default='echo')
parser.add_argument('server_mode',
                    choices=('mq', 'server', 'client'),
                    default='mq')
args = parser.parse_args()

print args.app_mode, args.server_mode
# TODO:
