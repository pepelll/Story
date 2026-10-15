"""Procedural sound design, frame-locked to comp/timeline.py.

Brief: warm, deep, slightly muted. Soft-but-satisfying impacts, smooth
whooshes, controlled low end, nothing piercing or metallic. Every source is
synthesised (no samples), shaped with spectral masks / low-passes, then glued
with a dark synthetic room reverb and a soft-knee master.

Usage: python sfx.py out.wav
"""
import os
import sys

import numpy as np
from scipy import signal

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "comp"))
import timeline as T

SR = 48000
DUR = T.TOTAL / T.FPS + 0.6
N = int(SR * DUR)
rng = np.random.default_rng(42)
mix = np.zeros((2, N), np.float64)


def at(frame):
    return int(round(frame / T.FPS * SR))


def lp(x, fc, order=4):
    return signal.sosfilt(signal.butter(order, fc, "low", fs=SR, output="sos"), x)


def hp(x, fc, order=2):
    return signal.sosfilt(signal.butter(order, fc, "high", fs=SR, output="sos"), x)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(signal.butter(order, [lo, hi], "band", fs=SR, output="sos"), x)


def pink(n):
    w = rng.standard_normal(n)
    f = np.fft.rfftfreq(n, 1 / SR)
    s = np.fft.rfft(w) / np.sqrt(np.maximum(f, 20))
    x = np.fft.irfft(s, n)
    return x / np.abs(x).max()


def place(sig, frame, gain=1.0, pan=0.0):
    i = at(frame)
    if i < 0:
        sig, i = sig[-i:], 0
    n = min(len(sig), N - i)
    l = np.cos((pan + 1) * np.pi / 4)
    r = np.sin((pan + 1) * np.pi / 4)
    mix[0, i:i + n] += sig[:n] * gain * l * 1.414
    mix[1, i:i + n] += sig[:n] * gain * r * 1.414


def env_ar(n, a, d, curve=2.0):
    t = np.arange(n) / SR
    e = np.where(t < a, (t / max(a, 1e-4)) ** 1.5, np.exp(-(t - a) / d))
    return e


# ------------------------------------------------------------------ sources
def whoosh(dur, peak, f0, f1, width=0.9, ceiling=4500):
    """Band-limited air: a spectral band sweeping f0->f1, swelling to `peak` (s)."""
    n = int(dur * SR)
    x = pink(n + 4096)[:n]
    f, t, Z = signal.stft(x, SR, nperseg=2048, noverlap=1536)
    tt = t / dur
    centre = f0 * (f1 / f0) ** np.clip(tt, 0, 1)
    lf = np.log2(np.maximum(f[:, None], 1))
    mask = np.exp(-((lf - np.log2(centre[None, :])) / width) ** 2)
    mask *= 1 / (1 + (f[:, None] / ceiling) ** 4)  # muted top end
    _, y = signal.istft(Z * mask, SR, nperseg=2048, noverlap=1536)
    y = y[:n]
    tn = np.arange(n) / SR
    e = np.where(tn < peak, (tn / peak) ** 2.2, np.exp(-(tn - peak) / (0.22 * dur)))
    y = y * e
    return y / (np.abs(y).max() + 1e-9)


def impact(weight=1.0, f_hi=78, f_lo=40, decay=0.45, body=0.6, click=0.12):
    """Soft cinematic hit: pitched sub drop + padded body thump + tiny felt transient."""
    n = int((decay * 4 + 0.1) * SR)
    t = np.arange(n) / SR
    freq = f_lo + (f_hi - f_lo) * np.exp(-t / 0.06)
    sub = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t / decay)
    th = lp(rng.standard_normal(n), 320) * np.exp(-t / 0.07) * body * 6
    tr = bp(rng.standard_normal(n), 700, 2600) * np.exp(-t / 0.006) * click * 3
    y = sub + th + tr
    y = np.tanh(1.6 * y) / np.tanh(1.6)
    return lp(y, 5000) * weight


def knock(size=1.0, gain=1.0):
    """Lacquered-wood 'tok' (domino). Bigger pieces: lower modes, longer decay, more sub."""
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    m1, m2 = 520 / size ** 0.55, 1240 / size ** 0.55
    d = 0.03 * size ** 0.5
    modes = (np.sin(2 * np.pi * m1 * t) * np.exp(-t / d) + 0.35 * np.sin(2 * np.pi * m2 * t) * np.exp(-t / (d * 0.6)))
    thud = lp(rng.standard_normal(n), 260 / size ** 0.3) * np.exp(-t / (0.025 * size ** 0.6)) * 3
    sub = np.sin(2 * np.pi * (60 / size ** 0.25) * t) * np.exp(-t / (0.05 * size ** 0.8)) * min(1.0, 0.15 * size)
    y = lp(modes * 0.6 + thud + sub, 3800)
    return np.tanh(1.3 * y) * gain


