#!/usr/bin/env python3
"""BTERTD, closer: when the harmony changes (fine chroma novelty), the swells in the bands, and
the pulse (autocorrelation of the band energy) - for cutting on it.

    .venv/Scripts/python tools/explore_ed2.py
"""
import numpy as np
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter1d
from scipy.signal import find_peaks

SRC = 'asset/music/Toby Fox - But The Earth Refused To Die.mp3'
SR, HOP = 44100, 441  # 10 ms frames
y, sr = librosa.load(SRC, sr=SR, mono=True)
dur = len(y) / sr
t = lambda n: np.arange(n) * HOP / sr

# chroma (CQT) at 10 ms, smoothed over 0.3 s; novelty = distance between the 0.6 s before and after
C = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP, bins_per_octave=36)
Cs = gaussian_filter1d(C, 8, axis=1)
W = 50
nov = np.zeros(C.shape[1])
for i in range(W, C.shape[1] - W):
    a, b = Cs[:, i - W:i].mean(1), Cs[:, i:i + W].mean(1)
    nov[i] = 1 - np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
pk, _ = find_peaks(nov, height=0.004, distance=60)
NAMES = 'C C# D D# E F F# G G# A A# B'.split()
print('harmony changes (t, strength, before -> after):')
for p in pk:
    if p * HOP / sr > 32.5:
        continue
    a, b = Cs[:, max(0, p - W):p].mean(1), Cs[:, p:p + W].mean(1)
    ta = ' '.join(NAMES[k] for k in np.argsort(a)[::-1][:3])
    tb = ' '.join(NAMES[k] for k in np.argsort(b)[::-1][:3])
    print(f'  {p * HOP / sr:6.2f} s  {nov[p]:.3f}  {ta:10s} -> {tb}')

# band energies (dB), smoothed 0.1 s
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP)) ** 2
f = librosa.fft_frequencies(sr=sr, n_fft=2048)
bands = {'sub <150': (0, 150), 'low 150-500': (150, 500), 'mid 500-1500': (500, 1500), 'hi 1.5-4k': (1500, 4000), 'air 4-10k': (4000, 10000)}
E = {}
for k, (a, b) in bands.items():
    e = S[(f >= a) & (f < b)].sum(0)
    E[k] = gaussian_filter1d(10 * np.log10(e + 1e-9), 10)
tt = t(S.shape[1])
print('band dB per 0.5 s (sub low mid hi air):')
for s in np.arange(0, 33, 0.5):
    m = (tt >= s) & (tt < s + 0.5)
    print(f'  {s:5.1f}  ' + '  '.join(f'{E[k][m].mean():6.1f}' for k in bands))

# the pulse: autocorrelation of the onset-ish derivative of each band (0.2 .. 4 s lags)
for k in bands:
    d = np.diff(E[k], prepend=E[k][0])
    d = np.maximum(d, 0)
    d = d[(tt > 0.5) & (tt < 28)]
    d = d - d.mean()
    ac = np.correlate(d, d, 'full')[len(d) - 1:]
    ac /= ac[0]
    lags = np.arange(len(ac)) * HOP / sr
    m = (lags > 0.2) & (lags < 8)
    pp, _ = find_peaks(ac[m], distance=10)
    best = sorted(pp, key=lambda i: -ac[m][i])[:5]
    print(f'pulse {k:12s}: ' + ', '.join(f'{lags[m][i]:.2f}s ({ac[m][i]:.2f})' for i in sorted(best)))

fig, ax = plt.subplots(3, 1, figsize=(24, 11), sharex=True)
ax[0].plot(tt[:len(nov)], nov[:len(tt)], lw=0.7)
for p in pk: ax[0].axvline(p * HOP / sr, color='r', lw=0.6)
ax[0].set_ylabel('harmony change')
for k in bands: ax[1].plot(tt, E[k] - E[k][(tt > 1) & (tt < 28)].mean(), lw=0.7, label=k)
ax[1].legend(); ax[1].set_ylim(-12, 8); ax[1].set_ylabel('band dB (rel)')
ax[2].imshow(Cs, aspect='auto', origin='lower', extent=[0, dur, 0, 12], cmap='magma')
ax[2].set_yticks(np.arange(12) + 0.5); ax[2].set_yticklabels(NAMES)
for a_ in ax: a_.set_xticks(np.arange(0, dur, 0.5)); a_.grid(axis='x', lw=0.3)
plt.tight_layout(); plt.savefig('work/ed_look2.png', dpi=55)
print('-> work/ed_look2.png')
