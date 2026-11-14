#!/usr/bin/env python3
"""Second pass on the 145 BPM grid: per-section average drum profile per 16th
(downbeat check), key estimate per section, the onsets of the intro / break /
drop with their grid slots, and a per-bar note dump (bass per beat, lead per
8th). Used to write the section map (not needed at runtime).

    ../mtt-mv/.venv/Scripts/python tools/explore_notes.py [music.mp3] [offset]
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa

SRC = sys.argv[1] if len(sys.argv) > 1 else 'asset/music/power_of_neo_unfinished_wip.mp3'
OFF = float(sys.argv[2]) if len(sys.argv) > 2 else 0.028
BPM = 145.0
SR = 22050
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, _ = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / SR
s16 = 60 / BPM / 4
nb = int(np.ceil((dur - OFF) / (s16 * 16)))
hop = 64
yh, yp = librosa.effects.hpss(y)

def mkflux(sig):
    S = np.abs(librosa.stft(sig, n_fft=512, hop_length=hop, center=False))
    f = librosa.fft_frequencies(sr=SR, n_fft=512)
    L = np.log1p(S * 20)
    def flux(lo, hi):
        m = (f >= lo) & (f < hi)
        d = np.diff(L[m], axis=1, prepend=L[m][:, :1]); d[d < 0] = 0
        return d.mean(0)
    return flux
st = (np.arange(1 + (len(y) - 512) // hop) * hop + 512) / SR
fy, fp, fh = mkflux(y), mkflux(yp), mkflux(yh)
B = dict(K=fy(30, 130), S=fp(1500, 5000), H=fp(7000, 11000), T=fh(300, 3000), F=fy(30, 11000))
def per_slot(v):
    return np.array([v[(st >= OFF + i * s16 - 0.01) & (st < OFF + i * s16 + 0.04)].max(initial=0) for i in range(nb * 16)])
P = {k: per_slot(v) for k, v in B.items()}
R = {k: v.copy() for k, v in P.items()}
for k in P:  # normalise per 8-bar window
    v = P[k]; out = np.zeros_like(v)
    for b in range(nb):
        w = v[max(0, b - 4) * 16:min(nb, b + 4) * 16]
        lo, hi = np.percentile(w, 30), np.percentile(w, 98)
        out[b * 16:(b + 1) * 16] = np.clip((v[b * 16:(b + 1) * 16] - lo) / (hi - lo + 1e-9), 0, 1)
    P[k] = out

SECT = [(0, 8), (8, 10), (10, 18), (18, 34), (34, 42), (42, 50), (50, 66), (66, 82), (82, 90), (90, 98)]
print(f'grid: bar0 {OFF}s, 16th {s16:.5f}s, beat {4*s16:.4f}s, bar {s16*16:.4f}s, {nb} bars, song {dur:.3f}s')
print('\naverage onset strength per 16th slot (normalised per section):')
for a, b in SECT:
    print(f' bars {a}-{b}')
    for k in ('K', 'S', 'H', 'T'):
        v = R[k][a * 16:b * 16].reshape(-1, 16).mean(0)
        v = v / (v.max() + 1e-9)
        print(f'   {k} ' + ' '.join(f'{x:.2f}' for x in v))

# key per section (Krumhansl-Kessler)
maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTES = 'C C# D D# E F F# G G# A A# B'.split()
chroma = librosa.feature.chroma_cqt(y=yh, sr=SR, hop_length=512)
ctm = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=SR, hop_length=512)
print('\nkey estimate per section:')
for a, b in SECT:
    m = (ctm >= OFF + a * 16 * s16) & (ctm < OFF + b * 16 * s16)
    ch = chroma[:, m].mean(1)
    sc = []
    for i in range(12):
        sc.append((np.corrcoef(np.roll(maj, i), ch)[0, 1], NOTES[i] + ' major'))
        sc.append((np.corrcoef(np.roll(mnr, i), ch)[0, 1], NOTES[i] + ' minor'))
    sc.sort(reverse=True)
    prof = ' '.join(f'{NOTES[i]}:{ch[i]/ch.max():.2f}' for i in range(12))
    print(f'  {a:2d}-{b:2d}: {sc[0][1]} ({sc[0][0]:.2f}), {sc[1][1]} ({sc[1][0]:.2f}), {sc[2][1]} ({sc[2][0]:.2f})   {prof}')

print('\nstrong onsets 0-18 s and 146-162 s (full-band flux peaks) with grid slot:')
F = B['F']
pk = librosa.util.peak_pick(F, pre_max=6, post_max=6, pre_avg=20, post_avg=20, delta=0.05, wait=6)
for i in pk:
    t = st[i]
    if (t < 18) or (t > 146):
        sl = (t - OFF) / s16
        print(f'  {t:7.3f}s  bar {int(sl // 16):3d} slot {sl % 16:5.2f}  full {F[i]:.2f}  kick {B["K"][i]:.2f} snare {B["S"][i]:.2f} hat {B["H"][i]:.2f} tone {B["T"][i]:.2f}')

# pitch: CQT on the harmonic part
C = np.abs(librosa.cqt(yh, sr=SR, hop_length=256, fmin=librosa.note_to_hz('C1'), n_bins=84, bins_per_octave=12))
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=SR, hop_length=256)
Cd = librosa.amplitude_to_db(C, ref=np.max)
def pitch(t0, t1, lo, hi, floor=-45):
    m = (ct >= t0) & (ct < t1)
    if not m.any(): return '-'
    seg = Cd[lo:hi, m].mean(1)
    i = int(np.argmax(seg))
    if seg[i] < floor: return '-'
    return librosa.midi_to_note(24 + lo + i, unicode=False)
BASS = (librosa.note_to_midi('E1') - 24, librosa.note_to_midi('E3') - 24)
LEAD = (librosa.note_to_midi('G4') - 24, librosa.note_to_midi('C7') - 24)

def row(v, th=(0.35, 0.65)):
    return ''.join('X' if x > th[1] else 'x' if x > th[0] else '.' for x in v)
print('\nper bar: K S H T per 16th | bass per beat | lead per 8th')
for b in range(nb):
    t0 = OFF + b * 16 * s16
    bass = ' '.join(pitch(t0 + k * 4 * s16, t0 + (k + 1) * 4 * s16, *BASS) for k in range(4))
    lead = ' '.join(pitch(t0 + k * 2 * s16, t0 + (k + 1) * 2 * s16, *LEAD) for k in range(8))
    sl = slice(b * 16, (b + 1) * 16)
    print(f'{b:2d} {t0:7.2f} K {row(P["K"][sl])} S {row(P["S"][sl])} H {row(P["H"][sl])} T {row(P["T"][sl])} | {bass:15s} | {lead}')
