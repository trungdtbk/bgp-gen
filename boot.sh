#!/bin/bash

BGP_LOCAL_AS=`printenv BGP_LOCAL_AS`
BGP_PEER_AS=`printenv BGP_PEER_AS`
BGP_LOCAL_ADDR=`printenv BGP_LOCAL_ADDR`
BGP_PEER_ADDR=`printenv BGP_PEER_ADDR`
BGP_PEER_PORT=`printenv BGP_PEER_PORT`


if [ -z "${BGP_LOCAL_AS}" ]; then
    BGP_LOCAL_AS=65000
fi
if [ -z "${BGP_PEER_AS}" ]; then
    BGP_PEER_AS=65000
fi
if [ -z "${BGP_PEER_ADDR}" ]; then
    BGP_PEER_AS=127.0.0.1
fi
if [ -z "${BGP_LOCAL_ADDR}" ]; then
    BGP_LOCAL_ADDR=0.0.0.0
fi
if [ -z "${BGP_PEER_PORT}" ]; then
    BGP_PEER_PORT=179
fi

cd /yabgp/bin
./yabgpd --bgp-local_as $BGP_LOCAL_AS --bgp-local_addr $BGP_LOCAL_AS \
    --bgp-remote_as $BGP_PEER_AS --bgp-remote_addr $BGP_PEER_ADDR \
    --bgp-remote_port $BGP_PEER_PORT --rest-bind_host 0.0.0.0 \
    --rest-bind_port 8080 &
cd /bgp-update-gen/src
./bgp-update-gen.py --agent=yabgp
