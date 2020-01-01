import config

class helper:
    #######################################################################################################
    # get Switch Index flow statistics- for each node query all port statistics
    def getIndex(self, sw):
        sw_id = int(sw.split(":")[1])
        try:
            port_ID = int(sw.split(":")[2])
        except:
            port_ID = -1
        return sw_id, port_ID
    #######################################################################################################
    # helper function get-packets for two edge nodes
    def get_packet_count(self, route_ports, port_matching):
        list = []
        for r in route_ports:
            if (r[0] == port_matching):
                list.append(r)
        return list

    def createFlowID(self,SrcMAC, DstMAC):
        SrcIP = self.getIP_from_Mac(SrcMAC)
        DstIP = self.getIP_from_Mac(DstMAC)
        if (SrcIP != -1 and DstIP != -1):
            x = str(SrcIP).split(".")
            y = str(DstIP).split(".")
            flowID = str(x[3]) + str(y[3])
            return flowID
        else:
            return -1


    #######################################################################################################
    # find edge in a rout
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def find_edge(self, headNode, tailNode):
        for edge in self.odlEdges:
            if (edge['source']['source-node'] == headNode) and (edge['destination']['dest-node'] ==tailNode):
                return edge
    #######################################################################################################
    # get hostID from IP address
    #------------------------------------------------------------------------------------------------------

    @staticmethod
    def gethostID_from_IP(IP):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if node['host-tracker-service:addresses'][0]['ip'] == IP:
                    return node['node-id']
        return -1

    @staticmethod
    def gethostID_from_Mac(MAC):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if node['host-tracker-service:addresses'][0]['mac'] == MAC:
                    return node['node-id']
        return -1
    #######################################################################################################
    # get Mac from hostID
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def getMac_from_host_ID(hostID):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if  node['node-id'] == hostID:
                    return node['host-tracker-service:addresses'][0]['mac']
        return -1
    #######################################################################################################
    # get IP from hostID
    #------------------------------------------------------------------------------------------------------
    @staticmethod
    def getIP_from_host_ID(hostID):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if  node['node-id'] == hostID:
                    return node['host-tracker-service:addresses'][0]['ip']
        return -1

    @staticmethod
    def getIP_from_Mac(Mac):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if  node['host-tracker-service:addresses'][0]['mac'] == Mac:
                    return node['host-tracker-service:addresses'][0]['ip']
        return -1

    @staticmethod
    def getMac_from_IP(IP):
        for node in config.odlNodes:
            if node['node-id'].find("openflow") != 0:
                if  node['host-tracker-service:addresses'][0]['ip'] == IP:
                    return node['host-tracker-service:addresses'][0]['mac']
        return -1
