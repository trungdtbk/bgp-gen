#!/usr/bin/env python
import sys
import random
import time
import dpkt
from socket import inet_ntoa as inet_ntoa
from pybgpdump import BGPDump
from yabgpagent import YabgpAgent

from oslo_config import cfg


CONF = cfg.CONF

CONF.register_cli_opt(
    cfg.StrOpt('peerip', help='The BGP peer address'))

rest_server_ops = [
    cfg.StrOpt('host',
               default='0.0.0.0',
               help='Address to bind the API server to'),
    cfg.IntOpt('port',
               default=8801,
               help='Port the bind the API server to'),
    cfg.StrOpt('user',
               default='admin',
               help='Username for api server'),
    cfg.StrOpt('passwd',
               default='admin',
               help='Password for api server',
               secret=True)
]

CONF.register_cli_opts(rest_server_ops, group='rest')


msg_source_ops = [
    cfg.StrOpt('json',
               help='json format update messages'),
    cfg.StrOpt('list',
               help='yabgp raw message file'),
    cfg.StrOpt('mrt',
               help='bgp update file in mrt format'),
    cfg.StrOpt('announce_prefixes',
               help='announce prefixes e.g. \"1.0.0.0/24 2.0.0.0/24\"'),
    cfg.StrOpt('withdraw_prefixes',
               help='withdraw prefixes e.g. \"1.0.0.0/24 2.0.0.0/24\"'),
]

rand_ops = [
        cfg.StrOpt('m', help='number of prefixes per update'),
        cfg.StrOpt('n', help='total number of updates'),
        ]
CONF.register_cli_opts(rand_ops, group='rand')

CONF.register_cli_opts(msg_source_ops, group='message')

bgp_config_ops = [
    cfg.StrOpt('nexthop',
               help='new next hop address'),
    cfg.StrOpt('originator_id',
               help='new originator id'),
    cfg.ListOpt('cluster_list',
                help='new cluster list'
                ),
    cfg.BoolOpt('no_origin_cluster',
                default=True,
                help='remove originator id and cluster list')
]

CONF.register_cli_opts(bgp_config_ops, group='attribute')

# Send updates from a MRT file
def send_updates_from_file(yagent, peerip, next_hop, filename):
    print filename
    bgpdump = BGPDump(filename)
    mrt_m = bgp_h = bgp_m = None
    delay = 0.01
    prev_ts = 0
    count = 0
    while True:
        try:
            (mrt_h, bgp_h, bgp_m) = bgpdump.next()
            if bgp_m.type == dpkt.bgp.UPDATE:
                count += 1
                #TODO: send out an update
                update = {}

                an_prefixes = []
                for an in bgp_m.update.announced:
                    prefix = "%s/%d" % (inet_ntoa(an.prefix), an.len)
                    an_prefixes.append(prefix)

                update['nlri'] = an_prefixes

                wd_prefixes = []
                for wd in bgp_m.update.withdrawn:
                    prefix = "%s/%d" % (inet_ntoa(an.prefix), an.len)
                    wd_prefixes.append(prefix)

                update['withdraw'] = wd_prefixes

                attr = {}
                for at in bgp_m.update.attributes:
                    if at.type == dpkt.bgp.ORIGIN:
                        attr['1'] = at.origin.type
                    elif at.type == dpkt.bgp.AS_PATH:
                        attr['2'] = []
                        for seg in at.as_path.segments:
                            type_ = seg.type
                            path = seg.path
                            attr['2'].append( [type_, path] )
                    elif at.type == dpkt.bgp.MULTI_EXIT_DISC:
                        pass
                    elif at.type == dpkt.bgp.LOCAL_PREF:
                        pass
                    elif at.type == dpkt.bgp.ATOMIC_AGGREGATE:
                        pass
                    elif at.type == dpkt.bgp.AGGREGATOR:
                        pass
                    elif at.type == dpkt.bgp.COMMUNITIES:
                        pass
                    elif at.type == dpkt.bgp.ORIGINATOR_ID:
                        pass
                    elif at.type == dpkt.bgp.CLUSTER_LIST:
                        pass
                    elif at.type == dpkt.bgp.MP_REACH_NLRI:
                        #TODO: Handle message with mp reach
                        mp_reach = at.mp_reach_nlri
                        afi_safi = [mp_reach.afi, mp_reach.safi]
                        print afi_safi
                        nexthop = []
                        nlri = []
                        pref = []

                    elif at.type == dpkt.bgp.MP_UNREACH_NLRI:
                        #TODO: handle mp unreach message
                        pass

                attr['3'] = next_hop
                update['attr'] = attr
                yagent.send_update(peerip, update)
                if prev_ts == 0:
                    delay = 0.01
                else:
                    delay = mrt_h.ts - prev_ts
                    print count, delay, mrt_h.ts
                prev_ts = mrt_h.ts
                time.sleep(delay)
        except Exception as e:
            print e

