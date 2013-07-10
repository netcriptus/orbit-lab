#!/usr/bin/python

""" This script can be used to execute a single command on all the nodes.
    For example exec.py nodes 'iwconfig ath0 channel 4'.
"""

from nodes import readNodes, forNodes
from sys import argv, exit

if(len(argv) < 2):
    print """usage: %s nodefile command [opts]
    s = serial
    d = debug
    n = non-blocking
    """ % argv[0]
    exit(-1)

nodes = readNodes(open(argv[1]))

ssh = "ssh "

cmd = argv[2]
opts = []
if(len(argv) > 3):
   opts = list(argv[3])


if('n' in opts):
    # don't ask me why it works
    cmd = "screen -D -m bash -c '%s' &" % cmd
run = ssh + ' root@%(ip)s "' + cmd + '"'


forNodes(nodes, run, serial=('s' in opts), debug=('d' in opts))

