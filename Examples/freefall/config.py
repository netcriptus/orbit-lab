#!/usr/bin/python

from sys import exit, argv, stderr
from os import system, popen

# First, configure the device in raw/monitor mode. 
madwifi = 'ng'
if(madwifi == 'old'):
    dev = 'ath0'
    rawdev = dev + 'raw'
    system("""
/sbin/ifconfig %(rawdev)s down
/sbin/ifconfig %(dev)s down
/sbin/sysctl -w dev.%(dev)s.rxfilter=0xff &> /dev/null
/sbin/sysctl -w dev.%(dev)s.rawdev_type=2 &> /dev/null
/sbin/sysctl -w dev.%(dev)s.rawdev=1 &> /dev/null
/sbin/ifconfig %(dev)s up txqueuelen 1
/sbin/ifconfig %(rawdev)s up txqueuelen 1
""" % globals())
    decap = "Prism2Decap -> ExtraDecap -> RadiotapDecap"
    decapfbk = decap
    encap = "RadiotapEncap"
elif(madwifi == 'ng'):
    dev = 'wifi0'
    rawdev = 'ath0'
    system("""
ifconfig %(rawdev)s down
ifconfig %(dev)s down
wlanconfig %(rawdev)s destroy
wlanconfig %(rawdev)s create wlandev %(dev)s wlanmode monitor 2> /dev/null > /dev/null
sysctl -w net.%(rawdev)s.dev_type=804 2> /dev/null > /dev/null
ifconfig %(dev)s up txqueuelen 1
ifconfig %(rawdev)s up txqueuelen 1 mtu 2000		
""" % globals())							# changed by Fan, mtu 1600
    decap = decapfbk = 'AthdescDecap'
    encap = 'AthdescEncap'

# obtain MAC address from device
p = popen('/sbin/ifconfig %(dev)s 2>&1'  % globals())
ifconfig = p.readline().split()
if('not' in ifconfig):
    print >> stderr, 'device not found?', ' '.join(ifconfig)
    exit(-1)
mac = ifconfig[4]
p.close()

mac = mac.split(':')
if(len(mac) < 6):
    mac = mac[0].split('-')
if(len(mac) < 6):
    print >> stderr, 'got invalid mac address!', mac
    exit(-1)

# take only 6 bytes for MAC
mac = ':'.join(mac[0:6])

print >> stderr, "using %(dev)s / %(rawdev)s MAC %(mac)s" % globals()

# obtain position from device eth0
q = popen('/sbin/ifconfig eth1 2>&1')
ifconfig = q.readline().split()
if('not' in ifconfig):
    print >> stderr, 'eth0 device not found?', ' '.join(ifconfig)
    exit(-1)
ifconfig = q.readline().split()
ip = ifconfig[1].split(':')[1]
q.close()

ip = ip.split('.')
if(len(ip) < 4):
    ip = ip[0].split('-')
if(len(ip) < 4):
    print >> stderr, 'got invalid ip address!', ip
    exit(-1)
x = ip[2]
y = ip[3]

print >> stderr, "position [%(x)s, %(y)s]" % globals()

# Actual click configuration

runDelay = '5' # seconds
runTime = '65' # seconds
proto = None
log = ''

from getopt import getopt, GetoptError
try:
    opts = getopt(argv[1:], 't:d:l:')
    for (o,d) in opts[0]:
        if(o == '-d'):
            runDelay = d
        if(o == '-t'):
            runTime = d
        if(o == '-l'):
            log = ", LOG %s" % d
    proto = opts[1][0]
    assert proto in ['spp', 'more']
except:
    print >> stderr, """usage: %s [-d <run delay>] [-t <run time>] [-l <MORE log>] (spp|more)
""" % argv[0]
    exit(-1)

# proto ethtypes
anytype = 'a5%ff'
spptype = 'a501'
datatype = 'a502'
acktype = 'a503'

