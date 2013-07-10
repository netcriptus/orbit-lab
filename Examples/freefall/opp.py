#!/usr/bin/python

from nodes import *
from sys import stderr, stdout, exit
from time import sleep, time
from os import system, mkdir
import wifi
import random
import math

runDelay = 5 # seconds
runTime = 35 # seconds
nodefile = '/root/more/nodes'
log = None
rate = 22

proto = 'more'
# generate configuration feed 
feed = "/root/more/%s.feed" % proto

alpha = 1.0
cheatfile = '/root/more/cheatlist'
cheatnum = 10
repeat = 3
plantform = 'grid' # 'sb' or 'grid'

random.seed()
src = '0'
dst = '1'

from getopt import getopt, GetoptError
try:
    opts = getopt(argv[1:], 't:d:n:l:p')
    for (o,d) in opts[0]:
        if(o == '-d'):
            runDelay = float(d)
        if(o == '-t'):
            runTime = float(d)
        if(o == '-n'):
            nodefile = d
        if(o == '-l'):
            log = d
    linkfile, repeats, plantform = opts[1]
    repeat = int(repeats)
except:
    print """usage: %s [opts] <linkfile> <repeat> <plantform>
    opts:
    -d <run delay>                          (default: 5)
    -t <run time> (including run delay)     (default: 65)
    -n <nodes file>                         (default: nodes)
    -l <MORE log filename> (relevant for MORE only)
    """ % argv[0]
    exit(1)

nodes = readNodes(file(nodefile, 'r'))

if(plantform == 'sb'):
    node_num = 2
elif(plantform == 'grid'):
    node_num = 25    
elif(plantform == '4hop'):
    node_num = 5
else:
    exit(1)

def echo(what, where):
    if(system("%s >> %s " % (what, where)) != 0):
        raise AssertionError("feed generation failed")

what = [ 'OUT.count', 'OUT_HP.count', 'IN.count', 'RECV.count', 'RECV.rate' ]
out_stat = file("/root/more/%s.stats" % proto, 'w')
##out_util = file("/root/more/%s.stats.util" % proto, 'w')
##print >> out_util, "#Utilities"
##print >> out_util, "#Run\tSrc\tDst\t[gain_h cum_h gain_c cum_c]n"
##out_util.write("#\t\t\t")
##for i in range(1,37):
##    out_util.write("%d\t\t\t\t\t\t\t\t\t\t\t\t" % i)
##out_util.write("\n")
out_thru = file("/root/more/%s.stats.thru" % proto, 'w')
print >> out_thru, "#Thrughput"
print >> out_thru, "#Run\tSrc\tDst\t[Thru Rate Realtime]_h\t[Thru Rate Realtime]_c"

##out_util.write("0\t0\t0")
##for n in nodes.values():
##    out_util.write("\t%.6f\t%.6f\t%.6f\t%.6f" % (0.0, 0.0, 0.0, 0.0))
##    n['gain_h'] = 0.0
##    n['cum_h'] = 0.0
##    n['gain_c'] = 0.0
##    n['cum_c'] = 0.0


if(log != None): log = '-l %s' % log
else: log = ''

for i in range(repeat):
    nodekeys = nodes.keys()

##    src = '1'
##    dst = '5'
    if(plantform == 'sb'):
        temp = random.randint(0,1)
        src = nodekeys[temp]
        dst = nodekeys[1 - temp]
    elif(plantform == 'grid'):
        tempsx = 0
        tempsy = 0
        tempdx = 0
        tempdy = 0
        if((i % 2) == 0):
            tempsy = tempdy = random.randint(0,4)
            while(abs(tempsx - tempdx) != 4):
                tempsx = random.randint(0,4)
                tempdx = random.randint(0,4)
        else:
            tempsx = tempdx = random.randint(0,4)
            while(abs(tempsy - tempdy) != 4):
                tempsy = random.randint(0,4)
                tempdy = random.randint(0,4)
                
#        while((abs(tempsx - tempdx) + abs(tempsy - tempdy)) != 4):
#        while(abs(tempsx - tempdx) < 4 and abs(tempsy - tempdy) < 4):
#        src = nodekeys[tempsx * 6 + tempsy]
#        dst = nodekeys[tempdx * 6 + tempdy]
        src = "%d" % (tempsx * 5 + tempsy + 1)
        dst = "%d" % (tempdx * 5 + tempdy + 1)
    elif(plantform == '4hop'):
        if(random.randint(0,1) == 0):
            src = "1"
            dst = "5"
        else:
            src = "5"
            dst = "1"
    else:
        print "Unknown plantform type!"
        exit(1)

