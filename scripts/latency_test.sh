#!/bin/bash

TARGET=localhost
TARGET=butterbrot.org

curl https://$TARGET:8080/quit
sleep 2

./webrtc_client.py --fake -t $TARGET -d -s "videotestsrc is-live=true pattern=smpte ! debugqroverlay" &
sleep 10
./webrtc_client.py --fake -t $TARGET -d --out "videoconvert ! zbar ! fpsdisplaysink" |& scripts/latency.py
