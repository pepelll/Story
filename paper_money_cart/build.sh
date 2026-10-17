#!/usr/bin/env bash
# Полная пересборка: превью-кадры → финальные MP4 (9:16 и 16:9) → проверка.
set -euo pipefail
cd "$(dirname "$0")"
for s in make_video.py make_video_16x9.py; do
  python3 -I "$s" --preview
  python3 -I "$s"
done
for f in out/paper_money_cart.mp4 out/paper_money_cart_16x9.mp4; do
  ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames -of compact "$f"
done