def coin_tap(gain=1.0, pitch=1.0):
    """Muted coin-on-coin: very short, damped, low-passed — no ring."""
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    tone = np.sin(2 * np.pi * 1750 * pitch * t) * np.exp(-t / 0.010)
    body = np.sin(2 * np.pi * 340 * pitch * t) * np.exp(-t / 0.020)
    tick = lp(rng.standard_normal(n), 2800) * np.exp(-t / 0.003)
    return lp(0.25 * tone + 0.8 * body + 0.6 * tick, 3200) * gain


def warm_tone(dur, freqs, attack=0.25, release=1.2, gain=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) / (1 + k * 0.8) for k, f in enumerate(freqs))
    e = np.minimum(1, t / attack) * np.exp(-np.maximum(0, t - attack) / release)
    return lp(y * e, 1800) * gain


def crackle(dur, density=90, gain=1.0):
    """Soft electrical ignition: sparse, low-passed micro-bursts."""
    n = int(dur * SR)
    y = np.zeros(n)
    for _ in range(int(density * dur)):
        i = rng.integers(0, n - 400)
        L = rng.integers(40, 300)
        y[i:i + L] += rng.standard_normal(L) * np.hanning(L) * rng.uniform(0.2, 1)
    return lp(hp(y, 300), 2600) * gain


# ------------------------------------------------------------------ score the picture
# room tone bed
bed = lp(pink(N), 400) * 0.05
bed *= np.minimum(1, np.arange(N) / (SR * 0.8)) * np.minimum(1, (N - np.arange(N)) / (SR * 0.8))
mix += bed * np.array([[1.0], [0.9]])

# title: soft air for the lead, a felt thump per word
place(whoosh(0.7, 0.35, 300, 900, 0.8, 2500), T.TITLE_IN - 10, 0.10)
for k, f in enumerate(T.TITLE_WORDS):
    place(whoosh(0.45, 0.22, 400, 1400, 0.7, 3000), f - 12, 0.12, pan=(-0.25, 0.0, 0.25)[k])
    place(impact(1.0, 95, 55, 0.18, 0.35, 0.05), f + 2, 0.22 + 0.06 * k)
place(warm_tone(1.4, [65.4, 98, 130.8], 0.05, 0.6), T.TITLE_WORDS[2] + 2, 0.12)

# zoom-through into the bulb: rising air -> landing
place(whoosh(0.55, 0.32, 180, 1600, 1.0, 3500), T.TITLE_OUT - 2, 0.42)
place(impact(1.0, 70, 38, 0.5, 0.5, 0.04), T.ZOOM_THROUGH[1] - 2, 0.32)

# filament ignition: flicker crackles + warm power-on bloom
for off, g in ((0, 0.9), (1, 0.6), (7, 0.5), (8, 0.7)):
    place(crackle(0.06, 400, 1.0), T.IGNITE + off, 0.18 * g, pan=0.05)
place(impact(1.0, 82, 44, 0.55, 0.6, 0.06), T.IGNITE + 12, 0.42)
place(warm_tone(2.0, [55, 110, 165, 220], 0.35, 0.9), T.IGNITE + 12, 0.16)
hum_n = int(1.6 * SR)
th = np.arange(hum_n) / SR
hum = lp(np.sin(2 * np.pi * 100 * th) + 0.4 * np.sin(2 * np.pi * 200 * th) + 0.15 * np.sin(2 * np.pi * 300 * th), 700)
hum *= np.minimum(1, th / 0.4) * np.exp(-th / 0.9)
place(hum, T.IGNITE + 12, 0.035)
# text slam whoosh for ИДЕИ
place(whoosh(0.35, 0.2, 250, 900, 0.8, 2500), T.IDEA_TEXT - 12, 0.12)

# whip pan
w0, wc, w1 = T.WHIP_1[0], (T.WHIP_1[0] + T.WHIP_1[1]) / 2 + 2, T.WHIP_1[1]
place(whoosh((w1 - w0 + 14) / T.FPS, (wc - w0) / T.FPS, 250, 2200, 0.9, 4200), w0, 0.5, pan=-0.3)
place(impact(1.0, 85, 50, 0.22, 0.45, 0.05), w1 - 6, 0.22)

