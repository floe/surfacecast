gst-launch-1.0 -tv udpsrc multicast-group=224.1.1.1 auto-multicast=true port=3000 ! application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96 ! rtph264depay ! avdec_h264 ! videoscale ! video/x-raw,width=1280,height=720 ! videoconvert ! video/x-raw,format=BGR ! v4l2sink device=/dev/video20
#gst-launch-1.0 -tv udpsrc multicast-group=224.1.1.1 auto-multicast=true port=3000 ! application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96 ! rtph264depay ! avdec_h264 ! videoconvert ! fpsdisplaysink sync=false
