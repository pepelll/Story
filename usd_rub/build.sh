#!/usr/bin/env bash
# Полная пересборка: звук → превью-кадры → финальные файлы → проверка.
set -euo pipefail
cd "$(dirname "$0")"
REF=${1:-reference.mp4}
[ -f audio/perc.npy ] || python3 -I audio/hpss.py "$REF" audio/perc.npy
python3 -I audio/sfx.py audio/perc.npy public/sfx.wav
node render.mjs stills 6,18,30,42,66
node render.mjs final
# AAC добавляет хвост ~16 мс: пересобираем дорожку ровно на 1.2 с
ffmpeg -v error -i out/usd_rub.mp4 -i public/sfx.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 320k -t 1.2 -movflags +faststart -y out/tmp.mp4 && mv out/tmp.mp4 out/usd_rub.mp4
for f in out/usd_rub.mp4 out/usd_rub_alpha.mov; do
  ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames -of compact "$f"
done
