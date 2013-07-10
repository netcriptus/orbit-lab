#!/usr/bin/python

from math import modf
from sys import stdin

# If ETX == True then all results are TX (transmission count) not TT (transmission time)
## NOTE: this features has not yet been tested in experiments.
ETX = False

""" Transmission time estimation (ETT)
    Original code by John Bicket in click/roofnet.
"""
WIFI_LLC_HEADER = 34  # IEEE 802.11 Fig. 22

WIFI_SLOT_B = 20
WIFI_DIFS_B = 50
WIFI_SIFS_B = 10
WIFI_PLCP_HEADER_LONG_B = 192
WIFI_PLCP_HEADER_SHORT_B = 96
WIFI_ACK_B = WIFI_PLCP_HEADER_LONG_B + (14 * 2) / 2 # 48?

WIFI_SLOT_A = 9
WIFI_DIFS_A = 28
WIFI_SIFS_A = 16
#?? WIFI_ACK_A = 30
WIFI_PLCP_HEADER_A = 20 # 16us preamble + 4us signal
WIFI_ACK_A = WIFI_PLCP_HEADER_A + (14 * 2) / 12

WIFI_CW_MIN = 31
WIFI_CW_MAX = 1023

def is_b_rate(rate):
    """ Checks if it's an 802.11b rate
    """
    return rate == 2 or rate == 4 or rate == 11 or rate == 22

def backoff(rate, t):
    """ returns expected backoff time for the bitrate and t tries
    """
    t_slot = WIFI_SLOT_A
    if(is_b_rate(rate)):
        t_slot = WIFI_SLOT_B
    cw = WIFI_CW_MIN;
    # there is backoff, even for the first packet
    for x in range(0, t):
        cw = (cw + 1) * 2
        if(cw > WIFI_CW_MAX):
            # why suffer?
            cw = WIFI_CW_MAX
            break
    return t_slot * cw / 2


def packetTime(length, rate, retries = 0):
    """ Computes the packet time in microseconds.
    """
    if(ETX):
        return retries + 1   ## == ETX/EOTX

    length+= WIFI_LLC_HEADER

    t_plcp_header = WIFI_PLCP_HEADER_SHORT_B
    if (rate == 2):
        t_plcp_header = WIFI_PLCP_HEADER_LONG_B
    elif (not is_b_rate(rate)):
        # 802.11a
        t_plcp_header = WIFI_PLCP_HEADER_A
        length+= 3 # 16 service + 6 tail bits
        # tx_time should be rounded to the next 4us
    tx_time = t_plcp_header + (2 * length * 8)/ rate

    t_slot = WIFI_SLOT_A
    t_ack = WIFI_ACK_A
    t_sifs = WIFI_SIFS_A

    if (is_b_rate(rate)):
        t_slot = WIFI_SLOT_B
        t_ack = WIFI_ACK_B
        t_sifs = WIFI_SIFS_B

    tt = 0
    v = 0
    for x in range(0, retries +1):
        v2 = backoff(rate, x) + tx_time + t_sifs + t_ack
        if(v2 == v):
            # why suffer? every next try is the same
            tt+= v2 * (retries + 1 - x)
            break
        tt+= v2
        v = v2
    return tt            ## == ETT/EOTT

def ett(length, rate, prob):
    """ Asymmetric ETT, assumes LLACKs are not lost.
    """
    if(prob == 0.0):
        return 1e20

    return packetTime(length, rate, 0)/prob


from sys import stderr
from time import sleep

def readLinks(filename, minQuality = 0.0, rateFilter = None, reverse = False, bidirectional = False):
    """ The link-file format is
        <node> <node> <rate> <prob> <rate> <prob> ...
        same pair can be repeated many times
        last entry for each rate counts
        Returns map: id -> rate -> id -> prob
        Use minQuality (float) and rateFilter (set/list) to restrict
        Use reverse to swap from and to
        Use bidirectional to remove links that have no backwards direction
    """
    link_file = None
    if(filename is None):
        link_file = stdin
    else:
        link_file = open(filename, "r")

    links = {}

    # read all
# Here read in multi-rate reception probability  -- Fan
    for line in link_file:
        fields = line.split()
        if(len(fields) == 0 or fields[0][0] == '#'):
            continue
        fr = fields[0]
        to = fields[1]
        if(reverse):
            fr,to = to,fr
        pt = links.setdefault(fr, {})
        for i in range(2, len(fields), 2):
            rate = int(fields[i])
            if(rateFilter is not None and rate not in rateFilter):
                continue
            prob = float(fields[i+1])
            if(prob > 1.0 or prob < 0.0):
                if(prob > 1.001 or prob < -0.001):
                    raise Exception("Link success probability out of range! %f" % prob)
                else:
                    print >> stderr, "WARNING: Link success probability out of range! %f" % prob
                    if(prob > 1.0): prob = 1.0
                    else: prob = 0.0
            if(prob > minQuality):
                rt = pt.setdefault(rate, {})
                rt[to] = prob
                assert(links[fr][rate][to] == prob)
                # to ensure links.keys() has all nodes
                links.setdefault(to, {})
    link_file.close()

    if(bidirectional):
        for f, l in links.items():
            for r, rl in l.items():
                for t, p in rl.items():
                    if(links.get(t, {}).get(r, {}).get(f, None) == None):
                        del rl[t]

    return links

if(__name__ == "__main__"):
   """ print the expected packet time for a set of
         cwmin cwmax tries
   """
   from sys import argv
   rate = int(argv[1])
   tries = int(argv[2])
   size = 1486
   if(len(argv) > 3):
       size = int(argv[3])
   for cwmin in range(3,11):
       WIFI_CW_MIN = (2**cwmin) - 1
       pkttime = packetTime(size, rate, tries-1)/tries
       print cwmin, 1e6/pkttime

