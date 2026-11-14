#!/usr/bin/env python3
"""Find the near-silent gaps / big re-entries of a track and print the strong
onsets around them in beat units of a reference grid (meter-change hunting).

    .venv/Scripts/python tools/explore_gaps.py asset/music/music2.mp3 114.8466 0.013
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa

SRC, BPM, OFF = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
SR = 22050
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, sr = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / sr
beat = 60 / BPM
hop = 64
rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop, center=False)[0]
rt = (np.arange(len(rms)) * hop + 1024) / sr
db = 20 * np.log10(rms + 1e-6)
# local loudness reference: 2 s moving median
k = int(2 * sr / hop)
from scipy.ndimage import median_filter, uniform_filter1d
ref = median_filter(db, size=k)
sm = uniform_filter1d(db, int(0.08 * sr / hop))
dip = sm < ref - 9
# group dips
gaps = []
i = 0
while i < len(dip):
    if dip[i]:
        j = i
        while j < len(dip) and dip[j]:
            j += 1
        if (rt[j - 1] - rt[i]) > 0.12:
            gaps.append((rt[i], rt[j - 1]))
        i = j
    else:
        i += 1
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, n_fft=1024, center=False)
ot = (np.arange(len(oenv)) * hop + 1024) / sr
on = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=hop, units='frames', delta=0.3)
def b(t):
    x = (t - OFF) / beat
    return f'{t:7.3f}s = beat {x:7.2f} (bar {int(x // 4)} + {x % 4:4.2f})'
print('gaps (loudness dips > 9 dB below local median):')
for g0, g1 in gaps:
    nxt = [ot[i] for i in on if ot[i] > g1 - 0.05][:3]
    print(f'  {b(g0)}  ->  {b(g1)}  ({g1 - g0:.2f}s)  next onsets: ' + ', '.join(f'{(t - OFF) / beat:.2f}' for t in nxt))