def rand_announce(yagent, peerip, burst_delays, burst_updates, max_prefixes, total, attr):
    """
    Send random prefixes to a peer. Updates are sent in bursts.
    Delay between bursts ranges randomly between 10 and 20 seconds.
    Number of updates per burst ranges randomly between 5 and 20.
    Attributes of a update defined in a dict, example as below:
        attr={'1': 0, '2': [[2, [100,200,300]], '3': '10.0.0.1'}
        attr[1] # origin
        attr[2] # aspath
        attr[3] # nexthop
    :param: yagent: YaBGP agent
    :param: peerip: IP address of the BGP peer
    :param: burst_delays: a tuple of min & max delay in second between bursts.
    :param: burst_updates: a tuple of min & max update per burst.
    :param: n: number of prefixes in one update
    :param: total: number of bursts
    :param: attr: attributes for each update, in a dict format
    :return: returns nothing
    """
    burst_delay_min, burst_delay_max = burst_delays
    burst_update_min, burst_update_max = burst_updates
    base = "%d.%d.%d.0/24" # base prefix
    rand = random.Random()
    for i in range(total):
        burst_updates = rand.randint(burst_delay_min, burst_delay_max)
        for l in range(burst_updates):
            update = {}
            update['attr'] = attr
            prefixes = []
            for j in range(rand.randint(1, max_prefixes)):
                x = rand.randint(1, 220)
                y = rand.randint(0, 255)
                z = rand.randint(0, 255)
                prefixes.append(base % (x, y, z))
            update['nlri'] = prefixes
            yagent.send_update(peerip, update)
            time.sleep(0)
        time.sleep(rand.randint(burst_update_min, burst_update_max))

if __name__ == '__main__':
    burst_updates = 10 # continuous updates
    burst_delay = 10 #second
    CONF(args=sys.argv[1:])
    yagent = YabgpAgent(CONF.rest.host, CONF.rest.port,
                        CONF.rest.user, CONF.rest.passwd)

    peerip = CONF.peerip

    if CONF.message.mrt:
        send_updates_from_file(yagent, CONF.peerip,
                CONF.attribute.nexthop, filename = CONF.message.mrt)

    if CONF.message.announce_prefixes:
        prefixes = CONF.message.announce_prefixes
        yagent.announce(peer_ip = CONF.peerip,
                    prefixes = [p for p in prefixes.split(' ') if p],
                    as_path = [4000,100], next_hop = CONF.attribute.nexthop)

    if CONF.message.withdraw_prefixes:
        prefixes = CONF.message.withdraw_prefixes
        yagent.withdraw(peer_ip = CONF.peerip,
                    prefixes = [p for p in prefixes.split(' ') if p])
    # Generate prefixes randomly
    rand_m = CONF.rand.m
    rand_n = CONF.rand.n
    if rand_m and rand_n:
        rand_m = int(rand_m)
        rand_n = int(rand_n)
        print 'Generate announcement randomly with %d prefixes/update, %d update \
                ' % (rand_m, rand_n)
        attr = {'1': 0, '2': [[2,[2000,1000,100]]], '3': '172.0.0.1'}
        burst_delays = (1,10)
        burst_updates = (5,10)
        rand_announce(yagent, peerip, burst_delays=burst_delays,attr=attr,
                burst_updates=burst_updates,max_prefixes=rand_m, total=rand_n)
