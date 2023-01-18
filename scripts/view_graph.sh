#!/bin/bash
pkill -USR1 -f webrtc_server.py
sleep 1
sed -i -e 's/\\\\//g' surfacestreams.dot
xdot surfacestreams.dot
