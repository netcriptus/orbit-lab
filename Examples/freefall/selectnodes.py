#!/usr/bin/python

from sys import stderr, stdout, exit, argv
from os import system
import random
import operator

host = 'grid'
num_nodes = 2	# number of nodes (src + intermediate)

from getopt import getopt, GetoptError
try:
    opts = getopt(argv[1:], 'h:n:')
    for (o,d) in opts[0]:
        if(o == '-h'):
            host = d
        if(o == '-n'):
            num_nodes = int(d)
except:
    print """usage: %s [opts]
    opts:
    -h <host>			(default: sb1)
    -n <number of nodes>	(default: 1)
    """ % argv[0]
    exit(1)

ip_second = 0
if(host == "grid"):
    ip_second = 10
if(host == "sb1"):
    ip_second = 11
if(host == "sb2"):
    ip_second = 12
if(host == "sb4"):
    ip_second = 14

in_topo = open("system_topo_active_%s.rb" % host, "r")
out_nodes = open("nodes", "w")
out_nodeset = open("nodeset", "w")
out_controlnode = open("controlnode", "w")

nodes = {}
select = {}
mac = {}
for x in range(1,21):
    n = nodes.setdefault(x, {})
    s = select.setdefault(x, {})
    m = mac.setdefault(x, {})
    for y in range(1,21):
        n[y] = 0
        s[y] = 0
        m[y] = ""

# Read node information
in_node_info = open("nodeInfo_%s" % host, "r")
for line in in_node_info:
    info = line.split()
    mac[int(info[0])][int(info[1])] = info[3]
in_node_info.close()

        
for ln in in_topo:
    if(ln[0] == "#" or ln[0] == " "):
        continue
    if(host == "grid"):
        ln = ln[41:-3]
    else:
        ln = ln[40:-3]
    ln = ln.split("[")
    if(len(ln) == 0):
        continue
    active = len(ln)
    for i in ln:
        i = i.split("]")
        i = i[0].split(",")
 #       print i[0], i[1]
        x = int(i[0])
        y = int(i[1])
        if(mac[x][y] != ""):
            n = nodes.get(x, {})
            n[y] = 1

print "Active nodes:", active
for y in range(20, 0, -1):
    for x in range(1,21):
        if(nodes[x][y] == 1):
            stdout.write("X ")
        else:
            stdout.write("O ")
#        stdout.write("%d " % nodes[x][y])
    if(operator.mod(y, 5) == 0 or y == 1):
        stdout.write("\t%d" % y)
    stdout.write("\n")
stdout.write("\n1       5         10        15        20\n")

backlist = [[16,5],[4,5],[11,11],[8,3],[4,16],[6,5],[5,16],[15,7],[16,16],[4,4],[15,16],[17,16],[16,4],[8,13],[13,3],[13,13],[15,5],[8,18],[15,8],[15,5],[13,13],[13,18],[3,13],[16,6],[18,13],[8,8],[17,5]]
for x, y in backlist:
    if(nodes[x][y] == 1):
        nodes[x][y] = 0
        active -= 1

random.seed()
x_min = 21
y_min = 21
x_max = 0
y_max = 0
for i in range(0,num_nodes):
    x = 0
    y = 0
    while(x == 0 or y == 0 or nodes[x][y] == 0 or select[x][y] == 1):
        if(host == "grid"):
            x = 1 + random.randint(1,18)
            y = 1 + random.randint(1,18)
            #if (i==0): 
                #x=4
                #y=5
            #if (i==1):
                #x=5
                #y=6
        else:
            if(host=="sb4"):
               x = 1
               y = random.randint(1,8)
            else:
               x=1
               y=random.randint(1,2)
    select[x][y] = 1
    if((x-1)*(x-1)+(y-1)*(y-1) < (x_min-1)*(x_min-1)+(y_min-1)*(y_min-1)):
        x_min = x
        y_min = y
    if((x-20)*(x-20)+(y-20)*(y-20) < (x_max-20)*(x_max-20)+(y_max-20)*(y_max-20)):
        x_max = x
        y_max = y
    print >> out_nodeset, "[%d,%d]" % (x,y)

print >> out_controlnode, "[%d,%d]" % (x_max,y_max)
    
nodename = 1
for x in range(1,21):
    for y in range(1,21):
        if(select[x][y] == 1):
            if(x == x_min and y == y_min):
                print >> out_nodes, "10.%d.%d.%d %s dst" % (ip_second,x,y,mac[x][y])
            elif(x == x_max and y == y_max):
                print >> out_nodes, "10.%d.%d.%d %s src" % (ip_second,x,y,mac[x][y])
            else:
                print >> out_nodes, "10.%d.%d.%d %s i%d" % (ip_second,x,y,mac[x][y],nodename)
                nodename += 1
        

print "\nSelected nodes:", num_nodes
for y in range(20, 0, -1):
    for x in range(1,21):
        if(select[x][y] == 1):
            stdout.write("X ")
        else:
            stdout.write("O ")
#        stdout.write("%d " % select[x][y])
    if(operator.mod(y, 5) == 0 or y == 1):
        stdout.write("\t%d" % y)
    stdout.write("\n")
stdout.write("\n1       5         10        15        20\n")


in_topo.close()
out_nodes.close()
out_nodeset.close()
out_controlnode.close()

