from twisted.internet import protocol, reactor
import txzmq


class AbstractClient(protocol.Protocol):
    """ Abstract Client """

    def __init__(self, handler):
        self.handler = handler

    def connectionMade(self):
        self.handler.on_client_connect(self)

    def connectionLost(self, reason):
        self.handler.on_client_close(self, reason)

    def dataReceived(self, data):
        message = data
        self.handler.on_client_received(self, message)

    def send(self, message):
        data = message
        self.transport.write(data)


class AbstractFactory(protocol.ClientFactory):
    """ Abstract Factory """

    def __init__(self, handler):
        self.handler = handler

    def buildProtocol(self, addr):
        return AbstractClient(self.handler)


class AbstractServer():
    """ Abstract Server """

    def __init__(self):
        self.factory = txzmq.ZmqFactory()

    def listen_client(self, port):
        reactor.listenTCP(port, AbstractFactory(self))

    def on_client_connect(self, client):
        pass

    def on_client_close(self, client, reason):
        pass

    def on_client_received(self, client, message):
        pass

    def connect_mq(self, host, pub_port, sub_port, tag):
        # publish
        mq_pub_addr = 'tcp://%s:%d' % (host, pub_port)
        mq_pub_endpoint = txzmq.ZmqEndpoint('connect', mq_pub_addr)
        self.mq_pub = txzmq.ZmqPubConnection(self.factory, mq_pub_endpoint)

        # subscribe
        mq_sub_addr = 'tcp://%s:%d' % (host, sub_port)
        mq_sub_endpoint = txzmq.ZmqEndpoint('connect', mq_sub_addr)
        self.mq_sub = txzmq.ZmqSubConnection(self.factory, mq_sub_endpoint)
        self.mq_sub.subscribe(tag)

        def on_sub(message, tag):
            self.on_mq_received(message)
        self.mq_sub.gotMessage = on_sub

    def publish_mq(self, message, tag):
        if self.mq_pub:
            self.mq_pub.publish(message, tag)
        else:
            pass

    def on_mq_received(self, message):
        pass

    def run(self):
        reactor.run()
