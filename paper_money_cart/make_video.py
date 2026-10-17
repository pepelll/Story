#!/usr/bin/env python3
"""
Paper-style animated background: grey paper, drifting window-blind shadows,
a stack of $100 bills sliding in from the top-right and an empty shopping cart
sliding in from the bottom-left. No text. Thin minimal hairline decor.

Requirements: python3, numpy, pillow, scipy, pycairo, ffmpeg
    pip install numpy pillow scipy pycairo
Run:
    python3 make_video.py            # renders out/paper_money_cart.mp4 (1080x1920, 30fps)
    python3 make_video.py --preview  # renders a few still frames into preview/ only
"""
import math, subprocess, sys, os
import numpy as np
import cairo
from PIL import Image, ImageFilter
from scipy.ndimage import gaussian_filter

OUT_W, OUT_H = 1080, 1920
FPS = 30
DURATION = 6.0
# working canvas is a bit bigger so we can do a slow camera push-in
CW, CH = 1166, 2074
rng = np.random.default_rng(7)
HERE = os.path.dirname(os.path.abspath(__file__))

INK = (0.27, 0.28, 0.27)


# ---------------------------------------------------------------- helpers
def surf_to_pil(surf):
    w, h = surf.get_width(), surf.get_height()
    a = np.ndarray((h, w, 4), np.uint8, surf.get_data()).copy()
    # cairo is premultiplied BGRA
    b, g, r, al = [a[..., i].astype(np.float32) for i in range(4)]
    alf = np.where(al > 0, al / 255.0, 1)
    rgba = np.stack([r / alf, g / alf, b / alf, al], -1).clip(0, 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def ease_out_cubic(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=1.2):
    x = min(max(x, 0.0), 1.0)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def paper_grain(img, amount=10, seed=0):
    """multiply sprite RGB by fine noise so it sits in the paper world"""
    a = np.asarray(img).astype(np.float32)
    r = np.random.default_rng(seed)
    n = gaussian_filter(r.normal(0, 1, a.shape[:2]), 0.8) * amount
    n += gaussian_filter(r.normal(0, 1, a.shape[:2]), 25) * amount * 2.5
    a[..., :3] = (a[..., :3] + n[..., None]).clip(0, 255)
    return Image.fromarray(a.astype(np.uint8), "RGBA")


# ---------------------------------------------------------------- $100 bill
def draw_bill(W=1640, H=700, seed=0):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    r = np.random.default_rng(seed)

    # base paper of the note
    g = cairo.LinearGradient(0, 0, W, H)
    g.add_color_stop_rgb(0, 0.90, 0.895, 0.875)
    g.add_color_stop_rgb(1, 0.84, 0.835, 0.815)
    c.rectangle(0, 0, W, H); c.set_source(g); c.fill()

    # fine engraving background lines
    c.set_line_width(1.0)
    c.set_source_rgba(*INK, 0.10)
    for y in range(0, H, 6):
        c.move_to(0, y)
        for x in range(0, W + 20, 20):
            c.line_to(x, y + 1.5 * math.sin(x / 90 + y / 40))
        c.stroke()

    # long guilloche waves across the note
    for k in range(18):
        c.set_source_rgba(*INK, 0.16)
        c.set_line_width(1.1)
        ph = k * 0.35
        for x in range(0, W + 8, 8):
            y = H * 0.5 + 200 * math.sin(x / 260 + ph) * math.cos(x / 520 - ph * 0.7)
            (c.move_to if x == 0 else c.line_to)(x, y)
        c.stroke()

    # border band with cross hatching
    c.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    c.rectangle(22, 22, W - 44, H - 44)
    c.rectangle(74, 74, W - 148, H - 148)
    c.save(); c.clip()
    c.set_source_rgba(0.93, 0.925, 0.905, 0.85); c.paint()
    c.set_line_width(1.2); c.set_source_rgba(*INK, 0.55)
    for d in range(-H, W + H, 9):
        c.move_to(d, 0); c.line_to(d + H, H)
        c.move_to(d + H, 0); c.line_to(d, H)
    c.stroke()
    # sine ribbons along the band
    for k in range(3):
        c.set_line_width(1.6); c.set_source_rgba(*INK, 0.8)
        for yb in (48, H - 48):
            for x in range(20, W - 19, 6):
                y = yb + 13 * math.sin(x / 11 + k * 2.1)
                (c.move_to if x == 20 else c.line_to)(x, y)
            c.stroke()
    c.restore()
    c.set_fill_rule(cairo.FILL_RULE_WINDING)

    c.set_source_rgba(*INK, 0.95)
    c.set_line_width(3.5); c.rectangle(22, 22, W - 44, H - 44); c.stroke()
    c.set_line_width(1.6); c.rectangle(74, 74, W - 148, H - 148); c.stroke()
    c.set_line_width(1.0); c.rectangle(84, 84, W - 168, H - 168); c.stroke()

    # central oval rosette (in place of a portrait)
    cx, cy, rx, ry = W * 0.5, H * 0.5, 205, 238
    c.save(); c.translate(cx, cy); c.scale(rx, ry)
    c.arc(0, 0, 1, 0, 2 * math.pi); c.restore()
    c.set_source_rgba(0.88, 0.875, 0.855, 1); c.fill()
    for j in range(42):
        ph = j * 2 * math.pi / 42
        c.set_line_width(0.9); c.set_source_rgba(*INK, 0.55)
        for i in range(0, 721):
            t = i / 720 * 2 * math.pi
            rad = 0.62 + 0.30 * math.cos(9 * t + ph) * math.sin(3 * t - ph)
            x, y = cx + rx * rad * math.cos(t), cy + ry * rad * math.sin(t)
            (c.move_to if i == 0 else c.line_to)(x, y)
        c.stroke()
    for k, sc in enumerate((1.0, 0.96, 0.93, 0.36, 0.30)):
        c.save(); c.translate(cx, cy); c.scale(rx * sc, ry * sc)
        c.arc(0, 0, 1, 0, 2 * math.pi); c.restore()
        c.set_line_width(3.0 if k == 0 else 1.3); c.set_source_rgba(*INK, 0.9); c.stroke()
    # radial engraving inside the small inner oval
    for i in range(120):
        t = i / 120 * 2 * math.pi
        c.move_to(cx + rx * 0.30 * math.cos(t) * 0.2, cy + ry * 0.30 * math.sin(t) * 0.2)
        c.line_to(cx + rx * 0.30 * math.cos(t), cy + ry * 0.30 * math.sin(t))
    c.set_line_width(0.8); c.set_source_rgba(*INK, 0.5); c.stroke()

    # left seal
    sx, sy, sr = W * 0.205, H * 0.56, 92
    c.arc(sx, sy, sr, 0, 2 * math.pi); c.set_source_rgba(0.9, 0.895, 0.875, 1); c.fill()
    for i in range(96):
        t = i / 96 * 2 * math.pi
        c.move_to(sx + sr * 0.78 * math.cos(t), sy + sr * 0.78 * math.sin(t))
        c.line_to(sx + sr * math.cos(t), sy + sr * math.sin(t))
    c.set_line_width(1.6); c.set_source_rgba(*INK, 0.8); c.stroke()
    for rr, lw in ((sr, 2.5), (sr * 0.78, 1.4), (sr * 0.55, 1.2)):
        c.arc(sx, sy, rr, 0, 2 * math.pi); c.set_line_width(lw); c.stroke()
    # star
    c.save(); c.translate(sx, sy)
    for i in range(10):
        t = i / 10 * 2 * math.pi - math.pi / 2
        rr = sr * 0.42 if i % 2 == 0 else sr * 0.18
        (c.move_to if i == 0 else c.line_to)(rr * math.cos(t), rr * math.sin(t))
    c.close_path(); c.set_source_rgba(*INK, 0.85); c.fill(); c.restore()

    # vertical security ribbon
    rx0 = W * 0.335
    c.rectangle(rx0, 84, 46, H - 168); c.set_source_rgba(0.78, 0.775, 0.76, 1); c.fill()
    c.set_source_rgba(*INK, 0.6); c.set_line_width(1.2)
    for y in range(90, H - 84, 14):
        c.move_to(rx0 + 6, y); c.line_to(rx0 + 40, y + 7)
    c.stroke()
    c.rectangle(rx0, 84, 46, H - 168); c.set_line_width(1.2); c.stroke()

    # denomination numerals
    def num(txt, x, y, size, fill=0.9, outline=True):
        c.select_font_face("Bitstream Charter", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        c.set_font_size(size)
        e = c.text_extents(txt)
        c.move_to(x - e.x_bearing - e.width / 2, y - e.y_bearing - e.height / 2)
        c.text_path(txt)
        c.set_source_rgba(*INK, fill); c.fill_preserve()
        if outline:
            c.set_source_rgba(0.12, 0.12, 0.12, 0.9); c.set_line_width(1.5); c.stroke()
        else:
            c.new_path()

    num("100", W * 0.80, H * 0.66, 210)
    for (x, y) in ((150, 140), (W - 150, 140), (150, H - 140)):
        num("100", x, y, 64, 0.85)
    # small engraved line blocks
    c.set_source_rgba(*INK, 0.55); c.set_line_width(1.2)
    for i in range(7):
        y = H * 0.30 + i * 9
        c.move_to(W * 0.66, y); c.line_to(W * 0.92, y)
    c.stroke()

    # outer edge
    c.rectangle(1, 1, W - 2, H - 2); c.set_source_rgba(0.2, 0.2, 0.2, 0.7)
    c.set_line_width(2); c.stroke()
    img = surf_to_pil(s)
    # slight worn/ink variation
    return paper_grain(img, amount=7, seed=seed + 11)


def bills_stack(scale):
    """fan of several bills, returns RGBA sprite"""
    base = draw_bill(seed=1)
    W, H = base.size
    canvas = Image.new("RGBA", (int(W * 1.7), int(H * 2.6)), (0, 0, 0, 0))
    cx, cy = canvas.size[0] // 2, canvas.size[1] // 2
    layout = [(-16, -150, 70), (9, 120, -40), (-5, 30, 20), (2, 0, 0)]  # angle, dx, dy
    for i, (ang, dx, dy) in enumerate(layout):
        b = base if i == len(layout) - 1 else draw_bill(seed=i + 3)
        # tone each lower bill a touch darker
        if i < len(layout) - 1:
            arr = np.asarray(b).astype(np.float32)
            arr[..., :3] *= 0.93 + 0.02 * i
            b = Image.fromarray(arr.clip(0, 255).astype(np.uint8), "RGBA")
        rb = b.rotate(ang, resample=Image.BICUBIC, expand=True)
        # soft shadow cast onto the bill below
        sh = Image.new("RGBA", rb.size, (0, 0, 0, 0))
        sh.putalpha(rb.getchannel("A").point(lambda v: int(v * 0.35)))
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        px, py = cx - rb.size[0] // 2 + dx, cy - rb.size[1] // 2 + dy
        canvas.alpha_composite(sh, (px + 10, py + 16))
        canvas.alpha_composite(rb, (px, py))
    canvas = canvas.crop(canvas.getbbox())
    return canvas.resize((int(canvas.size[0] * scale), int(canvas.size[1] * scale)), Image.LANCZOS)


# ---------------------------------------------------------------- shopping cart
def draw_cart(W=1600, H=1420):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    c.set_line_cap(cairo.LINE_CAP_ROUND); c.set_line_join(cairo.LINE_JOIN_ROUND)
    DARK = (0.13, 0.13, 0.14)
    FAR = (0.45, 0.45, 0.46)

    def metal_line(pts, lw, col=DARK, hl=0.42):
        c.set_line_width(lw); c.set_source_rgb(*col)
        c.move_to(*pts[0]); [c.line_to(*p) for p in pts[1:]]; c.stroke()
        c.set_line_width(max(lw * 0.28, 1.0)); c.set_source_rgba(1, 1, 1, hl)
        c.move_to(pts[0][0] - lw * 0.18, pts[0][1] - lw * 0.18)
        [c.line_to(p[0] - lw * 0.18, p[1] - lw * 0.18) for p in pts[1:]]; c.stroke()

    # basket corners: back-top, front-top, front-bottom, back-bottom
    near = [(330, 360), (1430, 360), (1210, 860), (390, 860)]
    off = (95, -60)
    far = [(x + off[0], y + off[1]) for x, y in near]

    def basket(poly, col, lw, step, hl):
        c.save()
        c.move_to(*poly[0]); [c.line_to(*p) for p in poly[1:]]; c.close_path(); c.clip()
        x0 = min(p[0] for p in poly); x1 = max(p[0] for p in poly)
        y0 = min(p[1] for p in poly); y1 = max(p[1] for p in poly)
        x = x0 + step / 2
        while x < x1:
            metal_line([(x, y0 - 5), (x, y1 + 5)], lw, col, hl); x += step
        y = y0 + step / 2
        while y < y1:
            metal_line([(x0 - 5, y), (x1 + 5, y)], lw * 0.8, col, hl); y += step
        c.restore()
        metal_line(poly + [poly[0]], lw * 2.2, col, hl)

    # --- far side (lighter, behind)
    basket(far, FAR, 4.6, 48, 0.25)
    for p, q in zip(near, far):
        metal_line([p, q], 7, FAR, 0.2)
    # far chassis + wheels
    def chassis(dx, dy, col, hl, wheel_dark):
        bb, fb = (390 + dx, 860 + dy), (1210 + dx, 860 + dy)
        metal_line([bb, (405 + dx, 1135 + dy)], 12, col, hl)
        metal_line([fb, (1170 + dx, 1135 + dy)], 12, col, hl)
        metal_line([(350 + dx, 1135 + dy), (1250 + dx, 1135 + dy)], 14, col, hl)
        for wx in (420, 1150):
            cx_, cy_ = wx + dx, 1225 + dy
            metal_line([(wx + dx - 22, 1135 + dy), (cx_, cy_), (wx + dx + 22, 1135 + dy)], 9, col, hl)
            c.arc(cx_, cy_, 64, 0, 2 * math.pi); c.set_source_rgb(*wheel_dark); c.fill()
            c.arc(cx_, cy_, 46, 0, 2 * math.pi); c.set_source_rgba(1, 1, 1, 0.10); c.set_line_width(5); c.stroke()
            c.arc(cx_, cy_, 16, 0, 2 * math.pi); c.set_source_rgba(0.75, 0.75, 0.76, 1); c.fill()
            c.arc(cx_ - 18, cy_ - 20, 50, math.pi * 1.05, math.pi * 1.55)
            c.set_source_rgba(1, 1, 1, 0.22); c.set_line_width(4); c.stroke()
    chassis(off[0], off[1], FAR, 0.2, (0.38, 0.38, 0.39))

    # --- lower tray
    c.save()
    c.rectangle(430, 1050, 720, 80); c.clip()
    for x in range(430, 1160, 36):
        metal_line([(x, 1040), (x, 1140)], 3, DARK, 0.3)
    c.restore()
    metal_line([(430, 1050), (1150, 1050)], 6, DARK, 0.35)

    # --- near side
    chassis(0, 0, DARK, 0.4, (0.09, 0.09, 0.10))
    basket(near, DARK, 6.0, 48, 0.42)
    # rim reinforcement + mid bar
    metal_line([(330, 360), (1430, 360)], 13, DARK, 0.5)
    metal_line([(352, 610), (1320, 610)], 8, DARK, 0.4)
    # handle
    metal_line([(330, 360), (205, 205)], 16, DARK, 0.5)
    metal_line([(330 + off[0], 360 + off[1]), (205 + off[0], 205 + off[1])], 14, FAR, 0.2)
    metal_line([(205, 205), (205 + off[0], 205 + off[1])], 40, (0.06, 0.06, 0.07), 0.35)
    # child seat flap hint
    metal_line([(345, 380), (470, 300 - 10), (470 + off[0] * 0.6, 300 + off[1] * 0.6)], 5, DARK, 0.3)

    img = surf_to_pil(s)
    img = img.crop(img.getbbox())
    return paper_grain(img, amount=6, seed=5)


# ---------------------------------------------------------------- paper + light
def make_paper():
    base = np.array([224, 221, 214], np.float32)
    img = np.ones((CH, CW, 3), np.float32) * base
    fine = gaussian_filter(rng.normal(0, 1, (CH, CW)), 0.7) * 5
    mid = gaussian_filter(rng.normal(0, 1, (CH, CW)), 4) * 10
    big = gaussian_filter(rng.normal(0, 1, (CH, CW)), 90) * 140
    img += (fine + mid + big)[..., None]
    # faint perforated dot texture (like the reference paper)
    yy, xx = np.mgrid[0:CH, 0:CW]
    dots = ((xx % 9 - 4) ** 2 + (yy % 9 - 4) ** 2) < 3
    img[dots] *= 0.975
    # fibers
    fib = np.zeros((CH, CW), np.float32)
    for _ in range(900):
        x, y = rng.integers(0, CW), rng.integers(0, CH)
        L, a = rng.integers(6, 26), rng.uniform(0, math.pi)
        for t in range(L):
            xi, yi = int(x + t * math.cos(a)), int(y + t * math.sin(a))
            if 0 <= xi < CW and 0 <= yi < CH:
                fib[yi, xi] = 1
    fib = gaussian_filter(fib, 0.6)
    img -= fib[..., None] * 30
    # vignette
    v = ((xx / CW - 0.5) ** 2 * 1.2 + (yy / CH - 0.5) ** 2) ** 0.5
    img *= (1 - 0.18 * np.clip(v - 0.2, 0, 1))[..., None]
    return img


ANG = math.radians(32)
U = None


def make_shadow_profile(n=7000):
    """1-D cross-section of window/blind shadows, very soft"""
    x = np.arange(n, dtype=np.float32)
    p = np.zeros(n, np.float32)
    pos = 0
    while pos < n:
        w = rng.uniform(140, 420)
        gap = rng.uniform(160, 520)
        strength = rng.uniform(0.22, 0.42)
        sig = lambda v: 1 / (1 + np.exp(np.clip(-v / 28, -60, 60)))
        p += strength * (sig(x - pos) - sig(x - pos - w))
        pos += w + gap
    return gaussian_filter(p, 22)


PROFILE = make_shadow_profile()


def shadow_mask(t):
    global U
    if U is None:
        yy, xx = np.mgrid[0:CH, 0:CW].astype(np.float32)
        U = (xx * math.cos(ANG) - yy * math.sin(ANG) + 2600).astype(np.float32)
    off = 380 + t * 42  # slow drift
    idx = (U + off).astype(np.int32) % len(PROFILE)
    m = PROFILE[idx]
    # a second, very wide soft dark band (like the broad shadow in the ref)
    wide = 0.18 * np.exp(-(((U - 2600 + off * 0.6 - 900) / 380) ** 2))
    return np.clip(m + wide, 0, 0.6)


# ---------------------------------------------------------------- decor
def decor_layer(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, CW, CH)
    c = cairo.Context(s)
    p = ease_in_out((t - 1.1) / 1.3)
    if p <= 0:
        return None
    col = (0.16, 0.16, 0.16)
    m = 120
    half = (CW / 2 - m - 34) * p
    for y in (215, CH - 215):
        c.set_source_rgba(*col, 0.75); c.set_line_width(1.3)
        c.move_to(CW / 2 - 34, y); c.line_to(CW / 2 - 34 - half, y)
        c.move_to(CW / 2 + 34, y); c.line_to(CW / 2 + 34 + half, y)
        c.stroke()
        # fine ticks near the line ends
        c.set_line_width(1.0)
        for i in range(9):
            for sgn in (-1, 1):
                x = CW / 2 + sgn * (CW / 2 - m - i * 14)
                if abs(x - CW / 2) - 34 <= half:
                    h = 10 if i == 0 else 5
                    c.move_to(x, y - h); c.line_to(x, y + h)
        c.stroke()
        # small diamond in the middle
        a = min(1, p * 1.6)
        c.save(); c.translate(CW / 2, y); c.rotate(math.pi / 4)
        c.rectangle(-6, -6, 12, 12); c.restore()
        c.set_source_rgba(*col, 0.8 * a); c.set_line_width(1.2); c.stroke()
        c.arc(CW / 2, y, 1.8, 0, 2 * math.pi); c.set_source_rgba(*col, 0.8 * a); c.fill()
    # corner marks
    a = ease_in_out((t - 1.6) / 0.9)
    if a > 0:
        c.set_source_rgba(*col, 0.6 * a); c.set_line_width(1.2)
        L, ins = 30, 0
        for (x, y, sx, sy) in ((105, 150, 1, 1), (CW - 105, 150, -1, 1),
                               (105, CH - 150, 1, -1), (CW - 105, CH - 150, -1, -1)):
            c.move_to(x + sx * L, y); c.line_to(x, y); c.line_to(x, y + sy * L)
        c.stroke()
    return surf_to_pil(s)


# ---------------------------------------------------------------- object helpers
class Obj:
    def __init__(self, img):
        pad = 90  # room so blurred shadows are not clipped by the sprite box
        big = Image.new("RGBA", (img.size[0] + 2 * pad, img.size[1] + 2 * pad), (0, 0, 0, 0))
        big.paste(img, (pad, pad))
        self.img = img = big
        a = img.getchannel("A")
        self.sh_soft = a.point(lambda v: int(v * 0.50)).filter(ImageFilter.GaussianBlur(26))
        self.sh_hard = a.point(lambda v: int(v * 0.40)).filter(ImageFilter.GaussianBlur(5))

    def place(self, frame, shadow, cx, cy, angle, lift=0.0):
        im = self.img.rotate(angle, resample=Image.BICUBIC, expand=True)
        w, h = im.size
        x, y = int(cx - w / 2), int(cy - h / 2)
        for sh, (ox, oy) in ((self.sh_soft, (26 + 30 * lift, 38 + 40 * lift)), (self.sh_hard, (6, 9))):
            sr = sh.rotate(angle, resample=Image.BICUBIC, expand=True)
            tmp = Image.new("L", shadow.size, 0)
            tmp.paste(sr, (x + int(ox), y + int(oy)))
            shadow_arr = np.maximum(np.asarray(shadow), np.asarray(tmp))
            shadow.paste(Image.fromarray(shadow_arr))
        layer = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        layer.paste(im, (x, y))
        frame.alpha_composite(layer)


# ---------------------------------------------------------------- main
def main():
    preview = "--preview" in sys.argv
    print("building sprites...")
    bills = Obj(bills_stack(scale=0.47))
    cart_img = draw_cart()
    cart_img = cart_img.resize((int(cart_img.size[0] * 0.56), int(cart_img.size[1] * 0.56)), Image.LANCZOS)
    cart = Obj(cart_img)
    paper = make_paper()
    grains = [gaussian_filter(rng.normal(0, 1, (OUT_H, OUT_W)), 0.6) * 3.5 for _ in range(6)]

    # final resting positions (canvas coords)
    BILL_END = (900, 520, -27.0)
    BILL_START = (1500, -380, -40.0)
    CART_END = (470, 1490, 6.0)
    CART_START = (-420, 2350, 16.0)

    def render(t):
        frame = Image.new("RGBA", (CW, CH), (0, 0, 0, 0))
        shadow = Image.new("L", (CW, CH), 0)
        # bills
        p = ease_out_cubic((t - 0.15) / 1.45)
        fl = math.sin(t * 1.4) * (1 if p >= 1 else p)
        bx = BILL_START[0] + (BILL_END[0] - BILL_START[0]) * p + 4 * fl
        by = BILL_START[1] + (BILL_END[1] - BILL_START[1]) * p + 6 * fl
        ba = BILL_START[2] + (BILL_END[2] - BILL_START[2]) * p + 0.5 * fl
        # cart
        q = ease_out_cubic((t - 0.55) / 1.5)
        fl2 = math.sin(t * 1.2 + 1.3) * (1 if q >= 1 else q)
        cx = CART_START[0] + (CART_END[0] - CART_START[0]) * q + 3 * fl2
        cy = CART_START[1] + (CART_END[1] - CART_START[1]) * q + 5 * fl2
        ca = CART_START[2] + (CART_END[2] - CART_START[2]) * q + 0.4 * fl2
        cart.place(frame, shadow, cx, cy, ca, lift=1 - q)
        bills.place(frame, shadow, bx, by, ba, lift=1 - p)

        img = paper.copy()
        sh = np.asarray(shadow).astype(np.float32) / 255.0
        img *= (1 - 0.75 * sh)[..., None]
        fa = np.asarray(frame).astype(np.float32)
        al = fa[..., 3:4] / 255.0
        img = img * (1 - al) + fa[..., :3] * al
        d = decor_layer(t)
        if d is not None:
            da = np.asarray(d).astype(np.float32)
            al = da[..., 3:4] / 255.0
            img = img * (1 - al) + da[..., :3] * al
        # window light over everything
        m = shadow_mask(t)
        img *= (1 - m)[..., None]
        img *= 1.04
        # camera: slow push-in (centered crop shrinking with zoom)
        z = 1 + 0.045 * ease_in_out(t / DURATION)
        crop_w, crop_h = OUT_W / z, OUT_H / z
        x0 = (CW - crop_w) / 2
        y0 = (CH - crop_h) / 2
        pil = Image.fromarray(img.clip(0, 255).astype(np.uint8))
        pil = pil.resize((OUT_W, OUT_H), Image.BICUBIC, box=(x0, y0, x0 + crop_w, y0 + crop_h))
        out = np.asarray(pil).astype(np.float32) + grains[int(t * FPS) % 6][..., None]
        return out.clip(0, 255).astype(np.uint8)

    if preview:
        os.makedirs(os.path.join(HERE, "preview"), exist_ok=True)
        for t in (0.7, 1.4, 3.0, 5.9):
            Image.fromarray(render(t)).save(os.path.join(HERE, "preview", f"preview_{t:.1f}.png"))
        print("previews written")
        return

    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    out_path = os.path.join(HERE, "out", "paper_money_cart.mp4")
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{OUT_W}x{OUT_H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
    n = int(DURATION * FPS)
    for i in range(n):
        ff.stdin.write(render(i / FPS).tobytes())
        if i % 30 == 0:
            print(f"frame {i}/{n}")
    ff.stdin.close(); ff.wait()
    print("done:", out_path)


if __name__ == "__main__":
    main()
