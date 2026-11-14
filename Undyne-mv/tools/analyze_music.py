#!/usr/bin/env python3
"""Analyse 'asset/music/Toby Fox - Battle Against A True Hero.mp3' together with the FL Studio
deconstruction of it and write src/analysis.js for the MV engine.

Same data layout as ../mtt-neo-mv/src/analysis.js (window.MV_ANALYSIS = {...}),
so the engine helpers (T.at / T.acc / T.env ...) read it unchanged. New here is
`score`: the exact notes of every voice and every drum hit, from the FLP.
Requires numpy, scipy, librosa, pyflp (pyflp 2.2.1 needs Python <= 3.10) and an
ffmpeg binary on PATH.

    .venv/Scripts/python tools/analyze_music.py [music.mp3] [project.flp] [src/analysis.js]

All times are MUSIC time (0 = first sample of the mp3). The film may play a
silent prologue before the music; the engine adds that offset (T.pre).
"""
import json, os, subprocess, sys, tempfile
import numpy as np
import librosa
from flp_notes import flatten

SRC = sys.argv[1] if len(sys.argv) > 1 else 'asset/music/Toby Fox - Battle Against A True Hero.mp3'
FLP = sys.argv[2] if len(sys.argv) > 2 else 'asset/music/Deconstruction-Battle Against a True HeroFL20.flp'
OUT = sys.argv[3] if len(sys.argv) > 3 else 'src/analysis.js'
SR = 22050

with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, sr = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / sr

# ---------------------------------------------------------------- tempo grid
# Brute-force constant 16th grid on a non-centred short-window flux (frame END
# time minus half a hop): 150.00 BPM overall and in every 20 s window. The flux
# puts the phase at 12 ms, but it reads attacks ~6 ms late (../mtt-neo-mv): the
# waveform's first attack (the piano, from digital silence) is at 6.0 ms and the
# bar-12 tutti at +5.4 ms, so the grid origin is 0.006 s.
hop = 64
Sx = np.abs(librosa.stft(y, n_fft=512, hop_length=hop, center=False))
Lx = np.log1p(Sx * 20)
flux = np.diff(Lx, axis=1, prepend=Lx[:, :1]); flux[flux < 0] = 0
flux = flux.mean(0)
ftt = (np.arange(len(flux)) * hop + 512) / sr - hop / 2 / sr
best = None
for bpm in np.arange(148, 152, 0.01):
    per = 60 / bpm / 4
    for ph in np.arange(0, per, 0.002):
        s = np.interp(np.arange(ph, dur - 1, per), ftt, flux).mean()
        if best is None or s > best[0]:
            best = (s, bpm, ph)
bpm = round(best[1])  # 150
s16 = 60 / bpm / 4    # 0.1 s
offset = 0.006
bar_len = s16 * 16    # 1.6 s
nbars = int(round((dur - offset) / bar_len))  # 98: 96 bars of music + the decay / loop gap
nslots = nbars * 16

# ---------------------------------------------------------------- the score (FLP)
# The FLP grid IS the audio grid: FL tick 0 = mp3 sample 0, 300 FL-BPM = 150 BPM
# with no stretch, and its drum hits sit on the same flux phase (12 ms) as the
# grid fit, drifting < 3 ms over the song. So music time = offset + tick / 480,
# and a 16th of the music is 48 ticks.
F = flatten(FLP)
TICK16 = 48
# sounding = written + shift. Soundfont channels carry a -200 cent channel
# pitch; the NES VST channels show 0 but sound a tritone away (the plugin's own
# tuning). Pitch class from correlating each channel's roll with the audio
# chroma (tools/explore_transpose.py); octave from CQT energy at +-6 (the NES
# basses sound an octave above the NES leads' shift).
SOUNDFONT = {1, 2, 4, 5, 6, 7, 11, 13, 14, 19, 20, 21, 22}
SHIFT = {**{c: -2 for c in SOUNDFONT}, 8: 6, 9: 6, 15: 6, 3: -6, 10: -6, 12: -6}
VOICES = {1: 'pianoIntro', 2: 'piano', 3: 'nesLead', 4: 'trumpet', 5: 'trumpetPiano', 6: 'saw',
          7: 'bassPiano', 8: 'squareBass', 9: 'triangleBass', 10: 'nesArp', 11: 'flute', 12: 'nesSquare',
          13: 'vins', 14: 'choir2', 19: 'steelGuitar', 20: 'bell', 21: 'choir', 22: 'violin'}
