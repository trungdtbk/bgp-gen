#!/usr/bin/env python
import sys
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
               help='announce prefixes e.g. \"1.0.0.0/24, 2.0.0.0/24\"'),
    cfg.StrOpt('withdraw_prefixes',
               help='withdraw prefixes e.g. \"1.0.0.0/24, 2.0.0.0/24\"')
]

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
    delay = 0
    prev_ts = 0
    while True:
        try:
            (mrt_h, bgp_h, bgp_m) = bgpdump.next()
            if prev_ts == 0:
                prev_ts = mrt_h.ts
            delay = mrt_h.ts - prev_ts

            if bgp_m.type == dpkt.bgp.UPDATE:
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
                        print "heell"
                        print afi_safi
                        nexthop = []
                        nlri = []
                        pref = []

                    elif at.type == dpkt.bgp.MP_UNREACH_NLRI:
                        #TODO: handle mp unreach message
                        pass

                attr['3'] = next_hop

                update['attr'] = attr

                time.sleep(delay+1)

                yagent.send_update(peerip, update)
        except Exception as e:
            #print e
            break


if __name__ == '__main__':
    CONF(args=sys.argv[1:])
    yagent = YabgpAgent(CONF.rest.host, CONF.rest.port,
                        CONF.rest.user, CONF.rest.passwd)

    if CONF.message.mrt:
        send_updates_from_file(yagent, CONF.peerip,
                CONF.attribute.nexthop, filename = CONF.message.mrt)

    if CONF.message.announce_prefixes:
        prefixes = CONF.message.announce_prefixes
        yagent.announce(peer_ip = CONF.peerip,
                    prefixes = prefixes.split(','),
                    as_path = [123], next_hop = CONF.attribute.nexthop)

    if CONF.message.withdraw_prefixes:
        prefixes = CONF.message.withdraw_prefixes
        yagent.withdraw(peer_ip = CONF.peerip,
                    prefixes = prefixes.split(','))
