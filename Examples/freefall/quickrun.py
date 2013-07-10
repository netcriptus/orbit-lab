#!/usr/bin/python

from nodes import *
from sys import stderr, stdout, exit
from time import sleep, time
from os import system, mkdir

runDelay = 5 # seconds
runTime = 65 # seconds
nodefile = '/root/more/nodes'
log = None

from getopt import getopt, GetoptError
try:
    opts = getopt(argv[1:], 't:d:n:l:')
    for (o,d) in opts[0]:
        if(o == '-d'):
            runDelay = float(d)
        if(o == '-t'):
            runTime = float(d)
        if(o == '-n'):
            nodefile = d
        if(o == '-l'):
            log = d
    linkfile, src, dst, proto = opts[1]
except:
    print """usage: %s [opts] <linkfile> <src> <dst> (spp|more)
    opts:
    -d <run delay>                          (default: 5)
    -t <run time> (including run delay)     (default: 65)
    -n <nodes file>                         (default: nodes)
    -l <MORE log filename> (relevant for MORE only)
    """ % argv[0]
    exit(1)

nodes = readNodes(file(nodefile, 'r'))

# generate configuration feed 
feed = "%s.feed" % proto

def echo(what, where):
    if(system("%s >> %s " % (what, where)) != 0):
        raise AssertionError("feed generation failed")

# clear
system("echo -n > %s" % feed) 

if(proto == 'spp'):
    # get bitrate from linkfile
    o = file(linkfile, 'r')
    for l in o:
        l = l.split()
        if not l or l[0].startswith('#'): continue
        bitrate = int(l[2])
        break
    o.close()
    
    for n in nodes.keys():
        echo("echo '%s.ip rate.rate %d'" % (n, bitrate), feed)
        echo("echo '%s.ip end.switch 0'"% (n), feed) # everyone forwards
    echo("/root/more/feed.py -l %s -b - -q 0.1 -m etx -p single -f spp e.dst %s %s" % 
       (linkfile, src, dst), feed)
    echo("echo '%s.ip end.switch 1'"% (dst), feed)

if(proto == 'more'):
    # Remove stat file
    echo("rm /root/more.stats", feed)
    
    # DATA src -> dst
    echo("/root/more/feed.py -l %s -b - -q 0.1 -m eotx -p metric-down --tl 1.1 --tml 1.03 --zifile more.stats -f more m %s %s" % 
       (linkfile, src, dst), feed)
    # Changed by Fan
    #echo("/root/more/feed.py -l %s -b - -m eotx --zifile more.stats -f more m %s %s" % 
    #   (linkfile, src, dst), feed)
    # ACKS
    echo("/root/more/feed.py -l %s -m etx -p single -b - -q 0.1 --zifile more.stats -f moreack m.ack %s %s" % 
       (linkfile, dst, src), feed)

    echo("echo '%s.ip m.dst 0'" % (dst), feed)

    # general config, batches are 64*1500bytes
    echo("echo '%s.ip m.src 1500 64 1'" % (src), feed)

###########################
##  general run
###########################
if(log != None): log = '-l %s' % log
else: log = ''
startClick(nodes, '-d %s -t %s %s %s' % (runDelay, runTime, log, proto))
waitForClick(10, nodes[src])

if(system("/root/more/nodes.py %s < %s | /root/more/writeAll.py 5 &> %s.log" % (nodefile, feed, feed)) != 0):
    raise IOError("writeAll failed")

ewrtNodes(nodes, 'kill.run', '/dev/null')
ewrt('run.run', nodes[src])
print "    sleeping for %.1f seconds" % runTime
mysleep(runTime+1.0)

print "    ...done"

# obtain stats
what = [ 'OUT.count', 'OUT_HP.count', 'IN.count', 'RECV.count', 'RECV.rate' ]
out = file("%s.stats" % proto, 'a')
print >> out, "{"
thru = 0
thrurate = 0
for n in nodes.values():
    read = rd(what, n['ip'])
    print >> out, "'%s' :" % n['dn'], read, ","
    if(read[3] != '0' and n['dn'] != dst):
        raise Exception("non-dst %s reports %s" % (n['dn'], read))
    if(n['dn'] == dst):
        thru = int(read[3])
        thrurate = float(read[4])
        if(thrurate > 0):
            realtime = thru / thrurate
            if(realtime < 0.8 * (runTime - runDelay)):
                print ">>>>dst was busy for only %s [s]" % realtime
                print >> out, "#dst was busy for only %s [s]" % realtime
                #raise Exception("dst was busy for only %s [s] reports %s" % realtime, read)
    if(n['dn'] == src):
        if(read[0] == '0' and proto != 'null'):
            print >> out, "#src %s reports %s" % (src, read)
            raise Exception('src %s reports %s' % (src, read))
    
print >> out, "}\n"

print ">>>> delivered %d packets" % thru
print ">>>> throughput %.2f p/s" % thrurate

print >> out, "#Delivered packets:\n%d\n" % thru
print >> out, "#Throughput (mbps):\n%.6f\n" % (thrurate * 1500 * 8 / 1000 / 1000)
out.close()

killClick(nodes)