#    out_util.write("\n%d\t%s\t%s" % (i+1, src, dst))
    out_thru.write("\n%d\t%s\t%s" % (i+1, src, dst))

    ###############
    # honest case #
    ###############
    # clear
    system("echo -n > %s" % feed) 

    # DATA src -> dst
#    echo("/root/more/feed.py -l %s -b - -q 0.1 -m eotx -p metric-down --tl 1.1 --tml 1.03 -f more m %s %s" % 
#       (linkfile, src, dst), feed)
    echo("/root/more/feed.py -l %s -b - -q 0.1 -m eotx -p metric-down --tl 0.5 --tn 5 -f more m %s %s" % 
       (linkfile, src, dst), feed)
    # ACKS
    echo("echo '%s.ip m.ack %d %s.mac'" % (src, 0, src), feed)
    echo("echo '%s.ip m.ack %d %s.mac'" % (dst, rate, src), feed)
##    echo("/root/more/feed.py -l %s -m etx -p single -b - -q 0.1 -f moreack m.ack %s %s" % 
##       (linkfile, dst, src), feed)

    echo("echo '%s.ip m.dst 0'" % (dst), feed)

    # general config, batches are 32x1500bytes
    echo("echo '%s.ip m.src 1500 32 1'" % (src), feed)

##    if(log != None): log = '-l %s' % log
##    else: log = ''
    print "RUN #%d (Honest) [%s] --> [%s] ...start" % (i+1, src, dst)
    killClick(nodes)
    
##    feedin = file("/root/more/%s.feed" % proto, 'r')
##    usenodes = []
##    for l in feedin:
##        l = l.split()[0]
##        l = l.split('.')[0]
##        if(l in usenodes):
##            continue
##        else:
##            usenodes.append(nodes[l])
##    feedin.close()
##    startClick(usenodes, '-d %s -t %s %s %s' % (runDelay, runTime, log, proto))
   
    startClick(nodes, '-d %s -t %s %s %s' % (runDelay, runTime, log, proto))
    waitForClick(10, nodes[src])

    if(system("/root/more/nodes.py %s < %s | /root/more/writeAll.py 5 &> %s.log" % (nodefile, feed, feed)) != 0):
        raise IOError("writeAll failed")

    ewrtNodes(nodes, 'kill.run', '/dev/null')
    ewrt('run.run', nodes[src])
    print "    sleeping for %.1f seconds" % runTime
    mysleep(runTime+1.0)

    print "RUN #%d (Honest) [%s] --> [%s] ...done" % (i+1, src, dst)

    print >> out_stat, ">> RUN #%d (Truth) [%s] --> [%s]:" % (i+1, src, dst)
    thru = thrurate = 0
    realtime = 0.0
    for n in nodes.values():
#    for n in usenodes:
        read = rd(what, n['ip'])
        print >> out_stat, "'%s' :" % n['dn'], read, ","
        if(read[3] != '0' and n['dn'] != dst):
            raise Exception("non-dst %s reports %s" % (n['dn'], read))
        if(n['dn'] == dst):
            thru = int(read[3])
            thrurate = float(read[4])
            if(thrurate > 0.0):
                realtime = thru / thrurate
            if(realtime < 0.8 * (runTime - runDelay)):
                print ">>>> dst was busy for only %s [s] reports %s" % (realtime, read)
        if(n['dn'] == src):
            if(read[0] == '0' and proto != 'null'):
                raise Exception('src %s reports %s' % (src, read))

    print ">>>> delivered %d packets" % thru
    print ">>>> throughput %.2f p/s" % thrurate
    out_thru.write("\t%d\t%.2f\t%.2f" % (thru, thrurate, realtime))
    
###    print >> out, "\nutilities:"
###    print "\nutilities:"
##    links = wifi.readLinks(linkfile, minQuality = 0.1, bidirectional = False)
###    utility = {}
##    for f, l in links.items():
##        nodes[f]['gain_h'] = 0.0
##        if(f == src or f == dst):
##            continue
##        for r, rl in l.items():
##            for t, p in rl.items():
##                nodes[f]['gain_h'] += alpha * p / 2.0
##        nodes[f]['cum_h'] += nodes[f]['gain_h']
##        
##    for n in range(1,node_num+1):
##        out_util.write("\t%.6f\t%.6f" % (nodes[str(n)]['gain_h'], nodes[str(n)]['cum_h']))
##        
###    ewrt("src.active false", nodes[src])
    stderr.flush()
