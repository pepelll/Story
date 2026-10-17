# Разделение референса на перкуссионную (клики/whoosh) и гармоническую (музыка) части, без scipy
import sys, subprocess, numpy as np, wave
src, out = sys.argv[1], sys.argv[2]
SR = 48000
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).astype(np.float64)
N, H = 2048, 512
win = np.hanning(N)
pad = np.concatenate([np.zeros(N), x, np.zeros(N)])
nf = (len(pad) - N) // H
S = np.stack([np.fft.rfft(pad[i*H:i*H+N] * win) for i in range(nf)], 1)  # bins × frames
M = np.abs(S)
from numpy.lib.stride_tricks import sliding_window_view as sw
k = 17
Mh = np.median(sw(np.pad(M, ((0, 0), (k//2, k//2)), mode='edge'), k, axis=1), axis=-1)
Mp = np.median(sw(np.pad(M, ((k//2, k//2), (0, 0)), mode='edge'), k, axis=0), axis=-1)
mask = Mp**2 / (Mp**2 + Mh**2 + 1e-12)
P = S * mask
y = np.zeros(len(pad)); wsum = np.zeros(len(pad))
for i in range(nf):
    y[i*H:i*H+N] += np.fft.irfft(P[:, i]) * win; wsum[i*H:i*H+N] += win**2
y = (y / np.maximum(wsum, 1e-6))[N:N+len(x)]
np.save(out, y)
# onset report
fr = int(0.01*SR)
e = np.array([np.sqrt((y[i:i+fr]**2).mean()) for i in range(0, len(y)-fr, fr)])
ex = np.array([np.sqrt((x[i:i+fr]**2).mean()) for i in range(0, len(x)-fr, fr)])
for i in range(1, len(e)-1):
    if e[i] > e[i-1] and e[i] >= e[i+1] and 20*np.log10(e[i]+1e-9) > -30:
        print(f"{i*0.01:5.2f}s perc {20*np.log10(e[i]):6.1f} dB  full {20*np.log10(ex[i]):6.1f} dB")
