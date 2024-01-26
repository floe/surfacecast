#!/bin/bash
#SINK="video/x-raw,format=BGR ! v4l2sink device=/dev/video20"
SINK="fpsdisplaysink"
pgrep wayfire && SINK="waylandsink display=wayland-1 fullscreen=true"
gst-launch-1.0 -mtv udpsrc address=0.0.0.0 port=3000 ! application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96 ! rtpjitterbuffer ! rtph264depay ! avdec_h264 ! videoconvert ! $SINK
