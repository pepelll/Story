"""Static style-approval frames 01-05 (1080x1920). No animation.

Usage: python frames.py OBJ_DIR OUT_DIR
"""
import math
import os
import sys

import cv2
import numpy as np
from PIL import ImageFont

import style
from style import *  # noqa: F401,F403  (background, text_mask, place, ink, vfade, over, finish, ...)

style.OBJ = OBJ = sys.argv[1] if len(sys.argv) > 1 else "."
style.OUT = OUT = sys.argv[2] if len(sys.argv) > 2 else "."
os.makedirs(OUT, exist_ok=True)


# ================================================================== frame 1: ИДЕЯ (word behind object)
img = background(1, cx=0.62, cy=0.40)
mk = np.zeros((H, W), np.float32)
place(mk, text_mask("всё начинается с", F("Light", 66), 0.0), 360, 660)
mb = np.zeros((H, W), np.float32)
place(mb, text_mask("ИДЕИ", F("Black", 270), -0.01), 380, 830)
img = ink(img, mk, MID, shadow=0.25, sh_off=(4, 6), sh_blur=4)
img = ink(img, mb, CHAR, shadow=0.5, grad=vfade(760, 1000, (0.22, 0.22, 0.23), (0.10, 0.10, 0.11)))
img = over(img, load_obj("bulb.png"), dx=330, dy=260, scale=0.95)
save(finish(img, 1), "01_idea.png")

# ================================================================== frame 2: ДЕЙСТВИЕ (title over object)
img = background(2, cx=0.45, cy=0.55)
img = over(img, load_obj("dominoes.png"), dx=0, dy=220, scale=1.0)
mk = np.zeros((H, W), np.float32)
place(mk, text_mask("один шаг запускает", F("Light", 70)), W / 2, 420)
mb = np.zeros((H, W), np.float32)
place(mb, text_mask("ДЕЙСТВИЕ", F("Black", 210), -0.01), W / 2, 570)
img = ink(img, mk, MID, shadow=0.25, sh_off=(4, 6), sh_blur=4)
img = ink(img, mb, CHAR, shadow=0.55)
# hairline underline, like the "ДОХ*ДА ОТДАЛ" reference
cv2.line(img, (170, 690), (930, 676), (0.18, 0.18, 0.19), 3, cv2.LINE_AA)
save(finish(img, 2), "02_action.png")

# ================================================================== frame 3: РЕЗУЛЬТАТ (number behind coin)
img = background(3, cx=0.5, cy=0.5)
mk = np.zeros((H, W), np.float32)
place(mk, text_mask("ДОХОД ЗА ГОД,  ₽", F("Light", 58), 0.42), W / 2, 640)
img = ink(img, mk, MID, shadow=0.2, sh_off=(3, 5), sh_blur=3)
mb = np.zeros((H, W), np.float32)
place(mb, text_mask("1 000 000", F("Black", 250), -0.03), W / 2, 860)
img = ink(img, mb, CHAR, shadow=0.0, grad=vfade(760, 1000, (0.10, 0.10, 0.11), (0.62, 0.62, 0.63)))
img = over(img, load_obj("coins.png"), dx=0, dy=440, scale=0.7)
save(finish(img, 3), "03_result.png")

# ================================================================== frame 4: dossier card (graphic insert)
img = background(4, cx=0.5, cy=0.45, base=0.82)
card_w, card_h = 760, 1000
card = np.ones((card_h, card_w, 3), np.float32) * 0.975
for gx in range(0, card_w, 38):  # grid paper
    card[:, gx:gx + 1] *= 0.86
for gy in range(0, card_h, 38):
    card[gy:gy + 1, :] *= 0.86
card_mask = np.ones((card_h, card_w), np.float32)
# text on the card
cm = np.zeros((card_h, card_w), np.float32)


def card_place(mask, m, x, y):
    h, w = m.shape
    mask[y:y + h, x:x + w] = np.maximum(mask[y:y + h, x:x + w], m[:card_h - y, :card_w - x][:h, :w])


card_place(cm, text_mask("Идея", F("Medium", 78)), 56, 70)
card_place(cm, text_mask("ДЕЙСТВИЕ", F("Black", 150), -0.01), 50, 560)
card_place(cm, text_mask("→ РЕЗУЛЬТАТ", F("ExtraBold", 92)), 56, 760)
cmask3 = cm[..., None]
card = card * (1 - cmask3) + cmask3 * np.array(CHAR, np.float32)
# dotted hand-drawn arrow from "Идея" down to ДЕЙСТВИЕ
pts = [(120 + 60 * math.sin(t * 2.6) + 70 * t, 190 + 330 * t) for t in np.linspace(0, 1, 40)]
for k, (x, y) in enumerate(pts):
    if k % 2 == 0:
        cv2.circle(card, (int(x), int(y)), 6, CHAR, -1, cv2.LINE_AA)
