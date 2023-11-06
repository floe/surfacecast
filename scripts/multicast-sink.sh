#!/bin/bash
export DISPLAY=":0.0"
SINK="videoscale ! video/x-raw,width=1280,height=720 ! videoconvert ! video/x-raw,format=BGR ! v4l2sink device=/dev/video20"
[ -e /dev/video20 ] || SINK="autovideosink" # fpsdisplaysink sync=false
gst-launch-1.0 -tv udpsrc port=3000 ! application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96 ! rtph264depay ! avdec_h264 ! videoconvert ! $SINK
