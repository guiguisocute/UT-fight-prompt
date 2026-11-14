#!/usr/bin/env python3
"""Analyse asset/music/power_of_neo_unfinished_wip.mp3 (Toby Fox's unfinished extended
"Power of NEO" mockup) and write src/analysis.js for the MV engine.

Same data layout as ../mtt-mv/src/analysis.js (window.MV_ANALYSIS = {...}), so
the mtt-mv engine (util.js T.at / T.acc / T.env ...) reads it unchanged.
Requires numpy, scipy, librosa and an ffmpeg binary on PATH.

    ../mtt-mv/.venv/Scripts/python tools/analyze_music.py [music.mp3] [src/analysis.js]

All times are MUSIC time (0 = first sample of the mp3). The film plays a silent
prologue before the music; the engine adds that offset (T.pre).
"""
import json, subprocess, sys, tempfile, os
import numpy as np
import librosa

SRC = sys.argv[1] if len(sys.argv) > 1 else 'asset/music/power_of_neo_unfinished_wip.mp3'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'src/analysis.js'
SR = 22050

with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, sr = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / sr

# ---------------------------------------------------------------- tempo grid
# The mockup is sequenced (MIDI-tight): a brute-force 16th grid on the onset
# envelope gives 145.00 BPM in every 20 s window, and the onset residuals drift
# only 2.7 ms over the whole song. Phase: the first attack of the file is at
# 0.0288 s (waveform), the non-centred short-window flux (frame END time minus
# half a hop) gives 0.0348 s and the backtracked onsets sit ~8 ms before that,
# so the grid origin is 0.029 s. (A centred STFT reports attacks 20-40 ms early,
# see ../mtt-mv; don't use it for the phase.)
hop = 64
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, n_fft=1024)
ft = librosa.frames_to_time(np.arange(len(oenv)), sr=sr, hop_length=hop)
best = None
for bpm in np.arange(140, 150, 0.01):
    per = 60 / bpm / 4
    for ph in np.arange(0, per, 0.004):
        s = np.interp(np.arange(ph, dur - 1, per), ft, oenv).mean()
        if best is None or s > best[0]:
            best = (s, bpm, ph)
bpm = round(best[1])  # 145.00
s16 = 60 / bpm / 4
offset = 0.029
bar_len = s16 * 16
# the file is cut 4 ms after the downbeat of bar 98: 98 full bars
nbars = int(np.floor((dur - offset) / bar_len + 0.01))
nslots = nbars * 16

# --------------------------------------------------------------- band fluxes
# short, non-centred frames: a frame's END time is right after the attack
yh, yp = librosa.effects.hpss(y)
def flux_of(sig, lo, hi, n_fft=512):
    S = np.abs(librosa.stft(sig, n_fft=n_fft, hop_length=hop, center=False))
    f = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    L = np.log1p(S[(f >= lo) & (f < hi)] * 20)
    d = np.diff(L, axis=1, prepend=L[:, :1]); d[d < 0] = 0
    return d.mean(0)
