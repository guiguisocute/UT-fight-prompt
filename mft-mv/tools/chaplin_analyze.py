"""The cold open's music (Charlie Chaplin, "At the Picture", Modern Times 1936): tempo and beats,
the loudness, where the music changes (sections from a self-similarity novelty curve), the accents -
to cut an excerpt on its phrases and hang the gags on its hits.
-> work/chaplin/analysis.png (loudness, onsets, beats, section boundaries over time) and a printout.

usage: python -I tools/chaplin_analyze.py [wav]
"""
import os
import sys

import librosa
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
wav = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'chaplin', 'chaplin.wav')
y, sr = librosa.load(wav, sr=22050, mono=True)
dur = len(y) / sr
HOP = 512
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=HOP, tightness=100)
bt = librosa.frames_to_time(beats, sr=sr, hop_length=HOP)
rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
ft = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=HOP)
print(f'duration {dur:.2f} s, global tempo {float(np.atleast_1d(tempo)[0]):.1f} BPM, {len(bt)} beats')
# local tempo: beat intervals in 8-beat windows
ibi = np.diff(bt)
for i in range(0, len(ibi) - 8, 8):
    print(f'  {bt[i]:7.2f} s  {60 / np.median(ibi[i:i + 8]):6.1f} BPM')
# sections: chroma + mfcc beat-synchronous self-similarity -> checkerboard novelty
C = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP)
M = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=HOP)
F = np.vstack([librosa.util.normalize(C), librosa.util.normalize(M)])
Fs = librosa.util.sync(F, beats, aggregate=np.median)
S = np.corrcoef(Fs.T)
S = np.nan_to_num(S)
K = 8
g = np.outer(np.r_[np.ones(K), -np.ones(K)], np.r_[np.ones(K), -np.ones(K)])
nov = np.zeros(S.shape[0])
for i in range(K, S.shape[0] - K):
    nov[i] = np.sum(S[i - K:i + K, i - K:i + K] * g)
nov = np.maximum(nov, 0)
pk = librosa.util.peak_pick(nov, pre_max=6, post_max=6, pre_avg=8, post_avg=8, delta=nov.max() * 0.08, wait=8)
bounds = [float(bt[min(p, len(bt) - 1)]) for p in pk]
print('section boundaries (s):', ' '.join(f'{b:.2f}' for b in bounds))
# accents: the strongest onsets
on = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=HOP, units='frames')
strong = on[np.argsort(-oenv[on])[:40]]
print('strongest accents (s):', ' '.join(f'{v:.2f}' for v in sorted(librosa.frames_to_time(strong, sr=sr, hop_length=HOP))))
# the picture: loudness (white), onset strength (grey), beats (ticks), boundaries (red), 1 px = 0.05 s
PX = 20
Wd, Hd = int(dur * PX) + 40, 220
img = Image.new('RGB', (Wd, Hd), (0, 0, 0))
d = ImageDraw.Draw(img)
r = rms / rms.max(); o = oenv / oenv.max()
for i in range(len(ft)):
    x = 20 + int(ft[i] * PX)
    d.line([(x, 200), (x, 200 - int(r[i] * 120))], fill=(200, 200, 200))
    d.point((x, 200 - int(o[i] * 70) - 125), fill=(110, 110, 110))
for b in bt:
    x = 20 + int(b * PX); d.line([(x, 200), (x, 206)], fill=(80, 200, 255))
for b in bounds:
    x = 20 + int(b * PX); d.line([(x, 0), (x, 210)], fill=(255, 60, 60)); d.text((x + 2, 2), f'{b:.1f}', fill=(255, 120, 120))
for s in range(0, int(dur) + 1, 5):
    x = 20 + s * PX; d.text((x, 208), str(s), fill=(255, 255, 0))
img.save(os.path.join(ROOT, 'work', 'chaplin', 'analysis.png'))
np.save(os.path.join(ROOT, 'work', 'chaplin', 'beats.npy'), bt)
print('work/chaplin/analysis.png', img.size)
