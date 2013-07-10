#!/usr/bin/python

from sys import argv, stderr
import wifi, eotx, etx
from optparse import OptionParser

''' routing feed generator
    basically a UI for eotx.py
'''

def parse(args):
    parser = OptionParser(usage = 'usage: %prog [options] <handle> <src> <dst> [<dst2> ...]')
    parser.add_option('-v', '--verbose',
                  action='store_true', dest='verbose', default=True,
                  help='make lots of noise on stderr [default]')

    parser.add_option('-l', '--linkfile', default='-', dest='linkfile',
                  help='link qualities in standard form; if ommitted or "-", read from stdin')
    parser.add_option('-b', '--backlinks', default='', dest='backlinks',
                  help='reverse link qualities (ETX only); if "-", takes reverse of --linkfile')

#Added by Fan: cheat nodes
    parser.add_option('-c', '--cheatlist', default='-', dest='cheatlist',
                  help='list of nodes who cheat their lossing probability; if ommitted or "-", no node cheats')

    parser.add_option('-q', '--quality', type='float', default=0.0, dest='quality',
                  help='min link quality threshold')
    parser.add_option('-r', '--rates', action='append', type='int', dest='rates',
                  help='select rates from links, use multiple switches for multiple rates')
    parser.add_option('--bidir', '--bidirectional', action='store_true', dest='bidir', default=False, 
                  help='only allows links that are bidirectional (after quality and rate filtering)')
    parser.add_option('-s', '--size', type='int', default=0, dest='size',
                  help='packet size [bytes], implies (ETT/EOTT)')

    parser.add_option('-m', '--metric', choices=['eotx','etx'], default='etx', dest='metric',
                  help='primary metric logic (eotx | etx) [default: %default]')

    parser.add_option('--scale', type='float', default=1000.0, dest='scale',
                  help='metric scale [default: %default]')

    parser.add_option('--loads', dest='loads', default='',
                  help='file to which dump the expected loads')
# Added by Fan
    parser.add_option('--zifile', dest='zifile', default='',
                  help='file to which dump z_i of each node')

    parser.add_option('--loadsingle', action='store_true', dest='loadsingle',
                  help='compute expected load on a single path -- also useful for -f metric')

    parser.add_option('--multicast', action='store_true', dest='multicast',
                  help='use multicast logic even if one destination')

    pruning = ['none','single','single-extend','load-once','load-down', 'metric-down', 'metric-up', 'metric-up-fs']
    parser.add_option('-p', '--prune', choices=pruning, dest='prune', default='none',
                  help='pruning logic (' + '|'.join(pruning) + ') [default: %default]')
    parser.add_option('--tl', '--threshold-load', type='float', default=0.0, dest='minload',
                  help='pruning min load [default: %default]')
    parser.add_option('--tn', '--threshold-num', type='int', default=2, dest='minfwd',
                  help='pruning min #fwd [default: %default]')
    parser.add_option('--tml', '--threshold-max-loss', type='float', default=eotx.infinity, dest='maxloss',
                  help='pruning max metric loss [default: %default]')

    parser.add_option('-f', '--format', choices=['spp','more','moreack','metric','lp'], dest='format', help='feed output format; also implies final load distribution')
    parser.add_option('--ratescale', type='float', default=1.0, dest='ratescale', 
                  help='scaling factor for source inflow rate')

    (options, args) = parser.parse_args(args)
    args = args[1:]
    if len(args) < 3:
        parser.error('Incorrect number of arguments %d.\nTry --help' % len(args))

    if (options.metric == 'eotx' and options.prune in ['single', 'single-extend']):
        parser.error('%s only allowed with --metric=etx' % options.prune)
    if (len(args) > 3 and options.format != 'more'):
        parser.error('multicast supported only for --format more')
        
    if args[1] in args[2:]:
        parser.error('source among sinks!')

    return (options, args)

def getLinks(options):
    wifi.ETX = False
    if(options.size > 0):
        wifi.ETX = False
    if(options.linkfile == '-'):
        options.linkfile = None
    options.links = wifi.readLinks(options.linkfile, minQuality = options.quality, rateFilter= options.rates, bidirectional = options.bidir)
    if(options.backlinks != ''):
        if(options.backlinks == '-'):
            options.backlinks = options.linkfile
        options.backlinks = wifi.readLinks(options.backlinks, minQuality=options.quality, rateFilter=options.rates, reverse=True, bidirectional = options.bidir)
    else:
        options.backlinks = None

