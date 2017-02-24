#!/usr/bin/env python
import sys
import random
import time
import dpkt
import os
import json
import struct
import traceback
import ipaddr
from socket import inet_ntoa as inet_ntoa
from pybgpdump import BGPDump
import requests
from requests.auth import HTTPBasicAuth
import logging
from oslo_config import cfg

class TestAgent(object):

    def get_peers(self):
        return ['127.0.0.1']

    def send_update(self, update):
        print update

class ExaBGPAgent(object):

    def __init__(self, logger, bgp_srv_addr):
        self.logger = logger

    def get_peers(self):
        return []

    def send_update(self, update):
        raise NotImplementedError

class YaBGPAgent(object):

    def __init__(self, logger, bgp_srv_addr, user='admin', password='admin'):

        self.logger = logger
        self.auth = HTTPBasicAuth(user, password)
        self.url = 'http://%s/v1/' % bgp_srv_addr

    def get_peers(self):
        r = requests.get(self.url + 'peers', auth=self.auth)
        peers = r.json()
        self._peers = []
        for peer in peers['peers']:
            if peer['fsm'] == 'ESTABLISHED':
                self._peers.append(peer['remote_addr'])
        return self._peers

    def _send_yabgp_msgs(self, msgs):
        for peer_ip, msg in msgs.iteritems():
            headers = {'content-type':'application/json'}
            r = requests.post(
                    self.url + 'peer/%s/send/update' % peer_ip,
                    data=json.dumps(msg), auth=self.auth,
                    headers=headers)
            self.logger.debug('send_update %s to %s', msg, peer_ip)

    def _build_yabgp_msgs(self, update):
        yabgp_msgs = {}
        for peer_ip, data in update.iteritems():
            nlri = []
            withdraw = []
            attr = {}
            attr[3] = peer_ip
            attributes = data['attr']
            if 'next-hop' in attributes:
                attr[3] = attributes['next-hop']
            if 'origin' in attributes:
                attr[1] = attributes['origin']
            if 'as-path' in attributes:
                as_path = attributes['as-path']
                if 'as-seq' in as_path:
                    attr[2] = [[2, as_path['as-seq']]]
                else:
                    attr[2] = [[1, as_path['as-seq']]]
            if 'local-pref' in attributes:
                attr[5] = attributes['local-pref']
            if 'nlri' in data:
                nlri = data['nlri']
            if 'withdraw' in data:
                withdraw = data['withdraw']
            yabgp_msgs[peer_ip] = {'attr':attr, 'nlri':nlri, 'withdraw':withdraw}
        return yabgp_msgs

    def send_update(self, update):
        """update format:
        { "10.0.0.1": {
            'attr': {
                'as-path' [10 20 30],
                'local-pref': 100,
                'next-hop': '10.0.0.250',
                'comm': '65000:100',
                'med': 100,
                'origin': 'incomplete'
                },
            'nlri': ["1.0.0.0/24", "2.0.0.0/24"]
            'withdraw': ["3.0.0.0/24']
            }
        }
        """
        msgs = self._build_yabgp_msgs(update)
        self._send_yabgp_msgs(msgs)

