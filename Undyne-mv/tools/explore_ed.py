#!/usr/bin/env python3
"""Look at "But the Earth Refused to Die" before choreographing on it: tempo, beats, onsets, the
loudness and the harmony over time - printed, and drawn into work/ed_look.png.

    .venv/Scripts/python tools/explore_ed.py
"""
import numpy as np
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

SRC = 'asset/music/Toby Fox - But The Earth Refused To Die.mp3'
SR = 44100
HOP = 256

y, sr = librosa.load(SRC, sr=SR, mono=True)
dur = len(y) / sr
print(f'duration {dur:.3f} s')

# the first sound out of digital silence (the waveform, not the flux)
a = np.abs(y)
first = np.argmax(a > 10 ** (-50 / 20))
print(f'first sample above -50 dBFS at {first / sr * 1000:.1f} ms')

# loudness (RMS, dBFS) every 0.5 s
rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=HOP)[0]
rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=HOP)
db = 20 * np.log10(np.maximum(rms, 1e-6))
print('RMS dB per 1 s:', ' '.join(f'{db[(rt >= s) & (rt < s + 1)].mean():.0f}' for s in range(int(dur))))

# onsets (non-centred short window, as the earlier MVs: it reports ~6 ms late)
env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP, center=False)
et = librosa.frames_to_time(np.arange(len(env)), sr=sr, hop_length=HOP) + 2048 / sr / 2
ons = librosa.onset.onset_detect(onset_envelope=env, sr=sr, hop_length=HOP, units='frames', backtrack=False, delta=0.08)
print(f'{len(ons)} onsets')

# tempo: brute-force a constant grid on the onset envelope (period, phase)
best = None
for bpm in np.arange(100, 140.01, 0.05):
    per = 60 / bpm
    for ph in np.arange(0, per, 0.005):
        ts = np.arange(ph, 28, per)
        idx = np.searchsorted(et, ts)
        idx = idx[idx < len(env)]
        sc = env[idx].mean()
        if best is None or sc > best[0]:
            best = (sc, bpm, ph)
print(f'grid fit: {best[1]:.2f} BPM, phase {best[2]:.3f} s (score {best[0]:.2f})')
tempo, beats = librosa.beat.beat_track(onset_envelope=env, sr=sr, hop_length=HOP, start_bpm=best[1], units='time')
print('librosa beat_track', np.round(tempo, 2), 'beats:', ' '.join(f'{b:.2f}' for b in beats))

# harmony per beat of the fitted grid: chroma (CQT), the strongest three pitch classes
C = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=HOP)
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=sr, hop_length=HOP)
NAMES = 'C C# D D# E F F# G G# A A# B'.split()
per = 60 / best[1]
grid = np.arange(best[2], dur, per)
print('per beat (grid): t, loudness, top pitch classes')
prev = None
for i, g in enumerate(grid):
    m = (ct >= g) & (ct < g + per)
    if not m.any():
        continue
    v = C[:, m].mean(1)
    top = [NAMES[k] for k in np.argsort(v)[::-1][:3]]
    l = db[(rt >= g) & (rt < g + per)].mean()
    # change of harmony: cosine distance from the previous beat
    ch = 0 if prev is None else 1 - np.dot(v, prev) / (np.linalg.norm(v) * np.linalg.norm(prev) + 1e-9)
    prev = v
    print(f'  beat {i:3d}  {g:6.2f} s  {l:5.1f} dB  {" ".join(top):10s}  change {ch:.2f}')

# novelty: where the music turns (self-similarity of chroma + MFCC, checkerboard kernel)
M = librosa.feature.mfcc(y=y, sr=sr, hop_length=HOP, n_mfcc=13)
F = np.vstack([librosa.util.normalize(C, axis=0), librosa.util.normalize(M, axis=0) * 0.5])
# beat-synchronous
bf = librosa.time_to_frames(grid, sr=sr, hop_length=HOP)
Fs = librosa.util.sync(F, bf, aggregate=np.mean)
S = np.dot(librosa.util.normalize(Fs, axis=0).T, librosa.util.normalize(Fs, axis=0))
K = 4
ker = np.kron(np.array([[1, -1], [-1, 1]]), np.ones((K, K)))
nov = np.zeros(len(S))
for i in range(K, len(S) - K):
    nov[i] = np.sum(S[i - K:i + K, i - K:i + K] * ker)
order = np.argsort(nov)[::-1][:8]
print('novelty peaks (beat, time):', ', '.join(f'{i} @ {grid[i] if i < len(grid) else -1:.2f}s ({nov[i]:.1f})' for i in sorted(order)))

# picture
fig, ax = plt.subplots(4, 1, figsize=(22, 13), sharex=True)
ax[0].plot(rt, db, lw=0.6); ax[0].set_ylabel('RMS dB'); ax[0].set_ylim(-60, 0)
ax[1].plot(et, env, lw=0.5)
for o in ons: ax[1].axvline(et[o], color='r', lw=0.4, alpha=0.5)
ax[1].set_ylabel('onsets')
librosa.display.specshow(C, sr=sr, hop_length=HOP, x_axis='time', y_axis='chroma', ax=ax[2]) if hasattr(librosa, 'display') else ax[2].imshow(C, aspect='auto', origin='lower', extent=[0, dur, 0, 12])
ax[2].set_ylabel('chroma')
Sx = np.abs(librosa.stft(y, n_fft=4096, hop_length=HOP))
ax[3].imshow(20 * np.log10(Sx[:700] + 1e-6), aspect='auto', origin='lower', extent=[0, dur, 0, 700 * sr / 4096], vmin=-40, vmax=40)
ax[3].set_ylabel('Hz')
for a_ in ax:
    for g in grid: a_.axvline(g, color='w' if a_ is ax[3] else 'k', lw=0.3, alpha=0.4)
    a_.set_xticks(np.arange(0, dur, 1))
plt.tight_layout()
plt.savefig('work/ed_look.png', dpi=60)
print('-> work/ed_look.png')