#Added by Fan
def cheatLinks(options):
    cheat_file = open(options.cheatlist, "r")
    cheatfor = []
    cheatp = {}
    for line in cheat_file:
        fields = line.split()
        if(len(fields) == 0 or fields[0][0] == '#'):
            continue
        node = fields[0]
        #type = fields[1] # 'u': up; 'd': down; 'r': random
        type = fields[1] # 'p': percentage; 'a': amount
        diff = float(fields[2])
        if(type == 'p'):
            cheatfor.append(node)
            cheatp[node] = float(fields[3])
        pt = options.links.get(node, {})
        if(pt == {}):
            continue
        for r, rl in pt.items():
            for t, p in rl.items():
                if(type == 'a'):
                    rl[t] += diff
                elif(type == 'p'):
                    rl[t] *= (1.0 + diff)
                if(rl[t] < 0.0):
                    rl[t] = 0.0
                if(rl[t] > 1.0):
                    rl[t] = 1.0
                    
    for f, l in options.links.items():
        for r, rl in l.items():
            for t, p in rl.items():
                if(t in cheatfor):
                    rl[t] *= (1.0 + cheatp[t])
                if(rl[t] < 0.0):
                    rl[t] = 0.0
                if(rl[t] > 1.0):
                    rl[t] = 1.0
    cheat_file.close()


#### Compute unicast parameters using multi-rate   -- Fan
def computeUnicast(options, e, src, dst):
    if(options.metric == 'etx'): e.setRelaxSingle()
    else: e.setRelaxOpp()

    e.initMetric(dst)
    e.computeMetric(src)
    if(not e.connected(src)):
        print >> stderr, "SORRY, NO ROUTE! %s -> %s" % (src, dst)
        return False # no route

    # pruning
    if(options.prune == 'single'):
        e.computeLoadSingle(src)
        e.pruneOnce(1.0)
    elif(options.prune == 'single-extend'):
        e.computeLoadSingle(src)
        e.pruneOnce(0.5)
    elif(options.prune == 'load-once'):
        e.computeLoadOpp(src)
        e.pruneOnce(options.minload)
    else:
        e.computeLoadOpp(src)
        prune = { 'load-down': lambda a,b,c : e.pruneLoad(a,b,c),
                  'metric-down' : lambda a,b,c : e.pruneMetricDown(a,b,c,maxloss=options.maxloss),
                  'metric-up' : e.pruneMetricUp,
                  'metric-up-fs' : lambda a,b,c : e.pruneMetricUp(a,b,c,single=True),
                  }
        options.pruned = False
        if(options.prune in prune):
            prune[options.prune](src, options.minload, options.minfwd)
            options.pruned = True

    # after pruning need to recompute loads (for more)
    if((options.format in ['more', 'metric'] or options.loads != '') and options.prune != 'none'):	#Modified by Fan
        # needed to reestablish P (a bit expensive way)
        # but the metric it computes is BS
        e.computeMetric(src)
        if(options.loadsingle):
            e.computeLoadSingle(src)
        else:
            e.computeLoadOpp(src)

    if(not e.connected(src)):
        print >> stderr, "SORRY, NO ROUTE! %s -> %s" % (src, dst)
        return False # no route

    return True

def outputUnicast(options, e, src, dst, handle):
    # output
    if(options.format == 'metric'):
        # print expected total cost only
        print '%.2f\t%.2f' % e.totalTX()
    elif(options.format == 'lp'):
        print 'Value of objective function: %f' % e.totalTX()[0]
        print 'Actual values of variables:'
        for n in e.nodes:
            print 'z_%s \t\t %f' % (n.id, n.tx)
        # also output loads
        for n in e.nodes:
            for (m, l) in n.loads.items():
                print 'x_%s_%s \t\t %f' % (n.id, m, l)

    else:
        scale = options.scale

        # compute the inflow at source as the sum of all rates in vicinity
        if(options.format == 'more'):
            srcnode = e.nodes[-1]
            assert srcnode.id == src 
            srcnode.rx = (e.neighborTX(srcnode) + srcnode.tx) / options.ratescale

        for n in e.nodes:
            if(options.format == 'spp'):
                print '%s.ip %s %s.mac' % (n.id, handle, n.next.id)
            elif(options.format == 'moreack'):
                print '%s.ip %s %d %s.mac' % (n.id, handle, n.rate, n.next.id),
                if(options.prune in [ 'single-extend', 'none' ]):
                    #flooding
                    print '%d' % int(n.metric * scale)
                else:
                    print
            elif(options.format == 'more'):
#### Output n.rate is computed best rate  -- Fan
                print '%s.ip %s.set %d %d' % (n.id, handle, int(n.metric * scale), n.rate),
                print

                print '%s.ip %s.outflow %.3f' % (n.id, handle, n.tx)
                print '%s.ip %s.inflow %.3f' % (n.id, handle, n.rx)

