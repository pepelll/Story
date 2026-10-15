"""Concept board: «отсутствие 10 месяцев» — prison bars in 5 sequential stills.

01 ПОЯВЛЕНИЕ  a single bar rises into the empty pearl frame
02 РОСТ       bars grow in a staggered rhythm; a giant «10» fades in behind
03 РЕШЁТКА    the grid closes; «10 МЕСЯЦЕВ» is caged behind the bars
04 ТЕНЬ       3/4 angle, hard side light: bar stripes fall across wall + words
05 ФИНАЛ      close-up through soft foreground bars, sharp headline lock-up

Usage: python bars_board.py RENDER_DIR OUT_DIR
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import style
from style import W, H, F, background, text_mask, place, ink, vfade, over, finish, save, CHAR, MID

style.OBJ = sys.argv[1] if len(sys.argv) > 1 else "."
style.OUT = OUT = sys.argv[2] if len(sys.argv) > 2 else "."
os.makedirs(OUT, exist_ok=True)


def mask():
    return np.zeros((H, W), np.float32)


def lead(img, text, y, size=78, x=W / 2):
    m = mask()
    place(m, text_mask(text, F("Light", size)), x, y)
    return ink(img, m, MID, shadow=0.22, sh_off=(4, 6), sh_blur=4)


frames = []

# 01 — appearance
img = background(11, cx=0.5, cy=0.45)
img = lead(img, "отсутствие", 610)
img = over(img, style.load_obj("b1.png"), dy=120)
frames.append(("01", "ПОЯВЛЕНИЕ", finish(img, 11)))

# 02 — growth, giant 10 behind
img = background(12, cx=0.5, cy=0.45)
img = lead(img, "отсутствие", 360)
m = mask()
place(m, text_mask("10", F("Black", 820), -0.04), W / 2 - 20, 900)
img = ink(img, m, CHAR, shadow=0.0, grad=vfade(560, 1250, (0.12, 0.12, 0.13), (0.70, 0.70, 0.71)))
img = over(img, style.load_obj("b2.png"), dy=120)
frames.append(("02", "РОСТ", finish(img, 12)))

# 03 — the grid closes over the words
img = background(13, cx=0.5, cy=0.45)
m = mask()
place(m, text_mask("10 МЕСЯЦЕВ", F("Black", 196), -0.01), W / 2, 960)
img = ink(img, m, CHAR, shadow=0.5)
img = over(img, style.load_obj("b3.png"), dy=60)
img = lead(img, "отсутствие", 300, 84)
frames.append(("03", "РЕШЁТКА", finish(img, 13)))

# 04 — shadows: words on the wall, bar stripes fall across them
img = background(14, cx=0.35, cy=0.40, base=0.84)
img = lead(img, "отсутствие", 330, 84)
m = mask()
place(m, text_mask("10", F("Black", 330), -0.03), 300, 640)
place(m, text_mask("МЕСЯЦЕВ", F("Black", 150), -0.01), 330, 850)
img = ink(img, m, CHAR, shadow=0.35)
img = over(img, style.load_obj("b4.png"), dx=160, dy=60)
frames.append(("04", "ТЕНЬ", finish(img, 14)))

# 05 — close-up through soft bars, final lock-up
img = background(15, cx=0.5, cy=0.42, base=0.86)
m = mask()
place(m, text_mask("ОТСУТСТВИЕ", F("Black", 176), -0.01), W / 2, 900)
img = ink(img, m, CHAR, shadow=0.5)
m2 = mask()
place(m2, text_mask("10 месяцев", F("Light", 120)), W / 2, 1075)
img = ink(img, m2, MID, shadow=0.3, sh_off=(5, 7), sh_blur=5)
img = over(img, style.load_obj("b5.png"))
frames.append(("05", "ФИНАЛ", finish(img, 15)))

for n, name, im in frames:
    save(im, f"bars_{n}_{name.lower()}.png")

# ------------------------------------------------------------------ board
tw, th, gut, top, bot = 432, 768, 40, 190, 120
BW = 5 * tw + 6 * gut
BH = top + th + bot
board = Image.new("RGB", (BW, BH), (24, 24, 26))
dr = ImageDraw.Draw(board)
inter = lambda w, s: ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", s)
dr.text((gut, 58), "ОТСУТСТВИЕ 10 МЕСЯЦЕВ", font=F("Black", 72), fill=(236, 236, 236))
dr.text((gut, 140), "Concept board · prison bars · 5 sequential stills · grey/pearl monochrome", font=inter("Medium", 24),
        fill=(140, 140, 146))
for k, (n, name, im) in enumerate(frames):
    x = gut + k * (tw + gut)
    th_img = Image.fromarray((cv2.resize(im, (tw, th), interpolation=cv2.INTER_AREA) * 255 + 0.5).astype(np.uint8))
    board.paste(th_img, (x, top))
    dr.text((x, top + th + 26), n, font=inter("SemiBold", 26), fill=(236, 236, 236))
    dr.text((x + 50, top + th + 26), name, font=inter("Medium", 26), fill=(150, 150, 156))
    if k < 4:
        dr.text((x + tw + 8, top + th / 2 - 18), "→", font=inter("Medium", 28), fill=(110, 110, 116))
board.save(os.path.join(OUT, "bars_board_5_frames.png"))
print("wrote board")
