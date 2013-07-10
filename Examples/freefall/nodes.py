#!/usr/bin/python

from sys import argv, stdin, stderr, stdout, exit
from os import system, fork, wait, getpid
from socket import socket, timeout

# a few useful tools:
# readNodes parses the nodes file
# forNodes executes the command substituting node params
# wrt is a dumb handler writer
# rd is a handler reader

# the main function translates <nodeid>.<value> using the nodes file

default = { "ip" : "0.0.0.0", "mac" : "FF:FF:FF:FF:FF:FF", "dn" : "nohost" }
RUNTIME_DIR = '/root/more'

def readNodes(file):
    """ Parses a nodes file.
        Empty lines or lines commented with '#' are skipped
    """
    out = {}
    for lr in file:
        if(lr[0] == "#"):
            continue
        l = lr.split()
        if(len(l) == 0):
            continue
        if(len(l) < 3):
            raise Exception("Malformed nodes file! " + lr)
        r = {}
        r["ip"] = l[0]
        r["mac"] = l[1]
        r["dn"] = l[2]
        out[l[2]] = r

    try: file.close()
    except: pass
    return out

def writeNodes(nodes, file):
    """ dumps to a file
    """
    for r in nodes.values():
        print >> file, r["ip"], r["mac"], r["dn"]
    file.close()


class SocketStream:
    """ poor performance impl of
        recvline and recv(amount) """
    def __init__(self):
        self.s = socket()
        self.s.settimeout(10.0) # 10-second timeout on read
        self.buf = ""
    def recv(self, ln):
        buf = self.buf
        try:
          while(len(buf) < ln):
            buf+= self.s.recv(4096) # throws IOError on timeout
        except:
          print >> stderr, "Timeout? read %d out of %d\n" % (len(buf), ln)
          raise
        res = buf[:ln]
        self.buf = buf[ln:]
        return res
    def recvline(self):
        buf = self.buf
        pos = buf.find('\n')
        try:
          while(pos < 0):
            b = self.s.recv(4096)
            buf+= b
            pos = buf.find('\n', len(buf) - len(b))
        except:
          print >> stderr, "Timeout? '\\n' not found in '%s' of %d bytes at %d " % (buf, len(buf), buf.find('\n'))
          raise
        pos+= 1
        res = buf[:pos]
        self.buf = buf[pos:]
        return res

def rd(handlers, ip):
    """ read and return the stripped output
        accepts list of handlers
        all done in one nc connection
    """
    # coerce to common types
    if(type(handlers) == str):
        handlers = [handlers]
    if(type(ip) == dict):
        ip = ip['ip']
    for i in range(0,4):
     try:
      s = SocketStream()
      s.s.connect((ip,7777))
      s.recvline() # hello
      results = []
      for h in handlers:
        s.s.sendall('read %s\n' % h)
        l = s.recvline()
        if(l.startswith('200')):
            oldl = l
            l = s.recvline()
            reslen = int(l.split()[1])
            b = s.recv(reslen)
            results.append(b)
        else:
            results.append(l)
      return results
     except timeout, e:
      print >> stderr, e
      continue
    raise Exception('Timeout')

def wrt(handlers, ip):
    if(type(handlers) == str):
        handlers = [handlers]
    if(type(ip) == dict):
        ip = ip['ip']
    handlers = "\nwrite ".join([' '] + handlers) + "\nquit"
    # this is nasty :)
    return system(("echo '%s' | nc -w 10 %s 7777 | tail -n2 | head -n1 >&2") % (handlers, ip))

def ewrt(f, n):
    if(wrt(f, n)):
        raise Exception("could not write handler %s to %s", f, n['ip'])

from threading import Thread
from thread import interrupt_main
def forNodes(nodes, cmd, serial=False, debug=False):
    errors = []
    if(type(nodes) is dict):
        # we just need a list
        nodes = nodes.values()

    def forOne(n):
        try:
            c = cmd % n
            if(debug):
                print >> stderr, n['dn'], c
            rv = system(c)
            if(rv != 0):
                errors.append((c, rv))
        except KeyboardInterrupt:
            interrupt_main()

    if(serial): 
        for n in nodes: forOne(n)
    else: 
        # create threads
        threads = []
        for n in nodes:
            threads.append(Thread(target=forOne, args=(n,)))
        for t in threads: t.start()
        for t in threads: t.join()
    return errors


def wrtNodes(nodes, handlers, out='&2'): # single write to all nodes
    if(type(handlers) == str):
        handlers = [handlers]
    handlers = "\nwrite ".join([' '] + handlers) + '\nquit'
    #print handlers
    return forNodes(nodes, "echo '%s' | nc -w 10 %%(ip)s 7777 | tail -n1 >%s" % (handlers, out))

def ewrtNodes(nodes, handlers, out):
    errors = wrtNodes(nodes, handlers, out)
    if(errors):
        raise Exception("The following write calls failed: %s"  % errors)

def killClick(nodes):
    forNodes(nodes, "/root/more/myssh root@%(ip)s 'killall -w click'")

def startClick(nodes, cmd,  dir = RUNTIME_DIR):
    print "START", cmd
    forNodes(nodes, '/root/more/myssh root@%(ip)s ' + ("'cd %s && bash ./startup.sh %s &'" % (dir,cmd)) )

from time import sleep
def waitForClick(tmo, n):
    while(tmo > 0 and system('echo quit | nc -w %s %s 7777 &> /dev/null' % (tmo, n['ip']))):
        sleep(1)
        tmo-= 1

def mysleep(amount, res=1.0):
    while(amount > 0.0):
        sleep(res)
        amount-= res
        print '\r%s   ' % amount,
        stdout.flush()
    print

# all this script does is it converts nodes_ids to actual nodes
# provide a nodes-like file
# then wherever it sees 1.ip it will put in the ip of node 1
# ip = ethernet IP
# mac = roofnet MAC
# dn = domain name
def main(args):
    if(len(args) < 2):
        print "Usage: %s <nodefile>" % args[0]
        return -1

    nodes = readNodes(open(argv[1]))

    for l in stdin:
        # find all int.string
        l = l.split()
        for e in l:
            es = e.split('.')
            try:
                print nodes.get(es[0], default)[es[1]],
            except:
                print e,
        print

if(__name__ == "__main__"):
    main(argv)

