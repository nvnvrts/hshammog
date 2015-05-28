class AbstractMQ():
    ''' AbstractMQ '''

    def __init__(self, pub_port, sub_port):
        self.pub_port = pub_port
        self.sub_port = sub_port

    def run(self):
        pass
