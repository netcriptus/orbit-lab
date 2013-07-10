#!/usr/bin/python

from sys import argv, stderr
import wifi

""" EOTX and ETX for a single flow both use Dijkstra, relaxation is a bit different tho'
    For EOTT we need to chose the best rate in every relaxation.
    For ETT we can determine the best rate for each link in advance.
"""

# set to count transmissions not time
wifi.ETX = False
scale = 100.0

infinity = 1e3000

class Node:
    """ For EOTX computation.
    """
    PACKETSIZE = 1500

    def __init__(self, id, links, etts = None):
        """ Init with id and OWN links
            links: rate -> id -> prob
            ett: id -> (rate, ett)
        """
        self.id = id
        self.links = links
        self.etts = etts # only needed to speedup ETX

    def reset(self):
        self.metric = infinity
        # P = prob. that will retransmit and use self path
        # total = metric * (1-P)  [this part is additive!]
        # totalP = { rate : [total, P] }
        self.totalP = {}
        for rate in self.links.keys():
            self.totalP[rate] = [wifi.packetTime(Node.PACKETSIZE, rate), 1.0]
        self.rate = 0       # = Madwifi 802.11 bit-rate
        self.totalP[0] = [0.0, 1.0]
        self.P = 1.0        # = totalP[rate][1] [for load distribution]
        self.usedlinks = None

        self.loads = {}     # = x_ik
        self.load = 0.0     # = sumk x_ik
        self.tx = -1.0      # = load / (1-P)
        self.tt = 0.0       # = tx * packetTime(rate)
        self.next = self    # = argmax_k x_ik | next hop in ett
        self.rx = 0.0       # = E[number of packets heard from teachers]

    def __str__(self):
        return "%s m %.2f P %.3f l %.3f r %d t %.2f n %s" % (self.id, self.metric, self.P, self.load, self.rate, self.tx, self.next.id)

    def __cmp__(self, other):
        """ compare by metric!! """
        if(type(other) is type(self)):
            return cmp(self.metric, other.metric)
        if(type(other) is str):
            return cmp(self.id, other)
        raise Exception("can't compare to %s" % str(type(other)))


#### Here multi-rate is used to compute metric  -- Fan
    def relaxOpp(self, other):
        """ Relax this node's metric using the other node.
            We require strictly better metrics because
            ties are not good for information flow.
            !!! REQUIRES: other are given in order of increasing metric
        """
        if(self.metric > other.metric):  # excludes =
            """ Try to relax for each rate, find best rate. """
            best_rate, best_metric, best_P = 0, self.metric, 0.0

            for (rate, probs) in self.links.items():
                puv = probs.get(other.id, 0)
                if(puv == 0): continue

                [total, P] = tp = self.totalP[rate]
                total += other.metric * puv * P
                P *= (1 - puv)
                tp[:] = [total, P]

                if(best_metric * (1 - P) > total):
                    # found better candidate
                    best_rate, best_metric, best_P = rate, total / (1 - P), P

            if(best_rate > 0):
                self.rate = best_rate
                self.metric = best_metric
                self.P = best_P
                self.usedlinks = self.links[best_rate]

    def relaxSingle(self, other):
        """ Single-path relaxation.
            !!! REQUIRES: self.ett
            AND that other are given in order of increasing metric (to compute .P)
        """
        assert(self.etts is not None)
        ett, rate = self.etts.get(other.id, (0,0))
        if(rate == 0): return
        newmetric = other.metric + ett
        if(self.metric > newmetric):
            # found better
            self.rate = rate
            self.metric = newmetric
            self.next = other
            self.usedlinks = self.links[rate]


