# Звуковая дорожка 1.2 с: клики из референса (перкуссионная часть после HPSS) + синтез whoosh/shimmer.
# python3 -I sfx.py perc.npy ../public/sfx.wav
import sys, json, wave, numpy as np
SR = 48000
DUR = 1.2
perc = np.load(sys.argv[1])
out_path = sys.argv[2]
cfg = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
T = {'usd': 0.08, 'sep': 0.15, 'rub': 0.22, 'shine': 0.45, **cfg}
rng = np.random.default_rng(5)
n = int(SR * DUR)
L = np.zeros(n); R = np.zeros(n)

def env_adsr(m, a, d_tau):
    t = np.arange(m) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) / d_tau)

def onepole_lp(x, fc):
    # fc может быть массивом (развёртка фильтра)
    fc = np.broadcast_to(fc, x.shape)
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.zeros_like(x); s = 0.0
    for i in range(len(x)):
        s = (1 - a[i]) * x[i] + a[i] * s; y[i] = s
    return y

def bandpass(x, lo, hi):
    return onepole_lp(x - onepole_lp(x, lo), hi)

def place(sig, t0, gain=1.0, pan=0.0):
    i = int(t0 * SR); m = min(len(sig), n - i)
    if m <= 0: return
    gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    L[i:i+m] += sig[:m] * gain * gl * 1.414; R[i:i+m] += sig[:m] * gain * gr * 1.414

def ref_click(t_peak, pre=0.006, length=0.11):
    # вырезаем транзиент вокруг пика, с плавными краями
    i = int((t_peak - pre - 0.01) * SR)
    seg = perc[i:i + int(length * SR)].copy()
    # точная привязка к пику
    pk = np.argmax(np.abs(seg[: int(0.04 * SR)]))
    seg = perc[i + pk - int(pre * SR): i + pk - int(pre * SR) + int(length * SR)].copy()
    m = len(seg)
    fade = np.ones(m); a = int(0.003 * SR); r = int(0.04 * SR)
    fade[:a] = np.linspace(0, 1, a); fade[-r:] = np.linspace(1, 0, r) ** 2
    seg *= fade * np.exp(-np.arange(m) / SR / 0.05)
    return seg / (np.abs(seg).max() + 1e-9)

def pop(freq, dur=0.09):
    # мягкий «pop»: синус с быстрым спадом высоты + щелчок
    m = int(dur * SR); t = np.arange(m) / SR
    f = freq * (1 + 0.6 * np.exp(-t / 0.008))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env_adsr(m, 0.0015, 0.025)
    click = onepole_lp(rng.standard_normal(m), 6000) * env_adsr(m, 0.0003, 0.003) * 0.4
    return s + click

# 1) whoosh на старте: шум с развёрткой полосы вверх + низ «воздуха»
m = int(0.42 * SR); t = np.arange(m) / SR
sweep = 300 + 5200 * (t / t[-1]) ** 1.6
wn = rng.standard_normal(m)
wh = onepole_lp(wn - onepole_lp(wn, sweep * 0.25), sweep)
shape = np.sin(np.pi * np.clip(t / 0.36, 0, 1)) ** 1.5 * np.exp(-np.maximum(0, t - 0.2) / 0.08)
wh *= shape
wh /= np.abs(wh).max()
sub = np.sin(2 * np.pi * np.cumsum(55 + 40 * t / t[-1]) / SR) * np.sin(np.pi * np.clip(t / 0.3, 0, 1)) ** 2
place(wh, 0.0, 0.3, -0.35)
place(sub, 0.0, 0.18)
# стерео-проход whoosh слева направо: второй экземпляр с другим шумом
wn2 = rng.standard_normal(m)
wh2 = onepole_lp(wn2 - onepole_lp(wn2, sweep * 0.25), sweep) * shape
place(wh2 / np.abs(wh2).max(), 0.01, 0.24, 0.4)

# 2) клики на появление частей: транзиенты из референса + мягкий синус-pop
# самый чистый клик референса — на 0.21 с; для частей — его варианты с разной высотой (ресэмплинг)
base = ref_click(0.21)
def repitch(x, r):
    idx = np.arange(0, len(x) - 1, r)
    return np.interp(idx, np.arange(len(x)), x)
clicks = {'usd': (1.0, 520, -0.12, 0.62), 'sep': (1.18, 760, 0.0, 0.45), 'rub': (0.92, 600, 0.15, 0.66)}
for key, (r, f, pan, g) in clicks.items():
    place(repitch(base, r), T[key], g, pan)
    place(pop(f), T[key], g * 0.45, pan)

# 3) shimmer на блик: стек высоких частиалей с тремоло + искристый шум
m = int(0.55 * SR); t = np.arange(m) / SR
e = np.minimum(1, t / 0.06) * np.exp(-t / 0.16)
sh = np.zeros(m)
for k, fq in enumerate([2637, 3520, 4186, 5274, 6272, 7040]):
    sh += np.sin(2 * np.pi * fq * t * (1 + 0.002 * np.sin(2 * np.pi * 7 * t)) + k) * (0.8 ** k)
sh *= e * (0.75 + 0.25 * np.sin(2 * np.pi * 22 * t))
sp = rng.standard_normal(m); sp = sp - onepole_lp(sp, 7000)
sp *= e * (rng.random(m) < 0.02) * 6
sh = sh / np.abs(sh).max() + onepole_lp(sp, 12000) * 0.25
place(sh, T['shine'], 0.28, -0.3)
place(sh, T['shine'] + 0.012, 0.24, 0.45)

# мастер: мягкое насыщение, fade-out 50 мс, пик -6 dBFS
mix = np.stack([L, R])
mix = np.tanh(mix * 1.2) / 1.2
fo = int(0.05 * SR)
mix[:, -fo:] *= np.linspace(1, 0, fo) ** 2
mix *= 10 ** (-6 / 20) / np.abs(mix).max()
pcm = (mix.T * 32767).astype('<i2')
with wave.open(out_path, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('wrote', out_path, 'peak dBFS', round(20 * np.log10(np.abs(mix).max()), 2))