class BGPUpdateGenerator(object):

    MODES = ['RAND', 'MRT_FILE']
    GEN_TYPES = ['ANNOUNCE', 'WITHDRAW', 'MIXED']
    BGP_SERVERS = ['EXABGP', 'YABGP', 'TEST']

    def __init__(self):

        self.logfile = os.getenv('BGPGEN_LOGFILE', '')
        self.mode = os.getenv('BGPGEN_MODE', 'RAND').upper()
        self.gen_type = os.getenv('BGPGEN_TYPE', 'MIXED').upper()
        self.update_count = int(os.getenv('BGPGEN_COUNT', 0))
        self.update_per_sec = int(os.getenv('BGPGEN_RATE', 1))
        self.max_prefix_per_update = int(os.getenv('BGPGEN_MAX_PREFIX', 4))
        self.bgp_agent = os.getenv('BGPGEN_AGENT', 'test').upper()
        self.srv_addr = os.getenv('BGPGEN_SRV_ADDR', '127.0.0.1:8080')
        self.nexthop_range = os.getenv('BGPGEN_NEXTHOP_RANGE', '10.0.0.1-10.0.0.5')

        self.logger = logging.getLogger('bgp-gen')
        self.logger.setLevel(logging.DEBUG)
        s_handler = logging.StreamHandler()
        s_handler.setLevel(logging.INFO)
        self.logger.addHandler(s_handler)
        if self.logfile:
            f_handler = logging.FileHandler(self.logfile, mode='w')
            self.logger.addHandler(f_handler)

        try:
            ip_min, ip_max = self.nexthop_range.split('-')
            ip_min = ipaddr.IPAddress(ip_min)
            ip_max = ipaddr.IPAddress(ip_max)
            self.nexthop_range = []
            for ip in range(ip_min, ip_max):
                self.nexthop_range.append(str(ipaddr.IPAddress(ip)))
        except:
            self.nexthop_range = None

        self.bgpagent = None
        if self.bgp_agent in self.BGP_SERVERS:
            if self.bgp_agent == 'TEST':
                self.bgpagent = TestAgent()
            elif self.bgp_agent == 'YABGP':
                self.bgpagent = YaBGPAgent(self.logger, self.srv_addr)
            else:
                self.bgpagent = ExaBGPAgent(self.logger, srv_addr)

        if self.mode not in self.MODES:
            self.mode = 'RAND'

        if self.gen_type not in self.GEN_TYPES:
            self.gen_type = 'MIXED'

        self.mrt_file = os.getenv('BGPGEN_MRT_FILE')

    def run(self):
        self.logger.info(
                '\nBGPUpdateGen running with params: ' \
                'run mode=%s, agent=%s, server_addr=%s, mrt_file=%s, ' \
                'max-prefix-per-update=%s, number-updates=%s, ' \
                'update-rate=%s, nexthop range=%s',
            self.mode, self.bgp_agent, self.srv_addr, self.mrt_file,
            self.max_prefix_per_update, self.update_count,
            self.update_per_sec, self.nexthop_range)
        self._peers = None
        self.logger.info('Waiting for BGP session established')
        while self._peers is None:
            try:
                self._peers = self.bgpagent.get_peers()
                time.sleep(5)
            except KeyboardInterrupt:
                return "Stopped by user"
            except:
                time.sleep(5)
        self.logger.info('Sending updates...')
        if self.mode == 'MRT_FILE':
            self._send_update_from_mrt_file(self.mrt_file)
        else:
            self._send_rand_update()
        self.logger.info("\nBGPUpdateGen finished!. %s updates generated", self.count)

    def _gen_prefix(self):
        prefix = ".".join(map(str, (random.randint(0,255) for _ in range(3))))
        prefix += '.0/24'
        return prefix

    def _gen_prefixes(self, max_prefix):
        prefixes = []
        for _ in range(random.randint(1, max_prefix)):
            prefixes.append(self._gen_prefix())

        return prefixes

    def _get_rand_nexthop(self):
        if self.nexthop_range is None:
            return None
        idx = random.randint(0, len(self.nexthop_range)-1)
        return self.nexthop_range[idx]

    def _send_rand_update(self):
        updates = {}
        update = {}
        attr = {}
        attr['next-hop'] = None
        attr['as-path'] = {}
        attr['as-path']['as-seq'] = [10,20,30]
        attr['origin'] = 0
        update['attr'] = attr
        count = 0
        announced_prefixes = []
        while count < self.update_count or self.update_count == 0:
            update['nlri'] = []
            update['withdraw'] = []
            if self.gen_type == 'ANNOUNCE':
                update['nlri'] = self._gen_prefixes(self.max_prefix_per_update)
            elif self.gen_type == 'WITHDRAW':
                update['nlri'] = self._gen_prefixes(self.max_prefix_per_update)
            else:
                if random.randint(0,1):
                    if announced_prefixes:
                        idx = random.randint(0, len(announced_prefixes)-1)
                        update['withdraw'] = announced_prefixes.pop(idx)
                if random.randint(0,1):
                    nlri = self._gen_prefixes(self.max_prefix_per_update)
                    update['nlri'] = nlri
                    announced_prefixes.append(nlri)
            for peer_ip in self._peers:
                update['attr']['next-hop'] = self._get_rand_nexthop()
                updates[peer_ip] = update
            self.bgpagent.send_update(updates)
            count += 1
            time.sleep(1/self.update_per_sec)

        self.count = count

    def _send_update_from_mrt_file(self, filename):
        bgpdump = BGPDump(filename)
        mrt_m = bgp_h = bgp_m = None
        delay = 0.0
        prev_ts = 0
        count = 0
        while count < self.update_count or self.update_count == 0:
            try:
                (mrt_h, bgp_h, bgp_m) = bgpdump.next()
                if bgp_m.type == dpkt.bgp.UPDATE:
                    count += 1
                    update = {}
                    nlri = []
                    for p in bgp_m.update.announced:
                        nlri.append("%s/%d" % (inet_ntoa(p.prefix), p.len))
                    withdraw = []
                    for p in bgp_m.update.withdrawn:
                        withdraw.append("%s/%d" % (inet_ntoa(p.prefix), p.len))

                    attr = {}
                    for at in bgp_m.update.attributes:
                        if at.type == dpkt.bgp.NEXT_HOP:
                            attr['next-hop'] = inet_ntoa(
                                    struct.pack(b'I', at.next_hop.ip))
                        elif at.type == dpkt.bgp.ORIGIN:
                            attr['origin'] = at.origin.type
                        elif at.type == dpkt.bgp.AS_PATH:
                            attr['as-path'] = {}
                            for seg in at.as_path.segments:
                                type_ = seg.type
                                path = seg.path
                                if type_ == 1:
                                    attr['as-path']['as-set'] = path
                                else:
                                    attr['as-path']['as-seq'] = path
                        elif at.type == dpkt.bgp.MULTI_EXIT_DISC:
                            pass
                        elif at.type == dpkt.bgp.LOCAL_PREF:
                            attr['local-pref'] = at.value
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
                            nexthop = []
                            #nlri = []
                        elif at.type == dpkt.bgp.MP_UNREACH_NLRI:
                            #TODO: handle mp unreach message
                            pass

                    attr['next-hop'] = self._get_rand_nexthop()
                    update['attr'] = attr
                    update['nlri'] = nlri
                    update['withdraw'] = withdraw
                    updates = {}
                    for peer_ip in self._peers:
                        updates[peer_ip] = update
                    self.bgpagent.send_update(updates)
                    if prev_ts == 0:
                        delay = 0.01
                    else:
                        delay = mrt_h.ts - prev_ts
                    prev_ts = mrt_h.ts
                    time.sleep(delay)
            except Exception as e:
                traceback.print_exc()
                time.sleep(5)
        self.count = count

