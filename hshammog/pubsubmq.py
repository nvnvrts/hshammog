import mq.pubsub as pubsub


class PubSubMQ(pubsub.PubSub):
    """ PubSubMQ """

    def run(self):
        pubsub.PubSub.run(self)


if __name__ == '__main__':
    mq = PubSubMQ(5561, 5562)
    mq.run()