ftt = (np.arange(1 + (len(y) - 512) // hop) * hop + 512) / sr

def per_slot(v):
    return np.array([v[(ftt >= offset + i * s16 - 0.01) & (ftt < offset + i * s16 + 0.04)].max(initial=0)
                     for i in range(nslots)])

def local_norm(v, win_bars=8):
    out = np.zeros_like(v)
    for b in range(nbars):
        w = v[max(0, b - win_bars // 2) * 16:min(nbars, b + win_bars // 2) * 16]
        lo, hi = np.percentile(w, 30), np.percentile(w, 98)
        out[b * 16:(b + 1) * 16] = np.clip((v[b * 16:(b + 1) * 16] - lo) / (hi - lo + 1e-9), 0, 1)
    return out

full = local_norm(per_slot(flux_of(y, 30, 11000)))
low = local_norm(per_slot(flux_of(y, 30, 150)))
mid = local_norm(per_slot(flux_of(y, 250, 2000)))
high = local_norm(per_slot(flux_of(y, 2000, 8000)))
kick = local_norm(per_slot(flux_of(y, 30, 130)))      # mostly the pulsing D#1 sub-bass in 10-89
snare = local_norm(per_slot(flux_of(yp, 1500, 5000)))  # the 3-3-3-3-2-2 accents
hat = local_norm(per_slot(flux_of(yp, 7000, 11000)))   # open hat on every off-beat 8th (10-89)
tone = local_norm(per_slot(flux_of(yh, 300, 3000)))    # lead / guitar / pluck attacks
# absolute loudness per 16th (not normalised): the coda is ~8 dB down, the break near silent
rms_s = librosa.feature.rms(y=y, frame_length=1024, hop_length=256)[0]
rt_s = librosa.frames_to_time(np.arange(len(rms_s)), sr=sr, hop_length=256)
loud = np.array([rms_s[(rt_s >= offset + i * s16) & (rt_s < offset + (i + 1) * s16)].mean() for i in range(nslots)])
loud = np.clip(20 * np.log10(loud / np.percentile(loud, 99) + 1e-9) / 40 + 1, 0, 1)  # 0 = -40 dB, 1 = loudest

# --------------------------------------------------------------- pitch
# CQT on the harmonic part: bass note per beat, lead note per 16th (MIDI, -1 = none).
# Range-edge trap: a note just below a range leaks into its lowest bin and wins the
# argmax (an E1-based bass range reads the D#1 pedal as E1; a G4-based lead range
# reads theme C's D#4 / F#4 as G4). So the ranges reach below the real notes and an
# argmax on the lowest bin counts as unknown.
C = librosa.amplitude_to_db(np.abs(librosa.cqt(yh, sr=sr, hop_length=256, fmin=librosa.note_to_hz('A0'),
                                                n_bins=87, bins_per_octave=12)), ref=np.max)
A0 = int(librosa.note_to_midi('A0'))
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=sr, hop_length=256)
def pitch(t0, t1, lo, hi, floor=-50):
    m = (ct >= t0) & (ct < t1)
    if not m.any():
        return -1
    seg = C[lo - A0:hi - A0, m].mean(1)
    i = int(np.argmax(seg))
    return -1 if seg[i] < floor or i == 0 else lo + i
A0n, E3, C4, C7 = (int(librosa.note_to_midi(n)) for n in ('A0', 'E3', 'C4', 'C7'))
bass = [pitch(offset + k * 4 * s16, offset + (k + 1) * 4 * s16, A0n, E3) for k in range(nbars * 4)]
lead = [pitch(offset + i * s16, offset + (i + 1) * s16 + 0.03, C4, C7, floor=-45) for i in range(nslots)]

# ---------------------------------------------------------------- envelopes
ehop = 512
rms = librosa.feature.rms(y=y, hop_length=ehop)[0]
et = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=ehop)
E = np.abs(librosa.stft(y, n_fft=2048, hop_length=ehop)) ** 2
ef = librosa.fft_frequencies(sr=sr, n_fft=2048)
def band_env(lo, hi):
    return E[(ef >= lo) & (ef < hi)].sum(0)
FPS = 60
tt = np.arange(0, dur, 1 / FPS)
def env(v, db=False):
    v = np.interp(tt, et, v)
    if db:
        v = 10 * np.log10(v + 1e-9)
        v = (v - np.percentile(v, 2)) / (np.percentile(v, 99.5) - np.percentile(v, 2))
    else:
        v = v / np.percentile(v, 99.5)
    return np.clip(v, 0, 1)
env_rms = env(rms)
env_low = env(band_env(20, 150), db=True)
env_high = env(band_env(2500, 11000), db=True)  # shows the noise risers (9, 33, 65, 81)

# ---------------------------------------------------------------- sections
# From the bar-level novelty curve, band energies, bar-gridded spectrograms /
# CQT rolls (work/spec_*.png, work/roll_*.png) and a time-resolved bar
# fingerprint (A2 = A, B2 = B, C2 = C at corr 0.97-0.98). See README.
bar_rms = [float(rms[(et >= offset + b * bar_len) & (et < offset + (b + 1) * bar_len)].mean()) for b in range(nbars)]
SECTIONS = [
    ('intro',   0,  8, 'the in-game loop: C#2 bass (C# C# C# C / A-D#-B), main melody B C# F# G# E, 3-3-3-3-4 accents; 4 + 4'),
    ('break',   8, 10, 'bar 8: last hit decays to -41 dB at 14.1 s (near silence); from 8.6 a white-noise riser, snare flam 9.14-15'),
    ('themeA', 10, 18, 'drop onto a pulsing D#1 pedal (39 Hz), D# phrygian, snare 3-3-3-3-2-2, open hat every off-beat 8th; 4 + 4'),
    ('themeB', 18, 34, 'darker (presence -5 dB), lyrical E-major line over the D# pedal; 8-bar phrases 18 / 26; 33 noise riser'),
    ('themeC', 34, 42, 'melody leaps two octaves between B5-C#6 and D#4-F#4; 34-37 repeated as 38-41'),
    ('themeA2', 42, 50, 'theme A again (= 10-17, corr 0.97)'),
    ('themeB2', 50, 66, 'theme B again (= 18-33, corr 0.98); 65 noise riser'),
    ('guitar', 66, 82, 'new: guitar lead with bends and slides; D# pedal, bass pushes up on beats 3-4 (G-G# even bars, F-F# odd bars), brighter; 16-bar solo, 81 riser'),
    ('themeC2', 82, 90, 'theme C again (= 34-41, corr 0.97); 89 drum fill'),
    ('coda',   90, 98, 'drums, sub and hats out (-8 dB): plucked line over A-B-C#-(D#), VI-VII-i in C# minor, strict 3-3-3-3-2-2; 4 + 4; cut at the bar-98 downbeat'),
]
mx = max(bar_rms)
sections = [dict(name=n, bar0=a, bar1=b, note=d, energy=round(float(np.mean(bar_rms[a:b]) / mx), 3))
            for n, a, b, d in SECTIONS]

q = lambda a, k=2: [round(float(x), k) for x in a]
data = dict(
    bpm=bpm, offset=offset, sixteenth=round(s16, 6), barLength=round(bar_len, 6),
    duration=round(dur, 3), bars=nbars,
    barRms=q(np.array(bar_rms) / mx, 3), sections=sections,
    # the song's rhythmic signature: accents on these 16ths of every bar
    pattern=[0, 3, 6, 9, 12, 14],
    slots=dict(full=q(full), low=q(low), mid=q(mid), high=q(high), kick=q(kick), snare=q(snare), hat=q(hat),
               tone=q(tone), loud=q(loud)),
    bass=bass, lead=lead,
    envFps=FPS, env=dict(rms=q(env_rms, 3), low=q(env_low, 3), high=q(env_high, 3)),
)
os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
with open(OUT, 'w') as f:
    f.write('// Generated by tools/analyze_music.py - do not edit by hand.\n')
    f.write('window.MV_ANALYSIS = ')
    json.dump(data, f, separators=(',', ':'))
    f.write(';\n')
print(f'bpm={bpm} (fit {best[1]:.2f}) offset={offset}s bars={nbars} duration={dur:.2f}s -> {OUT}')
for s in sections:
    print(f"  {s['name']:8s} bars {s['bar0']:2d}-{s['bar1']:2d}  t={offset + s['bar0'] * bar_len:7.2f}s  energy {s['energy']:.2f}  {s['note']}")
