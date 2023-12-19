#!/bin/bash
./webrtc_client.py -d -n Aalborg -t butterbrot.org -f /dev/video0 -s /dev/video20 --persp "0.776637,-0.0148357,74.732,-0.0105345,0.783265,32.8821,-2.07266e-05,-3.60662e-05,0.996427" --out "queue max-size-time=100000000 leaky=downstream ! x264enc bitrate=6000 speed-preset=ultrafast tune=zerolatency key-int-max=15 ! video/x-h264,profile=constrained-baseline,stream-format=byte-stream ! queue ! h264parse config-interval=-1 ! rtph264pay config-interval=1 ! application/x-rtp,media=video,encoding-name=H264,payload=96 ! udpsink host=spiderpi.lan port=3000"