#!/usr/bin/env bash
# Полная пересборка: превью-кадры → финальный MP4 → проверка.
set -euo pipefail
cd "$(dirname "$0")"
python3 -I make_video.py --preview
python3 -I make_video.py
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames -of compact out/paper_money_cart.mp4
