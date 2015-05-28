# grinder libraries
from net.grinder.script import Test
from net.grinder.script.Grinder import grinder

# json library
from org.json import JSONObject

# generic python library
import struct
import socket
import random


class TestRunner:
    def __init__(self):
        grinder.statistics.delayReports = True

    def client_connect(self):
        try:
            clientsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            clientsock.connect(('192.168.0.5', 5800))
            l_onoff = 1
            l_linger = 0
            clientsock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,
                                  struct.pack('ii', l_onoff, l_linger))

            return clientsock
        except:
            print 'client connect error\n'

    def send_message(self, clientsock, msg):
        try:
            clientsock.send(msg+'\n')
            ret_msg = clientsock.recv(4096)
            return ret_msg
        except:
            print 'send message error\n'

    def sConnect_test(self, clientsock):
        try:
            msg_dic = {}
            msg_dic['cmd'] = 'sConnect'
            msg_json = JSONObject(msg_dic)

            msg = self.send_message(clientsock, str(msg_json))

            return msg
        except:
            print 'sConnect error\n'

    def sExit_test(self, clientsock, cid):
        try:
            msg_dic = {}
            msg_dic['cmd'] = 'sExit'
            msg_dic['cId'] = cid
            msg_json = JSONObject(msg_dic)

            msg = self.send_message(clientsock, str(msg_json))

            return msg
        except:
            print 'sExit error\n'

    def fStart_test(self, clientsock, cid):
        try:
            msg_dic = {}
            msg_dic['cmd'] = 'fStart'
            msg_dic['cId'] = cid
            msg_dic['xCoordinate'] = random.randint(0, 511)
            msg_dic['yCoordinate'] = random.randint(0, 511)
            msg_json = JSONObject(msg_dic)

            msg = self.send_message(clientsock, str(msg_json))
            return msg
        except:
            print 'fStart error\n'

    def fMove_test(self, clientsock, cid, x, y):
        try:
            msg_dic = {}
            msg_dic['cmd'] = 'fMove'
            msg_dic['cId'] = cid
            msg_dic['xDelta'] = max(min(x + random.randint(-2, 2), 511), 0) - x
            msg_dic['yDelta'] = max(min(y + random.randint(-2, 2), 511), 0) - y
            msg_json = JSONObject(msg_dic)

            msg = self.send_message(clientsock, str(msg_json))
            return msg

        except:
            print 'fMove error\n'

    # test method
    def __call__(self):
        try:
            # connect client
            clientsock = self.client_connect()

            # sConnect
            msg = self.sConnect_test(clientsock)
            if len(msg) == 0:
                grinder.logger.error('msg length==0')
            elif JSONObject(msg).getString('cmd') != 'sAccept':
                grinder.logger.error('not accepted')
            else:
                print 'connect success!\n'

            cid = JSONObject(msg).getString('cId')

            # fStart
            msg = self.fStart_test(clientsock, cid)
            msg_json = JSONObject(msg)

            x = msg_json.getInt('xCoordinate')
            y = msg_json.getInt('yCoordinate')

            for i in range(100):
                msg = self.fMove_test(clientsock, cid, x, y)
                msg_json = JSONObject(msg)

                x = msg_json.getInt('xCoordinate')
                y = msg_json.getInt('yCoordinate')

            # sExit
            msg = self.sExit_test(clientsock, cid)

            print 'done!'

        except socket.error, e:
            grinder.logger.error(str(e))
            grinder.statistics.forLastTest.success = 0
        finally:
            clientsock.close()

Test(1, 'NNI-LookupServer Test').record(TestRunner.send_message)
