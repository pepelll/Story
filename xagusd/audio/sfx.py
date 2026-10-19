# Звук 3.5 с, только SFX (без музыки). Тайминги совпадают с CFG в scene.html.
# python3 -I audio/sfx.py out/sfx.wav
import sys, wave, numpy as np

SR = 48000
DUR = 3.5
out_path = sys.argv[1]
rng = np.random.default_rng(11)
n = int(SR * DUR)
L = np.zeros(n); R = np.zeros(n)

HIST_T0, HIST_STEP, HIST_N = 0.24, 0.026, 24
BARS_T0 = [0.50, 0.62, 0.76]
BIG = [(1.10, 0.42), (1.66, 0.42), (2.20, 0.50)]
FINALE = 2.80


def tt(m):
    return np.arange(m) / SR


def env(m, a, tau):
    t = tt(m)
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / tau)


def lp(x, fc):
    # однополюсный ФНЧ, fc может быть массивом
    fc = np.broadcast_to(np.asarray(fc, float), x.shape)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x); s = 0.0
    for i in range(len(x)):
        s = (1 - a[i]) * x[i] + a[i] * s; y[i] = s
    return y


def hp(x, fc):
    return x - lp(x, fc)


def norm(x):
    return x / (np.abs(x).max() + 1e-9)


def place(sig, t0, gain=1.0, pan=0.0):
    i = int(round(t0 * SR))
    if i < 0: sig = sig[-i:]; i = 0
    m = min(len(sig), n - i)
    if m <= 0: return
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i + m] += sig[:m] * gain * gl * 1.414
    R[i:i + m] += sig[:m] * gain * gr * 1.414


def sine_sweep(f0, f1, m, curve=1.0):
    t = tt(m) / (m / SR)
    f = f0 + (f1 - f0) * t ** curve
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def tick(freq, dur=0.03, bright=1.0):
    # короткий UI-тик: синус с быстрым спадом + щелчок шума
    m = int(dur * SR); t = tt(m)
    f = freq * (1 + 0.5 * np.exp(-t / 0.002))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(m, 0.0006, dur / 5)
    c = hp(rng.standard_normal(m), 3000) * env(m, 0.0002, 0.0015) * 0.5 * bright
    return s + c


def pop(freq, dur=0.12):
    m = int(dur * SR); t = tt(m)
    f = freq * (1 + 0.9 * np.exp(-t / 0.01))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(m, 0.001, 0.03)
    c = lp(rng.standard_normal(m), 5000) * env(m, 0.0003, 0.004) * 0.35
    return s + c


def whoosh(dur, f0, f1, peak=0.6, curve=1.5):
    m = int(dur * SR); t = tt(m) / dur
    fc = f0 + (f1 - f0) * t ** curve
    w = rng.standard_normal(m)
    w = lp(hp(w, fc * 0.3), fc)
    shape = np.where(t < peak, (t / peak) ** 2, np.exp(-(t - peak) / (1 - peak) * 4))
    return norm(w * shape)


def metal(freq, dur=0.9):
    # удар по металлическому бруску: негармонические моды свободного стержня
    m = int(dur * SR); t = tt(m)
    s = np.zeros(m)
    for ratio, amp, tau in [(1, 1, 0.35), (2.756, 0.55, 0.22), (5.404, 0.35, 0.12), (8.933, 0.2, 0.07), (13.34, 0.1, 0.04)]:
        s += amp * np.sin(2 * np.pi * freq * ratio * t + ratio) * np.exp(-t / tau)
    s *= np.minimum(1, t / 0.0008)
    knock = lp(rng.standard_normal(m), 2500) * env(m, 0.0004, 0.01) * 0.8
    thud = np.sin(2 * np.pi * np.cumsum(140 * (1 + np.exp(-t / 0.01))) / SR) * env(m, 0.001, 0.04) * 0.7
    return norm(s + knock + thud)


def boom(f0=52, dur=0.7):
    # импакт: саб с падением высоты + тело + транзиент
    m = int(dur * SR); t = tt(m)
    f = f0 * (1 + 2.2 * np.exp(-t / 0.03))
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(m, 0.002, 0.16)
    body = lp(rng.standard_normal(m), 900) * env(m, 0.001, 0.06) * 1.2
    click = hp(rng.standard_normal(m), 2500) * env(m, 0.0002, 0.006) * 0.7
    return norm(np.tanh((sub * 1.3 + body + click) * 1.5))


def riser(dur, f0, f1):
    # подъём к удару: развёртка шума + восходящий синус с вибрато
    m = int(dur * SR); t = tt(m) / dur
    nz = whoosh(dur, 400, 7000, peak=0.97, curve=2.0)
    tone = sine_sweep(f0, f1, m, 1.6) + 0.4 * sine_sweep(f0 * 1.5, f1 * 1.5, m, 1.6)
    tone *= t ** 2.2
    return norm(nz * 0.8 + tone * 0.35)


def bell(freq, dur=1.2):
    m = int(dur * SR); t = tt(m)
    s = np.zeros(m)
    for ratio, amp, tau in [(1, 1, 0.6), (2, 0.4, 0.4), (3.01, 0.25, 0.25), (4.2, 0.12, 0.12)]:
        s += amp * np.sin(2 * np.pi * freq * ratio * t) * np.exp(-t / tau)
    return norm(s * np.minimum(1, t / 0.002))


