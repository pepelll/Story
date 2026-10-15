#!/usr/bin/env bash
# Full rebuild: 3D renders -> composite -> sound -> mux -> contact sheet + stills.
# Requires: python env with bpy==5.2.2 numpy scipy pillow opencv-python-headless, ffmpeg, imagemagick.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-python}"
RENDERS="${RENDERS:-$HERE/_renders}"
OUT="$HERE/deliverables"
mkdir -p "$RENDERS" "$OUT"

if [ "${SKIP_3D:-0}" != "1" ]; then
  # Cycles CPU, rendered on twos at 80% (864x1536); comp upsamples + flow-interpolates to 1080x1920@60
  RES_PCT=80 $PY "$HERE/blender/scene_idea.py"   -- out="$RENDERS/idea"   f0=0 f1=156 step=2 samples=24
  RES_PCT=80 $PY "$HERE/blender/scene_action.py" -- out="$RENDERS/action" f0=0 f1=162 step=2 samples=20
  RES_PCT=80 $PY "$HERE/blender/scene_result.py" -- out="$RENDERS/result" f0=0 f1=190 step=2 samples=20
fi

$PY "$HERE/comp/comp.py" --renders "$RENDERS" --out "$RENDERS/picture.mp4"
$PY "$HERE/audio/sfx.py" "$RENDERS/sfx.wav"

ffmpeg -y -v error -i "$RENDERS/picture.mp4" -i "$RENDERS/sfx.wav" -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 320k -ar 48000 -shortest -movflags +faststart \
  "$OUT/IDEA_ACTION_RESULT_test_1080x1920_60fps.mp4"

# contact sheet: every 15th frame (4 per second), timecoded
ffmpeg -y -v error -i "$OUT/IDEA_ACTION_RESULT_test_1080x1920_60fps.mp4" \
  -vf "select='not(mod(n\,15))',scale=270:-1,drawtext=fontfile=/usr/share/fonts/opentype/inter/Inter-SemiBold.otf:text='%{pts\:hms}':x=8:y=8:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=4,tile=8x5:padding=6:margin=6:color=0x111111" \
  -frames:v 1 "$OUT/contact_sheet.png"

# hero stills of the designer scenes (full-resolution composited frames)
$PY "$HERE/comp/comp.py" --renders "$RENDERS" --preview "$RENDERS/stills" --list 60,190,330,520
cp "$RENDERS/stills/g0060.png" "$OUT/still_0_title.png"
cp "$RENDERS/stills/g0190.png" "$OUT/still_1_idea_bulb.png"
cp "$RENDERS/stills/g0330.png" "$OUT/still_2_action_dominoes.png"
cp "$RENDERS/stills/g0520.png" "$OUT/still_3_result_coins.png"
echo "done -> $OUT"
