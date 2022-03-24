#!/bin/bash

# VLC can't play Opus inside MP4 container
if ffmpeg -i "$1" |& grep Opus ; then
	# in that case, recode Opus as MP3...
	OUTPUT="${1/%.mp4/-fixed.mp4}"
	ffmpeg -i "$1" -acodec mp3 -vcodec copy -map 0:0 -map 0:1 -map 0:2 "$OUTPUT"
	# ... and replace original file
	mv "$OUTPUT" "$1"
fi

# play all video streams in parallel
vlc --sout-all --sout '#display' "$1"
