#!/usr/bin/env python
import os, sys, time
from datetime import datetime
import yaml
from _pybgpstream import BGPStream, BGPRecord, BGPElem

stream = BGPStream()

class BGPStreamReader(object):
    defaults = {
        'mrt_file': None,
        'collector': 'rrc00',
        'record_type': 'update',
        'from_date': int(time.time())i - 3600*24*7, # back up a week
        'until_date': 0,
        'prefix_filter': None,
        'peer_as_filter': None,
        'communities_filter': None,
    }

    def __init__(self, config={}):
        self.config = config
        for k, v in self.defaults.items():
            self.config.setdefault(k, v)
        if self.config['mrt_file'] is None:
            stream.add_filter('collector', self.config['collector'])
            stream.add_filter('record-type', self.config['record_type'])
            stream.add_interval_filter(self.config['from_date'], self.config['until_date'])
            stream.set_live_mode()
        else:
            stream.set_data_interface('singlefile')
            stream.set_data_interface_option('singlefile', 'upd-file', self.config['mrt_file'])
        if self.config['prefix_filter']:
            for prefix in self.config['prefix_filter']:
                stream.add_filter('prefix', prefix)
        if self.config['peer_as_filter']:
            for asn in self.config['peer_as_filter']:
                stream.add_filter('peer-asn', str(asn))
        if self.config['communities_filter']:
            for community in self.config['communities_filter']:
                stream.add_filter('community', community)
        stream.start()
        print('BGPSteamReader has started')

    def __iter__(self):
        return self

    def next(self):
        rec = BGPRecord()
        print('get next rec')
        if stream.get_next_record(rec):
            if rec.status == 'valid':
                elem = rec.get_next_elem()
                timestamp = rec.time
                nlri = []
                withdraw = []
                attr = {}
                while(elem):
                    peer_address = elem.peer_address
                    peer_asn = elem.peer_asn
                    if elem.type == 'A' or elem.type == 'R':
                        nlri.append(elem.fields['prefix'])
                        attr['as_path'] = elem.fields['as-path']
                        attr['nexthop'] = elem.fields['next-hop']
                        attr['community'] = elem.fields['communities']
                    elif elem.type == 'W':
                        withdraw.append(elem.fields['prefix'])
                    elem = rec.get_next_elem()
                return (timestamp, attr, nlri, withdraw)
            else:
                return self.next(rec)
        else:
            StopIteration

if __name__=='__main__':
    stream = BGPStreamGenerator("")
    stream.run()
