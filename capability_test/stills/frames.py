"""Static style-approval frames (1080x1920). No animation.

Visual language taken from the user's reference screenshots:
  * light grey / white seamless background with a soft shimmer
    (radial falloff, diagonal sheen, film dust specks, fine grain, Orton glow)
  * monochrome, polished, slightly stylised objects (objects.py renders)
  * bold condensed ITALIC keyword + light italic lead line (Roboto Condensed,
    OFL), charcoal on light grey, soft drop shadow, hairline chromatic offset
  * depth layering: big numerals/words can sit BEHIND the object

Usage: python frames.py OBJ_DIR OUT_DIR
"""
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
OBJ = sys.argv[1] if len(sys.argv) > 1 else "."
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
os.makedirs(OUT, exist_ok=True)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)


def F(style, size):
    return ImageFont.truetype(os.path.join(FD, f"RobotoCondensed-{style}Italic.ttf"), size,
                              layout_engine=ImageFont.Layout.RAQM)


# ------------------------------------------------------------------ background
def background(seed=1, cx=0.5, cy=0.42, base=0.80, edge=0.56):
    rng = np.random.default_rng(seed)
    r = np.sqrt(((xx - W * cx) / (W * 0.95)) ** 2 + ((yy - H * cy) / (H * 0.62)) ** 2)
    v = edge + (base - edge) * np.exp(-r ** 2 * 1.6)
    # diagonal sheen bands -> the "shimmer"
    d = (xx * 0.62 + yy * 0.38) / W
    sheen = 0.035 * np.exp(-((d - 0.55) / 0.10) ** 2) + 0.02 * np.exp(-((d - 0.95) / 0.05) ** 2)
    # large soft mottling, like a lit paper sweep
    m = cv2.resize(rng.standard_normal((12, 7)).astype(np.float32), (W, H), interpolation=cv2.INTER_CUBIC)
    v = v + sheen + 0.012 * m
    img = np.repeat(v[..., None], 3, 2)
    img *= np.array([1.0, 1.0, 1.012], np.float32)  # hair cooler, like the refs
    # film dust: small soft specks, mostly light, a few dark
    for _ in range(70):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        rad = rng.uniform(1.0, 3.8)
        col = 1.0 if rng.random() < 0.8 else 0.25
        a = rng.uniform(0.15, 0.6)
        s = int(rad * 3) + 2
        x0, y0 = int(x) - s, int(y) - s
        if x0 < 0 or y0 < 0 or x0 + 2 * s >= W or y0 + 2 * s >= H:
            continue
        gy, gx = np.mgrid[-s:s, -s:s].astype(np.float32)
        sx = rng.uniform(0.6, 2.2)  # some specks are short streaks
        disc = np.exp(-((gx / sx) ** 2 + gy ** 2) / (2 * (rad * 0.5) ** 2))[..., None] * a
        img[y0:y0 + 2 * s, x0:x0 + 2 * s] = img[y0:y0 + 2 * s, x0:x0 + 2 * s] * (1 - disc) + col * disc
    return img


