#!/usr/bin/python

from nodes import *
from sys import argv, exit, stderr, stdout
from time import sleep, time
from os import system
from getopt import getopt, GetoptError


runTime = 10
nodes = '/root/more/nodes'
outfile = None
rate = "2"
size = "1500"
dieOnError = False

try:
    for (o,d) in getopt(argv[1:], 'T:n:o:r:s:e')[0]:
        if(o == '-T'):
            runTime = float(d)
            pass
        if(o == '-n'):
            nodes = d
        if(o == '-o'):
            outfile = d
        if(o == '-s'):
            size = d
        if(o == '-r'):
            rate = d
        if(o == '-e'):
            dieOnError = True
    if(outfile is None):
        raise Exception()
except:
    print """usage: %s [opts]
    -T <sleeptime> \t (30)
    -n <nodefile> \t ('nodes')
    -r <rate> \t (2)
    -s <size> \t (1500)
    -o <outputfile> \t REQUIRED
    -e \t die on errors?
    """ % argv[0]
    exit(1)
    
nodes = readNodes(file(nodes, 'r'))
outfile = file(outfile, 'w')

all_rate = ["2","4","11","22","12","18","24","36","48","72","96","108"]#totally 12 kinds of bitrate
realrate = "%.1f Mbps" % (0.5 * float(rate))
#print"!!!rate = 2"#kai
for rate_1 in  range(0,4):
    rate = all_rate[rate_1]
    realrate = "%.1f Mbps" % (0.5 * float(rate))
    for i, n in enumerate(nodes.values()):
        killClick(nodes)
        #forNodes(nodes, "/root/more/myssh root@%(ip)s 'killall -w click'")

        startClick(nodes, '-d 3 -t %s spp' % (runTime + 3))
        #forNodes(nodes, '/root/more/myssh root@%(ip)s ' + ("'cd %s && bash ./startup.sh %s &'" % (dir,cmd)) )
        waitForClick(10, n)

        print "\n%d/%d :: Source %s\tRate %s\n" % (i+1, len(nodes), n['dn'], realrate)  

        ewrt("e.dst FF:FF:FF:FF:FF:FF", n) 
        ewrt("rate.rate " + rate, n)


        # start it
        ewrt("kill.run", n)
        ewrt("run.run", n)

        #wait for sleeptime seconds
        try:
            mysleep(runTime+1.0)
        except:
            wrt("src.active false", n)
            break

        #stop the src
        ewrt("src.active false", n)
        stderr.flush()

        sleep(0.5) # let the output queue flush

        #get the sent count
        out = rd("OUT.count", n)
        if(len(out) < 1):
            print "!!!!! Could not read OUT"
            if(dieOnError):
                exit(1)
            continue
        sent = int(out[0].split()[0])
        print "\nTransmitted", sent
        #get the recv count
        for m in nodes.values():
            if(m is n):
                continue
            out = rd("IN.count", m)
            if(len(out) < 1):
                print m['dn'],"!!!!! Could not read IN"
                if(dieOnError):
                    exit(1)
                continue
            rcv = int(out[0].split()[0])
            if(rcv > 0):
                q = rcv*1.0/sent
                print '%s\trecv %d\t= %.3f' % (m['dn'], rcv, q)
                q = min(q, 1.0)
                print >> outfile, n['dn'], m['dn'], rate, q
        print
        stdout.flush()

outfile.close()
killClick(nodes)



