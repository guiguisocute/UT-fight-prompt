#!/usr/bin/env python3
"""Check that the FLP transcription lines up with the mp3, and fit the grid.

1. audio alone: brute-force constant 16th grid on the onset envelope (as in the
   sibling projects) -> BPM and phase;
2. FLP vs audio: lag/scale that maximise the audio flux at the FLP onsets;
3. per-onset residuals (local flux peak near each FLP drum hit) over the song.

    .venv/Scripts/python tools/explore_align.py
"""
import json
import numpy as np, librosa

D = json.load(open('work/flp_notes.json'))
y, sr = librosa.load('asset/music/Toby Fox - Battle Against A True Hero.mp3', sr=22050, mono=True)
dur = len(y) / sr
hop = 64
# non-centred short frames: frame END time is right after the attack
S = np.abs(librosa.stft(y, n_fft=512, hop_length=hop, center=False))
L = np.log1p(S * 20)
flux = np.diff(L, axis=1, prepend=L[:, :1]); flux[flux < 0] = 0
flux = flux.mean(0)
ft = (np.arange(len(flux)) * hop + 512) / sr - hop / 2 / sr

print(f'duration {dur:.3f}s')
# 1. audio-only grid
best = None
for bpm in np.arange(148, 152, 0.01):
    per = 60 / bpm / 4
    for ph in np.arange(0, per, 0.002):
        s = np.interp(np.arange(ph, dur - 1, per), ft, flux).mean()
        if best is None or s > best[0]:
            best = (s, bpm, ph)
print(f'audio grid: {best[1]:.2f} BPM, phase {best[2] * 1000:.1f} ms')
for w0 in range(0, int(dur) - 20, 20):
    bb = None
    for bpm in np.arange(149, 151, 0.01):
        per = 60 / bpm / 4
        for ph in np.arange(0, per, 0.002):
            s = np.interp(np.arange(w0 + ph, w0 + 20, per), ft, flux).mean()
            if bb is None or s > bb[0]:
                bb = (s, bpm, ph)
    print(f'  window {w0:3d}-{w0 + 20:3d}s: {bb[1]:.2f} BPM phase {(bb[2] + w0) % (15 / bb[1]) * 1000:.1f} ms')

# 2. FLP onsets vs audio
on = np.array(sorted({n['t'] for n in D['notes']} | {c['t'] for c in D['clips']}))
drum = np.array(sorted({n['t'] for n in D['notes'] if n['ch'] in (16, 17)}))
res = []
for sc in np.arange(0.998, 1.002, 0.0002):
    for lag in np.arange(-0.15, 0.15, 0.001):
        res.append((np.interp(on * sc + lag, ft, flux).mean(), sc, lag))
res.sort(reverse=True)
print('FLP vs audio (all onsets): best', [(round(s, 4), round(sc, 4), round(l * 1000)) for s, sc, l in res[:5]])
res = [(np.interp(drum + lag, ft, flux).mean(), lag) for lag in np.arange(-0.15, 0.15, 0.001)]
res.sort(reverse=True)
print('FLP drums vs audio: best lag', [(round(s, 4), round(l * 1000)) for s, l in res[:5]])

# 3. residuals: flux peak within +-40 ms of each kick/snare
pk = []
for t in drum:
    m = (ft > t - 0.04) & (ft < t + 0.04)
    if m.any():
        pk.append((t, ft[m][np.argmax(flux[m])] - t))
pk = np.array(pk)
for a in range(0, int(dur), 20):
    sel = pk[(pk[:, 0] >= a) & (pk[:, 0] < a + 20)]
    if len(sel):
        print(f'  {a:3d}-{a + 20:3d}s  drum hits {len(sel):3d}  median residual {np.median(sel[:, 1]) * 1000:+.1f} ms')

# first audible sample
env = np.abs(y)
print('first sample above -40 dBFS', np.argmax(env > 0.01) / sr, 's;  last above', (len(env) - np.argmax(env[::-1] > 0.01)) / sr, 's')
