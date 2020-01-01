import calculateRoute
import CollectData
from threading import Thread
import json
import networkx as nx
import datetime
import numpy as np
import difflib
import socket
import time
import sys
import WebSocketClient
import config
from multiprocessing import Process
from collections import OrderedDict
import graphRoute
import helper



def monitor_edge_port_events(O):
    # print "thread events"
    ws = WebSocketClient.WebSockettracker()
    track_flow = {}
    TTL = time.time()
    # print "TTL time"
    # print TTL
    while 1:
        e = ws.events.get()
        srcIP = helper.getIP_from_Mac(e[0])
        dstIP = helper.getIP_from_Mac(e[1])
        item_1 = str(e[0] + ',' + e[1])
        if (srcIP ==-1 or dstIP == -1):
            # x = str(e[0]).split(":")
            # y = str(e[1]).split(".")
            x = int(sum([int(_, 16) for _ in e[0].split(':')])/10)
            y = int(sum([int(_, 16) for _ in e[1].split(':')])/10)
            flowID = str(x)+str(y)
        else:
            x = str(srcIP).split(".")
            y = str(dstIP).split(".")
            flowID = str(x[3])+str(y[3])
        if item_1 not in track_flow:
            print (srcIP, 'is talking to', dstIP)
            print ("calculate short path for", item_1)
            track_flow[item_1] = time.time()
            # track_flow[item_2] = time.time()
            c.set_Shortest_path_FlowID(str(e[0]), str(e[1]),flowID)
            #  set_Shortest_path_QoS(e[0],e[1],d,j,l,u)
            #  set_Shortest_path_QoS_proactive(str(e[0]),str(e[1]))
            # Object_c.set_dijkstra_Utilization_QoS_proactive_passive(str(e[0]), str(e[1]),srcIP,dstIP, 1, 0, 0)
            #     calculateRoute.set_Shortest_path_QoS_Utilization(Object_c,str(e[0]),str(e[1]),srcIP,dstIP,1,0,0)
            # set_Shortest_path(str(e[0]), str(e[1]))
            # calculateRoute.set_Shortest_path_QoS_proactive_passive(Object_c, str(e[0]), str(e[1]), 1, 0, 0)

def metric_matrices(Object_d):
    while 1:
        config.data_collected.update_metric_Matrices()

def main():
    # this thread is continuously updating the the link utilization matrix
    W1 = Thread(target=metric_matrices, args=(config.data_collected,))
    W1.setDaemon(True)
    W1.start()
    print("next thread")
    print("start sleep")
    time.sleep(5)
    print("wake up")
    # for n in switch_list:
    #     c.delete_all_flows_node(n,'0')
    # # utilization_matrix = collectObject.get_Byte_link_utilization()
    # ws.start_listening()
    # c.fix_congested_flows()
    # l = data_collected.getLinkStatAdjaencyMatrix()
    # x,y,z = data_collected.get_Bytes_PortStats_Matrix()
    # Congsrc = data_collected.getMac_from_IP("10.0.0.17")
    # Congdst = data_collected.getMac_from_IP("10.0.0.18")
    # path1 = ["host:" + Congsrc, u'openflow:16', u'openflow:14', u'openflow:4', u'openflow:18', u'openflow:20', "host:" + Congdst]
    # rpath1 = list(reversed(path1))
    # c.set_congested_path(Congsrc, Congdst, path1)
    # c.set_congested_path(Congdst, Congsrc, rpath1)

    # # c.set_dijkstra_Utilization_QoS_proactive_passive(u'host:2e:5b:09:32:3c:76',u'host:56:21:bf:cd:2f:0f',3,4,5)
    # #       ls.pop
    # #    ls.insert(0, "new")
    W2 = Thread(target=monitor_edge_port_events, args=(c,))
    W2.setDaemon(True)
    W2.start()
    # print("next thread")
    # print "###################"

    # worker_2 = Thread(target=monitor_edge_port_events(), args=())
    # threads.append(worker_2)
    # worker_2.setDaemon(True)
    # worker_2.start()
    # P2 = Process(target=monitor_edge_port_events(), args=())
    # P2.start()
    # P3.join()
    # for x in threads:
    #     x.join()
    W1.join()
    W2.join()


if __name__ == '__main__':
    main()
