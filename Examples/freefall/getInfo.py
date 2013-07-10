#!/usr/bin/python

from sys import exit, argv, stderr
from os import system, popen

print"#kai getInfo.py "#kai

# First, configure the device in raw/monitor mode. 
madwifi = 'ng'
if(madwifi == 'old'):
    dev = 'eth0'
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
#    dev = 'wlan0'
    rawdev = 'eth0'
    system("""
ifconfig %(rawdev)s down
ifconfig %(dev)s down
wlanconfig %(rawdev)s destroy
wlanconfig %(rawdev)s create wlandev %(dev)s wlanmode monitor 2> /dev/null > /dev/null
sysctl -w net.%(rawdev)s.dev_type=804 2> /dev/null > /dev/null
ifconfig %(dev)s up txqueuelen 1
ifconfig %(rawdev)s up txqueuelen 1 mtu 1600
""" % globals())
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
    #print >> stderr, 'eth0 device not found?', ' '.join(ifconfig)
    raise Exception('eth0 device not found')
    exit(-1)
ifconfig = q.readline().split()
ip = ifconfig[1].split(':')[1]
q.close()

ip = ip.split('.')
if(len(ip) < 4):
    ip = ip[0].split('-')
if(len(ip) < 4):
    #print >> stderr, 'got invalid ip address!', ip
    raise Exception('got invalid ip address!')
    exit(-1)
x = ip[2]
y = ip[3]

ip = '.'.join(ip[0:4])

print >> stderr, "position [%(x)s, %(y)s]" % globals()

out_nodeinfo = open("nodeinfo", "w")

print >> out_nodeinfo, "%(x)s %(y)s %(ip)s %(mac)s" % globals()

out_nodeinfo.close()