# COMMON From/ToDevice STACK
print """
ControlSocket("TCP", 7777);
ChatterSocket("TCP", 7778);

// INPUT PATH
FromDevice(%(rawdev)s, OUTBOUND true)
-> ibreak :: Switch(0)
-> %(decap)s() -> FilterPhyErr 
-> Classifier(0/08%%0c) -> WifiDupeFilter() -> WifiDecap(POSX %(x)s, POSY %(y)s) 
-> Classifier(12/%(anytype)s)
-> txf :: FilterTX()[0]
-> Print(i0, TIMESTAMP 1, NBYTES 14) -> IN :: AverageCounter();

txf[1] 
-> TXF :: PrintTXFeedback(x0);

// OUTPUT PATH
psout :: PrioSched()
-> SetTXPower(POWER 1)
-> WifiEncap(0x0, 00:00:00:00:00:00, ETHTYPE 0x%(datatype)s, ACKTYPE 0x%(acktype)s, SPPTYPE 0x%(spptype)s, POSX %(x)s, POSY %(y)s) -> %(encap)s()
-> obreak :: PullSwitch(0)
-> to_dev :: ToDevice(%(rawdev)s);
to_dev_ctl :: SockControl(to_dev);
Script(TYPE ACTIVE,
   write to_dev_ctl.sndbuf 1000,
);

OUT :: AverageCounter()
-> Print(o0, TIMESTAMP 1, NBYTES 14) 
-> [1] psout;

// high priority output
OUT_HP :: AverageCounter() 
-> Print(p0, TIMESTAMP 1, NBYTES 14)
-> [0] psout;

RECV :: AverageCounter()
-> Print(r0, TIMESTAMP 1, NBYTES 0)
-> Discard;

// this script isolates the I/O when the experiment is done
kill :: Script(TYPE PASSIVE, 
    wait %(runTime)s, 
    write ibreak.switch -1, 
    write obreak.switch -1); 
// this one brings everything back to normal
reset :: Script(TYPE PASSIVE, 
    write IN.reset, 
    write OUT.reset,
    write OUT_HP.reset,  
    write RECV.reset, 
    write ibreak.switch 0, 
    write obreak.switch 0);
// that one starts the protocol with initial delay
run :: Script(TYPE PASSIVE,
    wait %(runDelay)s,
    write start.run);

""" % globals()

if(proto == 'spp'):
    print """
    IN
    -> hef::HostEtherFilter(%(mac)s, DROP_OWN true, DROP_OTHER true)
    -> end :: Switch(1)
    -> Strip(14)
    -> q :: FullNoteQueue(50)
    -> [1]ps :: PrioSched
    -> e :: EtherEncap(0x%(spptype)s, %(mac)s, 00:00:00:00:00:00)
    -> rate :: SetTXRate(RATE 2, TRIES 8) // 802.11 recommends 7 retries
    -> OUT;

    Idle -> OUT_HP;

    src :: InfiniteSource(DATASIZE 1524, ACTIVE false) -> [0]ps;
    TXF -> Discard;
    end[1] -> RECV;

    start :: Script(TYPE PASSIVE,
        write src.active true,
    );
""" % globals()
else: # more
    print """
// SIGNAL PATH (for preencoding)
to_dev[0] -> SIGpath :: %(decapfbk)s -> SIG :: WifiDecap(POSX %(x)s, POSY %(y)s);
// we have to route even the failures...
to_dev[1] -> Print(fail, NBYTES 2) -> SIGpath;

//    m :: MORE(ETH %(mac)s, ETHTYPE 0x%(datatype)s, ACKTYPE 0x%(acktype)s, POSX %(x)s, POSY %(y)s %(log)s) -> OUT;
    m :: MORE(ETH %(mac)s, ETHTYPE 0x%(datatype)s, ACKTYPE 0x%(acktype)s %(log)s) -> OUT;
    m[1] -> OUT_HP;
    m[2] -> RECV;

    IN -> [0]m;
    TXF -> [1]m;
    SIG -> [2]m;

    start :: Script(TYPE PASSIVE,
        write m.start,
    );

""" % globals()

