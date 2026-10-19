#!/usr/bin/env bash
# Полная пересборка: звук → превью-кадры → видео → сведение → проверка.
set -euo pipefail
cd "$(dirname "$0")"
python3 -I audio/sfx.py out/sfx.wav
node render.cjs stills 0.5,1.3,2.0,2.9,3.45
node render.cjs final
ffmpeg -v error -y -i out/xagusd_silent.mp4 -i out/sfx.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -t 3.5 -movflags +faststart out/xagusd.mp4
rm out/xagusd_silent.mp4
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames -of compact out/xagusd.mp4
