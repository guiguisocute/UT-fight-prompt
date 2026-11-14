#!/usr/bin/env python3
"""Downbeat / 16th-phase probe: average kick / snare / hat per 16th slot over
bar ranges, for each of the 16 possible rotations of the grid. Also prints the
exact onset times of the first seconds and the length of the sfx we prepend.
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa

SR = 22050
def load(p):
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, 'm.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p, '-ac', '1', '-ar', str(SR), wav], check=True)
        y, _ = librosa.load(wav, sr=SR, mono=True)
    return y
y = load('asset/music/music.mp3')
dur = len(y) / SR
BPM = 148.0
s16 = 60 / BPM / 4
hop = 64
S = np.abs(librosa.stft(y, n_fft=1024, hop_length=hop))
f = librosa.fft_frequencies(sr=SR, n_fft=1024)
st = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=hop)
L = np.log1p(S * 10)
def flux(lo, hi):
    m = (f >= lo) & (f < hi)
    d = np.diff(L[m], axis=1, prepend=L[m][:, :1]); d[d < 0] = 0
    return d.mean(0)
bands = dict(kick=flux(30, 120), snare=flux(150, 400) * 0.5 + flux(1500, 5000), hat=flux(7000, 11000), full=flux(30, 11000))

# fine phase using full flux at the 16th grid
oenv = librosa.onset.onset_strength(y=y, sr=SR, hop_length=hop)
ot = librosa.frames_to_time(np.arange(len(oenv)), sr=SR, hop_length=hop)
best = max(((np.interp(np.arange(ph, dur - 1, s16), ot, oenv).mean(), ph) for ph in np.arange(0, s16, 0.0005)))
ph = best[1]
print(f'16th phase at 148 BPM: {ph:.4f}s')

def slot_val(v, t):
    m = (st >= t - 0.012) & (st < t + 0.035)
    return v[m].max(initial=0)
nsl = int((dur - ph) / s16)
P = {k: np.array([slot_val(v, ph + i * s16) for i in range(nsl)]) for k, v in bands.items()}

RANGES = [(0, 4), (4, 8), (8, 12), (12, 24), (24, 40), (40, 55), (56, 72), (72, 80)]
for (a, b) in RANGES:
    print(f'\nbars {a}-{b} (grid rotation 0 = phase {ph:.3f})')
    for k in ('kick', 'snare', 'hat'):
        v = P[k][a * 16:b * 16]
        v = v[:len(v) // 16 * 16].reshape(-1, 16).mean(0)
        v = v / (v.max() + 1e-9)
        print(f'  {k:5s} ' + ' '.join(f'{x:.2f}' for x in v))

print('\nfirst 8 s strong onsets:')
pk = librosa.util.peak_pick(bands['full'], pre_max=8, post_max=8, pre_avg=20, post_avg=20, delta=0.08, wait=8)
for i in pk:
    if st[i] > 8: break
    sl = (st[i] - ph) / s16
    print(f'  {st[i]:.3f}s  slot {sl:6.2f}  kick {bands["kick"][i]:.2f} snare {bands["snare"][i]:.2f} hat {bands["hat"][i]:.2f}')

for p in ['asset/sfx/PC _ Computer - Undertale - Miscellaneous - Sound Effects/mus_ohyes.ogg']:
    yy = load(p)
    print(p.split('/')[-1], f'{len(yy)/SR:.3f}s')