CONF = cfg.CONF
CONF.register_cli_opt(
        cfg.StrOpt('log', help='path to log file (default: no logging)'))
CONF.register_cli_opt(
        cfg.StrOpt('mode', help='generate mode: MRT_FILE or RAND (default)'))
CONF.register_cli_opt(
        cfg.StrOpt('mrt_file', help='path to mrt_file'))
CONF.register_cli_opt(
        cfg.StrOpt('agent', help='supported ExaBGP, YaBGP and Console (default)'))
CONF.register_cli_opt(
        cfg.StrOpt('srv_addr', help='bgp server addr e.g. 127.0.0.1:8080 (default)'))
CONF.register_cli_opt(
        cfg.StrOpt('count',
                   help='number of updates to send, 0=unlimited (default)'))
CONF.register_cli_opt(
        cfg.StrOpt('rate', help='number of updates per sec, default=1'))
CONF.register_cli_opt(
        cfg.StrOpt('max_prefix',
                   help='number of prefixes per update, default=1'))
CONF.register_cli_opt(
        cfg.StrOpt('type', help='announce or withdraw or mixed (default)'))
CONF.register_cli_opt(
        cfg.StrOpt('nexthop_range',
            help='a range of nexthop to choose from, default 10.0.0.1-10.0.0.5'))

if __name__ == '__main__':
    CONF(args=sys.argv[1:])
    if CONF.mode:
        os.environ['BGPGEN_MODE'] = CONF.mode
    if CONF.mrt_file:
        os.environ['BGPGEN_MRT_FILE'] = CONF.mrt_file
        os.environ['BGPGEN_MODE'] = 'MRT_FILE'
    if CONF.agent:
        os.environ['BGPGEN_AGENT'] = CONF.agent
    if CONF.srv_addr:
        os.environ['BGPGEN_SRV_ADDR'] = CONF.srv_addr
    if CONF.count:
        os.environ['BGPGEN_COUNT'] = CONF.count
    if CONF.rate:
        os.environ['BGPGEN_RATE'] = CONF.rate
    if CONF.max_prefix:
        os.environ['BGPGEN_MAX_PREFIX'] = CONF.max_prefix
    if CONF.log:
        os.environ['BGPGEN_LOGFILE'] = CONF.log
    if CONF.type:
        os.environ['BGPGEN_TYPE'] = CONF.type
    if CONF.nexthop_range:
        os.environ['BGPGEN_NEXTHOP_RANGE'] = CONF.nexthop_range
    bgp_gen = BGPUpdateGenerator()
    bgp_gen.run()
