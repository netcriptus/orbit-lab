#!/usr/bin/ruby

require 'socket'
require 'thread'

# Orbit lab constants
MAX_GRID_SIZE       = 30
MULTICAST_SEND_ADDR = "224.4.0.1"
MULTICAST_SEND_PORT = 9006
MULTICAST_RECV_ADDR = "224.4.0.2"
MULTICAST_RECV_PORT = 9008
MULTICAST_INTERFACE = "eth1"

# general constants
MISSING_LIST_WIDTH = 20

def OrbitFixCommandParse(cmd,symbol)
    cmd = cmd + " "
    cmd2 = ""
    cmd.split(symbol).each { |part|
        cmd2 = cmd2 + part + "\\" + symbol
    }
    return cmd2.chop.chop.strip
end

# keeps track of lists of missing nodes
class OrbitMissingNodes

    def initialize
        @missingList = ""
        @skippedItem = 0
    end

    def addNode(x,y)

        # we're adding items based on current list width
        oldList = @missingList

        @missingList = @missingList + " #{x}-#{y},"
        if (@missingList.length > MISSING_LIST_WIDTH)
            @missingList = oldList
            @skippedItem = 1
        end
    end

    def getList(missingText)
        list = @missingList.chop
        list = missingText + list if (@missingList.length > 0)
        list = list + "..." if (@skippedItem == 1)
        @missingList = ""
        return list
    end

    def clearList
        @missingList = ""
        @skippedItem = 0
    end
end

# allows us multicast send a recv
class OrbitMulticast < UDPSocket

    # gets the IP address of the multicast interface
    def getMCInterfaceIP
        match = /[.\d]+\.[.\d]+\.[.\d]+\.[.\d]+/
        io = IO.popen("/sbin/ifconfig #{MULTICAST_INTERFACE}","r")
        ip = io.readlines[1][match]
        io.close
        return ip
    end

    def initialize(type) 

        if (type=="send") then
            @addr = MULTICAST_SEND_ADDR
            @port = MULTICAST_SEND_PORT
        else
            @addr = MULTICAST_RECV_ADDR
            @port = MULTICAST_RECV_PORT
        end

        interfaceIP = getMCInterfaceIP.to_s
        maddr = @addr.split('.').collect! { |b| b.to_i }.pack('CCCC')
        mreq  = maddr + Socket.gethostbyname(interfaceIP)[3]

        @sock = UDPSocket.new
        @sock.setsockopt(Socket::SOL_SOCKET,Socket::SO_REUSEADDR, 1)
        @sock.bind(@addr, @port)
        @sock.setsockopt(Socket::IPPROTO_IP, Socket::IP_MULTICAST_IF, Socket.gethostbyname(interfaceIP)[3])
        @sock.setsockopt(Socket::IPPROTO_IP, Socket::IP_ADD_MEMBERSHIP, mreq)
    end

    def recv
        return @sock.recvfrom(8192)
    end

    def send(data)
        @sock.send(data,0,@addr,@port)
    end

end

