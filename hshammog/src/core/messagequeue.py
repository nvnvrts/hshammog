class AbstractMQ():
    """ Message Queue Abstract Class """

    def __init__(self, out_port, in_port):
        self.out_port = out_port
        self.in_port = in_port

    def run(self):
        pass
