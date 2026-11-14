#!/usr/bin/env python3
"""Draw CQT piano-roll images on the beat grid so the arrangement can be read by
eye: one overview of the whole track plus one image per N bars.

    .venv/Scripts/python tools/plot_music.py asset/music/music2.mp3 114.8466 0.013 8 work/plot2
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SRC, BPM, OFF, PER, OUT = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
BEATS = int(sys.argv[6]) if len(sys.argv) > 6 else 4
os.makedirs(OUT, exist_ok=True)
SR = 22050
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, sr = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / sr
beat = 60 / BPM
bar = beat * BEATS
nb = int(np.ceil((dur - OFF) / bar))
yh, yp = librosa.effects.hpss(y)
hop = 128
C = librosa.amplitude_to_db(np.abs(librosa.cqt(yh, sr=sr, hop_length=hop, fmin=librosa.note_to_hz('C1'), n_bins=7 * 12 * 2, bins_per_octave=24)), ref=np.max)
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=sr, hop_length=hop)
S = np.abs(librosa.stft(yp, n_fft=512, hop_length=64, center=False))
f = librosa.fft_frequencies(sr=sr, n_fft=512)
st = (np.arange(S.shape[1]) * 64 + 512) / sr
Lp = np.log1p(S * 20)
def flux(lo, hi):
    m = (f >= lo) & (f < hi)
    d = np.diff(Lp[m], axis=1, prepend=Lp[m][:, :1]); d[d < 0] = 0
    v = d.mean(0)
    return v / np.percentile(v, 99.5)
kick, snare, hat = flux(30, 150), flux(1500, 5000), flux(6000, 11000)
rms = librosa.feature.rms(y=y, hop_length=512)[0]
rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)

# overview
fig, ax = plt.subplots(2, 1, figsize=(30, 8), gridspec_kw=dict(height_ratios=[4, 1]), sharex=True)
M = librosa.amplitude_to_db(librosa.feature.melspectrogram(y=y, sr=sr, hop_length=512, n_mels=96), ref=np.max)
ax[0].imshow(M, origin='lower', aspect='auto', extent=[0, dur, 0, 96], cmap='magma', vmin=-70, vmax=0)
ax[1].plot(rt, rms / rms.max(), lw=0.6)
for b in range(nb + 1):
    t = OFF + b * bar
    for a in ax:
        a.axvline(t, color='c', lw=0.8 if b % 4 else 1.6, alpha=0.7)
    ax[0].text(t + 0.05, 90, str(b), color='w', fontsize=8)
ax[0].set_title(f'{os.path.basename(SRC)}  {BPM} BPM  bar0={OFF}s  bar={bar:.4f}s')
plt.tight_layout(); plt.savefig(os.path.join(OUT, 'overview.png'), dpi=70); plt.close()

NOTES = 'C C# D D# E F F# G G# A A# B'.split()
for b0 in range(0, nb, PER):
    b1 = min(nb, b0 + PER)
    t0, t1 = OFF + b0 * bar, min(dur, OFF + b1 * bar)
    m = (ct >= t0) & (ct < t1)
    fig, ax = plt.subplots(2, 1, figsize=(26, 13), gridspec_kw=dict(height_ratios=[6, 1]), sharex=True)
    lo, hi = 2 * 12 * 1, 2 * 12 * 6  # C2..C7 in half-semitone bins
    ax[0].imshow(C[lo:hi, m], origin='lower', aspect='auto', extent=[t0, t1, 0, (hi - lo) / 2], cmap='inferno', vmin=-60, vmax=0)
    for o in range(5):
        for n in (0, 2, 4, 5, 7, 9, 11):
            ax[0].axhline(o * 12 + n, color='w' if n == 0 else 'gray', lw=0.6 if n == 0 else 0.15, alpha=0.6)
    ax[0].set_yticks([o * 12 + n for o in range(5) for n in (0, 2, 4, 5, 7, 9, 11)])
    ax[0].set_yticklabels([f'{NOTES[n]}{o + 2}' for o in range(5) for n in (0, 2, 4, 5, 7, 9, 11)], fontsize=7)
    ms = (st >= t0) & (st < t1)
    ax[1].plot(st[ms], kick[ms] + 2, lw=0.6, label='kick')
    ax[1].plot(st[ms], snare[ms] + 1, lw=0.6, label='snare')
    ax[1].plot(st[ms], hat[ms], lw=0.6, label='hat')
    ax[1].set_ylim(0, 3.5)
    for k in range(int((t1 - t0) / (beat / 4)) + 2):
        t = t0 + k * beat / 4
        if t > t1: break
        w = 1.8 if k % (4 * BEATS) == 0 else (0.7 if k % 4 == 0 else 0.15)
        for a in ax:
            a.axvline(t, color='c', lw=w, alpha=0.8)
        if k % (4 * BEATS) == 0:
            ax[0].text(t + 0.02, 59, f'bar {b0 + k // (4 * BEATS)}', color='c', fontsize=11)
    ax[0].set_title(f'bars {b0}-{b1 - 1}  t={t0:.2f}-{t1:.2f}s')
    plt.tight_layout(); plt.savefig(os.path.join(OUT, f'bars_{b0:02d}.png'), dpi=60); plt.close()
print('ok', nb, 'bars')
