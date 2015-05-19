from net.grinder.script import Test
from net.grinder.script.Grinder import grinder
from org.json import JSONObject

import struct
import socket
 
class TestRunner:
    def __init__(self):
        grinder.statistics.delayReports=True
 
    def client_connect(self) :
        try:
            clientsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            clientsock.connect(('192.168.0.5', 5800))
            l_onoff = 1
            l_linger = 0
            clientsock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', l_onoff, l_linger))

            return clientsock
        except:
            print "client connect error\n"

    def send_message(self, clientsock, msg):
        try:
            clientsock.send(msg+"\n")
            
            ret_msg = clientsock.recv(4096)
            while (JSONObject(ret_msg).getString("cmd") == "rBMsg" and (JSONObject(ret_msg).getString("cIdDest") != JSONObject(ret_msg).getString("cIdSrc"))) :
                ret_msg = clientsock.recv(4096)
                
            return ret_msg
        except:
            print "send message error\n"

    def sConnect_test(self, clientsock):
        try:
            msg = self.send_message(clientsock,'{ "cmd": "sConnect" }')
            return msg
        except:
            print "sConnect error\n"

    def sExit_test(self, clientsock, cid):
        try:
            msg_dic = {}
            msg_dic["cmd"] = "sExit"
            msg_dic["cId"] = cid
            msg_json = JSONObject(msg_dic)

            msg = self.send_message(clientsock, str(msg_json))
            return msg
        except:
            print "sExit error\n"
 
    def rLookup_test(self, clientsock, cid, n) :
        try:
            msg_dic = {}
            
            msg_dic["cmd"] = "rLookup"
            msg_dic["cId"] = cid
            msg_dic["nMaxRoom"] = n
            msg_json = JSONObject(msg_dic)
            
            msg = self.send_message(clientsock, str(msg_json))
            return msg
        except:
            print "rLookup error\n"
 
    def rJoin_test(self, clientsock, cid, rid):
        try:
            msg_dic = {}
            msg_dic["cmd"] = "rJoin"
            msg_dic["cId"] = cid
            msg_dic["rId"] = rid
            msg_json = JSONObject(msg_dic)

            msg = self.send_message(clientsock, str(msg_json))
            return msg
        except:
            print "rJoin error\n"
 
    def rMsg_test(self, clientsock, cidsrc, ciddest, rid, msg):
        try:
            msg_dic = {}
            msg_dic["cmd"] = "rMsg"
            msg_dic["cIdSrc"] = cidsrc
            msg_dic["cIdDest"] = ciddest
            msg_dic["rId"] = rid
            msg_dic["msg"] = msg
            msg_json = JSONObject(msg_dic)

            msg = self.send_message(clientsock, str(msg_json))
            return msg
        except:
            print "rMsg error\n"
 
    def rExit_test(self, clientsock, cid, rid):
        try:
            msg_dic = {}
            msg_dic["cmd"] = "rExit"
            msg_dic["cId"] = cid
            msg_dic["rId"] = rid
            msg_json = JSONObject(msg_dic)

            msg = self.send_message(clientsock, str(msg_json))
            return msg
        except:
            print "rExit error\n"
 
    # test method        
    def __call__(self):
        try :
            # connect client
            clientsock = self.client_connect()

            # sConnect
            msg = self.sConnect_test(clientsock)
            if len(msg) == 0:
                grinder.logger.error("msg length==0")
            elif JSONObject(msg).getString("cmd") != "sAccept":
                grinder.logger.error("not accepted")
            else :
                print 'connect success!\n'

            cid = JSONObject(msg).getString("cId")

            loop = 0
            while(loop<=10):
                # rLookup
                msg = self.rLookup_test(clientsock, cid, 5)
                msg_json = JSONObject(msg)
                roomlist_json = msg_json.getJSONObject("roomList")
                rid = roomlist_json.names().getString(0)
                
                # rJoin
                msg = self.rJoin_test(clientsock, cid, rid)
                
                # rMsg
                for i in range(100):
                    cidsrc = cid
                    ciddest = ""
                    msg = "message test"
                    msg = self.rMsg_test(clientsock, cidsrc, ciddest, rid, msg)
                
                # rExit
                msg = self.rExit_test(clientsock, cid, rid)
                
                loop = loop + 1
            
            # sExit
            msg = self.sExit_test(clientsock, cid)
            
            print "done!"

        except socket.error, e:
            grinder.logger.error(str(e))
            grinder.statistics.forLastTest.success = 0
        finally:
            clientsock.close()
        #grinder.sleep(200)
 
Test(1, "NNI-LookupServer Test").record(TestRunner.send_message)