class EOTX:
    """ Computation state:
            nodes : array of nodes, preferrably in metric order
    """
    def __init__(self, links, etts = None):
        self.links = links
        self.etts = etts
        
        nodes = []
        for (id, ln) in self.links.items():
            ett = None
            if(etts is not None):
                ett = etts.get(id, None)
            n = Node(id, ln, ett)
            nodes.append(n)

        self.nodes = nodes
        # no order yet

    def initMetric(self, dst):
        # locate destination
        nodes = self.nodes
        try:
            dstpos = nodes.index(dst)
        except ValueError:
            raise Exception("Destination %s not found in the link table!" % dst)

        # compute EOTX :)
        nodes[dstpos].reset()
        nodes[dstpos].metric = 0.0
        # sort :P
        nodes[dstpos],nodes[0] = nodes[0],nodes[dstpos]

    def sortMetric(self):
        """ Needed after each pruning that could reorder nodes. """
        self.nodes.sort()

    def setRelaxSingle(self, nodes=None):
        if(nodes == None): nodes = self.nodes
        for n in nodes: n.relax = n.relaxSingle
    def setRelaxOpp(self, nodes=None):
        if(nodes == None): nodes = self.nodes
        for n in nodes: n.relax = n.relaxOpp

    def computeMetric(self, src):
        """ This is done in Dijkstra fashion. All nodes are in metric-order.
            In each iteration of the outer loop, < i nodes are closed and set,
            the i-th node is being visited, taken as a forwarder for other nodes.
            src is used only to stop early
            Complexity: O(n^2) // TODO: change to O(nlgn + m) ?
            REQUIRES: set self.relax() !!
        """
        nodes = self.nodes
        for n in nodes[1:]: n.reset()
        assert src in nodes

        # visit 0
        for i in range(1, len(nodes)):
            ni = nodes[i-1]
            if(src == ni.id):
                # we've the metric for src, let's stop
                del nodes[i:]
                """ NOTE: this is not exactly accurate because
                    we might want to use nodes with equal metric
                    but not according to Node.relaxOpp """
                return
            bestm, besti = nodes[i].metric, i

            # visit node i-1
            for j in range(i, len(nodes)):
                nodes[j].relax(ni)
                if(bestm > nodes[j].metric):
                    bestm, besti = nodes[j].metric, j

            # finish the order
            nodes[besti],nodes[i] = nodes[i],nodes[besti]

        assert(src == None or nodes[-1].id == src)
        

    def computeP(self):
        nodes = self.nodes
        for i in range(1, len(nodes)):
            ni = nodes[i]
            links = ni.links[ni.rate]
            P = 1.0
            for j in range(i):
                nj = nodes[j]
                if(nj.metric >= ni.metric): break
                puv = links.get(nodes[j].id, 0.0)
                P*= (1-puv)
            ni.P = P 

    def computeLoadOpp(self, src):
        """ Compute opportunistic load and best hop.
            Process nodes in topological order and distribute loads.
            Expected packet rate is computed by sending a flow from src
            and forwarding at all those who receive and have better metric.
            Complexity: O(n^2)
        """
        nodes = self.nodes
        for n in nodes:
            n.load = n.tx = n.rx = 0.0
            n.loads = {}

        if(len(nodes) == 1): return # degenerate case
        srcnode = nodes[-1]
        assert(srcnode.id == src)
        if(srcnode.rate == 0):
            return
            raise Exception("No route!")

        if(srcnode.P == 1.0):
            # need to compute P
            self.computeP()
        srcnode.load = 1.0
        # Expected rate is computed by sending a flow from src
        # and forwarding at all those who receive and have STRICTLY better metric
        for i in range(len(nodes)-1, 0, -1):
            ni = nodes[i]

            if(ni.load == 0.0):
                continue

            P = ni.P
            assert P < 1.0

            pt = ni.usedlinks

            # compute actual #tx from the load
            ni.tx = ni.load / (1 - P)

            P = 1.0
            bestp = 0.0 # for next
            for j in range(0, i):
                if(nodes[j].metric == ni.metric): # we don't want equal metrics
                    break
                puv = pt.get(nodes[j].id, 0)
                if(puv == 0.0): continue
                # compute the load on (u,v)
                ld = ni.tx * puv * P
                ni.loads[nodes[j].id] = ld
                # add to total load of v
                nodes[j].load += ld
                if(P * puv > bestp):
                    bestp = P * puv
                    ni.next = nodes[j]
                P *= (1 - puv)

                #if(P == 0.0): # no point continuing
                #    break
                # we have to continue to compute rx
                nodes[j].rx += ni.tx * puv # used in unicast only
            assert(P == ni.P)

            # compute this node's tx time
            ni.tt = ni.tx * wifi.packetTime(Node.PACKETSIZE, ni.rate)

    def computeLoadSingle(self, src):
        """ Compute single-path load and best hop. Nice for visualization
            Complexity: O(n)
        """
        assert(self.etts is not None)
        nodes = self.nodes
        for n in nodes: n.load = n.tx = n.tt = 0.0

        for n in nodes[1:]:
            if(n.rate == 0): continue
            n.load = 0.1 # for visualization
            n.loads = { n.next.id : 0.1 }
            n.tx = 1.0/(n.usedlinks[n.next.id])
            n.tt = n.etts[n.next.id][1]

        if(src is None):
            return 0,0

        if(len(nodes) == 1): return # degenerate case
        srcnode = nodes[-1]
        assert (srcnode.id == src)
        if(srcnode.rate == 0):
            return
            raise Exception("No route!")

        # boost the load on the single path
        n = srcnode
        n.load = 1.0
        while(n.metric > 0):
            n.loads[n.next.id] = 1.0
            assert(n != n.next)
            n = n.next
            n.load = 1.0

        # boost the load on extensions
        for n in nodes:
            if(n.load < 1.0 and n.next.load == 1.0):
                n.load = 0.5 # for visualization
                n.loads = { n.next.id : 0.5 }

    def pruneOnce(self, minLoad):
        """ Requires: computed load
            removes all nodes with insufficient load
            use 1.0 to leave shortest path
            use 0.5 to leave shortest path + extensions
        """
       

    def pruneZeroLoad(self):
        """ Requires: computed load
            Ensures: no nodes with load = 0 remain
            Preserves: node content and order
        """
        

    def totalTX(self):
        sumtx = sumtt = 0.0
        for n in self.nodes[1:]:
            sumtx += n.tx
            sumtt += n.tt
        if(sumtx == 0.0): sumtx = sumtt = infinity
        return sumtx, sumtt

    def minLoad(self):
        assert(len(self.nodes) > 1)
        return min([ (n.load, n) for n in self.nodes[1:] ])[1]

    """ ###########
        Three pruning methods are provided:
        -- ByLoad: pick smallest load -> remove
        -- ByMetric: pick smallest metric increase -> remove
        -- ByMetricUp: pick largest metric decrease -> add
        All take 2 params:
        minload = minimum load allowed in output [0.0]
        minfwd = minimum #nodes allowed in output [2]
        minrel = minimum relative metric change [0.0]
        These are tested at the last step.
    """ ###########
    def pruneLoad(self, src, minload=1.1, minfwd=2):
        """ Requires: computed load
            iteratively removes all nodes with insufficient load
        """
        

    def pruneMetricDown(self, src, minload=1.1, minfwd=2, maxloss=infinity):
        """ Requires: computed load
            removes nodes greedily so that the metric is max
        """
     

    def pruneMetricUp(self, src, minload=0.0, minfwd=None, single=False):
        """ Requires: init metric
            add nodes greedily so that the metric is max
        """
      

    def computeSourceRate(self):
        # compute source rate
        nodes = self.nodes
        nsrc = nodes[-1]
        sumtx = nsrc.tx
        # count tx in all that are connected
        pt = nsrc.links[nsrc.rate]
        for i in range(1, len(nodes)):
            ni = nodes[i]
            p = pt.get(ni.id, 0)
            if(p > 0.0):
                sumtx += ni.tx

        return nsrc.tx / sumtx

    def checkLoads(self, src):
        """ diagnostics only
            check load consistency
        """
        nodes = self.nodes[1:]
        inp = {}
        outp = {}
        mis = []
        for n in nodes:
            for (m, l) in n.loads.items():
                outp[n.id] = outp.get(n.id, 0) + l
                inp[m] = inp.get(m, 0) + l
        for n in nodes:
            i = inp.get(n.id, 0)
            o = outp.get(n.id, 0)
            l = n.load
            if(n.id == src):
                i = l
            if(abs(i-o) + abs(o-l) > 1e-5):
                print "MISMATCH ", i, o, l, "at", n
                mis.append(n.id)
        return mis

    def connected(self, src):
        idx = self.nodes.index(src)
        if(self.nodes[idx].metric == infinity):
            return False
        return True

    def neighborTX(self, node):
        sum = 0
        for n in self.nodes:
            if(n.tx > 0):
                if(n.usedlinks.get(node.id, 0) + node.usedlinks.get(n.id, 0) > 0):
                    sum+= n.tx
        return sum