##    killClick(nodes)
##    mysleep(10.0)


    #################
    # cheating case # (5)
    #################

    cheat_out = open(cheatfile, "w")
    cheat_nodes = []
    cheatnum = 5
    for j in range(cheatnum):
        n = random.randint(1,node_num)
        while(n in cheat_nodes):
            n = random.randint(1,node_num)
        cheat_nodes.append(n)
        amount = random.uniform(0.1, 0.7)
        if(random.randint(0,1) == 0):
            amount = -1.0 * amount
        print >> cheat_out, "%d a %.6f" % (n, amount)
    cheat_out.close()
        
    system("echo -n > %s" % feed) 
    # DATA src -> dst
    echo("/root/more/feed.py -l %s -c %s -b - -q 0.1 -m eotx -p metric-down --tl 0.5 --tn 5 -f more m %s %s" % 
       (linkfile, cheatfile, src, dst), feed)
    # ACKS
    echo("echo '%s.ip m.ack %d %s.mac'" % (src, 0, src), feed)
    echo("echo '%s.ip m.ack %d %s.mac'" % (dst, rate, src), feed)
##    echo("/root/more/feed.py -l %s -m etx -p single -b - -q 0.1 -f moreack m.ack %s %s" % 
##       (linkfile, dst, src), feed)

    echo("echo '%s.ip m.dst 0'" % (dst), feed)

    # general config, batches are 32x1500bytes
    echo("echo '%s.ip m.src 1500 32 1'" % (src), feed)

##    if(log != None): log = '-l %s' % log
##    else: log = ''
    print "RUN #%d (Cheat [%d]) [%s] --> [%s] ...start" % (i+1, cheatnum, src, dst)
    killClick(nodes)
    startClick(nodes, '-d %s -t %s %s %s' % (runDelay, runTime, log, proto))
    waitForClick(10, nodes[src])

    if(system("/root/more/nodes.py %s < %s | /root/more/writeAll.py 5 &> %s.log" %
              (nodefile, feed, feed)) != 0):
        raise IOError("writeAll failed")

    ewrtNodes(nodes, 'kill.run', '/dev/null')
    ewrt('run.run', nodes[src])
    print "    sleeping for %.1f seconds" % runTime
    mysleep(runTime+1.0)

    print "RUN #%d (Cheat [%d]) [%s] --> [%s] ...done" % (i+1, cheatnum, src, dst)

    print >> out_stat, ">> RUN #%d (Cheat) [%s] --> [%s]" % (i+1, src, dst)
    thru = thrurate = 0
    realtime = 0.0
    for n in nodes.values():
        read = rd(what, n['ip'])
        print >> out_stat, "'%s' :" % n['dn'], read, ","
        if(read[3] != '0' and n['dn'] != dst):
            raise Exception("non-dst %s reports %s" % (n['dn'], read))
        if(n['dn'] == dst):
            thru = int(read[3])
            thrurate = float(read[4])
            if(thrurate > 0.0):
                realtime = thru / thrurate
            if(realtime < 0.8 * (runTime - runDelay)):
                print ">>>> dst was busy for only %s [s] reports %s" % (realtime, read)
        if(n['dn'] == src):
            if(read[0] == '0' and proto != 'null'):
                raise Exception('src %s reports %s' % (src, read))

    print ">>>> delivered %d packets" % thru
    print ">>>> throughput %.2f p/s" % thrurate
    out_thru.write("\t%d\t%.2f\t%.2f" % (thru, thrurate, realtime))

