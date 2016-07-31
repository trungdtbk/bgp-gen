#!/usr/bin/env python

import gzip, bz2
import dpkt

BZ2_MAGIC = '\x42\x5a\x68'
GZIP_MAGIC = dpkt.gzip.GZIP_MAGIC
MRT_HEADER_LEN = dpkt.mrt.MRTHeader.__hdr_len__
SUPPORTED_AFIS = ( dpkt.mrt.AFI_IPv4, )
SUPPORTED_TYPES = ( dpkt.bgp.UPDATE, )

class BGPDump:
    def __init__(self, filename):
        f = file(filename, 'rb')
        hdr = f.read(max(len(BZ2_MAGIC), len(GZIP_MAGIC)))
        f.close()

        if filename.endswith('.bz2') and hdr.startswith(BZ2_MAGIC):
            self.fobj = bz2.BZ2File
        elif filename.endswith('.gz') and hdr.startswith(GZIP_MAGIC):
            self.fobj = gzip.GzipFile
        else:
            self.fobj = file
        self.open(filename)

    def open(self, filename):
        self.f = self.fobj(filename, 'rb')

    def close(self):
        self.f.close()
        raise StopIteration

    def __iter__(self):
        return self

    def next(self):
        while True:
            s = self.f.read(MRT_HEADER_LEN)
            if len(s) < MRT_HEADER_LEN:
                print "header len too small"
                self.close()

            mrt_h = dpkt.mrt.MRTHeader(s)
            s = self.f.read(mrt_h.len)
            if len(s) < mrt_h.len:
                self.close()

            if mrt_h.type != dpkt.mrt.BGP4MP:
                continue

            if mrt_h.subtype == dpkt.mrt.BGP4MP_MESSAGE:
                bgp_h = dpkt.mrt.BGP4MPMessage(s)
            elif mrt_h.subtype == dpkt.mrt.BGP4MP_MESSAGE_32BIT_AS:
                bgp_h = dpkt.mrt.BGP4MPMessage_32(s)
            else:
                continue

            if bgp_h.family not in SUPPORTED_AFIS:
                continue
            bgp_m = dpkt.bgp.BGP(bgp_h.data)
            if bgp_m.type not in SUPPORTED_TYPES:
                continue
            if bgp_m.marker != '\xff' * 16:
                continue
            break
        return (mrt_h, bgp_h, bgp_m)
