#!/usr/bin/env python3
"""Per-bar note / rhythm dump on the corrected grid (148 BPM, bar 0 at 0.010 s):
bass pitch per beat, lead pitch per 8th (harmonic part), drum hits per 16th.
Used to write the section map and choreography notes (not needed at runtime).
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa

SR = 22050
OFF, BPM = 0.010, 148.0
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'asset/music/music.mp3', '-ac', '1', '-ar', str(SR), wav], check=True)
    y, _ = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / SR
s16 = 60 / BPM / 4
nb = int(np.ceil((dur - OFF) / (s16 * 16)))
hop = 64
yh, yp = librosa.effects.hpss(y)

# drums on short windows, not centred, so a frame's time is its attack
S = np.abs(librosa.stft(yp, n_fft=512, hop_length=hop, center=False))
f = librosa.fft_frequencies(sr=SR, n_fft=512)
st = (np.arange(S.shape[1]) * hop + 512) / SR  # frame END time: onset is inside it
L = np.log1p(S * 20)
def flux(lo, hi):
    m = (f >= lo) & (f < hi)
    d = np.diff(L[m], axis=1, prepend=L[m][:, :1]); d[d < 0] = 0
    return d.mean(0)
Sf = np.abs(librosa.stft(y, n_fft=512, hop_length=hop, center=False))
Lf = np.log1p(Sf * 20)
def fluxf(lo, hi):
    m = (f >= lo) & (f < hi)
    d = np.diff(Lf[m], axis=1, prepend=Lf[m][:, :1]); d[d < 0] = 0
    return d.mean(0)
B = dict(K=fluxf(30, 130), S=flux(1500, 5000), H=flux(7000, 11000), T=fluxf(400, 3000))
def per_slot(v):
    return np.array([v[(st >= OFF + i * s16 - 0.01) & (st < OFF + i * s16 + 0.04)].max(initial=0) for i in range(nb * 16)])
P = {k: per_slot(v) for k, v in B.items()}
for k in P:  # normalise per 8-bar window
    v = P[k]; out = np.zeros_like(v)
    for b in range(nb):
        w = v[max(0, b - 4) * 16:min(nb, b + 4) * 16]
        lo, hi = np.percentile(w, 30), np.percentile(w, 98)
        out[b * 16:(b + 1) * 16] = np.clip((v[b * 16:(b + 1) * 16] - lo) / (hi - lo + 1e-9), 0, 1)
    P[k] = out

# pitch: CQT on the harmonic part
C = np.abs(librosa.cqt(yh, sr=SR, hop_length=256, fmin=librosa.note_to_hz('C1'), n_bins=84, bins_per_octave=12))
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=SR, hop_length=256)
Cd = librosa.amplitude_to_db(C, ref=np.max)
def pitch(t0, t1, lo, hi):
    m = (ct >= t0) & (ct < t1)
    if not m.any(): return '-'
    seg = Cd[lo:hi, m].mean(1)
    i = int(np.argmax(seg))
    if seg[i] < -45: return '-'
    return librosa.midi_to_note(24 + lo + i, unicode=False)
BASS = (librosa.note_to_midi('E1') - 24, librosa.note_to_midi('E3') - 24)
LEAD = (librosa.note_to_midi('G4') - 24, librosa.note_to_midi('C7') - 24)

def row(v, th=(0.35, 0.65)):
    return ''.join('X' if x > th[1] else 'x' if x > th[0] else '.' for x in v)
print(f'grid: bar0 {OFF}s, 16th {s16:.5f}s, bar {s16*16:.4f}s, {nb} bars, song {dur:.3f}s')
for b in range(nb):
    t0 = OFF + b * 16 * s16
    bass = ' '.join(pitch(t0 + k * 4 * s16, t0 + (k + 1) * 4 * s16, *BASS) for k in range(4))
    lead = ' '.join(pitch(t0 + k * 2 * s16, t0 + (k + 1) * 2 * s16, *LEAD) for k in range(8))
    sl = slice(b * 16, (b + 1) * 16)
    print(f'{b:2d} {t0:7.2f} K {row(P["K"][sl])} S {row(P["S"][sl])} H {row(P["H"][sl])} T {row(P["T"][sl])} | bass {bass:18s} | lead {lead}')
