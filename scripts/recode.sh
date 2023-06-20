#!/bin/bash
OUTPUT="${1/%.mp4/-fixed.mp4}"

gst-launch-1.0 -v filesrc location="$1" ! qtdemux name=demux \
	demux.video_0 ! queue ! h264parse ! video/x-h264,stream-format=byte-stream ! filesink location=out0.264 \
  demux.video_1 ! queue ! h264parse ! video/x-h264,stream-format=byte-stream ! filesink location=out1.264 \
	demux.audio_0 ! queue ! opusparse ! opusdec ! wavenc ! filesink location=out.wav

ffmpeg -i out0.264 -i out1.264 -i out.wav -map 0 -map 1 -map 2 -acodec mp3 -vcodec copy "$OUTPUT"

rm out?.264 out.wav
