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
# Print the solution src & dst
class calculateRoute:
    def __init__(self, d):
        self.paping_path_list = {}
        self.port_count = 4
        self.hosts = []
        self.switches = []
        self.routes_dij = []
        self.routes_short_path = []
        self.route_ports_db = []
        self.controllerIP = config.controllerIP
        self.graph = nx.Graph()
        self.source_agent_HOST_listenPort = 5000
    #######################################################################################################
    # all diskstra rout between two hosts
    def getDijkRoute(self, Src, Dst):
        route = nx.dijkstra_path(config.graph, Src, Dst)
        return route
    # get All short paths based on the ho count
    def getShortestPath(self, g, Src, Dst):
        routes = []
        for m in (nx.all_shortest_paths(g, source=Src, target=Dst)):
            routes.append(m)
        return routes
    def getCaditatePaths(self, srcHost, dstHost):
        path = self.getShortestPath(config.graph, srcHost, dstHost)
        return path
    #######################################################################################################
    # calculate two candidate max disjoint shortest path QoS paper 3
    def get_dissimilar_paths(self, path):
        similarity = 1
        if type(path[0]) != list:
            return None, None
        for i in range(len(path)):
            for j in range(i + 1, len(path)):
                sm = difflib.SequenceMatcher(None, path[i], path[j])
                if sm.ratio() < similarity:
                    similarity = sm.ratio()
                    canditate1 = path[i]
                    canditate2 = path[j]
        return canditate1, canditate2
    #######################################################################################################
    # Configure path on switches between src and Dst [periority is 50]
    def set_congested_path(self, SrcMAC, DstMAC, path):
        flowID = helper.createFlowID(SrcMAC,DstMAC)
        self.push_path(path, SrcMAC, DstMAC, flowID, 50)
    #######################################################################################################
    # Configure shortpath on switches based on hop count  [periority is 20]
    def set_Shortest_path(self, SrcMAC, DstMAC):
        # calculate the short path based on hope count
        SrcHost = self.gethostID_from_Mac(SrcMAC)
        DstHost = self.gethostID_from_Mac(DstMAC)
        path = self.getDijkRoute(SrcHost, DstHost)
        # assign a flow ID with periority 20 to be installed on switches
        flowID = helper.createFlowID(SrcMAC,DstMAC)
        self.push_path(path, SrcMAC, DstMAC, flowID, 20)

    def set_Shortest_path_FlowID(self, SrcMAC, DstMAC,flowID):
        SrcHost = "host:"+SrcMAC
        DstHost = "host:"+DstMAC
        path = self.getDijkRoute(SrcHost, DstHost)
        self.push_path(path, SrcMAC, DstMAC, flowID, 20)
    #######################################################################################################
    def load_balance(self, vip_ip, dstPort, srcIP, dstIP, flowID, rvflowID):
        i = 0
        single_path = 1
        tableID = '0'
        ethTypeIp = 0x800
        ipTypeTcp = 0x6
        ipTypeUdp = 0x11
        path = self.getCaditatePaths(srcIP, dstIP)
        # path_file = open("path.txt", "a+")
        if type(path[0]) != list or (dstPort == 0):
            self.push_path_port(path[0], 0, srcIP, dstIP, str(flowID), str(rvflowID), 10)
        else:
            path1, path2 = self.get_dissimilar_paths(path)
            # if dst port is -1 distinguish based on the IP address, VIP goes to one path and rest goes to the other
            # if dst port is specified push the specified destination to a path and all other to different path
            if dstPort == -1:
                if vip_ip == 1:
                    self.push_path_port(path1, 0, srcIP, dstIP, str(flowID), str(rvflowID), 10)
                else:
                    self.push_path_port(path2, 0, srcIP, dstIP, str(flowID), str(rvflowID), 20)
            # if dst port is specified push the specified destination to a path and all other to different path
            else:
                self.push_path_port(path1, 0, srcIP, dstIP, str(flowID), str(rvflowID), 10)
                x = flowID + 1000
                y = rvflowID + 1000
                self.push_path_port(path2, dstPort, srcIP, dstIP, str(x), str(y), 20)

    #######################################################################################################
    # set shortest path QoS paper 4
    # ------------------------------------------------------------------------------------------------------
    def set_Shortest_path_QoS_proactive_active(self, SrcMAC, DstMAC):
        port_path_list = []
        port_list = []
        path_list = []
        Src_IP = self.getIP_from_Mac(SrcMAC)
        SrcIP = str(Src_IP)
        Dst_IP = self.getIP_from_Mac(DstMAC)
        DstIP = str(Dst_IP)
        temp_key_1 = SrcIP + '-' + DstIP
        temp_key_2 = DstIP + '-' + SrcIP
        # print 'path-list before if', paping_path_list
        # print 'paping before if', paping_path_list.get(temp_key_1,None)
        if (self.paping_path_list.get(temp_key_1, None) == None):
            port_list, path_list = self.set_paping_path(SrcMAC, DstMAC, str(SrcIP), str(DstIP))
            port_path_list.append(port_list)
            port_path_list.append(path_list)
            self.paping_path_list.update({temp_key_1: port_path_list})
            self.paping_path_list.update({temp_key_2: port_path_list})
        else:
            port_path_list = self.paping_path_list.get(temp_key_1, None)

        string_ports = str(port_list[0]) + ' ' + str(port_list[1]) + ' ' + str(port_list[2]) + ' ' + str(port_list[3])
        paping_values = str(self.get_delay_loss_paping(SrcIP, DstIP))
        paping = paping_values.split(' ')
        avg_array_paping_temp = [paping[3], paping[8], paping[13], paping[18]]
        x = np.array(avg_array_paping_temp)
        avg_array_paping = x.astype(np.float)
        avg_array_paping = avg_array_paping.tolist()

        # [5001,5002,5003,5004] ordered array of min values for each path
        portlist_temp = [5001, 5002, 5003, 5004]
        candidate_index_port = 5001
        while (len(avg_array_paping) > 0):
            if (float(min(avg_array_paping)) != 0):
                candidate_index_temp = avg_array_paping.index(min(avg_array_paping))
                break
            else:
                zero_index = avg_array_paping.index(min(avg_array_paping))
                del avg_array_paping[zero_index]
                del portlist_temp[zero_index]
        if (len(avg_array_paping) != 0):
            candidate_index_port = portlist_temp[candidate_index_temp]
        list_1 = self.paping_path_list.get(temp_key_1, None)
        cadidate_path_index = list_1[0].index(candidate_index_port)
        candidate_path = list_1[1][cadidate_path_index]
        x = str(SrcIP).split(".")
        y = str(DstIP).split(".")
        flowID = str(x[3]) + str(y[3])
        rvflowID = str(y[3]) + str(x[3])
        priority = 40
        self.push_path(candidate_path, SrcMAC, DstMAC, flowID, priority)
        candidate_path_rev = list(reversed(candidate_path))
        self.push_path(candidate_path_rev, DstMAC, SrcMAC, rvflowID, priority)
        # p1 = getBestPath(SrcMAC,DstMAC, str(SrcIP),str(DstIP),d,j,l,u)

    def set_paping_path(self, SrcMAC, DstMAC, srcIP, dstIP):
        path_list = []
        port_list = []
        x = str(srcIP).split(".")
        y = str(dstIP).split(".")
        flowID = str(x[3]) + str(y[3])
        rvflowID = str(y[3]) + str(x[3])
        priority = 20
        paths = self.getCaditatePaths(srcIP, dstIP)
        count = 0
        # print paths
        for p in paths:
            if str(p[3]) == 'openflow:1':
                count = 5001
                port_list.append(count)
                path_list.append(p)
            elif str(p[3]) == 'openflow:2':
                count = 5002
                port_list.append(count)
                path_list.append(p)
            elif str(p[3]) == 'openflow:3':
                count = 5003
                port_list.append(count)
                path_list.append(p)
            elif str(p[3]) == 'openflow:4':
                count = 5004
                port_list.append(count)
                path_list.append(p)
            flowID_new = str(int(flowID) * 10 + count)
            rvflowID_new = str(int(rvflowID) * 10 + count)
            self.push_path_port(p, count, SrcMAC, DstMAC, srcIP, dstIP, flowID_new, rvflowID_new, priority)
        return port_list, path_list

    def get_delay_jitter(self, srcIP, dstIP):
        path = self.getCaditatePaths(srcIP, dstIP)
        case = len(path)
        if case == 1:
            print ("only one hop")
            print (path)
            src_sw_id_, port_1 = self.getIndex(path[0][1])
            mid_sw_id_ = src_sw_id_
            mid_sw_ip_ = '10.0.0.' + str(mid_sw_id_ + 100)
            dst_sw_id_ = src_sw_id_
            list_ip_ping = mid_sw_ip_
            list_ID_ping = str(mid_sw_id_)
            rtt_src = 0
            rtt_dst = 0
            src_dst_ID = src_sw_id_ + ' ' + src_sw_id_
        elif case == 2:
            print ("pod level0")
            src_sw_id_ = [0, 0]
            mid_sw_id_ = [0, 0]
            mid_sw_ip_ = ['', '']
            dst_sw_id_ = [0, 0]
            for i in 0, 1:
                # print path[i]
                src_sw_id_[i], port_1 = self.getIndex(path[i][1])
                # print src_sw_id_[i]
                mid_sw_id_[i], port_1 = self.getIndex(path[i][2])
                mid_sw_ip_[i] = '10.0.0.' + str(mid_sw_id_[i] + 100)
                # print '10.0.0.'+str(mid_sw_id_[i])
                dst_sw_id_[i], port_1 = self.getIndex(path[i][3])
                # print dst_sw_id_[i]
                src_dst_ID = str(src_sw_id_[0]) + ' ' + str(dst_sw_id_[0])
            list_ip_ping = mid_sw_ip_[0] + ' ' + mid_sw_ip_[1]
            list_ID_ping = str(mid_sw_id_[0]) + ' ' + str(mid_sw_id_[1])
            # print list_ip_ping
            rtt_src, rtt_dst = self.get_avg_mdev(srcIP, dstIP, list_ip_ping)
        else:
            # print "core level"
            src_sw_id_ = [0, 0, 0, 0]
            mid_sw_id_ = [0, 0, 0, 0]
            mid_sw_ip_ = ['', '', '', '']
            dst_sw_id_ = [0, 0, 0, 0]
            for i in 0, 1, 2, 3:
                # print "path-through-core", path[i]
                src_sw_id_[i], port_1 = self.getIndex(path[i][1])
                mid_sw_id_[i], port_1 = self.getIndex(path[i][3])
                mid_sw_ip_[i] = '10.0.0.' + str(mid_sw_id_[i] + 100)
                dst_sw_id_[i], port_1 = self.getIndex(path[i][5])
            src_dst_ID = str(src_sw_id_[0]) + ' ' + str(dst_sw_id_[0])
            list_ip_ping = mid_sw_ip_[0] + ' ' + mid_sw_ip_[1] + ' ' + mid_sw_ip_[2] + ' ' + mid_sw_ip_[3]
            list_ID_ping = str(mid_sw_id_[0]) + ' ' + str(mid_sw_id_[1]) + ' ' + str(mid_sw_id_[2]) + ' ' + str(
                mid_sw_id_[3])
            rtt_src, rtt_dst = self.get_avg_mdev(srcIP, dstIP, list_ip_ping)
        return rtt_src, rtt_dst, list_ID_ping, src_dst_ID

    def get_avg_mdev(src_host, dst_host, ip_list):
        listenPort = 5000
        s1 = socket.socket()
        s2 = socket.socket()
        print ('get average', ip_list)
        print ('Socket created')
        try:
            s1.connect((src_host, listenPort))
            s2.connect((dst_host, listenPort))
        except socket.error as msg:
            # print 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]
            sys.exit()
        # print 'get average', ip_list
        s1.send(ip_list)
        s2.send(ip_list)
        rtt_src = s1.recv(1024).decode()
        s1.close()
        rtt_dst = s2.recv(1024).decode()
        s2.close()
        return rtt_src, rtt_dst

    def get_delay_loss_paping(src_host, dst_host):
        listenPort = 5000
        send_message = dst_host
        s1 = socket.socket()
        print('Socket created')
        print(src_host)
        try:
            s1.connect((src_host, listenPort))
        except socket.error as msg:
            print ('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
            sys.exit()
        s1.send(send_message)
        paping_src_value = s1.recv(1024).decode()
        s1.close()
        return paping_src_value

    #######################################################################################################
    # set shortest path QoS paper 5
    # ------------------------------------------------------------------------------------------------------
    def fix_congested_flows(self, priority = 50):
        set_path = 0
        adjMatrix = []
        OnesMatrix = np.ones([len(config.data_collected.getLinkStatAdjaencyMatrix()[0]),
                              len(config.data_collected.getLinkStatAdjaencyMatrix()[0])])
        graphMatrix = config.data_collected.getLinkStatAdjaencyMatrix().astype(
            int) + config.data_collected.getAdjaencyMatrix().astype(int) + OnesMatrix.astype(int)
        graph = np.delete(graphMatrix, [0], 0)
        for i in graph:
            j = (np.delete(i, [0])).tolist()
            adjMatrix.append(j)
        utilization = config.data_collected.get_Byte_port_utilization()
        # indices = np.where(utilization >= 1300)
        ind = np.unravel_index(np.argmax(utilization, axis=None), utilization.shape)
        # M = data_collected.get_Congested_port_utilization_matrix()
        current_link_cost_congested_path = utilization[ind[0]][ind[1]]
        switch_ID = str(ind[0])
        port_ID = str(ind[1])
        x = config.data_collected.getRuleState(switch_ID, port_ID)
        size_x_traffic = []
        flowID = []
        rvflowID = []
        for item in x:
            a = str(config.data_collected.getIP_from_Mac(item[0])).split(".")
            src_ID = a[3]
            b = str(config.data_collected.getIP_from_Mac(item[1])).split(".")
            Dst_ID = b[3]
            flowID.append(str(src_ID) + str(Dst_ID) + "1")
            rvflowID.append(str(Dst_ID) + str(src_ID) + "1")
            config.data_collected.update_Byte_packet_Traffic_Matrix()
            traffic_cost = config.data_collected.get_Byte_traffic_status_utilization_matrix()
            size_x_traffic.append(traffic_cost[src_ID][Dst_ID])
        while (x):
            traffic_value = max(size_x_traffic)
            rerouting_flow_index = size_x_traffic.index(max(size_x_traffic))
            temp = x[rerouting_flow_index]
            SrcMAC = temp[0]
            DstMAC = temp[1]
            SrcMAC_1 = "host:" + SrcMAC
            DstMAC_1 = "host:" + DstMAC
            Src_switch = [n for n in config.graph.neighbors(SrcMAC_1)]
            Dst_switch = [n for n in config.graph.neighbors(DstMAC_1)]
            Src_sw_id = int((str(Src_switch).split(":")[1])[:-2])
            Dst_sw_id = int((str(Dst_switch).split(":")[1])[:-2])
            temp_new_path, cost = g.dijkstra(adjMatrix, (Src_sw_id - 1), (Dst_sw_id - 1))
            if (cost + traffic_value) < current_link_cost_congested_path:
                best_path = [x + 1 for x in temp_new_path]
                best_path_name = []
                for i in best_path:
                    x = ('openflow:' + str(i))
                    best_path_name.append(x)
                best_path_name.insert(0, SrcMAC_1)
                best_path_name.append(DstMAC_1)
                # print "list -1", best_path_name, SrcMAC, DstMAC, priority
                self.push_path(best_path_name, SrcMAC, DstMAC, flowID[rerouting_flow_index], priority)
                best_path_name_rev = list(reversed(best_path_name))
                # # print "list -1", best_path_name_rev, DstMAC, SrcMAC, priority
                self.push_path(best_path_name_rev, DstMAC, SrcMAC, rvflowID[rerouting_flow_index], priority)
                set_path = 1
                break
            else:
                size_x_traffic.remove(size_x_traffic[rerouting_flow_index])
                x.remove(x[rerouting_flow_index])
                flowID.remove(flowID[rerouting_flow_index])
                rvflowID.remove(rvflowID[[rerouting_flow_index]])

    # caclulate the path based on the utilization matrix and a modified dijkstra algorithm


    #######################################################################################################
    # set shortest path QoS paper 5
    # ------------------------------------------------------------------------------------------------------
    def set_dijkstra_Utilization_QoS_proactive_passive(self, SrcMAC, DstMAC, SrcIP, DstIP, a, b, c):
        adjMatrix = []
        x = str(SrcIP).split(".")
        y = str(DstIP).split(".")
        flowID = str(x[3]) + str(y[3])
        rvflowID = str(y[3]) + str(x[3])
        priority = 50
        # paths = self.getCaditatePaths(Src_IP, Dst_IP)
        # a = config.graph.node()
        SrcMAC_1 = "host:" + SrcMAC
        DstMAC_1 = "host:" + DstMAC
        Src_switch = [n for n in config.graph.neighbors(SrcMAC_1)]
        Dst_switch = [n for n in config.graph.neighbors(DstMAC_1)]
        Src_sw_id = int((str(Src_switch).split(":")[1])[:-2])
        Dst_sw_id = int((str(Dst_switch).split(":")[1])[:-2])
        # get the graph Matrix
        # graphMatrix = data_collected.getAdjaencyMatrix()
        OnesMatrix = np.ones(
            [len(config.data_collected.getLinkStatAdjaencyMatrix()[0]), len(config.data_collected.getLinkStatAdjaencyMatrix()[0])])
        graphMatrix = config.data_collected.getLinkStatAdjaencyMatrix().astype(
            int) + config.data_collected.getAdjaencyMatrix().astype(int) + OnesMatrix.astype(int)
        graph = np.delete(graphMatrix, [0], 0)
        for i in graph:
            j = (np.delete(i, [0])).tolist()
            adjMatrix.append(j)
        temp_best_path, cost = config.g.dijkstra(adjMatrix, (Src_sw_id - 1), (Dst_sw_id - 1))
        best_path = [x + 1 for x in temp_best_path]
        best_path_name = []
        for i in best_path:
            x = ('openflow:' + str(i))
            best_path_name.append(x)
        best_path_name.insert(0, SrcMAC_1)
        best_path_name.append(DstMAC_1)
        # print "list -1", best_path_name, SrcMAC, DstMAC, priority
        self.push_path(best_path_name, SrcMAC, DstMAC, flowID, priority)
        best_path_name_rev = list(reversed(best_path_name))
        # # print "list -1", best_path_name_rev, DstMAC, SrcMAC, priority
        self.push_path(best_path_name_rev, DstMAC, SrcMAC, rvflowID, priority)

    # calculate the path based on the lowest utilizaed shorted path


    #######################################################################################################
    # set shortest path QoS paper 5
    # ------------------------------------------------------------------------------------------------------
    def set_Shortest_path_QoS_Utilization(self, SrcMAC, DstMAC, SrcIP, DstIP, a, b, c):
        linkCost = []
        x = str(SrcIP).split(".")
        y = str(DstIP).split(".")
        flowID = str(x[3]) + str(y[3])
        rvflowID = str(y[3]) + str(x[3])
        priority = 40
        SrcMAC_1 = "host:" + SrcMAC
        DstMAC_1 = "host:" + DstMAC
        paths = self.getCaditatePaths(SrcMAC_1, DstMAC_1)
        LinkstateMatrix = config.data_collected.getLinkStatAdjaencyMatrix().astype(int)
        # errorMatrix = data_collected.getLinkerrAdjaencyMatrix()
        for i in paths:
            linkCost.append(self.calculatePathCost(i, LinkstateMatrix))
        selectedPathIndex = linkCost.index(min(linkCost))
        selected_path = paths[selectedPathIndex]
        self.push_path(selected_path, SrcMAC, DstMAC, flowID, priority)
        selected_rev_path = list(reversed(selected_path))
        self.push_path(selected_rev_path, DstMAC, SrcMAC, rvflowID, priority)


    #######################################################################################################
    # set shortest path QoS paper 5
    # ------------------------------------------------------------------------------------------------------
    def calculatePathCost(self, path, LinkStatMatrix):
        linkCost = 0
        for i in range(1, len(path) - 2):
            edge = self.find_edge(path[i], path[i + 1])
            sw_edge_src, port_src = self.getIndex(edge['source']['source-tp'])
            sw_edge_dst, port_dst = self.getIndex(edge['destination']['dest-tp'])
            tempLinkcost = (LinkStatMatrix[sw_edge_src][sw_edge_dst] + LinkStatMatrix[sw_edge_src][sw_edge_dst]) / 2
            if tempLinkcost > linkCost:
                linkCost = tempLinkcost
        return linkCost

    def get_elephant_flows(self, Threshold):
        elephant_flows = []
        a = config.data_collected.get_Byte_traffic_status_utilization_matrix()
        for i, j in range(0, len(a) - 1, 1):
            if a[i][j] > Threshold:
                elephant_flows.append((i, j))
        return elephant_flows

    def get_large_avg_pkt(self, Threshold):
        elephant_pkt = []
        a = config.data_collected.get_Byte_traffic_status_utilization_matrix()
        b = config.data_collected.get_packet_traffic_status_utilization_matrix()
        for i, j in range(0, len(a) - 1, 1):
            if a[i][j] / b[i][j] > Threshold:
                elephant_pkt.append((i, j))
        return elephant_pkt

    ######################################################################################################
    # push path and build URLs
    # -----------------------------------------------------------------------------------------------------
    def push_path(self, path, SrcMAC, DstMAC, flowID, priority):
        for i in range(1, len(path) - 1, 1):
            print path[i], path[i + 1]
            edge_egress = self.find_edge(path[i], path[i + 1])
            port_egress = self.getIndex(edge_egress['source']['source-tp'])
            nodeID = path[i]
            print ("nodeID", nodeID)
            # edge_ingress = self.find_edge(path[i - 1], path[i])
            # # print edge_ingress
            # port_ingress = self.getIndex(edge_ingress['destination']['dest-tp'])
            newFlow = self.build_flow_src_dst_MAC('ip-1', str(port_egress[1]), str(SrcMAC), str(DstMAC), flowID, priority)
            Url = self.build_flow_url(nodeID, "0", flowID)
            resp, content = self.post_dict(Url, newFlow)

    def push_path_port(self, path, dstPort, SrcMAC, DstMAC, srcIP, dstIP, flowID, rvflowID, priority):
        for i in range(1, len(path) - 1, 1):
            edge_egress = self.find_edge(path[i], path[i + 1])
            port_egress = self.getIndex(edge_egress['source']['source-tp'])
            nodeID = path[i]
            edge_ingress = self.find_edge(path[i - 1], path[i])
            port_ingress = self.getIndex(edge_ingress['destination']['dest-tp'])
            if dstPort == 0:
                newFlow = self.build_flow_srcdst('foward-port-2', port_ingress[1], port_egress[1], dstPort, SrcMAC,
                                                 DstMAC, srcIP + "/32", dstIP + "/32", flowID, priority)
                revFlow = self.build_flow_srcdst('reverse-port-2', port_egress[1], port_ingress[1], dstPort, DstMAC,
                                                 SrcMAC, dstIP + "/32", srcIP + "/32", rvflowID, priority)
            else:
                newFlow = self.build_flow_srcdstIP_dstport('foward-port-2', port_ingress[1], port_egress[1], dstPort,
                                                           SrcMAC, DstMAC, srcIP + "/32", dstIP + "/32", flowID,
                                                           priority)
                revFlow = self.build_flow_srcdstIP_srcport('reverse-port-2', port_egress[1], port_ingress[1], dstPort,
                                                           DstMAC, SrcMAC, dstIP + "/32", srcIP + "/32", rvflowID,
                                                           priority)
            # print nodeID
            # print newFlow
            # print revFlow
            Url = self.build_flow_url(nodeID, "0", flowID)
            rvUrl = self.build_flow_url(nodeID, "0", rvflowID)
            resp, content = self.post_dict(rvUrl, revFlow)
            resp, content = self.post_dict(Url, newFlow)

    ###################################################################################################
    # build a URL
    # ---------------------------------------------------------------------------------------------------
    def build_flow_src_dst_MAC(self, flowName, EgressPort, srcMAC, dstMAC, flowID, priority):
        newFlow = {
            "flow": {
                "instructions": {
                    "instruction": {
                        "order": "0",
                        "apply-actions": {
                            "action": {
                                "order": "0",
                                "output-action": {
                                    "output-node-connector": EgressPort,
                                }
                            }
                        }
                    }
                },
                "table_id": "0",
                "id": flowID,
                "match": {
                    "ethernet-match": {
                        # "ethernet-type": {"type": "45"},
                        "ethernet-destination": {"address": dstMAC},
                        "ethernet-source": {"address": srcMAC}
                    }
                },
                # "hard-timeout": "30",
                "cookie": "4",
                "idle-timeout": "200",
                "flow-name": flowName,
                "priority": priority,
            }
        }
        return newFlow

    def build_flow_url(self, nodeID, tableID, flowID):
        url = "http://" + self.controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + nodeID + "/table/" + tableID + "/flow/" + flowID
        return url

    def build_flow_srcdstIP_dstport(self, flowName, inport, EgressPort, dstPort, SrcMAC, DstMAC, srcIP, dstIP, flowID,
                                    priority):
        # print EgressPort, "--", dstPort,SrcMAC,DstMAC,srcIP,dstIP,flowID
        newFlow = {"flow":
            {
                "id": flowID,
                "instructions": {
                    "instruction": {
                        "order": "0",
                        "apply-actions": {
                            "action": [
                                {"order": "0",
                                 "output-action": {"output-node-connector": EgressPort, "max-length": "65535"}}
                            ]
                        }
                    }
                },
                "flow-name": flowName,
                "match": {
                    "ethernet-match": {
                        "ethernet-type": {"type": "2048"},
                        "ethernet-destination": {"address": DstMAC},
                        "ethernet-source": {"address": SrcMAC}
                    },
                    "ipv4-source": srcIP,
                    "ipv4-destination": dstIP,
                    "ip-match": {
                        "ip-protocol": "6"
                    },
                    "tcp-destination-port": dstPort,
                    "in-port": inport

                    # "udp-source-port": srcPort,
                    # "udp-destination-port":dstPort,
                },
                "priority": priority,
                "table_id": "0"
            }
        }
        return newFlow

    def build_flow_srcdstIP_srcport(self, flowName, inport, EgressPort, srcPort, SrcMAC, DstMAC, srcIP, dstIP, flowID,
                                    priority):
        # print EgressPort, "--", srcPort,SrcMAC,DstMAC,srcIP,dstIP,flowID
        newFlow = {"flow":
            {
                "id": flowID,
                "instructions": {
                    "instruction": {
                        "order": "0",
                        "apply-actions": {
                            "action": [
                                {"order": "0",
                                 "output-action": {"output-node-connector": EgressPort, "max-length": "65535"}}
                            ]
                        }
                    }
                },
                "flow-name": flowName,
                "match": {
                    "ethernet-match": {
                        "ethernet-type": {"type": "2048"},
                        "ethernet-destination": {"address": DstMAC},
                        "ethernet-source": {"address": SrcMAC}
                    },
                    "ipv4-source": srcIP,
                    "ipv4-destination": dstIP,
                    "ip-match": {
                        "ip-protocol": "6"
                    },
                    "tcp-source-port": srcPort,
                    "in-port": inport

                    # "udp-source-port": srcPort,
                    # "udp-destination-port":dstPort,
                },
                "priority": priority,
                "table_id": "0"
            }
        }
        return newFlow

    # #######################################################################################################
    # Delete all flows in a node
    # ------------------------------------------------------------------------------------------------------
    def delete_all_flows_node(self, node, tableID):
        print (node)
        url = "http://" + config.controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + node
        resp, content = config.h.request(url, "GET")
        allFlows = json.loads(content)
        # print(allFlows)
        try:
            for m in allFlows['node'][0]['flow-node-inventory:table'][0]['flow']:
                # print(m['id'])
                delurl = "http://" + config.controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + node + "/table/" + str(tableID) + "/flow/" + str(m['id'])
                # delurl = "http://" + config.controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + node + "/table/" + tableID + "/flow/" + flowID
                resp, content = config.h.request(delurl, "DELETE")
        except:
            pass
            #
    # #######################################################################################################
    # Delete specific flow specified by nodeid and flowname
    # ------------------------------------------------------------------------------------------------------
    # def delete_spec_flow_node(node, tableID, flowID):
    #     delurl = "http://" + controllerIP + "/restconf/config/opendaylight-inventory:nodes/node/" + node + "/table/" + tableID + "/flow/" + flowID
    #     resp, content = h.request(delurl, "DELETE")
    #     print 'resp %s content %s', resp, content
    #######################################################################################################
    # return a matrix of zeros and ones, the colons indicates the switches and the rows indicates port
    # a one exists for a edgeport in an edge switch
    # ------------------------------------------------------------------------------------------------------
    # ######################################################################################################
    # post the using URL and flow in json
    # ---------------------------------------------------------------------------------------------
    def post_dict(self, url, d):
        resp, content = config.h.request(
            uri=url,
            method='PUT',
            headers={'Content-Type': 'application/json'},
            body=json.dumps(d)
        )
        return resp, content

    #######################################################################################################
    # get flow cost
    # ------------------------------------------------------------------------------------------------------





