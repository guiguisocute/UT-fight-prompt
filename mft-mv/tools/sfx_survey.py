"""A look at the game's sound effects pack before choosing from it: for each file its length, loudness,
where its energy sits (attack, sustain, tail) and which way its pitch goes (spectral centroid early vs
late - a slide whistle up or down, a falling bomb) - printed, sorted by name.

usage: python -I tools/sfx_survey.py <pack dir> [name ...]
"""
import os
import sys

import librosa
import numpy as np

pack = sys.argv[1]
only = set(sys.argv[2:])
rows = []
for f in sorted(os.listdir(pack), key=str.lower):
    n, ext = os.path.splitext(f)
    if ext.lower() not in ('.wav', '.ogg') or (only and n not in only):
        continue
    try:
        y, sr = librosa.load(os.path.join(pack, f), sr=22050, mono=True)
    except Exception as e:
        rows.append(f'{n:28s} unreadable ({e.__class__.__name__})')
        continue
    if len(y) < 64:
        rows.append(f'{n:28s} empty')
        continue
    dur = len(y) / sr
    rms = librosa.feature.rms(y=y, frame_length=512, hop_length=256)[0]
    pk = float(np.max(np.abs(y)))
    tpk = float(np.argmax(rms)) * 256 / sr
    live = float(np.sum(rms > rms.max() * 0.25)) * 256 / sr
    cen = librosa.feature.spectral_centroid(y=y, sr=sr, n_fft=512, hop_length=256)[0]
    on = rms > rms.max() * 0.1
    c = cen[on] if on.sum() > 2 else cen
    k = max(1, len(c) // 4)
    c0, c1 = float(np.median(c[:k])), float(np.median(c[-k:]))
    f0 = librosa.yin(y, fmin=80, fmax=2000, sr=sr, frame_length=1024) if dur > 0.12 else np.array([0.0])
    f0v = f0[np.isfinite(f0)]
    p0 = float(np.median(f0v[: max(1, len(f0v) // 4)])) if len(f0v) else 0.0
    p1 = float(np.median(f0v[-max(1, len(f0v) // 4):])) if len(f0v) else 0.0
    rows.append(f'{n:28s} {dur:6.2f}s  peak {pk:4.2f}  loudest {tpk:5.2f}s  live {live:5.2f}s  centroid {c0:6.0f}->{c1:6.0f}  pitch {p0:6.0f}->{p1:6.0f}')
print('\n'.join(rows))