def outputLoads(options, e, src, dst):
    # dump loads
    lds = open(options.loads, 'a')
    if(e.checkLoads(src)): return 2
    for n in e.nodes:
        for (m, l) in n.loads.items():
            if(l > 0.0):
                print >> lds, '%s %s x %.6f' % (n.id, m, l)

# funcation added by Fan
def outputZi(options, e, src, dst):
    # dump Z_i
    zifile = open(options.zifile, 'a')
    total_zi = 0.0
    counter = 0
    for n in e.nodes:
        print >> zifile, '%s %.6f' % (n.id, n.tx)
        total_zi += n.tx
        counter += 1
    print >> zifile, '[n Z_i]: %d %.6f\n' % (counter, total_zi)
    zifile.close()

def computeMulticast(options, src, dsts, handle):
    e = eotx.EOTX(options.links, options.linksett)
    allnodes = list(e.nodes) # make a copy resilient to pruning

    # compute individual unicasts and store .tx for each dst
    unicast = {} # tx[dst], rate, links, next (for TMO ONLY!)
    for n in allnodes:
        unicast[n.id] = [ [0.0] * len(dsts), 0, {}, None ]
    for d in range(len(dsts)):
        for n in allnodes: n.reset()
        e.nodes = list(allnodes)
        # XXX FIXME works only for single rate
        computeUnicast(options, e, src, dsts[d])
        for n in e.nodes:
            u = unicast[n.id]
            if(n.rate > 0):
                u[0][d] = n.tx
                u[1] = n.rate
                u[2] = n.links[n.rate]
                # HACK PART 1
                u[3] = n.next.id

        #print '\n\nUNICAST %d' % d
        #outputUnicast(options, e, src, dsts[d], handle)

    #print '\n\nMULTICAST'
    # determine teaching order
    et = eotx.EOTX(options.backlinks, etx.linksETT(options.backlinks, None, eotx.Node.PACKETSIZE))
    activenodes = []
    for n in et.nodes:
        if(n.id in dsts or sum(unicast[n.id][0]) > 0):
            activenodes.append(n)
    et.nodes = activenodes
    et.setRelaxSingle()
    et.initMetric(src)
    et.computeMetric(None)

    maxmetric = 0.0
    for n in et.nodes[::-1]: 
        if(n.metric < eotx.infinity):
            maxmetric = n.metric
            break

    # output
    #  make all links to source 1.0
    for n in et.nodes: unicast[n.id][2][src] = 1.0

    # then the rest
    for i in range(len(et.nodes)):
        ni = et.nodes[i]
        ui = unicast[ni.id]

        # print metric rate and pseudo-bcast next hop
        print '%s.ip %s.set %d %d FF:FF:FF:FF:FF:FF' % (ni.id, handle, int((maxmetric - ni.metric) * options.scale), ui[1]),
        print
      
        rng = i
        if(i == 0): rng = len(et.nodes) # everyone is "upstream" of source
        for j in range(rng):
            nj = et.nodes[j]
            uj = unicast[nj.id]
            txj = uj[0]
            p = uj[2].get(ni.id, 0.0)
            if(sum(txj) * p > 0.0005):
                print '%s.ip %s.inflow ' % (ni.id, handle),
                for d in range(len(dsts)):
                    print '%.3f' % (txj[d] * p),
                print
        txi = ui[0]
        if(sum(txi) > 0.0):
            # print outflow
            print '%s.ip %s.outflow ' % (ni.id, handle),
            for d in range(len(dsts)):
                print '%.3f' % (txi[d]),
            print        
    return True

def main(argv):
    options, args = parse(argv)
    handle = args[0]
    src = args[1]
    dsts = args[2:]

    getLinks(options)
    eotx.Node.PACKETSIZE = options.size

    if(options.cheatlist != '-'):
        cheatLinks(options)

    options.linksett = None
    if(options.metric == 'etx' or options.prune == 'metric-up-fs'):
        options.linksett = etx.linksETT(options.links, options.backlinks, eotx.Node.PACKETSIZE)

    if(not options.multicast and len(dsts) == 1):
        dst = dsts[0]
        e = eotx.EOTX(options.links, options.linksett)
        if(not computeUnicast(options, e, src, dst)):
            return 1
        outputUnicast(options, e, src, dst, handle)
        if(options.loads != ''):
            outputLoads(options, e, src, dst)
        if(options.zifile != ''):
            outputZi(options, e, src, dst)
    else:
        assert(options.format == 'more')
        if(not computeMulticast(options, src, dsts, handle)):
            return 1
        # output procedure

    return 0

if __name__ == '__main__':
    from sys import exit
    exit(main(argv))
