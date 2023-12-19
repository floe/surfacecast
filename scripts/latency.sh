#!/bin/bash

trap "trap - SIGTERM && kill -- -$$" SIGINT SIGTERM EXIT

TARGET=localhost
#TARGET=butterbrot.org

curl -k https://$TARGET:8080/quit
sleep 2

./webrtc_client.py --fake -t $TARGET -d --out "fakesink sync=false" -s "videotestsrc is-live=true pattern=ball ! timeoverlay ! debugqroverlay" &
./webrtc_client.py --fake -t $TARGET -d --out "videoconvert ! zbar ! fakesink sync=false" |& scripts/latency.py 0 &
sleep 60
curl -k https://$TARGET:8080/quit
