"""Compositor: 3D plates + editorial typography + transitions + finishing -> 60 fps.

Pipeline per frame
  1. Plates: Cycles renders (rendered on twos at 864x1536) are Lanczos-upscaled
     to 1080x1920; odd frames are synthesised with bidirectional DIS optical
     flow so the 3D runs at a true 60 fps cadence.
  2. Digital camera: push-ins, drift, impact shakes (affine, sub-pixel).
  3. Transitions: radial zoom-through, whip pan with directional blur,
     burn-out light-leak flash.
  4. Typography (Inter Display, RAQM shaping, tight negative tracking):
     per-glyph blur-rise reveals, slams, glow + soft drop shadow.
  5. Finishing: multi-scale bloom/halation, chromatic aberration, vignette,
     animated film grain, floating dust motes.

Usage: python comp.py --renders DIR --out out.mp4 [--frames a:b] [--preview DIR]
"""
import argparse
import functools
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as T

W, H = 1080, 1920
FONT_DIR = "/usr/share/fonts/opentype/inter/"
RNG = np.random.default_rng(3)


# ===================================================================== easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(t):
    t = clamp(t)
    return t * t * t * (t * (6 * t - 15) + 10)


def out_expo(t):
    t = clamp(t)
    return 1.0 if t >= 1 else 1 - 2 ** (-10 * t)


def out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def in_cubic(t):
    t = clamp(t)
    return t ** 3


def out_back(t, s=1.4):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def prog(g, a, b):
    return clamp((g - a) / float(b - a))


