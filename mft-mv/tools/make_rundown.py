"""The cold open's score with its ending: Chaplin's "At the Picture" as it is up to the throw, then the
record running down - a gramophone whose spring has given out: speed and pitch sinking together to a
stop, the sound dulling and dropping as it goes, the needle's hiss after (ENTRANCE.md).
-> asset/music/chaplin_cold.mp3 (the project root; src/util.js MV.MUSIC plays it from 0 to T.coldStop).

usage: python -I tools/make_rundown.py
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'asset/music/Charlie_Chaplin_-_At_the_Picture_k_f_Novye_Vremena_1936g_(mp3.pm).mp3')
OUT = os.path.join(ROOT, 'asset/music/chaplin_cold.mp3')
WORK = os.path.join(ROOT, 'work', 'chaplin')
SR = 44100
RELEASE = 45.58
DOWN = 1.1
HISS = 0.2

os.makedirs(WORK, exist_ok=True)
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', SRC, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
x = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).astype(np.float64)

head = x[: int(round(RELEASE * SR))]
n = int(DOWN * SR)
u = np.arange(n) / n
r = (1 - u) ** 1.6
pos = RELEASE * SR + np.cumsum(r)
i0 = np.floor(pos).astype(int)
f = (pos - i0)[:, None]
tail = x[i0] * (1 - f) + x[np.minimum(i0 + 1, len(x) - 1)] * f
cut = 300 + 9000 * r
a = np.exp(-2 * np.pi * cut / SR)
y = np.zeros_like(tail)
acc = tail[0].copy()
for k in range(n):
    acc = a[k] * acc + (1 - a[k]) * tail[k]
    y[k] = acc
y *= (0.35 + 0.65 * np.sqrt(r))[:, None]
rng = np.random.default_rng(7)
m = int(HISS * SR)
hiss = rng.normal(0, 0.012, (m, 2)) * np.linspace(1, 0, m)[:, None]
hiss += (rng.random((m, 1)) < 0.0015) * rng.normal(0, 0.08, (m, 1)) * np.linspace(1, 0, m)[:, None]
out = np.concatenate([head, y, hiss]).astype(np.float32)
wav = os.path.join(WORK, 'chaplin_cold.f32')
out.tofile(wav)
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-i', wav, '-c:a', 'libmp3lame', '-b:a', '192k', OUT], check=True)
print(f'{OUT}: {len(out) / SR:.3f} s (the record to {RELEASE} s, run down by {RELEASE + DOWN:.2f}, hiss to {len(out) / SR:.2f})')

raw2 = subprocess.run(['ffmpeg', '-v', 'error', '-i', OUT, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
z = np.frombuffer(raw2, dtype=np.float32).reshape(-1, 2)[:, 0].astype(np.float64)
seg0, seg1 = x[int(10 * SR): int(14 * SR), 0], z[int(10 * SR) - 4000: int(14 * SR) + 4000]
cc = np.correlate(seg1, seg0, mode='valid')
lag = int(np.argmax(cc)) - 4000
print(f'lag after re-encoding: {lag} samples ({lag / SR * 1000:.1f} ms)')
sys.exit(0 if abs(lag) <= 44 else 1)
