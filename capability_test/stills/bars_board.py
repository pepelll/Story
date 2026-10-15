"""Concept board: «отсутствие 10 месяцев» — prison bars in 5 sequential stills.

Layout: text in the top half only, bars only in the bottom half, no overlap.
01 ПОЯВЛЕНИЕ  a single bar rises from the floor; lead word alone
02 РОСТ       bars grow in a staggered rhythm; giant «10» above
03 РЕШЁТКА    the riveted grid closes; «10 МЕСЯЦЕВ» headline
04 ТЕНЬ       3/4 view, back light: bar shadows stretch toward camera
05 ФИНАЛ      full-bleed row of bars along the bottom; final lock-up

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
# Layout rule: typography lives in the TOP zone (y < 900); the bar renders are
# framed in-camera to stay in the BOTTOM half (y > 1000). Nothing crosses.


def big(img, text, cx, cy, size, anchor="c", grad=None, shadow=0.45):
    m = mask()
    place(m, text_mask(text, F("Black", size), -0.015), cx, cy, anchor)
    return ink(img, m, CHAR, shadow=shadow, grad=grad)


def lead_l(img, text, x, y, size=80):
    m = mask()
    place(m, text_mask(text, F("Light", size)), x, y, "l")
    return ink(img, m, MID, shadow=0.22, sh_off=(4, 6), sh_blur=4)


# 01 — appearance: one word, one bar
img = background(11, cx=0.5, cy=0.35)
img = lead(img, "отсутствие", 600, 104)
img = over(img, style.load_obj("b1.png"))
frames.append(("01", "ПОЯВЛЕНИЕ", finish(img, 11)))

# 02 — growth: a giant 10 above the rising bars
img = background(12, cx=0.5, cy=0.35)
img = lead(img, "отсутствие", 290, 84)
img = big(img, "10", W / 2 - 15, 610, 560, grad=vfade(400, 840, (0.12, 0.12, 0.13), (0.55, 0.55, 0.56)), shadow=0.0)
img = over(img, style.load_obj("b2.png"))
frames.append(("02", "РОСТ", finish(img, 12)))

# 03 — the grid closes: full headline
img = background(13, cx=0.5, cy=0.35)
img = lead(img, "отсутствие", 430, 88)
img = big(img, "10 МЕСЯЦЕВ", W / 2, 600, 200)
cv2.line(img, (180, 735), (900, 722), (0.18, 0.18, 0.19), 3, cv2.LINE_AA)
img = over(img, style.load_obj("b3.png"))
frames.append(("03", "РЕШЁТКА", finish(img, 13)))

# 04 — shadow: left-aligned editorial stack, stripes run toward camera below
img = background(14, cx=0.35, cy=0.35, base=0.84)
img = lead_l(img, "отсутствие", 96, 300, 84)
img = big(img, "10", 80, 520, 380, anchor="l")
img = big(img, "МЕСЯЦЕВ", 88, 770, 170, anchor="l")
img = over(img, style.load_obj("b4.png"))
frames.append(("04", "ТЕНЬ", finish(img, 14)))

# 05 — final lock-up over a full-bleed row of bars
img = background(15, cx=0.5, cy=0.30, base=0.86)
img = big(img, "ОТСУТСТВИЕ", W / 2, 470, 182)
m2 = mask()
place(m2, text_mask("10 месяцев", F("Light", 128)), W / 2, 650)
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