# ===================================================================== plates
class Plates:
    """Serves a 1080x1920 float RGB frame for any (possibly odd) local frame."""

    def __init__(self, folder, last):
        self.folder, self.last = folder, last
        self.dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)

    @functools.lru_cache(maxsize=6)
    def raw(self, f):
        f = max(0, min(self.last, f))
        p = os.path.join(self.folder, f"f{f:04d}.png")
        im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
        if im is None:
            raise FileNotFoundError(p)
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB).astype(np.float32) / (65535.0 if im.dtype == np.uint16 else 255.0)
        if im.shape[1] != W:
            im = cv2.resize(im, (W, H), interpolation=cv2.INTER_LANCZOS4)
            bl = cv2.GaussianBlur(im, (0, 0), 1.1)
            im = np.clip(im + 0.35 * (im - bl), 0, None)  # restore crispness after upscale
        return im

    def _gray(self, im):
        g = cv2.cvtColor(np.clip(im, 0, 1), cv2.COLOR_RGB2GRAY)
        g = cv2.resize(g, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        return (np.power(g, 1 / 2.2) * 255).astype(np.uint8)

    @functools.lru_cache(maxsize=4)
    def mid(self, f):
        """Synthesise odd frame f from f-1 and f+1 (bidirectional flow warp)."""
        a, b = self.raw(f - 1), self.raw(f + 1)
        ga, gb = self._gray(a), self._gray(b)
        fab = self.dis.calc(ga, gb, None)
        fba = self.dis.calc(gb, ga, None)
        fab = cv2.resize(fab, (W, H)) * 2
        fba = cv2.resize(fba, (W, H)) * 2
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        wa = cv2.remap(a, xx - 0.5 * fab[..., 0], yy - 0.5 * fab[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        wb = cv2.remap(b, xx - 0.5 * fba[..., 0], yy - 0.5 * fba[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return 0.5 * (wa + wb)

    def get(self, f):
        f = int(round(f))
        f = max(0, min(self.last, f))
        if f % 2 == 0 or f >= self.last:
            return self.raw(f - (f % 2)).copy()
        return self.mid(f).copy()


# ===================================================================== typography
@functools.lru_cache(maxsize=None)
def font(weight, size):
    return ImageFont.truetype(f"{FONT_DIR}InterDisplay-{weight}.otf", size, layout_engine=ImageFont.Layout.RAQM)


class Line:
    """A line of text split into per-glyph alpha sprites with kerning + tracking."""

    def __init__(self, text, weight="Bold", size=120, tracking=-0.035, features=None):
        self.text, self.size = text, size
        f = font(weight, size)
        feats = features or []
        tr = tracking * size
        self.glyphs = []
        asc, desc = f.getmetrics()
        pad = int(size * 0.25)
        for i, ch in enumerate(text):
            x = f.getlength(text[:i], features=feats) + tr * i
            if ch == " ":
                continue
            wch = int(f.getlength(ch, features=feats)) + 2 * pad
            im = Image.new("L", (wch, asc + desc + 2 * pad), 0)
            ImageDraw.Draw(im).text((pad, pad + asc), ch, font=f, fill=255, anchor="ls", features=feats)
            self.glyphs.append(dict(img=np.asarray(im, np.float32) / 255.0, x=x - pad, y=-asc - pad, ch=ch, i=i))
        self.width = f.getlength(text, features=feats) + tr * (len(text) - 1)
        self.asc = asc
        self.cap = size * 0.727  # Inter cap height


def paste_max(canvas, spr, x, y, alpha=1.0):
    h, w = spr.shape
    x0, y0 = int(math.floor(x)), int(math.floor(y))
    fx, fy = x - x0, y - y0
    if fx or fy:  # sub-pixel placement keeps slow moves smooth
        M = np.float32([[1, 0, fx], [0, 1, fy]])
        spr = cv2.warpAffine(spr, M, (w + 1, h + 1))
        h, w = spr.shape
    X0, Y0 = max(0, x0), max(0, y0)
    X1, Y1 = min(canvas.shape[1], x0 + w), min(canvas.shape[0], y0 + h)
    if X1 <= X0 or Y1 <= Y0:
        return
    sub = spr[Y0 - y0:Y1 - y0, X0 - x0:X1 - x0] * alpha
    np.maximum(canvas[Y0:Y1, X0:X1], sub, out=canvas[Y0:Y1, X0:X1])


def draw_line(mask, line, cx, baseline, t, style="rise", stagger=1.6, dur=14, scale=1.0, alpha=1.0):
    """Render `line` into `mask` (H×W float). t = frames since the line started."""
    left = cx - line.width * scale / 2
    n = len(line.glyphs)
    for k, g in enumerate(line.glyphs):
        if style == "rise":
            p = (t - k * stagger) / dur
            e = out_expo(p)
            dy = (1 - e) * line.size * 0.45
            a = clamp(p * 1.6)
            blur = (1 - out_cubic(p)) * line.size * 0.10
            sc = scale * (1 + 0.12 * (1 - e))
        elif style == "slam":
            p = t / dur
            e = out_back(p, 1.1)
            dy = 0
            a = clamp(p * 2.5)
            blur = (1 - out_cubic(p)) * line.size * 0.16
            sc = scale * (1.0 + 0.55 * (1 - e))
        else:  # static
            dy, a, blur, sc = 0, 1.0, 0, scale
        if a <= 0.002:
            continue
        spr = g["img"]
        if abs(sc - 1) > 1e-3:
            spr = cv2.resize(spr, None, fx=sc, fy=sc, interpolation=cv2.INTER_LINEAR)
        if blur > 0.4:
            spr = cv2.GaussianBlur(spr, (0, 0), blur)
        if style == "slam":
            gx = cx + (left - cx + g["x"] * scale) * sc / scale
            gy = baseline + g["y"] * sc
        else:
            gx = left + g["x"] * scale - (sc - scale) * g["img"].shape[1] / 2
            gy = baseline + g["y"] * sc + dy
        paste_max(mask, spr, gx, gy, a * alpha)


def vgrad(c_top, c_bot, y0, y1):
    """Vertical colour gradient (H,1,3) for text fills."""
    ys = np.clip((np.arange(H, dtype=np.float32) - y0) / max(1, (y1 - y0)), 0, 1)[:, None, None]
    return np.array(c_top, np.float32) * (1 - ys) + np.array(c_bot, np.float32) * ys


def apply_text(img, mask, fill, glow=None, glow_amt=0.0, shadow=0.55, glow_sigma=22):
    if mask.max() <= 0.001:
        return img
    m = mask[..., None]
    if shadow:
        sh = cv2.GaussianBlur(np.roll(mask, 10, axis=0), (0, 0), 14)[..., None]
        img = img * (1 - shadow * sh)
    img = img * (1 - m) + m * fill
    if glow is not None and glow_amt > 0:
        small = cv2.resize(mask, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
        g1 = cv2.resize(cv2.GaussianBlur(small, (0, 0), glow_sigma / 2), (W, H))
        g2 = cv2.resize(cv2.GaussianBlur(small, (0, 0), glow_sigma * 2.5), (W, H))
        img = img + (0.9 * g1 + 0.6 * g2)[..., None] * np.array(glow, np.float32) * glow_amt
    return img


# ===================================================================== fx helpers
def affine(img, scale=1.0, tx=0.0, ty=0.0, rot=0.0, border=cv2.BORDER_REFLECT101):
    M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, scale)
    M[0, 2] += tx
    M[1, 2] += ty
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=border)


def radial_blur(img, amount, n=7):
    if amount < 0.004:
        return img
    acc = np.zeros_like(img)
    for k in range(n):
        acc += affine(img, 1 + amount * k / (n - 1))
    return acc / n


def hblur(img, length):
    L = int(length)
    if L < 3:
        return img
    return cv2.blur(img, (L, 1), borderType=cv2.BORDER_REFLECT)


yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
RR = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = (1 - 0.42 * np.clip(RR - 0.35, 0, None) ** 1.6)[..., None].astype(np.float32)


def bloom(img, thresh=0.62, amt=1.0):
    hl = np.clip(img - thresh, 0, None)
    s = cv2.resize(hl, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    b = (0.55 * cv2.GaussianBlur(s, (0, 0), 3) + 0.45 * cv2.GaussianBlur(s, (0, 0), 12)
         + 0.35 * cv2.GaussianBlur(s, (0, 0), 34))
    b = cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    warm = np.array([1.0, 0.86, 0.72], np.float32)  # halation: warm skirt
    return img + b * warm * amt


def chroma(img, amt=0.0016):
    out = img.copy()
    out[..., 0] = affine(img[..., 0], 1 + amt)
    out[..., 2] = affine(img[..., 2], 1 - amt)
    return out


def grain(img, g, strength=0.028):
    rng = np.random.default_rng(1000 + g)
    n = rng.standard_normal((H // 2, W // 2)).astype(np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)
    lum = img.mean(axis=2, keepdims=True)
    w = 0.35 + 0.65 * np.clip(1 - np.abs(lum - 0.4) * 1.6, 0, 1)
    return img + n[..., None] * strength * w


def tonemap(img):
    """Soft shoulder so glows roll off like film instead of clipping."""
    return np.where(img < 0.8, img, 0.8 + 0.2 * np.tanh((img - 0.8) / 0.2))


# ===================================================================== dust motes
class Dust:
    def __init__(self, n=70, seed=5, warm=(1.0, 0.8, 0.55)):
        r = np.random.default_rng(seed)
        self.p = r.uniform([0, 0], [W, H], (n, 2)).astype(np.float32)
        self.z = r.uniform(0.15, 1.0, n).astype(np.float32)  # depth: 1 = near (big, soft)
        self.v = r.normal(0, 1, (n, 2)).astype(np.float32) * [0.25, 0.18] + [0.0, -0.35]
        self.ph = r.uniform(0, 6.28, n)
        self.warm = np.array(warm, np.float32)

    def render(self, g, intensity=1.0, light=None):
        layer = np.zeros((H, W), np.float32)
        for i in range(len(self.z)):
            z = self.z[i]
            x = (self.p[i, 0] + self.v[i, 0] * g * (0.6 + z)) % W
            y = (self.p[i, 1] + self.v[i, 1] * g * (0.6 + z) + 8 * math.sin(g * 0.03 + self.ph[i])) % H
            rad = 1.2 + 9 * z ** 2.2
            a = (0.35 + 0.65 * (1 - z)) * (0.6 + 0.4 * math.sin(g * 0.07 + self.ph[i] * 3))
            if light is not None:
                a *= light[int(y), int(x)]
            s = int(rad * 3) + 2
            x0, y0 = int(x) - s, int(y) - s
            if x0 < 0 or y0 < 0 or x0 + 2 * s >= W or y0 + 2 * s >= H:
                continue
            gy, gx = np.mgrid[-s:s, -s:s].astype(np.float32)
            disc = np.exp(-((gx ** 2 + gy ** 2) / (2 * (rad * 0.6) ** 2)) ** (1.5 if z > 0.6 else 1))
            layer[y0:y0 + 2 * s, x0:x0 + 2 * s] += disc * a
        return layer[..., None] * self.warm * 0.45 * intensity


# ===================================================================== title background
def beam_light(apex=(W * 0.5, -420), half_angle=0.30, length=2600):
    dx, dy = xx - apex[0], yy - apex[1]
    ang = np.abs(np.arctan2(dx, dy))
    d = np.sqrt(dx * dx + dy * dy)
    cone = np.clip(1 - ang / half_angle, 0, 1) ** 1.8
    fall = np.exp(-d / length)
    return (cone * fall).astype(np.float32)


BEAM = beam_light()
_hz = cv2.resize(RNG.standard_normal((96, 27)).astype(np.float32), (W, H * 2), interpolation=cv2.INTER_CUBIC)
_hz2 = cv2.resize(RNG.standard_normal((320, 90)).astype(np.float32), (W, H * 2), interpolation=cv2.INTER_CUBIC)
HAZE = (0.6 * _hz + 0.4 * _hz2)


def title_bg(g):
    off = int(g * 1.5) % H
    hz = 0.75 + 0.25 * HAZE[off:off + H]
    floor = np.clip((yy - H * 0.80) / (H * 0.2), 0, 1) * np.exp(-((xx - W / 2) / (W * 0.30)) ** 2)
    base = np.array([0.020, 0.021, 0.026], np.float32) + np.zeros((H, W, 3), np.float32)
    beam = (BEAM * hz)[..., None] * np.array([0.55, 0.50, 0.44], np.float32) * 0.8
    pool = (floor * 0.45)[..., None] * np.array([0.8, 0.72, 0.6], np.float32)
    return base + beam + pool


# ===================================================================== scene builders
def build(args):
    R = args.renders
    plates = dict(
        idea=Plates(os.path.join(R, "idea"), 156),
        action=Plates(os.path.join(R, "action"), 162),
        result=Plates(os.path.join(R, "result"), 190),
    )
    dust = Dust()
    dust_cool = Dust(50, seed=9, warm=(0.75, 0.85, 1.0))

    L = dict(
        t_lead=Line("формула", "Light", 64, -0.01),
        t1=Line("ИДЕЯ", "Bold", 150, -0.035),
        t2=Line("ДЕЙСТВИЕ", "Bold", 150, -0.035),
        t3=Line("РЕЗУЛЬТАТ", "Bold", 150, -0.035),
        i_lead=Line("всё начинается с", "Light", 62, -0.01),
        i_big=Line("ИДЕИ", "Bold", 230, -0.04),
        a_lead=Line("а потом —", "Light", 62, -0.01),
        a_big=Line("ДЕЙСТВИЕ", "Bold", 168, -0.04),
        r_lead=Line("и в итоге —", "Light", 62, -0.01),
        r_tag=Line("Р Е З У Л Ь Т А Т", "SemiBold", 40, 0.04),
        lock=Line("ИДЕЯ  →  ДЕЙСТВИЕ  →  РЕЗУЛЬТАТ", "SemiBold", 44, 0.0),
    )
    counter_cache = {}

    def counter_line(v):
        s = f"+{v:,}".replace(",", " ") + " ₽"
        if s not in counter_cache:
            counter_cache[s] = Line(s, "Bold", 132, -0.03, features=["tnum"])
        return counter_cache[s]

    WHITE = np.array([0.97, 0.96, 0.94], np.float32)
    AMBER = (1.0, 0.55, 0.18)
    ICE = (0.42, 0.62, 1.0)
    GOLD = (1.0, 0.70, 0.30)

    # -------------------------------------------------------------- per frame
    def frame(g):
        # ---------------- title (0..86)
        img = None
        if g < T.ZOOM_THROUGH[1]:
            bg = title_bg(g)
            bg = bg + dust.render(g, 1.2, light=0.35 + BEAM * 2.5)
            push = 1.0 + 0.04 * smooth(g / 86)
            bg = affine(bg, push)
            mask = np.zeros((H, W), np.float32)
            mgold = np.zeros((H, W), np.float32)
            y0 = 840
            draw_line(mask, L["t_lead"], W / 2, y0 - 175, g - T.TITLE_IN, "rise", 1.4, 16)
            draw_line(mask, L["t1"], W / 2, y0, g - T.TITLE_WORDS[0], "rise", 2.0, 16)
            draw_line(mask, L["t2"], W / 2, y0 + 170, g - T.TITLE_WORDS[1], "rise", 1.5, 16)
            draw_line(mgold, L["t3"], W / 2, y0 + 340, g - T.TITLE_WORDS[2], "rise", 1.3, 16)
            # gold underline that draws on under РЕЗУЛЬТАТ
            ul = out_expo(prog(g, T.TITLE_WORDS[2] + 8, T.TITLE_WORDS[2] + 30))
            if ul > 0:
                hw = int(L["t3"].width / 2 * ul)
                cv2.line(mgold, (int(W / 2 - hw), y0 + 380), (int(W / 2 + hw), y0 + 380), 1.0, 4, cv2.LINE_AA)
            txt = np.zeros((H, W, 3), np.float32) + bg
            txt = apply_text(txt, mask, WHITE, (0.9, 0.85, 0.8), 0.18)
            txt = apply_text(txt, mgold, vgrad((1.0, 0.9, 0.7), (0.95, 0.62, 0.26), y0 + 230, y0 + 360), GOLD, 0.9)
            # zoom-through exit: the whole title rushes into the lens
            z = in_cubic(prog(g, T.TITLE_OUT, T.ZOOM_THROUGH[1]))
            if z > 0:
                txt = radial_blur(affine(txt, 1 + 5 * z), 0.25 * z + 0.05)
            img = txt
            if g >= T.ZOOM_THROUGH[0] + 6:
                p = smooth(prog(g, T.ZOOM_THROUGH[0] + 6, T.ZOOM_THROUGH[1]))
                idea = idea_layer(g)
                idea = radial_blur(affine(idea, 1.35 - 0.35 * out_cubic(p)), 0.18 * (1 - p))
                img = img * (1 - p) + idea * p
            return img

        # ---------------- idea (86..240)
        if g < T.WHIP_1[1] - 8:
            img = idea_layer(g)
            if g >= T.WHIP_1[0]:  # whip out to the left
                p = in_cubic(prog(g, T.WHIP_1[0], T.WHIP_1[0] + 12))
                img = hblur(affine(img, 1 + 0.06 * p, tx=-p * W * 0.85), 6 + p * 420)
            return img
        # ---------------- action (232..392)
        if g < T.FLASH[1]:
            img = action_layer(g)
            if g < T.WHIP_1[1]:  # whip in from the right
                p = 1 - out_cubic(prog(g, T.WHIP_1[1] - 8, T.WHIP_1[1]))
                img = hblur(affine(img, 1 + 0.06 * p, tx=p * W * 0.85), 6 + p * 420)
            if g >= T.FLASH[0]:
                p = prog(g, T.FLASH[0], T.FLASH[1])
                img = img * (1 + 4 * in_cubic(p)) + leak(p ** 1.5)
            return img
        # ---------------- result (380..570)
        img = result_layer(g)
        p = 1 - prog(g, T.FLASH[1], T.FLASH[2])
        if p > 0:
            img = img * (1 + 3 * p ** 2) + leak(p ** 1.3)
            img = radial_blur(img, 0.06 * p)
        return img

    def leak(a):
        """Warm light-leak overlay, brighter from the upper right."""
        shape = np.exp(-(((xx - W * 0.85) / (W * 0.9)) ** 2 + ((yy - H * 0.15) / (H * 0.7)) ** 2))
        return (shape[..., None] * np.array([1.0, 0.78, 0.52], np.float32) * 1.4
                + np.array([1.0, 0.95, 0.9], np.float32) * 0.6) * a

    # ------------------------------------------------------------------ idea
    def idea_layer(g):
        lf = g - T.IDEA_START
        img = plates["idea"].get(lf)
        # digital camera: slow push + float
        img = affine(img, 1.02 + 0.05 * smooth(lf / 160), tx=6 * math.sin(lf * 0.021), ty=-10 * smooth(lf / 160))
        lvl = filament_level(lf)
        img = img + dust.render(g, 0.6 + 1.4 * min(1.2, lvl), light=0.25 + BEAM * 2.0)
        mask = np.zeros((H, W), np.float32)
        mbig = np.zeros((H, W), np.float32)
        draw_line(mask, L["i_lead"], W / 2, 300, g - (T.IDEA_TEXT - 14), "rise", 1.2, 16)
        draw_line(mbig, L["i_big"], W / 2, 520, g - T.IDEA_TEXT, "slam", 0, 16)
        img = apply_text(img, mask, WHITE, None, 0)
        fill = vgrad((1.0, 0.93, 0.80), (1.0, 0.62, 0.25), 360, 520)
        img = apply_text(img, mbig, fill, AMBER, 0.35 + 1.1 * min(1.2, lvl), glow_sigma=26)
        return img

    def filament_level(lf):
        IGN = T.IGNITE_LOCAL
        seq = {IGN: 0.55, IGN + 1: 0.9, IGN + 2: 0.35, IGN + 7: 0.25, IGN + 8: 0.6, IGN + 9: 0.15}
        lf = int(round(lf))
        if lf < IGN:
            return 0.0
        if lf in seq:
            return seq[lf]
        if lf < IGN + 12:
            return 0.0
        t = (lf - (IGN + 12)) / 18.0
        return out_cubic(t) * 1.12 if t <= 1 else 1.0

    # ------------------------------------------------------------------ action
    def action_layer(g):
        lf = g - T.ACTION_START
        img = plates["action"].get(lf)
        sx = sy = rot = 0.0
        punch = 0.0
        for i, h in enumerate(T.DOMINO_HITS):
            d = g - h
            if d >= 0:
                amp = 2.0 + 2.6 * i ** 1.35
                k = math.exp(-d / (4 + i))
                sx += amp * k * math.sin(d * 2.3 + i)
                sy += amp * 1.3 * k * math.sin(d * 3.1 + 1.7 * i)
                rot += 0.04 * i * k * math.sin(d * 2.7)
                punch += 0.004 * i * k
        img = affine(img, 1.03 + punch + 0.03 * smooth(lf / 160), sx, sy, rot)
        img = img + dust_cool.render(g, 0.8, light=None)
        mask = np.zeros((H, W), np.float32)
        mbig = np.zeros((H, W), np.float32)
        draw_line(mask, L["a_lead"], W / 2, 300, g - (T.ACTION_TEXT - 10), "rise", 1.2, 16)
        # keyword pulses on every domino impact
        pulse = sum(0.035 * (1 + 0.4 * i) * math.exp(-(g - h) / 5) for i, h in enumerate(T.DOMINO_HITS) if g >= h)
        draw_line(mbig, L["a_big"], W / 2, 480, g - T.ACTION_TEXT, "rise", 1.6, 14, scale=1 + pulse)
        img = apply_text(img, mask, WHITE, None, 0)
        fill = vgrad((0.92, 0.96, 1.0), (0.62, 0.74, 0.95), 350, 480)
        img = apply_text(img, mbig, fill, ICE, 0.55 + 4 * pulse, glow_sigma=22)
        return img

    # ------------------------------------------------------------------ result
    def result_layer(g):
        lf = g - T.RESULT_START
        img = plates["result"].get(lf)
        img = affine(img, 1.02 + 0.03 * smooth(lf / 190), tx=-5 * math.sin(lf * 0.02))
        img = img + dust.render(g + 400, 0.9, light=None)
        mask = np.zeros((H, W), np.float32)
        mgold = np.zeros((H, W), np.float32)
        draw_line(mask, L["r_lead"], W / 2, 290, g - (T.RESULT_TEXT - 4), "rise", 1.2, 16)
        cp = prog(g, *T.COUNT_UP)
        val = int(round(out_cubic(cp) ** 1.15 * 1_000_000 / 1000)) * 1000
        cl = counter_line(val)
        draw_line(mgold, cl, W / 2, 470, g - T.RESULT_TEXT, "rise", 0.8, 14)
        lock_on = g >= T.LOCKUP
        draw_line(mgold, L["r_tag"], W / 2, 560, g - (T.RESULT_TEXT + 26), "rise", 0.9, 16)
        img = apply_text(img, mask, WHITE, None, 0)
        settle = math.exp(-max(0, g - T.COUNT_UP[1]) / 6) if g >= T.COUNT_UP[1] else 0
        fill = vgrad((1.0, 0.93, 0.74), (0.98, 0.64, 0.24), 360, 480)
        img = apply_text(img, mgold, fill, GOLD, 0.75 + 1.2 * settle, glow_sigma=22)
        if lock_on:
            img = lockup(img, g - T.LOCKUP)
        return img

    def lockup(img, t):
        """Bottom line: the three words light up in sequence."""
        ln = L["lock"]
        y = 1745
        # dark gradient so the line reads on any plate
        a = out_cubic(t / 20)
        shade = np.clip((yy - 1450) / 470, 0, 1)[..., None] * 0.55 * a
        img = img * (1 - shade)
        m_dim = np.zeros((H, W), np.float32)
        draw_line(m_dim, ln, W / 2, y, t, "rise", 0.6, 18)
        img = apply_text(img, m_dim * 0.55, WHITE, None, 0, shadow=0.0)
        segs = [(0, 4), (9, 17), (22, 31)]
        for k, (a0, a1) in enumerate(segs):
            p = out_cubic((t - 18 - k * 9) / 10)
            if p <= 0:
                continue
            mk = np.zeros((H, W), np.float32)
            sub = Line.__new__(Line)
            sub.__dict__.update(ln.__dict__)
            sub.glyphs = [gl for gl in ln.glyphs if a0 <= gl["i"] < a1]
            draw_line(mk, sub, W / 2, y, 99, "static")
            col = (1.0, 0.78, 0.40) if k == 2 else (1.0, 1.0, 1.0)
            img = apply_text(img, mk * p, np.array(col, np.float32), GOLD if k == 2 else (1, 0.9, 0.8),
                             0.6 * p if k == 2 else 0.15 * p, shadow=0.0, glow_sigma=14)
        return img

    return frame


# ===================================================================== finishing + main
def finish(img, g):
    img = np.clip(img, 0, None)
    img = bloom(img, 0.6, 0.85)
    img = chroma(img)
    img = img * VIGNETTE
    img = tonemap(img)
    img = grain(img, g)
    return np.clip(img, 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--renders", required=True)
    ap.add_argument("--out", default="out.mp4")
    ap.add_argument("--frames", default=f"0:{T.TOTAL}")
    ap.add_argument("--preview", default=None, help="write PNG stills of the listed frames instead of video")
    ap.add_argument("--list", default=None, help="comma list of frames for --preview")
    args = ap.parse_args()
    frame = build(args)
    if args.preview:
        os.makedirs(args.preview, exist_ok=True)
        for g in [int(x) for x in args.list.split(",")]:
            im = finish(frame(g), g)
            cv2.imwrite(os.path.join(args.preview, f"g{g:04d}.png"),
                        cv2.cvtColor((im * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2BGR))
            print("preview", g, flush=True)
        return
    a, b = [int(x) for x in args.frames.split(":")]
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb48le", "-s", f"{W}x{H}",
           "-r", str(T.FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow", "-crf", "12",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-x264-params", "aq-mode=3:deblock=-1,-1",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", args.out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for g in range(a, b):
        im = finish(frame(g), g)
        # dither to 16-bit to avoid banding in the dark gradients
        pr.stdin.write((im * 65535).astype("<u2").tobytes())
        if g % 30 == 0:
            print("frame", g, flush=True)
    pr.stdin.close()
    pr.wait()


if __name__ == "__main__":
    main()