# dominoes: a finger-flick tip, then progressively deeper knocks
place(knock(0.6, 0.35), T.ACTION_START + T.DOMINO_TIP_LOCAL, 0.5, pan=-0.4)
for i, h in enumerate(T.DOMINO_HITS):
    size = 1.38 ** i
    pan = -0.35 + 0.7 * i / (len(T.DOMINO_HITS) - 1)
    if i < len(T.DOMINO_HITS) - 1:
        place(knock(size, 1.0), h, 0.32 + 0.06 * i, pan=pan)
        if i >= 3:
            place(impact(1.0, 70, 40, 0.25 + 0.06 * i, 0.4, 0.0), h, 0.06 * i)
    else:  # the giant lands: heavy, warm, no crack
        place(knock(size, 1.0), h, 0.55, pan=pan)
        place(impact(1.0, 62, 30, 0.9, 1.0, 0.03), h, 0.85)
        place(lp(pink(int(1.2 * SR)), 900) * np.exp(-np.arange(int(1.2 * SR)) / SR / 0.35), h + 1, 0.10)  # dust settle
# air under the keyword
place(whoosh(0.5, 0.28, 300, 1100, 0.8, 2800), T.ACTION_TEXT - 16, 0.12)

# flash transition: reverse swell into a soft bloom hit
f0, fp, f1 = T.FLASH
place(whoosh((fp - f0 + 4) / T.FPS, (fp - f0) / T.FPS, 200, 3000, 1.1, 4500), f0, 0.38)
rs_n = int((fp - f0) / T.FPS * SR)
rt_ = np.arange(rs_n) / SR
riser = lp(np.sin(2 * np.pi * (60 + 50 * (rt_ / rt_[-1]) ** 2) * rt_), 600) * (rt_ / rt_[-1]) ** 2.5
place(riser, f0, 0.14)
place(impact(1.0, 75, 36, 0.8, 0.8, 0.04), fp, 0.6)
place(warm_tone(2.4, [73.4, 110, 146.8, 220], 0.08, 1.1), fp, 0.16)

# coins: a muted cascade, slightly humanised
for k, f in enumerate(T.COIN_LANDS):
    place(coin_tap(rng.uniform(0.6, 1.0), rng.uniform(0.85, 1.12)), f + rng.uniform(-0.3, 0.3),
          0.20, pan=rng.uniform(-0.35, 0.45))
place(whoosh(0.5, 0.25, 300, 1000, 0.8, 2600), T.RESULT_TEXT - 14, 0.10)
# counter settles: warm major lift
place(impact(1.0, 80, 45, 0.4, 0.4, 0.03), T.COUNT_UP[1], 0.3)
place(warm_tone(2.6, [65.4, 98, 130.8, 164.8], 0.15, 1.2), T.COUNT_UP[1], 0.13)

# final lockup: three soft felt pops, last one with a low bloom
for k in range(3):
    fr = T.LOCKUP + 18 + 9 * k
    place(impact(1.0, 110 - 12 * k, 60, 0.12, 0.3, 0.04), fr, 0.16 + 0.05 * k, pan=(-0.3, 0, 0.3)[k])
place(warm_tone(2.0, [65.4, 98, 130.8, 196], 0.1, 0.9), T.LOCKUP + 36, 0.12)


# ------------------------------------------------------------------ room + master
def reverb(x, seconds=1.4, wet=0.16):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t / (seconds / 5))
        ir = lp(ir, 2400)
        ir[: int(0.012 * SR)] = 0  # pre-delay
        ir /= np.sqrt((ir ** 2).sum())
        out[ch] = signal.fftconvolve(x[ch], ir)[: x.shape[1]]
    return x * (1 - wet) + out * wet * 2.2


mix = reverb(mix)
mix = np.stack([lp(hp(c, 28, 2), 9000, 2) for c in mix])  # no rumble, no fizz
peak = np.abs(mix).max()
mix = mix / peak * 1.25
mix = np.tanh(mix) / np.tanh(1.25)  # soft-knee glue
mix *= 10 ** (-1.0 / 20)
out = sys.argv[1] if len(sys.argv) > 1 else "sfx.wav"
from scipy.io import wavfile

wavfile.write(out, SR, (mix.T * 32767).astype(np.int16))
print("wrote", out, f"{DUR:.2f}s")