# GM drum map of the 'SGM-Power' kit channels 16-18
DRUMS = {36: 'kick', 44: 'hat', 46: 'openHat', 38: 'snare', 40: 'snare', 39: 'clap', 57: 'crash', 83: 'jingle'}
r3 = lambda v: round(v, 3)
voices = {v: [] for v in VOICES.values()}
drums = {d: [] for d in dict.fromkeys(DRUMS.values())}
for n in F['notes']:
    s, ln = n['tick'] / TICK16, n['len'] / TICK16
    if n['ch'] in VOICES:
        voices[VOICES[n['ch']]].append([r3(s), r3(ln), n['key'] + SHIFT[n['ch']], n['vel']])
    else:
        drums[DRUMS[n['key']]].append([r3(s), n['vel']])
# audio clips: 'Crash 01b' is a plain crash; 'Crash 01a' is the same kit's crash
# with the sampler's reverse switch on: a 4.05 s swell ending exactly on the
# downbeats of bars 28, 60 and 96, plus a shorter one over bars 10-11 (there,
# with no drums, the audio's high band visibly rises: 0.35 -> 0.67)
for c in F['clips']:
    name = 'crash' if c['ch'] == 24 else 'swell'
    drums.setdefault(name, []).append([r3(c['tick'] / TICK16), 100] + ([r3(c['len'] / TICK16)] if name == 'swell' else []))
for d in drums.values():
    d.sort()
notes_all = [(n['tick'] / TICK16, n['len'] / TICK16, n['key'] + SHIFT.get(n['ch'], 0), n['ch']) for n in F['notes']]

# melody per 16th (MIDI sounding at the slot, -1 = none), from the voice that
# carries the tune in each part; leadOn = a melody note starts in the slot
# (the latest-struck note wins; the intro piano's notes ring over each other;
# on a chord, the top note)
LEAD = [(0, 12, {1}, 0), (12, 28, {2}, 72), (28, 60, {22}, 0), (60, 72, {2}, 60), (72, 96, {4}, 0)]
lead, lead_on = [-1] * nslots, [0] * nslots
lead_key = [(-1, -1)] * nslots  # (onset, pitch) of the note shown in each slot
for b0, b1, chs, floor in LEAD:
    for s, ln, k, ch in notes_all:
        if ch in chs and k >= floor and b0 * 16 <= s < b1 * 16:
            i0 = int(round(s))
            lead_on[i0] = 1
            for i in range(i0, min(int(np.ceil(s + ln - 0.01)), b1 * 16)):
                lead_key[i] = max(lead_key[i], (s, k))
lead = [k for _, k in lead_key]
# the 3-3-3-3-2-2 ostinato: the high piano of bars 0-59
motif = [0] * nslots
for s, ln, k, ch in notes_all:
    if ch in (1, 2) and k >= 72 and s < 60 * 16:
        motif[int(round(s))] = 1
# bass per beat: lowest bass-voice note sounding at the beat (piano pedals included)
bass = []
for q in range(nbars * 4):
    t = q * 4
    ks = [k for s, ln, k, ch in notes_all
          if (ch in (7, 8, 9, 15) or (ch == 2 and k < 48)) and s <= t + 0.5 and s + ln > t]
    bass.append(min(ks) if ks else -1)

# chord per beat: duration-weighted pitch classes of every pitched voice,
# matched against triad / power / sus templates (bass note counts double)
PC = 'C Db D Eb E F Gb G Ab A Bb B'.split()
TPL = {'': (0, 4, 7), 'm': (0, 3, 7), '5': (0, 7), 'sus4': (0, 5, 7), 'sus2': (0, 2, 7), 'dim': (0, 3, 6)}
chords = []
for q in range(nbars * 4):
    t0, t1 = q * 4, q * 4 + 4
    h = np.zeros(12)
    for s, ln, k, ch in notes_all:
        if ch in VOICES:
            o = min(s + ln, t1) - max(s, t0)
            if o > 0:
                h[k % 12] += o * (2 if (ch in (7, 8, 9, 15) or k < 48) else 1)
    if h.sum() == 0:
        chords.append('')
        continue
    h /= h.sum()
    sc = {}
    for r in range(12):
        for nm, iv in TPL.items():
            m = np.zeros(12); m[[(r + i) % 12 for i in iv]] = 1
            sc[PC[r] + nm] = h @ m - 0.3 * h @ (1 - m) - 0.02 * len(iv)  # small penalty: prefer simpler on ties
    chords.append(max(sc, key=sc.get))

