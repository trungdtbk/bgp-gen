Python BGP update generator. It can generate updates (announcement/withdraw) from MRT
file or randomly generated ones to a BGPspeaker.

Required YaBGP or ExaBGP to run.

==============================
Generate updates from MRT file
==============================

- MRT file can be compressed in bz2 or gz
- Update rate based on relative timestamps in MRT file
- Support ORIGIN, ASPath, LOCAL-PREF
- Next hop will be generated randomly from a pre-defined range

=========================
Generate updates randomly
=========================

- Generate updates with random prefixes at fix rate
- Multiple prefixes per update
- It randomly generates announcements or withdrawals
- Number of prefixes per update will be randomly generated
- AS path is fixed [10 20 30]
- Support generating only announcements, or withdrawals or both (mixed)

==========
Parameters
==========

Parameters can be set via environment varibles or via commandline

- --mode (env BGPGEN_MODE): mode to run, either MRT_FILE or RAND (default)
- --type (env BGPGEN_TYPE): mode to run, either MRT_FILE or RAND (default)
- --mrt_file (env BGPGEN_MRT_FILE): path to mrt file
- --agent (env BGPGEN_AGENT): bgp agent to use. Currently supported YaBGP only.
- --srv_addr (env BGPGEN_SRV_ADDR): YaBGP server address (default 127.0.0.1:8080)
- --count (env BGPGEN_COUNT): number of updates to send, 0 to run infinitely.
- --rate (env BGPGEN_RATE): update rate, default 1 per second.
- --max_prefix (env BGPGEN_MAX_PREFIX): max number of prefixes per update, default 4.
- --next_hop_range (env BGPGEN_NEXTHOP_RANGE): range of nexthops to be used (randomly selected). Default (10.0.0.1-10.0.0.5)

==========
How to run
==========

1. Install and start YaBGP on any PC
------------------------------------
- from pip: pip install yabgp
- from source: git clone https://github.com/trungdtbk/yabgp

- cd yabgp/bin
- ./yabgp --bgp-local_as <ASN> --bgp-remmote_as <ASN> --bgp-remote_addr <IP> \
[--bgp-remote_port <PORT>] --rest-bind_host 0.0.0.0 --rest-bind_port 8080

2. Run BGP generator
--------------------
- git clone https://github.com/trungdtbk/bgp-update-gen
- cd bgp-update-gen/src
- ./bgp-update-gen

Run with Docker

A docker container with YaBGP installed and a script to run update generator.

1. from bgp-update-gen directory
- docker build -t bgp-update-gen .
- ENV:
- BGP_LOCAL_AS
- BGP_LOCAL_ADDR
- BGP_PEER_ADDR
- BGP_PEER_AS
- BGP_PEER_PORT
