#!/usr/bin/env python3
"""Phase / downbeat probe on a fixed BPM: 16th phase from attack-aligned
(non-centred) flux and from backtracked onsets; downbeat from harmonic change
(chroma novelty per beat position) and band patterns averaged over bar ranges.

    .venv/Scripts/python tools/explore_phase.py asset/music/music2.mp3 114.8466
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa

SRC = sys.argv[1]
BPM = float(sys.argv[2])
SR = 22050
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, sr = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / sr
s16 = 60 / BPM / 4
hop = 64

# 1) attack-aligned flux: short non-centred frames, time = frame END
S = np.abs(librosa.stft(y, n_fft=512, hop_length=hop, center=False))
f = librosa.fft_frequencies(sr=SR, n_fft=512)
st = (np.arange(S.shape[1]) * hop + 512) / SR
L = np.log1p(S * 20)
def flux(lo, hi):
    m = (f >= lo) & (f < hi)
    d = np.diff(L[m], axis=1, prepend=L[m][:, :1]); d[d < 0] = 0
    return d.mean(0)
full = flux(30, 11000)
for name, v in (('full', full), ('low', flux(30, 200)), ('mid', flux(300, 3000)), ('high', flux(4000, 11000))):
    best = max((np.interp(np.arange(ph, dur - 1, s16), st, v).mean(), ph) for ph in np.arange(0, s16, 0.001))
    print(f'attack-flux {name:4s} phase {best[1]:.4f}')

# 2) backtracked onsets circular mean
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, n_fft=1024)
on = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=hop, backtrack=True, units='time')
ang = np.mod(on, s16) / s16 * 2 * np.pi
ph_bt = (np.angle(np.mean(np.exp(1j * ang))) % (2 * np.pi)) / (2 * np.pi) * s16
print(f'backtracked onsets circular phase {ph_bt:.4f} (R={abs(np.mean(np.exp(1j*ang))):.2f}, n={len(on)})')
print('first onsets:', np.round(on[:12], 3))

PH = float(sys.argv[3]) if len(sys.argv) > 3 else ph_bt
beat = 4 * s16
nbeats = int((dur - PH) / beat)
# 3) downbeat from harmonic change: chroma (CQT, harmonic part) per beat, change into each beat
yh = librosa.effects.harmonic(y)
ch = librosa.feature.chroma_cqt(y=yh, sr=SR, hop_length=256)
ct = librosa.frames_to_time(np.arange(ch.shape[1]), sr=SR, hop_length=256)
B = np.array([ch[:, (ct >= PH + i * beat) & (ct < PH + (i + 1) * beat)].mean(1) for i in range(nbeats)])
B = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-9)
chg = np.r_[0, 1 - (B[1:] * B[:-1]).sum(1)]
for a, b in ((0, 16), (16, 24), (24, 40), (40, 52), (52, 60), (60, 74), (0, 74)):
    sel = chg[a * 4:b * 4]
    sel = sel[:len(sel) // 4 * 4].reshape(-1, 4).mean(0)
    print(f'bars {a:2d}-{b:2d}: harmonic change into beat position 0..3: ' + ' '.join(f'{x:.3f}' for x in sel))

# 4) low-band (kick/bass) and full attack per 16th slot averaged over bar ranges
def slots(v):
    n = int((dur - PH) / s16)
    return np.array([v[(st >= PH + i * s16 - 0.01) & (st < PH + i * s16 + 0.04)].max(initial=0) for i in range(n)])
P = dict(low=slots(flux(30, 150)), mid=slots(flux(300, 3000)), high=slots(flux(4000, 11000)))
for a, b in ((0, 8), (16, 24), (24, 40), (44, 52), (53, 60), (60, 72)):
    print(f'bars {a}-{b}')
    for k, v in P.items():
        w = v[a * 16:b * 16]; w = w[:len(w) // 16 * 16].reshape(-1, 16).mean(0); w = w / w.max()
        print(f'   {k:4s} ' + ' '.join(f'{x:.2f}' for x in w))
