#!/bin/bash
export GST_DEBUG_DUMP_DOT_DIR=.
while true ; do
	./webrtc_server.py --sink
	sleep 1
done
