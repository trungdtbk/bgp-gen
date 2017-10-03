#!/usr/bin/env python
import os
import sys
import time
import logging
from datetime import datetime
import yaml
from _pybgpstream import BGPStream, BGPRecord, BGPElem

class BGPStreamGenerator(object):

    upd_file = None
    rib_file = None
    collector = None
    record_type = None
    from_date = None
    to_date = None
    prefix_filter = None
    peer_as_filter = None
    communities_filter = None
    asn_to_nexthop = None
    delay = None

    defaults = {
        'upd_file': None,
        'rib_file': None,
        'collector': 'rrc00',
        'record_type': 'update',
        'from_date': '2017-01-01',
        'to_date': None,
        'prefix_filter': None,
        'peer_as_filter': None,
        'communities_filter': None,
        'asn_to_nexthop': {},
        'delay': 0.1,
    }


    def __init__(self, logname):
        self.logfile = '/var/log/bgp_gen/bgp_gen.log'
        if 'BGP_GEN_LOG' in os.environ:
            self.logfile = os.environ['BGP_GEN_LOG']
        self.logger = logging.getLogger(logname + 'bgp_gen')
        self.logger.setLevel(logging.INFO)
        fh = logging.FileHandler(self.logfile)
        fh.setLevel(logging.INFO)
        self.logger.addHandler(fh)
        self.config_file = '/etc/bgp_gen/ben_gen.yaml'
        if len(sys.argv) == 2:
            self.config_file = sys.argv[1]
        elif 'BGP_GEN_CONFIG' in os.environ:
            self.config_file = os.environ['BGP_GEN_CONFIG']
        self.load_config()

    def load_config(self):
        try:
            with open(self.config_file) as f:
                self.config = yaml.load(f)
                self.__dict__.update(self.config)
                for key, value in list(self.defaults.items()):
                    if key not in self.__dict__ or self.__dict__[key] is None:
                        self.__dict__[key] = value
                if self.to_date is None:
                    self.to_date = 0
                else:
                    self.to_date = int(time.mktime(self.to_date.timetuple()))
                self.from_date = int(time.mktime(self.from_date.timetuple()))
        except Exception as e:
            self.logger.error('Error encountered when loading config %s', e)
            sys.exit(-1)

    def run(self):
        stream = BGPStream()
        rec = BGPRecord()
        if self.upd_file is None:
            stream.add_filter('collector', self.collector)
            stream.add_filter('record-type', self.record_type)
            stream.add_interval_filter(self.from_date, self.to_date)
            stream.set_live_mode()
        else:
            stream.set_data_interface('singlefile')
            if self.upd_file:
                stream.set_data_interface_option('singlefile', 'upd-file', self.upd_file)
            if self.rib_file:
                stream.set_data_interface_option('singlefile', 'rib-file', self.rib_file)
        if self.prefix_filter is not None:
            for prefix in self.prefix_filter:
                stream.add_filter('prefix', prefix)
        if self.peer_as_filter:
            for asn in self.peer_as_filter:
                stream.add_filter('peer-asn', str(asn))
        if self.communities_filter:
            for community in self.communities_filter:
                stream.add_filter('community', community)
        stream.start()
        stream.get_next_record(rec)
        prev = rec.time
        while(stream.get_next_record(rec)):
            now = rec.time
            if rec.status == 'valid':
                elem = rec.get_next_elem()
                while(elem):
                    statement = None
                    peer_address = elem.peer_address
                    peer_asn = elem.peer_asn
                    if peer_asn in self.asn_to_nexthop:
                        if elem.type == 'A' or elem.type == 'R':
                            prefix = elem.fields['prefix']
                            as_path = elem.fields['as-path']
                            nexthop = elem.fields['next-hop']
                            if peer_asn in self.asn_to_nexthop:
                                nexthop = self.asn_to_nexthop[peer_asn]
                                statement = 'announce route %s next-hop %s as-path' \
                                    ' [ %s ]' % (prefix, nexthop, as_path)
                        elif elem.type == 'W':
                            prefix = elem.fields['prefix']
                            statement = 'withdraw route %s' % prefix
                    if statement:
                        sys.stdout.write("%s\n" % statement)
                        sys.stdout.flush()
                    elem = rec.get_next_elem()
            time.sleep(self.delay + now - prev)
            prev = now

if __name__=='__main__':
    stream = BGPStreamGenerator("")
    stream.run()
