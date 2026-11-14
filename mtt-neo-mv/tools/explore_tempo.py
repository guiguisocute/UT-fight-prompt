#!/usr/bin/env python3
"""Exploration: is the tempo constant? Sliding-window tempo + global fit.

    ../mtt-mv/.venv/Scripts/python tools/explore_tempo.py [music.mp3]
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa

SRC = sys.argv[1] if len(sys.argv) > 1 else 'asset/music/power_of_neo_unfinished_wip.mp3'
SR = 22050
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, sr = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / sr
print(f'duration {dur:.3f}s')

hop = 64
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, n_fft=1024)
ft = librosa.frames_to_time(np.arange(len(oenv)), sr=sr, hop_length=hop)

# RMS per second to see silence / structure
rms = librosa.feature.rms(y=y, hop_length=512)[0]
rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
print('\nRMS per 2s:')
line = []
for s in np.arange(0, dur, 2):
    v = rms[(rt >= s) & (rt < s + 2)].mean()
    line.append(f'{s:5.0f}s {20*np.log10(v+1e-9):6.1f}dB')
for i in range(0, len(line), 6):
    print('  ' + ' | '.join(line[i:i + 6]))

# sliding-window tempo (12 s windows, 4 s step) via autocorrelation tempogram
print('\nwindowed tempo (librosa.feature.tempo, 12s windows):')
for s in np.arange(0, dur - 6, 4):
    m = (ft >= s) & (ft < s + 12)
    t = librosa.feature.tempo(onset_envelope=oenv[m], sr=sr, hop_length=hop, aggregate=None, start_bpm=150)
    t2 = librosa.feature.tempo(onset_envelope=oenv[m], sr=sr, hop_length=hop, start_bpm=150)
    print(f'  {s:6.1f}-{s+12:6.1f}s  tempo {float(t2[0]):7.2f}')

# brute force fine tempo per window: maximise mean onset strength on a 16th grid
def fit(t0, t1, lo=100, hi=200, step=0.05):
    m = (ft >= t0) & (ft < t1)
    best = None
    for bpm in np.arange(lo, hi, step):
        per = 60 / bpm / 4
        for ph in np.arange(0, per, 0.004):
            g = np.arange(t0 + ph, t1, per)
            s = np.interp(g, ft, oenv).mean()
            if best is None or s > best[0]:
                best = (s, bpm, ph)
    return best

print('\nbrute-force 16th-grid fit per 20s window (100-200 BPM):')
for s in np.arange(0, dur - 10, 10):
    b = fit(s, min(dur, s + 20))
    print(f'  {s:6.1f}-{min(dur, s+20):6.1f}s  bpm {b[1]:7.2f}  phase {b[2]:.3f}  score {b[0]:.3f}')
