"""Shared style kit for the static approval frames (background, type, ink).

Visual language taken from the user's reference screenshots:
  * light grey / white seamless background with a soft shimmer
    (radial falloff, diagonal sheen, film dust specks, fine grain, Orton glow)
  * monochrome, polished, slightly stylised objects (objects.py renders)
  * bold condensed ITALIC keyword + light italic lead line (Roboto Condensed,
    OFL), charcoal on light grey, soft drop shadow, hairline chromatic offset
  * depth layering: big numerals/words can sit BEHIND the object

"""
import math
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
OBJ = "."
OUT = "."

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
    width = int(font.getlength(text) + tr * (len(text) - 1)) + size * 2
    im = Image.new("L", (width, asc + desc + size // 2), 0)
    dr = ImageDraw.Draw(im)
    x = size // 2
    arrow = ImageFont.truetype("/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf", int(size * 0.9))
    if tracking == 0 and "→" not in text:
        dr.text((x, size // 4 + asc), text, font=font, fill=255, anchor="ls")
    else:
        xi = x
        for i, ch in enumerate(text):
            if ch == "→":
                dr.text((xi, size // 4 + asc - size * 0.04), ch, font=arrow, fill=255, anchor="ls")
            else:
                dr.text((xi, size // 4 + asc), ch, font=font, fill=255, anchor="ls")
            xi += (arrow.getlength(ch) + size * 0.06 if ch == "→" else font.getlength(ch)) + tr
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

