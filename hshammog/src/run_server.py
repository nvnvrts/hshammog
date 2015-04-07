import argparse

from echo import mqzmq
from echo import server_zmq
from echo import client_zmq


parser = argparse.ArgumentParser(description='Activate Server')
parser.add_argument('app_mode',
                    choices=('echo', 'roomlobby'),
                    default='echo')
parser.add_argument('server_mode',
                    choices=('mq-zmq', 'mq-server', 'mq-client'),
                    default='mq-zmq')
args = parser.parse_args()

if args.app_mode == 'echo' and args.server_mode == 'mq-zmq':
    mqzmq.run()
if args.app_mode == 'echo' and args.server_mode == 'mq-server':
    server_zmq.run()
if args.app_mode == 'echo' and args.server_mode == 'mq-client':
    client_zmq.run()
