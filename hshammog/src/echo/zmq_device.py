__author__ = 'wonjin'

import zmq

def main():
    try:
        # Create a zmq Context
        context = zmq.Context(1)

        # Socket facing Clients
        frontend = context.socket(zmq.XREP)
        frontend.bind("tcp://*:5559")

        # Socket facing Services
        backend = context.socket(zmq.XREQ)
        backend.bind("tcp://*:5560")

        zmq.device(zmq.QUEUE, frontend, backend)

    except Exception, e:
        print e
        print "zmq_device error"
    finally:
        pass
        frontend.close()
        backend.close()
        context.term()

if __name__ == '__main__':
    main()