def shimmer(dur=0.9):
    m = int(dur * SR); t = tt(m)
    e = np.minimum(1, t / 0.05) * np.exp(-t / 0.28)
    s = np.zeros(m)
    for k, fq in enumerate([2637, 3136, 3951, 4699, 5274, 6272, 7902]):
        s += np.sin(2 * np.pi * fq * t * (1 + 0.003 * np.sin(2 * np.pi * 6 * t)) + k) * 0.85 ** k
    s *= e * (0.7 + 0.3 * np.sin(2 * np.pi * 18 * t))
    sp = hp(rng.standard_normal(m), 6000) * (rng.random(m) < 0.015) * 5 * e
    return norm(norm(s) + lp(sp, 14000) * 0.4)


# --- 0. интро: мягкий воздушный свелл + саб
place(whoosh(0.7, 200, 3000, peak=0.45), 0.0, 0.16, -0.2)
m = int(0.6 * SR); place(sine_sweep(38, 60, m) * np.sin(np.pi * np.clip(tt(m) / 0.6, 0, 1)) ** 2, 0.0, 0.14)

# --- 1. шапка: иконка, цена, плашка
place(pop(620), 0.10, 0.32, -0.5)
place(tick(2400, 0.04), 0.11, 0.12, -0.5)
place(pop(820, 0.1), 0.22, 0.26, 0.55)
place(tick(3200, 0.03), 0.34, 0.16, 0.6)
place(pop(1040, 0.08), 0.36, 0.18, 0.6)

# --- 2. исторические свечи: россыпь тихих тиков слева направо, высота растёт
for i in range(HIST_N):
    t0 = HIST_T0 + i * HIST_STEP + 0.05
    f = 1500 * 2 ** (i / HIST_N * 0.9) * (1 + (rng.random() - 0.5) * 0.04)
    place(tick(f, 0.025, 0.6), t0, 0.07 + 0.03 * (i % 3 == 0), -0.75 + 1.2 * i / HIST_N)

# --- 3. слитки: металлический «клинк» при приземлении
for k, (t0, f, pan) in enumerate(zip(BARS_T0, [1180, 1320, 1560], [-0.35, 0.35, 0.0])):
    place(metal(f), t0 + 0.2, 0.45, pan)
place(whoosh(0.35, 300, 2500, peak=0.7), 0.42, 0.10)

# --- 4. ценовая линия: короткий свайп
place(whoosh(0.3, 1500, 6000, peak=0.5), 0.84, 0.08, 0.6)

# --- 5. три большие свечи
for k, (t0, d) in enumerate(BIG):
    hit = t0 + d * 0.55
    up = 2 ** (k * 3 / 12)                      # каждая следующая на малую терцию выше
    rd = 0.38
    place(riser(rd, 180 * up, 520 * up), hit - rd, 0.30, 0.15)
    place(boom(48 + k * 4), hit, 0.62 + 0.08 * k)
    place(pop(440 * up, 0.18), hit, 0.22, 0.1)
    place(bell(880 * up, 0.8), hit + 0.005, 0.10, 0.25)
    # счётчик цены: быстрые тики, редеющие к концу роста
    times = t0 + d * (np.linspace(0, 1, 16) ** 1.8)
    for j, tj in enumerate(times):
        place(tick(2800 * up * (1 + j / 40), 0.02, 0.4), tj, 0.06, 0.7)

# --- 6. финал: двойной чайм + искры + блик по слиткам
place(bell(1318.5, 1.0), FINALE, 0.36, -0.2)
place(bell(1975.5, 1.0), FINALE + 0.09, 0.32, 0.25)
place(bell(2637.0, 0.8), FINALE + 0.18, 0.12, 0.0)
place(shimmer(0.7), FINALE + 0.03, 0.28, -0.4)
place(shimmer(0.7), FINALE + 0.05, 0.18, 0.45)
place(whoosh(0.4, 2000, 9000, peak=0.4), FINALE, 0.08)
for k in range(3):
    place(tick(4200 + 500 * k, 0.05), FINALE + 0.08 + k * 0.07, 0.07, -0.4 + 0.4 * k)

# --- мастер: лёгкий ревер (свёртка с синтетическим IR), насыщение, нормализация
ir_m = int(0.9 * SR)
ir = rng.standard_normal((2, ir_m)) * np.exp(-tt(ir_m) / 0.22)
ir[:, :int(0.012 * SR)] = 0
ir = np.stack([lp(hp(ch, 300), 6000) for ch in ir])
ir /= np.sqrt((ir ** 2).sum(axis=1, keepdims=True))
dry = np.stack([L, R])
N = 1 << int(np.ceil(np.log2(n + ir_m)))
wet = np.fft.irfft(np.fft.rfft(dry, N) * np.fft.rfft(ir, N), N)[:, :n]
mix = dry + wet * 0.18
mix = np.tanh(mix * 1.3) / 1.3
fo = int(0.08 * SR)
mix[:, -fo:] *= np.linspace(1, 0, fo) ** 2
mix *= 10 ** (-1.0 / 20) / np.abs(mix).max()
pcm = (mix.T * 32767).astype('<i2')
with wave.open(out_path, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('wrote', out_path, 'rms dBFS', round(20 * np.log10(np.sqrt((mix ** 2).mean())), 1))
