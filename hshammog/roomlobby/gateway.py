# generic python libraries
import random
import psutil
import json

# python packages
from kazoo.exceptions import NoNodeError  # kazoo

# hshammog
from core import logger
from core.exceptions import *
from core.protocol import *
from core.server import AbstractServer


class Gateway(AbstractServer):
    '''
    Gateway
    '''

    def __init__(self,
                 client_tcp_port, client_websocket_port,
                 mq_host, mq_pub_port, mq_sub_port,
                 zk_hosts, zk_path):
        AbstractServer.__init__(self, 'gateway', zk_hosts, zk_path)

        logger.info('gateway %s initializing...' % self.id)

        # save given configurations
        self.client_tcp_port = client_tcp_port
        self.client_websocket_port = client_websocket_port
        self.mq_host = mq_host
        self.mq_pub_port = mq_pub_port
        self.mq_sub_port = mq_sub_port
        self.zk_hosts = zk_hosts
        self.zk_path = zk_path

        # mq message handlers
        self.mq_handlers = {
            'rJAccept': self.on_mq_r_j_accept,
            'rJReject': self.on_mq_r_j_reject,
            'rBMsg': self.on_mq_r_b_msg,
            'rBye': self.on_mq_r_bye,
        }

        # client message handlers
        self.client_handlers = {
            'sConnect': self.on_client_s_connect,
            'rLookup': self.on_client_r_lookup,
            'rJoin': self.on_client_r_join,
            'rMsg': self.on_client_r_msg,
            'rExit': self.on_client_r_exit,
            'sExit': self.on_client_s_exit,
            'sError': self.on_client_s_error,
        }

        # initialize client dictionary
        self.clients = {}

        # cache for mapping room id to room server id
        self.server_id_cache = {}

        logger.info('gateway %s initialized.' % self.id)

    def update_zk_node_data(self):
        path = self.zk_gateway_servers_path + self.id
        data = {
            'cpu_usage': psutil.cpu_percent(interval=None, percpu=True),
            'mem_usage': psutil.virtual_memory().percent,
            'num_clients': len(self.clients)
        }

        # set node data
        self.zk_client.set(path, json.dumps(data))

    def get_zk_roomserver(self, rid):
        server_id = self.server_id_cache.get(rid)
        if not server_id:
            path = self.zk_room_rooms_path + rid

            try:
                data, stat = self.zk_client.get(path)
            except NoNodeError:
                raise RoomServerNotFoundError(rid)

            room_data = json.loads(data)
            server_id = room_data['server_id']
            self.server_id_cache[rid] = server_id

        return server_id

    def on_zk_roomserver_added(self, roomservers):
        logger.info('roomservers added... %s' % roomservers)

    def on_zk_roomserver_removed(self, roomservers):
        logger.info('roomservers removed... %s' % roomservers)

        for roomserver in roomservers:
            for rid in self.server_id_cache.keys():
                server_id = self.server_id_cache.get(rid)
                if server_id == roomserver:
                    del self.server_id_cache[rid]

    def pub_message_to_mq(self, tag, message):
        data = '%s|%s|%s' % (self.id, message.dumps(), message.timestamp)

        logger.debug('PUB %s %s' % (tag, data))
        self.publish_mq(str(tag), data)

    def on_mq_data_received(self, tag, data):
        logger.debug('SUB %s %s' % (tag, data))

        # parse message from mq
        server_id, payload, timestamp = data.split('|', 2)
        message = MessageHelper.load_message(payload)
        message.timestamp = int(timestamp)

        # invoke mq message handler
        self.mq_handlers[message.cmd](message)

    def on_mq_r_j_accept(self, message):
        client = self.clients.get(message.cid)

        if client:
            self.send_message_to_client(client, message, message.timestamp)
        else:
            pass

    def on_mq_r_j_reject(self, message):
        client = self.clients.get(message.cid)

        if client:
            self.send_message_to_client(client, message, message.timestamp)
        else:
            pass

    def on_mq_r_b_msg(self, message):
        client = self.clients.get(message.ciddest)

        if client is not None and message.ciddest == message.cid:
            self.send_message_to_client(client, message, message.timestamp)
        elif client is not None:
            #TODO: removing of duplicated rBMsg
            self.send_message_to_client(client, message, -1)
        else:
            pass

    def on_mq_r_bye(self, message):
        client = self.clients.get(message.cid)
        if client:
            self.send_message_to_client(client, message, message.timestamp)
        else:
            pass

    def send_message_to_client(self, client, message, timestamp):
        data = message.dumps()

        # window do not care packets
        if timestamp < 0:
            logger.debug('SND client %s %s [do not care]'
                         % (client.get_id(), data))
            client.send_data(data)
        # should be held in buffer
        elif timestamp > client.last_responsed + 1:
            logger.debug('BUFFERED %s %s [%d] lastRCV(%d) lastRESP(%d)'
                         % (client.get_id(), data, timestamp,
                            client.last_received, client.last_responsed))
            client.data_buffer[timestamp] = data

        # response immediate
        elif timestamp == client.last_responsed + 1:
            logger.debug('SND client %s %s [%d]'
                         % (client.get_id(), data, timestamp))
            client.last_responsed += 1
            client.send_data(data)

            while (client.last_responsed + 1) in client.data_buffer:
                logger.debug('BUFFERED SND client %s %s [%d]'
                             % (client.get_id(), data,
                                client.last_responsed+1))
                client.last_responsed += 1
                client.send_data(client.data_buffer[client.last_responsed])
                del client.data_buffer[client.last_responsed]

        # ignore message
        else:
            logger.debug('DUMPED DUP. SND client %s %s [%d] '
                         'lastRCV(%d) lastRESP(%d)'
                         % (client.get_id(), data, timestamp,
                            client.last_received, client.last_responsed))

    def on_client_connect(self, client):
        logger.info('new %s connected' % client.get_id())

        # add client to hash
        self.clients[client.get_id()] = client

        self.update_zk_node_data()

    def on_client_close(self, client, reason):
        logger.info('%s disconnected' % client.get_id())

        # remove client from hash
        del self.clients[client.get_id()]

        self.update_zk_node_data()

        # send message to all room servers
        self.pub_message_to_mq('roomserver-allserver',
                               Message(cmd='rExitAll', cid=client.get_id()))

    def validate_client(self, client, message):
        fetched_client = self.clients.get(message.cid)
        validation = True

        if fetched_client is None:
            self.send_message_to_client(client,
                                        Message(cmd='sError',
                                                msg='Unknown cid-%s'
                                                % message.cid),
                                        message.timestamp)
            validation = False
        elif fetched_client.get_id() != client.get_id():
            self.send_message_to_client(client,
                                        Message(cmd='sError',
                                                msg='unauthorized cid(%s)'
                                                % message.cid),
                                        message.timestamp)
            validation = False

        return validation

    def on_client_data_received(self, client, data):
        logger.debug('RCV client %s %s [%d]' % (client.get_id(), data,
                                                client.last_received + 1))

        # timestamp as received
        client.last_received += 1

        # get message from data,
        message = MessageHelper.load_message(data)
        message.timestamp = client.last_received

        # invoke client message handler
        self.client_handlers[message.cmd](client, message)

    def on_client_s_connect(self, client, message):
        self.send_message_to_client(client,
                                    Message(cmd='sAccept',
                                            cid=client.get_id()),
                                    message.timestamp)

    def on_client_r_lookup(self, client, message):
        if self.validate_client(client, message):
            client = self.clients[message.cid]

            room_list = {}

            # gather room list from zk node data
            for room_server in self.get_zk_roomservers():
                path = self.zk_room_servers_path + room_server

                try:
                    data, stat = self.zk_client.get(path)
                    for rid, values in json.loads(data)['rooms'].iteritems():
                        if values['count'] < values['max'] and \
                           len(room_list) < message.nmaxroom:
                            room_list[rid] = values['count']
                except NoNodeError:
                    pass

                if len(room_list) >= message.nmaxroom:
                    break

            self.send_message_to_client(client,
                                        Message(cmd='rList',
                                                roomlist=room_list,
                                                cid=client.get_id()),
                                        message.timestamp)

    def on_client_r_join(self, client, message):
        if self.validate_client(client, message):
            client = self.clients[message.cid]

            if message.rid == 0:
                # gateway chooses a room if rid is 0
                roomservers = self.get_zk_roomservers()
                if roomservers:
                    server_id = random.choice(roomservers)
                else:
                    self.send_message_to_client(client,
                                                Message(cmd='rJReject',
                                                        cid=message.cid,
                                                        rid=message.rid,
                                                        msg='no room servers'),
                                                message.timestamp)
                    return
            else:
                try:
                    server_id = self.get_zk_roomserver(message.rid)
                except RoomServerNotFoundError:
                    self.send_message_to_client(client,
                                                Message(cmd='rJReject',
                                                        cid=message.cid,
                                                        rid=message.rid,
                                                        msg='room %s does not '
                                                        'exist' % message.rid),
                                                message.timestamp)
                    return

                self.pub_message_to_mq(server_id, message)

    def on_client_r_msg(self, client, message):
        if self.validate_client(client, message):
            client = self.clients[message.cid]
            try:
                server_id = self.get_zk_roomserver(message.rid)
                self.pub_message_to_mq(server_id, message)
            except RoomServerNotFoundError as e:
                self.send_message_to_client(client, Message(cmd='rBye',
                                                            cid=message.cid,
                                                            rid=message.rid),
                                            message.timestamp)

    def on_client_r_exit(self, client, message):
        if self.validate_client(client, message):
            client = self.clients[message.cid]
            try:
                server_id = self.get_zk_roomserver(message.rid)
                self.pub_message_to_mq(server_id, message)
            except RoomServerNotFoundError as e:
                self.send_message_to_client(client, Message(cmd='rBye',
                                                            cid=message.cid,
                                                            rid=message.rid),
                                            message.timestamp)

    def on_client_s_exit(self, client, message):
        if self.validate_client(client, message):
            self.send_message_to_client(client, Message(cmd='sBye',
                                                        cid=client.get_id()),
                                        message.timestamp)

    def on_client_s_error(self, client, message):
        logger.error('client %s error %s' % (client.get_id(), message.msg))
        self.send_message_to_client(client, message, message.timestamp)

    def run(self):
        try:
            zk_success = self.initialize_zk()

            if zk_success is not None:
                raise GatewayError(zk_success)

            data = {
                'cpu_usage': psutil.cpu_percent(interval=None, percpu=True),
                'mem_usage': psutil.virtual_memory().percent,
                'num_clients': len(self.clients)
            }

            # zookeeper setup
            node = self.zk_client.create(path=self.zk_gateway_servers_path +
                                         self.id,
                                         value=json.dumps(data),
                                         ephemeral=True,
                                         sequence=False)

            # connect to mq as a gateway
            self.connect_mq(self.mq_host, self.mq_pub_port,
                            self.mq_sub_port, self.id)

            self.watch_zk_roomservers()

            self.listen_tcp_client(self.client_tcp_port)
            self.listen_websocket_client(self.client_websocket_port)

            self.add_timed_call(self.update_zk_node_data, 5)

            AbstractServer.run(self)

        except Exception as e:
            logger.error(str(e))

        except KeyboardInterrupt:
            logger.info('Keyboard Interrupt')

        finally:
            logger.info('Shutting down %s' % self.id)
            self.close_zk()