####    print >> out, "\nutilities:"
####    print "\nutilities:"
##    cheat_in = open(cheatfile, "r")
##    cheat = {}
##    for line in cheat_in:
##        fields = line.split()
##        if(len(fields) == 0 or fields[0][0] == '#'):
##            continue
##        n = fields[0]
##        #type = fields[1] # 'u': up; 'd': down; 'r': random
##        type = fields[1] # 'p': percentage; 'a': amount
##        diff = float(fields[2])
##        l = cheat.setdefault(n, {})
##        l['type'] = type
##        l['diff'] = diff
##    cheat_in.close()
##
##    for f, l in links.items():
##        nodes[f]['gain_c'] = 0.0
##        if(f == src or f == dst):
##            continue
##        for r, rl in l.items():
##            for t, p in rl.items():
##                pp = p
##                c = cheat.get(f, {})
##                if(c != {}):
##                    if(cheat[f]['type'] == "a"):
##                        pp += cheat[f]['diff']
##                    elif(cheat[f]['type'] == "p"):
##                        pp *= (1.0 + cheat[f]['diff'])
##                if(pp < 0.1):
##                    continue
##                if(pp > 1.0):
##                    pp = 1.0
##                nodes[f]['gain_c'] += alpha * pp - alpha * pp * pp / p / 2.0
##        nodes[f]['cum_c'] += nodes[f]['gain_c']
##        
##    for n in range(1,node_num+1):
##        out_util.write("\t%.6f\t%.6f" % (nodes[str(n)]['gain_c'], nodes[str(n)]['cum_c']))

#    ewrt("src.active false", nodes[src])
    stderr.flush()

##    killClick(nodes)
##    mysleep(10.0)

    #################
    # cheating case # (10)
    #################

    cheat_out = open(cheatfile, "w")
    cheat_nodes = []
    cheatnum = 10
    for j in range(cheatnum):
        n = random.randint(1,node_num)
        while(n in cheat_nodes):
            n = random.randint(1,node_num)
        cheat_nodes.append(n)
        amount = random.uniform(0.1, 0.7)
        if(random.randint(0,1) == 0):
            amount = -1.0 * amount
        print >> cheat_out, "%d a %.6f" % (n, amount)
    cheat_out.close()
        
    system("echo -n > %s" % feed) 
    # DATA src -> dst
    echo("/root/more/feed.py -l %s -c %s -b - -q 0.1 -m eotx -p metric-down --tl 0.5 --tn 5 -f more m %s %s" % 
       (linkfile, cheatfile, src, dst), feed)
    # ACKS
    echo("echo '%s.ip m.ack %d %s.mac'" % (src, 0, src), feed)
    echo("echo '%s.ip m.ack %d %s.mac'" % (dst, rate, src), feed)
##    echo("/root/more/feed.py -l %s -m etx -p single -b - -q 0.1 -f moreack m.ack %s %s" % 
##       (linkfile, dst, src), feed)

    echo("echo '%s.ip m.dst 0'" % (dst), feed)

    # general config, batches are 32x1500bytes
    echo("echo '%s.ip m.src 1500 32 1'" % (src), feed)

##    if(log != None): log = '-l %s' % log
##    else: log = ''
    print "RUN #%d (Cheat [%d]) [%s] --> [%s] ...start" % (i+1, cheatnum, src, dst)
    killClick(nodes)
    startClick(nodes, '-d %s -t %s %s %s' % (runDelay, runTime, log, proto))
    waitForClick(10, nodes[src])

    if(system("/root/more/nodes.py %s < %s | /root/more/writeAll.py 5 &> %s.log" %
              (nodefile, feed, feed)) != 0):
        raise IOError("writeAll failed")

    ewrtNodes(nodes, 'kill.run', '/dev/null')
    ewrt('run.run', nodes[src])
    print "    sleeping for %.1f seconds" % runTime
    mysleep(runTime+1.0)

    print "RUN #%d (Cheat [%d]) [%s] --> [%s] ...done" % (i+1, cheatnum, src, dst)

    print >> out_stat, ">> RUN #%d (Cheat) [%s] --> [%s]" % (i+1, src, dst)
    thru = thrurate = 0
    realtime = 0.0
    for n in nodes.values():
        read = rd(what, n['ip'])
        print >> out_stat, "'%s' :" % n['dn'], read, ","
        if(read[3] != '0' and n['dn'] != dst):
            raise Exception("non-dst %s reports %s" % (n['dn'], read))
        if(n['dn'] == dst):
            thru = int(read[3])
            thrurate = float(read[4])
            if(thrurate > 0.0):
                realtime = thru / thrurate
            if(realtime < 0.8 * (runTime - runDelay)):
                print ">>>> dst was busy for only %s [s] reports %s" % (realtime, read)
        if(n['dn'] == src):
            if(read[0] == '0' and proto != 'null'):
                raise Exception('src %s reports %s' % (src, read))

    print ">>>> delivered %d packets" % thru
    print ">>>> throughput %.2f p/s" % thrurate
    out_thru.write("\t%d\t%.2f\t%.2f" % (thru, thrurate, realtime))


    
out_stat.close()
#out_util.close()
out_thru.close()




