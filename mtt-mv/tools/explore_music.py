#!/usr/bin/env python3
"""First-pass exploration of music.mp3: tempo grid, per-bar energy / bands /
chroma and a bar-level novelty curve. Prints a table used to write the section
map in tools/analyze_music.py (not needed at runtime).

    .venv/Scripts/python tools/explore_music.py [music.mp3]
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa

SRC = sys.argv[1] if len(sys.argv) > 1 else 'asset/music/music.mp3'
SR = 22050
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, sr = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / sr
print(f'duration {dur:.3f}s')

hop = 128
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
ft = librosa.frames_to_time(np.arange(len(oenv)), sr=sr, hop_length=hop)
tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop)
print('librosa tempo', tempo)

# coarse then fine brute force of a constant 16th grid
def score(bpm, ph, t1=None):
    per = 60 / bpm / 4
    return np.interp(np.arange(ph, (t1 or dur) - 1, per), ft, oenv).mean()
best = None
for bpm in np.arange(120, 180, 0.05):
    per = 60 / bpm / 4
    for ph in np.arange(0, per, 0.004):
        s = score(bpm, ph)
        if best is None or s > best[0]:
            best = (s, bpm, ph)
_, b0, _ = best
for bpm in np.arange(b0 - 0.1, b0 + 0.1, 0.002):
    per = 60 / bpm / 4
    for ph in np.arange(0, per, 0.001):
        s = score(bpm, ph)
        if s > best[0]:
            best = (s, bpm, ph)
sc, bpm, phase = best
print(f'grid bpm={bpm:.3f} phase={phase:.4f} score={sc:.3f}')
# check tempo stability: best bpm per 20 s window
for w0 in range(0, int(dur) - 20, 20):
    bb = None
    for b in np.arange(bpm - 1.5, bpm + 1.5, 0.02):
        per = 60 / b / 4
        for ph in np.arange(0, per, 0.004):
            m = (ft >= w0) & (ft < w0 + 20)
            s = np.interp(np.arange(w0 + ph, w0 + 20, per), ft, oenv).mean()
            if bb is None or s > bb[0]:
                bb = (s, b, ph)
    print(f'  window {w0:3d}-{w0+20:3d}s: bpm {bb[1]:.2f}')

s16 = 60 / bpm / 4
beat = s16 * 4
bar = beat * 4

S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
st = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop)
L = np.log1p(S * 10)
def flux(lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    d = np.diff(L[m], axis=1, prepend=L[m][:, :1]); d[d < 0] = 0
    return d.mean(0)
kick = flux(30, 120); snare = flux(1500, 5000); hat = flux(7000, 11000)

# downbeat: which of the 4 beat phases carries the strongest kick on beat 1 over bars
cands = [phase + k * beat for k in range(4)]
def kick_at(t):
    m = (st >= t - 0.02) & (st < t + 0.05)
    return kick[m].max(initial=0)
ds = []
for c in cands:
    nb = int((dur - c) // bar)
    ds.append(np.mean([kick_at(c + i * bar) for i in range(nb)]))
print('downbeat kick score per beat phase', np.round(ds, 3))

# per-16th onset strength per band
def per_slot(f, off, n):
    return np.array([f[(st >= off + i * s16 - 0.015) & (st < off + i * s16 + 0.045)].max(initial=0) for i in range(n)])

off = phase
while off - bar > -0.01:
    off -= bar
nbars = int(np.ceil((dur - off) / bar))
print(f'first grid point {off:.3f}  s16={s16:.5f} beat={beat:.4f} bar={bar:.4f} nbars={nbars}')

rms = librosa.feature.rms(y=y, hop_length=512)[0]
rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=512)
E = S ** 2
def band_e(lo, hi):
    m = (freqs >= lo) & (freqs < hi)
    return E[m].sum(0)
bands = {'sub': band_e(20, 80), 'bass': band_e(80, 250), 'mid': band_e(250, 2000), 'pres': band_e(2000, 6000), 'air': band_e(6000, 11000)}
NOTES = 'C C# D D# E F F# G G# A A# B'.split()

rows = []
feats = []
kslots = per_slot(kick, off, nbars * 16)
sslots = per_slot(snare, off, nbars * 16)
hslots = per_slot(hat, off, nbars * 16)
def pat(v):
    v = v / (v.max() + 1e-9)
    return ''.join('X' if x > 0.6 else 'x' if x > 0.35 else '.' for x in v)
for b in range(nbars):
    t0, t1 = off + b * bar, off + (b + 1) * bar
    m = (rt >= t0) & (rt < t1)
    ms = (st >= t0) & (st < t1)
    r = rms[m].mean() if m.any() else 0
    ch = chroma[:, m].mean(1) if m.any() else np.zeros(12)
    bnd = {k: 10 * np.log10(v[ms].mean() + 1e-9) for k, v in bands.items()}
    top = ''.join(NOTES[i] + ' ' for i in np.argsort(ch)[::-1][:3])
    ks, ss, hs = kslots[b*16:(b+1)*16], sslots[b*16:(b+1)*16], hslots[b*16:(b+1)*16]
    rows.append((b, t0, r, bnd, top, pat(ks), pat(ss), pat(hs)))
    feats.append(np.concatenate([mfcc[:, m].mean(1) if m.any() else np.zeros(13), ch * 10]))
feats = np.array(feats)
fn = (feats - feats.mean(0)) / (feats.std(0) + 1e-9)
# novelty: distance between mean of previous 2 bars and next 2 bars
nov = [0.0]
for b in range(1, nbars):
    a = fn[max(0, b - 2):b].mean(0); c = fn[b:b + 2].mean(0)
    nov.append(float(np.linalg.norm(a - c)))
rmax = max(r[2] for r in rows)
print('\nbar  time    rms  sub  bass  mid  pres  air  nov  chroma      kick             snare            hat')
for (b, t0, r, bnd, top, kp, sp, hp), nv in zip(rows, nov):
    print(f'{b:3d} {t0:7.2f} {r/rmax:5.2f} {bnd["sub"]:5.1f}{bnd["bass"]:6.1f}{bnd["mid"]:6.1f}{bnd["pres"]:6.1f}{bnd["air"]:6.1f} {nv:5.2f} {top:11s} {kp} {sp} {hp}')

# self-similarity: which earlier bar is each bar most similar to
print('\nrepeats (bar -> most similar earlier bar, corr):')
C = np.corrcoef(fn)
for b in range(nbars):
    if b < 2: continue
    j = int(np.argmax(C[b, :b - 1]))
    print(f'{b}->{j}({C[b,j]:.2f})', end='  ')
print()
