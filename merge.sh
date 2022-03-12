ffmpeg -i audio-20220312-170713.mp4 -i surface-20220312-170713.mp4 -i front-20220312-170713.mp4 -vcodec copy -map 0 -map 1 -map 2 test.mp4
