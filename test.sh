#!/bin/bash

# on exit, kill the whole process group
trap 'trap - SIGTERM && kill 0' SIGINT SIGTERM EXIT

URL="https://localhost:8080/stream.html"

if [ "$1" = "" ] ; then
	echo Usage: $0 default\|firefox\|chrome\|live-front\|live-surf\|live-both
	exit 1
fi

xterm -e ./webrtc_server.py &
[ $(jobs -p | wc -l) = 1 ] || { echo "Server failed to start." ; exit 1 ; }
sleep 2.5

xterm -e ./webrtc_client.py --fake &
[ $(jobs -p | wc -l) = 2 ] || { echo "Client failed to start." ; exit 1 ; }
sleep 2.5
	
case "$1" in

	default)
		xterm -e ./webrtc_client.py --fake &
		sleep 20
		;;

	firefox)
		firefox "$URL"
		sleep 40
		;;

	chrome)
		/opt/google/chrome/chrome "$URL"
		sleep 40
		;;

	live-front)
		xterm -e ./webrtc_client.py --fake \
		-f "v4l2src device=/dev/video0 do-timestamp=true ! videorate ! videoconvert" \
		-s "videotestsrc is-live=true pattern=ball background-color=0x00FF00FF ! timeoverlay" &
		sleep 40
		;;

	live-surf)
		xterm -e ./webrtc_client.py --fake \
		-s "v4l2src device=/dev/video0 do-timestamp=true ! jpegdec ! videorate ! videoconvert" \
		-f "videotestsrc is-live=true pattern=smpte ! timeoverlay" &
		sleep 40
		;;

	live-both)
		xterm -e ./webrtc_client.py -s /dev/video-surf -f /dev/video-face &
		sleep 40
		;;

	persp*)
		xterm -e ./webrtc_client.py --fake -p 0.276051,-0.141577,408.683,-0.0140174,0.382771,129.458,-5.60278e-05,-0.00014859,0.846134 \
		-s "v4l2src device=/dev/video0 do-timestamp=true ! jpegdec ! videorate ! videoconvert" \
		-f "videotestsrc is-live=true pattern=smpte ! timeoverlay" &
		sleep 40
		;;

esac