class OrbitMulticastStateReader
    
    # recv states from nodes
    RECV_STATE_nothing      = 'nothing'
    RECV_STATE_nonpxe_image = 'booted'
    RECV_STATE_pxe_image    = 'pxe'
    RECV_STATE_first_hb     = 'firsthb'
    RECV_STATE_imaging      = 'imaging'

    def initialize
        
        @recvIPAddress = Array.new
        @recvStateArray = Array.new
        @mcRecv = OrbitMulticast.new("recv")
        @mutex = Mutex.new 
        Thread.new do mainLoop end
    end

    def getIP(x,y)
        ip = nil
        @mutex.lock
        ip = @recvIPAddress[x*MAX_GRID_SIZE+y]
        @mutex.unlock
        return ip
    end
        
    def getState(x,y)
        state = nil
        @mutex.lock
        state = @recvStateArray[x*MAX_GRID_SIZE+y]
        @mutex.unlock
        return state
    end

    def setState(x,y,state)
        @mutex.lock    
        @recvStateArray[x*MAX_GRID_SIZE+y] = state
        @mutex.unlock
    end

    def mainLoop
        loop {

            # read in the recvd msg and parse it
            recvd = @mcRecv.recv
            recvdText = recvd[0]
            
            nodeX = recvd[1][3].split('.')[2].to_i
            nodeY = recvd[1][3].split('.')[3].to_i
    
            @recvIPAddress[nodeX*MAX_GRID_SIZE+nodeY] = recvd[1][3]

            state = RECV_STATE_nothing
            param = 0

            if (recvdText["WHOAMI"]) then
                if (recvdText["pxe"]) then
                    state = RECV_STATE_pxe_image
                else
                    state = RECV_STATE_nonpxe_image
                end
            end

            if (recvdText["HEARTBEAT 0"]) then
                state = RECV_STATE_first_hb
            end

            if (recvdText["APP_EVENT STARTED builtin:load_image"]) then
                state = RECV_STATE_imaging
                param = 0
            end

            if (recvdText["Progress"]) then
                state = RECV_STATE_imaging
                param = recvdText.split("gress:")[1].split("%")[0].to_i
            end

            if (recvdText["APP_EVENT DONE.OK builtin:load_image"]) then
                state = RECV_STATE_imaging
                param = 100
            end
            
            @mutex.lock
            if (state != RECV_STATE_nothing) then
                @recvStateArray[nodeX*MAX_GRID_SIZE+nodeY] = {'type' => state,'param' => param}
            #else
            #    @recvStateArray[nodeX*MAX_GRID_SIZE+nodeY] = nil
            end
            @mutex.unlock
        }

    end

end


# reads the node list file and presents to easily to the user
class OrbitNodeSets
    MAX_GRID_SIZE = 30

    # we parse the list of nodes, the list may be
    # an add or a subtract, duplicate adds are added once
    # ex:
    #   [1..20,1..20]   # add 400 nodes
    #   -[4,5]          # remove node 4,5 from the list
    #   [1,1..12]       # add 12 nodes

    def initialize(nodeListFile)

        # array used to store the nodes we're going to use
        @useNodes = [0]
        
        # temp storage
        useRanges = [0]

        File.open(nodeListFile).each { |line|

            # remove line comments
            line = line.split('#')[0]
            line = line.strip

            # is this a negative add
            negAdd = 0 
            if line["-["] then
                line = line[1..line.length] 
                negAdd = 1
            end

            # our ranges to set
            offset = 0
            useRanges = [0,0,0,0]
           
            # parse each line to get the range
            line.split(',').each { |item|
                item["["] = "" if item["["]
                item["]"] = "" if item["]"]

                rangeLow = 0
                rangeHi = 0     

                if item[".."] then
                    rangeLow = item.split('..')[0].to_i
                    if (item.split('..').length == 1) then
                        rangeHi = item.split('..')[0].to_i
                    else
                        rangeHi = item.split('..')[1].to_i
                    end
                else
                    rangeLow = item.to_i
                    rangeHi = item.to_i
                end
            
                rangeLow = 1             if (rangeLow < 1)
                rangeHi  = MAX_GRID_SIZE if (rangeHi > MAX_GRID_SIZE)
                rangeLow = rangeHi       if (rangeLow > rangeHi)

                useRanges[offset*2] = rangeLow
                useRanges[offset*2+1] = rangeHi 
                offset = offset + 1 
            }

            # since we have the range, we'll fill the array
            for x in useRanges[0]..useRanges[1] 
                for y in useRanges[2]..useRanges[3]
                    offset = x*MAX_GRID_SIZE + y
                    if negAdd == 1 then
                        @useNodes[offset] = nil
                    else    
                        @useNodes[offset] = 1
                    end
                end
            end
        }

        @nodeIter = Array.new

        # now we'll make an iterable array
        for x in 1..MAX_GRID_SIZE
            for y in 1..MAX_GRID_SIZE
                if isNodeSelected(x,y) then
                    tmpAry = {'x' => x, 'y' => y}
                    @nodeIter[@nodeIter.size] = tmpAry
                end
            end
        end
    end

    def nodeList
        return @nodeIter
    end

    def isNodeSelected(x,y)
        if (@useNodes[x * MAX_GRID_SIZE+y] == 1) then
            return 1
        end
        return nil
    end
end

