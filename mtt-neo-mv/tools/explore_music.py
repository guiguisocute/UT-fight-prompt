#!/usr/bin/env python3
"""First-pass exploration of power_of_neo_unfinished_wip.mp3: tempo grid,
downbeat, per-bar energy / bands / chroma / drum patterns, novelty curve and
bar self-similarity. Prints the table used to write the section map in
tools/analyze_music.py (not needed at runtime).

    ../mtt-mv/.venv/Scripts/python tools/explore_music.py [music.mp3]
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

def score(bpm, ph):
    per = 60 / bpm / 4
    return np.interp(np.arange(ph, dur - 1, per), ft, oenv).mean()
best = None
for bpm in np.arange(143, 147, 0.01):
    per = 60 / bpm / 4
    for ph in np.arange(0, per, 0.002):
        s = score(bpm, ph)
        if best is None or s > best[0]:
            best = (s, bpm, ph)
sc, bpm_fit, ph_fit = best
print(f'grid fit bpm={bpm_fit:.3f} phase={ph_fit:.4f} score={sc:.3f}')
bpm = round(bpm_fit)
s16 = 60 / bpm / 4
on = librosa.onset.onset_detect(onset_envelope=oenv, sr=sr, hop_length=hop, backtrack=True, units='time')
ang = np.mod(on, s16) / s16 * 2 * np.pi
phase = (np.angle(np.mean(np.exp(1j * ang))) % (2 * np.pi)) / (2 * np.pi) * s16
R = np.abs(np.mean(np.exp(1j * ang)))
print(f'rounded bpm={bpm}  s16={s16:.5f}  backtracked-onset phase={phase:.4f} (resultant {R:.2f}, {len(on)} onsets)')
print('first onsets:', np.round(on[:12], 3))

beat = s16 * 4
bar = beat * 4

# short non-centred band fluxes (frame END time ~ attack)
yh, yp = librosa.effects.hpss(y)
def flux_of(sig, lo, hi, n_fft=512):
    S = np.abs(librosa.stft(sig, n_fft=n_fft, hop_length=hop, center=False))
    f = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    L = np.log1p(S[(f >= lo) & (f < hi)] * 20)
    d = np.diff(L, axis=1, prepend=L[:, :1]); d[d < 0] = 0
    return d.mean(0)
ftt = (np.arange(1 + (len(y) - 512) // hop) * hop + 512) / sr
kick = flux_of(y, 30, 130); snare = flux_of(yp, 1500, 5000); hat = flux_of(yp, 7000, 11000)
tone = flux_of(yh, 300, 3000)

def slots(v, off, n):
    return np.array([v[(ftt >= off + i * s16 - 0.01) & (ftt < off + i * s16 + 0.04)].max(initial=0) for i in range(n)])

# downbeat: which beat phase carries the strongest kick / full onset
cands = [phase + k * beat for k in range(4)]
for name, f in (('kick', kick), ('snare', snare)):
    ds = []
    for c in cands:
        nb = int((dur - c) // bar)
        ds.append(np.mean([f[(ftt >= c + i * bar - 0.01) & (ftt < c + i * bar + 0.04)].max(initial=0) for i in range(nb)]))
    print(f'{name} strength on beat phase 0..3:', np.round(ds, 3))

off = phase
nbars = int(np.ceil((dur - off) / bar))
print(f'grid origin {off:.3f}  beat={beat:.4f} bar={bar:.4f} nbars={nbars}')

rms = librosa.feature.rms(y=y, hop_length=512)[0]
rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
chroma = librosa.feature.chroma_cqt(y=yh, sr=sr, hop_length=512)
mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=512)
S2 = np.abs(librosa.stft(y, n_fft=2048, hop_length=512)) ** 2
f2 = librosa.fft_frequencies(sr=sr, n_fft=2048)
def band_e(lo, hi):
    return S2[(f2 >= lo) & (f2 < hi)].sum(0)
bands = {'sub': band_e(20, 80), 'bass': band_e(80, 250), 'mid': band_e(250, 2000), 'pres': band_e(2000, 6000), 'air': band_e(6000, 11000)}
NOTES = 'C C# D D# E F F# G G# A A# B'.split()

N = nbars * 16
ks, ss, hs, ts = slots(kick, off, N), slots(snare, off, N), slots(hat, off, N), slots(tone, off, N)
def pat(v, ref):
    v = v / (ref + 1e-9)
    return ''.join('X' if x > 0.6 else 'x' if x > 0.33 else '.' for x in v)
kref, sref, href, tref = (np.percentile(a, 97) for a in (ks, ss, hs, ts))

rows, feats = [], []
for b in range(nbars):
    t0, t1 = off + b * bar, off + (b + 1) * bar
    m = (rt >= t0) & (rt < t1)
    r = rms[m].mean() if m.any() else 0
    ch = chroma[:, m].mean(1) if m.any() else np.zeros(12)
    bnd = {k: 10 * np.log10(v[m].mean() + 1e-9) for k, v in bands.items()}
    top = ' '.join(NOTES[i] for i in np.argsort(ch)[::-1][:3])
    sl = slice(b * 16, (b + 1) * 16)
    rows.append((b, t0, r, bnd, top, pat(ks[sl], kref), pat(ss[sl], sref), pat(hs[sl], href), pat(ts[sl], tref)))
    feats.append(np.concatenate([mfcc[:, m].mean(1) if m.any() else np.zeros(13), ch * 10]))
feats = np.array(feats)
fn = (feats - feats.mean(0)) / (feats.std(0) + 1e-9)
nov = [0.0]
for b in range(1, nbars):
    a = fn[max(0, b - 2):b].mean(0); c = fn[b:b + 2].mean(0)
    nov.append(float(np.linalg.norm(a - c)))
rmax = max(r[2] for r in rows)
print('\nbar   time   rms   sub  bass   mid  pres   air   nov  chroma    kick             snare            hat              tone')
for (b, t0, r, bnd, top, kp, sp, hp, tp), nv in zip(rows, nov):
    print(f'{b:3d} {t0:7.2f} {r/rmax:5.2f} {bnd["sub"]:5.1f}{bnd["bass"]:6.1f}{bnd["mid"]:6.1f}{bnd["pres"]:6.1f}{bnd["air"]:6.1f} {nv:5.2f}  {top:9s} {kp} {sp} {hp} {tp}')

print('\nrepeats (bar -> most similar earlier bar, corr):')
C = np.corrcoef(fn)
out = []
for b in range(2, nbars):
    j = int(np.argmax(C[b, :b - 1]))
    out.append(f'{b}->{j}({C[b, j]:.2f})')
for i in range(0, len(out), 10):
    print('  ' + '  '.join(out[i:i + 10]))