def finish(img, seed=0, glow=0.18):
    img = np.clip(img, 0, 1)
    # Orton-style soft glow (the dreamy bloom in the references)
    bl = cv2.GaussianBlur(img, (0, 0), 18)
    img = 1 - (1 - img) * (1 - bl * glow)  # screen
    # hairline chromatic offset at the edges
    M = cv2.getRotationMatrix2D((W / 2, H / 2), 0, 1.0012)
    img[..., 0] = cv2.warpAffine(img[..., 0], M, (W, H), borderMode=cv2.BORDER_REFLECT)
    vig = 1 - 0.18 * np.clip(np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) - 0.5, 0, None)
    img *= vig[..., None]
    rng = np.random.default_rng(100 + seed)
    n = cv2.resize(rng.standard_normal((H // 2, W // 2)).astype(np.float32), (W, H))
    img += n[..., None] * 0.018
    return np.clip(img, 0, 1)


# ------------------------------------------------------------------ text
def text_mask(text, font, tracking=0.0, skew=0.0):
    """Return an alpha mask (h,w) with kerning (RAQM) + tracking."""
    asc, desc = font.getmetrics()
    size = font.size
    tr = tracking * size
    width = int(font.getlength(text) + tr * (len(text) - 1)) + size
    im = Image.new("L", (width, asc + desc + size // 2), 0)
    dr = ImageDraw.Draw(im)
    x = size // 2
    if tracking == 0:
        dr.text((x, size // 4 + asc), text, font=font, fill=255, anchor="ls")
    else:
        for i, ch in enumerate(text):
            xi = x + font.getlength(text[:i]) + tr * i
            dr.text((xi, size // 4 + asc), ch, font=font, fill=255, anchor="ls")
    m = np.asarray(im, np.float32) / 255
    ys, xs = np.nonzero(m > 0.01)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def place(canvas_mask, m, cx, cy, anchor="c"):
    h, w = m.shape
    x0 = int(cx - w / 2) if anchor == "c" else int(cx)
    y0 = int(cy - h / 2)
    X0, Y0, X1, Y1 = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    canvas_mask[Y0:Y1, X0:X1] = np.maximum(canvas_mask[Y0:Y1, X0:X1], m[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0])
    return (x0, y0, w, h)


def ink(img, mask, color=(0.16, 0.16, 0.17), shadow=0.45, sh_off=(10, 14), sh_blur=10, grad=None, glow=0.0):
    m = mask[..., None]
    if shadow:
        sh = np.roll(np.roll(mask, sh_off[1], 0), sh_off[0], 1)
        sh = cv2.GaussianBlur(sh, (0, 0), sh_blur)[..., None]
        img = img * (1 - shadow * sh)
    fill = np.array(color, np.float32) if grad is None else grad
    img = img * (1 - m) + m * fill
    if glow:
        g = cv2.GaussianBlur(mask, (0, 0), 16)[..., None]
        img = 1 - (1 - img) * (1 - g * glow)
    return img


def vfade(y0, y1, c0, c1):
    t = np.clip((np.arange(H, dtype=np.float32) - y0) / (y1 - y0), 0, 1)[:, None, None]
    return np.array(c0, np.float32) * (1 - t) + np.array(c1, np.float32) * t


def load_obj(name):
    im = cv2.imread(os.path.join(OBJ, name), cv2.IMREAD_UNCHANGED)
    im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA).astype(np.float32) / (65535.0 if im.dtype == np.uint16 else 255.0)
    if im.shape[1] != W:
        im = cv2.resize(im, (W, H), interpolation=cv2.INTER_LANCZOS4)
    return im


def over(img, rgba, dx=0, dy=0, scale=1.0, rot=0.0):
    """Composite a premultiplied render (shadow-catcher alpha) over img."""
    if scale != 1 or dx or dy or rot:
        M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, scale)
        M[0, 2] += dx
        M[1, 2] += dy
        rgba = cv2.warpAffine(rgba, M, (W, H), flags=cv2.INTER_LANCZOS4, borderValue=(0, 0, 0, 0))
    a = rgba[..., 3:4]
    return img * (1 - a) + rgba[..., :3]


def save(img, name):
    cv2.imwrite(os.path.join(OUT, name), cv2.cvtColor((img * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
    print("wrote", name)


CHAR = (0.15, 0.15, 0.16)
MID = (0.28, 0.28, 0.30)

# ================================================================== frame 1: ИДЕЯ (word behind object)
img = background(1, cx=0.62, cy=0.40)
mk = np.zeros((H, W), np.float32)
place(mk, text_mask("всё начинается с", F("Light", 70), 0.0), 330, 700)
mb = np.zeros((H, W), np.float32)
place(mb, text_mask("ИДЕИ", F("Black", 300), -0.01), 360, 880)
img = ink(img, mk, MID, shadow=0.25, sh_off=(4, 6), sh_blur=4)
img = ink(img, mb, CHAR, shadow=0.5, grad=vfade(760, 1000, (0.22, 0.22, 0.23), (0.10, 0.10, 0.11)))
img = over(img, load_obj("bulb.png"), dx=150, dy=170, scale=1.0)
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
place(mk, text_mask("ДОХОД ЗА ГОД", F("Light", 58), 0.42), W / 2, 520)
img = ink(img, mk, MID, shadow=0.2, sh_off=(3, 5), sh_blur=3)
mb = np.zeros((H, W), np.float32)
place(mb, text_mask("1 000 000", F("Black", 270), -0.03), W / 2, 760)
img = ink(img, mb, CHAR, shadow=0.0, grad=vfade(650, 900, (0.10, 0.10, 0.11), (0.62, 0.62, 0.63)))
img = over(img, load_obj("coins.png"), dx=0, dy=330, scale=0.92)
mt = np.zeros((H, W), np.float32)
place(mt, text_mask("рублей", F("Medium", 76)), W / 2 + 250, 920)
img = ink(img, mt, MID, shadow=0.3, sh_off=(4, 6), sh_blur=5)
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
y0, x0 = 330, 700
reg = img[y0:y0 + 450, x0:x0 + 300]
reg[:] = reg * (1 - clip[..., 3:4]) + clip[..., :3]
save(finish(img, 4, 0.14), "04_dossier_card.png")

# ================================================================== frame 5: typography sheet
img = background(5, cx=0.5, cy=0.35, base=0.83)
rows = [
    ("Light Italic · lead line", F("Light", 66), "если ты не боишься", 300),
    ("Black Italic · keyword", F("Black", 190), "ДЕЙСТВОВАТЬ", 470),
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