x1, y1 = pts[-1]
cv2.line(card, (int(x1), int(y1)), (int(x1 - 30), int(y1 - 34)), CHAR, 9, cv2.LINE_AA)
cv2.line(card, (int(x1), int(y1)), (int(x1 + 22), int(y1 - 40)), CHAR, 9, cv2.LINE_AA)
# polaroid with the bulb render (desaturated crop)
bulb = load_obj("bulb.png")
bg_p = np.ones((H, W, 3), np.float32) * 0.72
ph = over(bg_p, bulb)[300:1420, 120:1080]
ph = cv2.resize(ph, (330, 385), interpolation=cv2.INTER_AREA)
ph = (ph - 0.5) * 1.25 + 0.48
pol = np.ones((450, 370, 3), np.float32) * 0.985
pol[20:405, 20:350] = np.clip(ph, 0, 1)


def paste_rot(dst, src, cx, cy, ang, shadow=0.35):
    h, w = src.shape[:2]
    a = np.ones((h, w), np.float32)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1.0)
    cs, sn = abs(M[0, 0]), abs(M[0, 1])
    nw, nh = int(h * sn + w * cs), int(h * cs + w * sn)
    M[0, 2] += nw / 2 - w / 2
    M[1, 2] += nh / 2 - h / 2
    s2 = cv2.warpAffine(src, M, (nw, nh), flags=cv2.INTER_LANCZOS4)
    a2 = cv2.warpAffine(a, M, (nw, nh), flags=cv2.INTER_LINEAR)
    x0, y0 = int(cx - nw / 2), int(cy - nh / 2)
    reg = dst[y0:y0 + nh, x0:x0 + nw]
    if shadow:
        sh = cv2.GaussianBlur(np.pad(a2, 30)[18:18 + nh, 12:12 + nw], (0, 0), 14)
        reg *= (1 - shadow * sh)[..., None]
    reg[:] = reg * (1 - a2[..., None]) + s2 * a2[..., None]
    return dst


img = paste_rot(img, card, W / 2 - 30, 980, 3.0, 0.4)
img = paste_rot(img, pol, 760, 640, -8.0, 0.45)
clip = cv2.imread(os.path.join(OBJ, "clip.png"), cv2.IMREAD_UNCHANGED)
clip = cv2.cvtColor(clip, cv2.COLOR_BGRA2RGBA).astype(np.float32) / (65535.0 if clip.dtype == np.uint16 else 255.0)
clip = cv2.resize(clip, (300, 450), interpolation=cv2.INTER_AREA)
y0, x0 = 300, 560
reg = img[y0:y0 + 450, x0:x0 + 300]
reg[:] = reg * (1 - clip[..., 3:4]) + clip[..., :3]
save(finish(img, 4, 0.14), "04_dossier_card.png")

# ================================================================== frame 5: typography sheet
img = background(5, cx=0.5, cy=0.35, base=0.83)
rows = [
    ("Light Italic · lead line", F("Light", 66), "если ты не боишься", 300),
    ("Black Italic · keyword", F("Black", 150), "ДЕЙСТВОВАТЬ", 470),
    ("ExtraBold Italic · caption", F("ExtraBold", 110), "ИДЕЯ → РЕЗУЛЬТАТ", 760),
    ("Black Italic · numerals", F("Black", 250), "150К", 1010),
    ("Medium Italic · sub", F("Medium", 70), "при зарплате", 1190),
    ("Light Italic · tracked caps", F("Light", 54), "Д О Х О Д   З А   Г О Д", 1340),
]
lab = np.zeros((H, W), np.float32)
txt = np.zeros((H, W), np.float32)
for label, fnt, s, y in rows:
    place(txt, text_mask(s, fnt), W / 2, y)
    place(lab, text_mask(label.upper(), ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 22)), W / 2,
          y - fnt.size * 0.62 - 14)
img = ink(img, lab, (0.45, 0.45, 0.47), shadow=0)
img = ink(img, txt, CHAR, shadow=0.45)
# white-on-footage caption variant (for talking-head parts)
plate = np.zeros((420, W, 3), np.float32) + vfade(0, 420, (0.22, 0.22, 0.24), (0.10, 0.10, 0.11))[:420]
img[1460:1880] = plate
cap = np.zeros((H, W), np.float32)
place(cap, text_mask("тем меньше", F("Light", 68)), W / 2, 1585)
place(cap, text_mask("У НАС ВРЕМЕНИ", F("Black", 140), -0.01), W / 2, 1715)
img = ink(img, cap, (0.97, 0.97, 0.97), shadow=0.6, sh_off=(6, 8), sh_blur=8, glow=0.25)
lb = np.zeros((H, W), np.float32)
place(lb, text_mask("CAPTION OVER FOOTAGE", ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Medium.otf", 22), 0.1), W / 2, 1490)
img = ink(img, lb, (0.6, 0.6, 0.62), shadow=0)
save(finish(img, 5, 0.12), "05_typography_sheet.png")
