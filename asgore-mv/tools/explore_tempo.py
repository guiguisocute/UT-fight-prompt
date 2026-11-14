#!/usr/bin/env python3
"""Precise tempo / phase probe: scores candidate BPMs on the onset envelope and
fits a line through backtracked onsets snapped to the grid (drift check).

    .venv/Scripts/python tools/explore_tempo.py asset/music/music2.mp3 114.5 115.2
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa

SRC = sys.argv[1]
LO, HI = float(sys.argv[2]), float(sys.argv[3])
SR = 22050
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, sr = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / sr
hop = 32
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, n_fft=1024)
ft = librosa.frames_to_time(np.arange(len(oenv)), sr=sr, hop_length=hop)
T1 = float(sys.argv[4]) if len(sys.argv) > 4 else dur - 0.5
res = []
for bpm in np.arange(LO, HI, 0.005):
    per = 60 / bpm / 4
    best = max((np.interp(np.arange(ph, T1, per), ft, oenv).mean(), ph) for ph in np.arange(0, per, 0.001))
    res.append((best[0], bpm, best[1]))
res.sort(reverse=True)
for s, b, p in res[:8]:
    print(f'bpm {b:.3f} phase {p:.4f} score {s:.4f}')
for b in (114.0, 114.5, 114.8, 114.85, 114.9, 115.0, 120.0):
    per = 60 / b / 4
    s = max(np.interp(np.arange(ph, T1, per), ft, oenv).mean() for ph in np.arange(0, per, 0.001))
    print(f'  check {b}: {s:.4f}')

# drift: snap backtracked onsets to the best grid, regress residual vs time
_, bpm, ph = res[0]
s16 = 60 / bpm / 4
on = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=hop, backtrack=False, units='time')
st = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
k = np.round((on - ph) / s16)
r = on - (ph + k * s16)
m = np.abs(r) < s16 * 0.3
A = np.vstack([on[m], np.ones(m.sum())]).T
slope, icpt = np.linalg.lstsq(A, r[m], rcond=None)[0]
print(f'residual drift slope {slope*1e3:.4f} ms/s, mean residual {r[m].mean()*1e3:.1f} ms; corrected bpm {bpm/(1+slope):.4f}')
for w0 in range(0, int(dur), 20):
    mm = m & (on >= w0) & (on < w0 + 20)
    if mm.any():
        print(f'  {w0:3d}-{w0+20:3d}s: median residual {np.median(r[mm])*1e3:6.1f} ms  (n={mm.sum()})')
