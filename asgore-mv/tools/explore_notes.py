#!/usr/bin/env python3
"""Per-bar note dump on a fixed grid: bass per beat, top voice per 8th
(harmonic part, CQT), drum hits per 16th (attack-aligned flux).

    .venv/Scripts/python tools/explore_notes.py asset/music/music2.mp3 114.8466 0.013 [bar0 bar1]
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa

SRC, BPM, OFF = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
B0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
B1 = int(sys.argv[5]) if len(sys.argv) > 5 else 999
SR = 22050
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, _ = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / SR
s16 = 60 / BPM / 4
nb = min(B1, int(np.ceil((dur - OFF) / (s16 * 16))))
hop = 64
yh, yp = librosa.effects.hpss(y)
S = np.abs(librosa.stft(y, n_fft=512, hop_length=hop, center=False))
Sp = np.abs(librosa.stft(yp, n_fft=512, hop_length=hop, center=False))
f = librosa.fft_frequencies(sr=SR, n_fft=512)
st = (np.arange(S.shape[1]) * hop + 512) / SR
def fl(M, lo, hi):
    L = np.log1p(M * 20); m = (f >= lo) & (f < hi)
    d = np.diff(L[m], axis=1, prepend=L[m][:, :1]); d[d < 0] = 0
    return d.mean(0)
B = dict(K=fl(S, 30, 130), S=fl(Sp, 1500, 5000), H=fl(Sp, 7000, 11000), T=fl(S, 400, 3000))
def per_slot(v):
    return np.array([v[(st >= OFF + i * s16 - 0.01) & (st < OFF + i * s16 + 0.04)].max(initial=0) for i in range(nb * 16)])
P = {}
for k, v in B.items():
    v = per_slot(v); out = np.zeros_like(v)
    for b in range(nb):
        w = v[max(0, b - 4) * 16:min(nb, b + 4) * 16]
        lo, hi = np.percentile(w, 30), np.percentile(w, 98)
        out[b * 16:(b + 1) * 16] = np.clip((v[b * 16:(b + 1) * 16] - lo) / (hi - lo + 1e-9), 0, 1)
    P[k] = out
C = np.abs(librosa.cqt(yh, sr=SR, hop_length=256, fmin=librosa.note_to_hz('C1'), n_bins=84, bins_per_octave=12))
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=SR, hop_length=256)
Cd = librosa.amplitude_to_db(C, ref=np.max)
def pitch(t0, t1, lo, hi, floor=-42):
    m = (ct >= t0) & (ct < t1)
    if not m.any(): return '--'
    seg = Cd[lo:hi, m].mean(1)
    i = int(np.argmax(seg))
    if seg[i] < floor: return '--'
    return librosa.midi_to_note(24 + lo + i, unicode=False).ljust(3)
BASS = (librosa.note_to_midi('C1') - 24, librosa.note_to_midi('C3') - 24)
LEAD = (librosa.note_to_midi('C4') - 24, librosa.note_to_midi('C7') - 24)
def row(v, th=(0.35, 0.65)):
    return ''.join('X' if x > th[1] else 'x' if x > th[0] else '.' for x in v)
print(f'grid: bar0 {OFF}s, 16th {s16:.5f}s, bar {s16*16:.4f}s, {nb} bars')
for b in range(B0, nb):
    t0 = OFF + b * 16 * s16
    bass = ' '.join(pitch(t0 + k * 4 * s16, t0 + (k + 1) * 4 * s16, *BASS) for k in range(4))
    lead = ' '.join(pitch(t0 + k * 2 * s16 + 0.03, t0 + (k + 1) * 2 * s16, *LEAD) for k in range(8))
    sl = slice(b * 16, (b + 1) * 16)
    print(f'{b:2d} {t0:7.2f} K {row(P["K"][sl])} S {row(P["S"][sl])} T {row(P["T"][sl])} | bass {bass} | top {lead}')
