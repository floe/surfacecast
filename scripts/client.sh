#!/bin/bash
export DISPLAY=:0.0
while true ; do
	(sleep 10 && wmctrl -F -r surface -e 0,0,1200,-1,-1 && sleep 1 && wmctrl -F -r surface -b add,fullscreen && wmctrl -F -r front -b add,fullscreen) &
	./webrtc_client.py -t butterbrot.org -f /dev/video-surf -s /dev/video20
	clear
	echo Restarting, please wait...
	sleep $((2+$RANDOM/2000))
done
