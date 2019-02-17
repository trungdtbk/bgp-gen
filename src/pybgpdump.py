"""Parse BGP updates from MRT file (uncompressed or compressed in bz2 or gz format.
"""
import gzip, bz2
import dpkt, struct
from socket import inet_ntoa as inet_ntoa

BZ2_MAGIC = '\x42\x5a\x68'
GZIP_MAGIC = dpkt.gzip.GZIP_MAGIC
MRT_HEADER_LEN = dpkt.mrt.MRTHeader.__hdr_len__
SUPPORTED_AFIS = ( dpkt.mrt.AFI_IPv4, )
SUPPORTED_TYPES = ( dpkt.bgp.UPDATE, )
BGP_MARKER = '\xff' * 16
class BGPDump:
    """A BGPDump object wraps around a MRT file. next() method can be used to get next updates from the file."""
    def __init__(self, filename):
        with open(filename, 'rb') as f:
            hdr = f.read(max(len(BZ2_MAGIC), len(GZIP_MAGIC)))
            if filename.endswith('.bz2') and hdr.startswith(BZ2_MAGIC.encode('utf-8')):
                self.fobj = bz2.BZ2File
            elif filename.endswith('.gz') and hdr.startswith(GZIP_MAGIC.encode('utf-8')):
                self.fobj = gzip.GzipFile
            else:
                self.fobj = open
        self.open(filename)

    def open(self, filename):
        self.f = self.fobj(filename, 'rb')

    def close(self):
        self.f.close()
        raise StopIteration

    def __iter__(self):
        return self

    def next(self):
        mrt_h = bgp_h = bgp_m = None
        while True:
            try:
                s = self.f.read(MRT_HEADER_LEN)
                if len(s) < MRT_HEADER_LEN:
                    self.close()
                    break

                mrt_h = dpkt.mrt.MRTHeader(s)
                s = self.f.read(mrt_h.len)
                if len(s) < mrt_h.len:
                    self.close()
                    break

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
                break
            except:
                pass
        if mrt_h is None or bgp_h is None or bgp_m is None:
            StopIteration
        if bgp_m.type != dpkt.bgp.UPDATE:
            print(bgp_m.type, 'not an update')
            return self.next()
        nlri = []
        for p in bgp_m.update.announced:
            nlri.append("%s/%d" % (inet_ntoa(p.prefix), p.len))
        withdraw = []
        for p in bgp_m.update.withdrawn:
            withdraw.append("%s/%d" % (inet_ntoa(p.prefix), p.len))
        attr = {}
        for at in bgp_m.update.attributes:
            if at.type == dpkt.bgp.NEXT_HOP:
                attr['nexthop'] = inet_ntoa(
                        struct.pack(b'I', at.next_hop.ip))
            elif at.type == dpkt.bgp.ORIGIN:
                attr['origin'] = at.origin.type
            elif at.type == dpkt.bgp.AS_PATH:
                attr['as_path'] = at.as_path.segments
            elif at.type == dpkt.bgp.MULTI_EXIT_DISC:
                attr['med'] = at.multi_exit_disc.value
            elif at.type == dpkt.bgp.LOCAL_PREF:
                attr['local_pref'] = at.local_pref.value
            elif at.type == dpkt.bgp.COMMUNITIES:
                attr['community'] = at.communities.list
            elif at.type == dpkt.bgp.MP_REACH_NLRI:
                #TODO: Handle message with mp reach
                mp_reach = at.mp_reach_nlri
                afi_safi = [mp_reach.afi, mp_reach.safi]
                nexthop = []
            elif at.type == dpkt.bgp.MP_UNREACH_NLRI:
                #TODO: handle mp unreach message
                pass
        return (mrt_h.ts, attr, nlri, withdraw)
