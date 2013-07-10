#!/usr/bin/python

# the format of the handlerfile is simply
# IP <handler line>
# use "#" as first char to comment out
# use nodes.py to substitute values from nodes-file into handler line

from sys import stdin, stdout, stderr, argv, exit
from os import system, fork, wait
from time import sleep


maxtries = 1
if(len(argv) > 1):
    maxtries = int(argv[1])

def write_feeds(feeds):
    # TODO parallelize this!
    for (node, feed) in feeds.items():
        
        feed = "write ".join(feed) + '\nquit'
        print >> stderr, "\n\nFeed for %s\n" % node, feed
        stderr.flush()
        cmd = 'echo "%s" | nc -w 10 %s 7777' % (feed, node)

        tries = 0
        while(True): 
            ret = system(cmd)
            if(ret == 0): break
            tries += 1
            if(tries >= maxtries):
                print >> stderr, "\n\nMAX tries for %s exceeded" % node
                exit(-1)
            sleep(0.2)

        stdout.flush()

feeds = {}

for l in stdin:
    if(l[0] == '#'):
        # comment
        continue
    l = l.split(None, 1)
    if(len(l) == 0):
        # blank
        continue
    if(len(l) == 1):
        raise Exception("Malformed feed ", l)
    feeds.setdefault(l[0], [""]).append(l[1])

write_feeds(feeds)

exit(0)
