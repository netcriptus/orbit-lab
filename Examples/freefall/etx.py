#!/usr/bin/python

from sys import argv, stderr
import wifi

def linksETT(links, backlinks, PACKETSIZE):
    """ Transforms the link map into ETT link-table, chooses best rate
        if backlinks == None assume all backlinks are 1.0
    """
    etts = {}  # [ metric, best_rate ]
    for i in links.keys():
        m = etts[i] = {}
        m[i] = (0, 0)
        for j in links.keys():
            if(j is i):
                continue
            # compute ETT i->j
            pt = links.get(i, {})
            ptb = None
            if(backlinks != None):
                ptb = backlinks.get(i, {})
            bestett = 1e20
            bestrate = 0
            for (rate, ln) in pt.items():
                p = ln.get(j, 0)

                if(ptb != None and len(ptb) > 0):
                    # lookup backlink prob, use lowest rate
                    bp = ptb.get(min(ptb), {}).get(j, 0)
                    p *= bp

                ett = wifi.ett(PACKETSIZE, rate, p)
                if(ett < bestett):
                    bestett = ett
                    bestrate = rate
            if(bestrate > 0):
                m[j] = (bestett, bestrate)
    return etts

def allETT(etts):
    """ all-pairs shortest paths Floyd-Warshall.
        outputs modified metric from : to : (metric, (bestrate, besthop), #hops)
    """
    nodes = etts.keys()
    metric = {}
    # init
    for k in nodes:
        for i in nodes:
            mki = etts[i].get(k, (1e20,0))
            metric.setdefault(i, {})[k] = ( mki[0], (mki[1], k), 1 )
    for k in nodes:
        for i in nodes:
            for j in nodes:
                mikj = metric[i][k][0] + metric[k][j][0]
                hcij = metric[i][k][2] + metric[k][j][2]
                if(metric[i][j][0] > mikj):
                    metric[i][j] = ( mikj, metric[i][k][1], hcij )
    return metric