# ---------------------------------------------------------------- band fluxes (audio)
# short, non-centred frames: a frame's END time is right after the attack
yh, yp = librosa.effects.hpss(y)
def flux_of(sig, lo, hi, n_fft=512):
    S = np.abs(librosa.stft(sig, n_fft=n_fft, hop_length=hop, center=False))
    f = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    L = np.log1p(S[(f >= lo) & (f < hi)] * 20)
    d = np.diff(L, axis=1, prepend=L[:, :1]); d[d < 0] = 0
    return d.mean(0)
ftt2 = (np.arange(1 + (len(y) - 512) // hop) * hop + 512) / sr

def per_slot(v):
    return np.array([v[(ftt2 >= offset + i * s16 - 0.01) & (ftt2 < offset + i * s16 + 0.04)].max(initial=0)
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
kick = local_norm(per_slot(flux_of(yp, 30, 130)))
snare = local_norm(per_slot(flux_of(yp, 1500, 5000)))
hat = local_norm(per_slot(flux_of(yp, 7000, 11000)))
tone = local_norm(per_slot(flux_of(yh, 300, 3000)))
# absolute loudness per 16th (not normalised; 0 = -40 dB, 1 = loudest)
rms_s = librosa.feature.rms(y=y, frame_length=1024, hop_length=256)[0]
rt_s = librosa.frames_to_time(np.arange(len(rms_s)), sr=sr, hop_length=256)
loud = np.array([rms_s[(rt_s >= offset + i * s16) & (rt_s < offset + (i + 1) * s16)].mean() if offset + i * s16 < dur else 0
                 for i in range(nslots)])
loud = np.clip(20 * np.log10(loud / np.percentile(loud, 99) + 1e-9) / 40 + 1, 0, 1)

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
env_high = env(band_env(2500, 11000), db=True)  # shows the reversed-crash swells

# ---------------------------------------------------------------- sections
# From the FLP playlist (pattern blocks), checked against the audio: bar energy,
# drum hits, crash placement. Pitches below are SOUNDING (F minor), not as written
# in the FLP (G minor for the soundfonts).
bar_rms = [float(rms[(et >= offset + b * bar_len) & (et < offset + (b + 1) * bar_len)].mean()) for b in range(nbars)]
SECTIONS = [
    ('intro',      'intro',     0,  4, 'solo piano: the motif Eb F Bb C Ab F on the 16ths 0 3 6 9 12 14 (3-3-3-3-2-2); no drums'),
    ('rise',       'intro',     4, 12, '+ choir pad, tubular bell, low F pedal; the motif twice (4-7, 8-11); bar 11 the piano bass climbs Db Db Db Eb Eb Eb Bb Bb Bb; a reversed crash rises over 10-11'),
    ('A1',         'themeA',   12, 20, 'drums in (kick 0 3 7 9 12, snare + clap on every off-beat 8th, hats); 16th octave bass F-C / Db-Ab; the motif in piano octaves + NES lead + bells; crash on 12'),
    ('A2',         'themeA',   20, 28, 'A again, bells out, violin + choir counter-line; crash on 20; reversed crash into 28'),
    ('B1',         'themeB',   28, 44, 'new long-note melody (violin + NES lead: C F Ab F ...) over the motif ostinato; heavier kick (0 4 7 9 11 12), electric snare; triangle bass; crash on 28'),
    ('B2',         'themeB',   44, 60, '= B1 (same patterns); crash on 44; bar 59 drum fill; reversed crash into 60'),
    ('interlude1', 'interlude', 60, 66, 'drums and bass out: piano alone with the theme-C melody (F C Bb C Ab C G ...) over arpeggiated steel-guitar chords, jingle accents; one crash on the 60 downbeat'),
    ('interlude2', 'interlude', 66, 72, '= interlude1 + choir'),
    ('C1',         'themeC',   72, 84, 'tutti: trumpets in parallel 4ths play the interlude melody in straight 8ths; NES arp + staccato flute 16ths, choir stabs on the off-beat 8ths, saw, triangle bass, full drums; accompaniment cycles every 6 bars (crash on 72, 78)'),
    ('C2',         'themeC',   84, 96, '= C1 + NES lead descant; crash on 84, 90; reversed crash into 96; the last chord (F5) ends on the bar-96 downbeat'),
    ('tail',       'tail',     96, 98, 'decay to silence at 154.8 s; in game the track loops back to bar 0 (the recording: song starts 1:33.28, loops at 4:06.9)'),
]
mx = max(bar_rms)
sections = [dict(name=n, part=p, bar0=a, bar1=b, note=d, energy=round(float(np.mean(bar_rms[a:b]) / mx), 3))
            for n, p, a, b, d in SECTIONS]

q = lambda a, k=2: [round(float(x), k) for x in a]
data = dict(
    bpm=bpm, offset=offset, sixteenth=round(s16, 6), barLength=round(bar_len, 6),
    duration=round(dur, 3), bars=nbars, musicEnd=96,
    barRms=q(np.array(bar_rms) / mx, 3), sections=sections,
    # the song's rhythmic signature: accents on these 16ths of every bar
    pattern=[0, 3, 6, 9, 12, 14],
    slots=dict(full=q(full), low=q(low), mid=q(mid), high=q(high), kick=q(kick), snare=q(snare), hat=q(hat),
               tone=q(tone), loud=q(loud)),
    bass=bass, lead=lead, leadOn=lead_on, motif=motif, chords=chords,
    envFps=FPS, env=dict(rms=q(env_rms, 3), low=q(env_low, 3), high=q(env_high, 3)),
    # exact notes: voices[name] = [[16th, length in 16ths, MIDI (sounding), velocity], ...]
    #              drums[name]  = [[16th, velocity(, swell length)], ...]   (16th 0 = bar 0 = `offset`)
    score=dict(voices=voices, drums=drums),
)
os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
with open(OUT, 'w') as f:
    f.write('// Generated by tools/analyze_music.py - do not edit by hand.\n')
    f.write('window.MV_ANALYSIS = ')
    json.dump(data, f, separators=(',', ':'))
    f.write(';\n')

# ---------------------------------------------------------------- report
dl = sorted((np.interp(np.array([d[0] for d in drums['kick'] + drums['snare']]) * s16 + lag, ftt, flux).mean(), lag)
            for lag in np.arange(-0.05, 0.05, 0.001))[-1][1]
print(f'bpm={bpm} (fit {best[1]:.2f}, flux phase {best[2] * 1000:.0f} ms; FLP drums best at flux lag {dl * 1000:.0f} ms) '
      f'offset={offset}s bars={nbars} duration={dur:.2f}s -> {OUT} ({os.path.getsize(OUT) // 1024} KB)')
for s in sections:
    print(f"  {s['name']:10s} bars {s['bar0']:2d}-{s['bar1']:2d}  t={offset + s['bar0'] * bar_len:7.2f}s  energy {s['energy']:.2f}")
print('voices:', {k: len(v) for k, v in voices.items()})
print('drums :', {k: len(v) for k, v in drums.items()})
for name, v in (('swell', drums['swell']),):
    for s, _, ln in v:
        a, b = offset + s * s16, offset + (s + ln) * s16
        m = (tt >= a) & (tt < b)
        h = env_high[m]
        print(f'  swell {a:6.2f}-{b:6.2f}s: high env first half {h[:len(h) // 2].mean():.2f} -> second half {h[len(h) // 2:].mean():.2f}')
print('chords per bar (beat 1 / 2 / 3 / 4):')
for b in range(nbars):
    print(f"  {b:3d} {' '.join(f'{c:6s}' for c in chords[b * 4:b * 4 + 4])}  bass {' '.join(librosa.midi_to_note(k, unicode=False) if k >= 0 else '-' for k in bass[b * 4:b * 4 + 4])}"
          f"  rms {bar_rms[b] / mx:.2f}")
