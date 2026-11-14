"""spider dance.mp4 -> src/analysis.js (window.MV_ANALYSIS), the same fields as the earlier MVs'
(bpm, offset, sixteenth, barLength, duration, sections, pattern, slots.*, env.*). The grid is the one
verified in MUSIC2.md: 115 BPM, bar 0 at 0.0845 s, 51 bars.

usage: python tools/make_analysis.py   (decodes work/music/spider.wav with ffmpeg if it is missing)
"""
import json
import os
import subprocess

import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WAV = os.path.join(ROOT, 'work', 'music', 'spider.wav')
if not os.path.exists(WAV):
    os.makedirs(os.path.dirname(WAV), exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(ROOT, 'asset/music/spider dance.mp4'), '-vn', '-ac', '2',
                    '-ar', '44100', '-c:a', 'pcm_s16le', WAV], check=True)

BPM, OFFSET, BARS = 115.0, 0.08453, 51
S16 = 60 / BPM / 4
y2, sr = sf.read(WAV)
y = y2.mean(1)
dur = len(y) / sr
nslot = BARS * 16


def bp(x, lo=None, hi=None):
    if lo and hi:
        sos = butter(4, [lo, hi], btype='band', fs=sr, output='sos')
    elif lo:
        sos = butter(4, lo, btype='high', fs=sr, output='sos')
    else:
        sos = butter(4, hi, btype='low', fs=sr, output='sos')
    return sosfiltfilt(sos, x)


HOP = 44
FR = HOP / sr


def attack(x):
    n = len(x) // HOP
    e = 10 * np.log10((x[: n * HOP] ** 2).reshape(n, HOP).mean(1) + 1e-12)
    c = np.cumsum(np.r_[0, e])
    i = np.arange(n)
    a = np.maximum(0, i - 12)
    prev = np.where(i > 0, (c[i] - c[a]) / np.maximum(1, i - a), e[0])
    return np.maximum(0, e - prev)


bands = {'low': bp(y, 30, 150), 'mid': bp(y, 150, 2500), 'high': bp(y, 5000), 'full': bp(y, 30)}
slots = {}
for k, x in bands.items():
    d = attack(x)
    v = np.zeros(nslot)
    for s in range(nslot):
        t = OFFSET + s * S16
        a, b = int((t - 0.010) / FR), int((t + 0.025) / FR)
        v[s] = d[max(0, a): min(len(d), b)].max() if b > a else 0
    slots[k] = np.clip(v / (np.percentile(v, 98) + 1e-9), 0, 1)
# the earlier MVs' names for the drum-ish bands
slots['kick'], slots['snare'], slots['hat'] = slots['low'], slots['mid'], slots['high']
# loudness per 16th: 0 = -40 dB, 1 = the 99th percentile
db = np.array([10 * np.log10(np.mean(y[int((OFFSET + s * S16) * sr): int((OFFSET + (s + 1) * S16) * sr)] ** 2) + 1e-12) for s in range(nslot)])
slots['loud'] = np.clip(1 + (db - np.percentile(db, 99)) / 40, 0, 1)

ENV_FPS = 60
env = {}
for k, x in (('rms', y), ('low', bp(y, 25, 200)), ('high', bp(y, 4000))):
    hop = sr // ENV_FPS
    n = len(x) // hop
    r = np.sqrt((x[: n * hop] ** 2).reshape(n, hop).mean(1))
    env[k] = np.clip(r / (np.percentile(r, 99) + 1e-9), 0, 1)

bar_rms = [float(np.sqrt(np.mean(y[int((OFFSET + b * 16 * S16) * sr): int((OFFSET + (b + 1) * 16 * S16) * sr)] ** 2))) for b in range(BARS)]
mx = max(bar_rms)

SECTIONS = [
    ('A1a', 'themeA', 0, 4, 'full band from the first beat; 16th bass F-Eb-Db-C / F-G-Ab-Eb / Db; gallop percussion (3 on, 1 off); bar 3 stop-time'),
    ('A1b', 'themeA', 4, 8, 'again; bars 5-6 the bass climbs F-G-Ab-Bb over C / Db; bar 7 stop-time'),
    ('A2a', 'themeA', 8, 12, '= bars 0-3; bar 11 stop-time'),
    ('A2b', 'themeA', 12, 15, '= bars 4-6'),
    ('break', 'break', 15, 16, 'everything stops on beat 1; a lone stereo melody starting C-Db'),
    ('B1', 'themeB', 16, 24, 'wide sustained pads, dotted bouncing bass, off-beat cymbals; Fm-Bbm | Db-C x3, bar 22 Gb (Neapolitan), 23 walks up to F'),
    ('B2', 'themeB', 24, 32, 'B again; bar 25 the loudest, 30 = 22, 31 cymbals out'),
    ('C1a', 'interlude', 32, 36, 'last B hit on 32 beat 1, then no drums, no bass: high plucked arpeggios (music box)'),
    ('C1b', 'interlude', 36, 40, '+ a sustained middle line crawling by semitones F-E-Eb-D-Db-C-Db-D-Eb-E-F-Ab-G-Ab'),
    ('C2', 'themeC', 40, 47, 'drums and bass back; the bass takes the crawl; march stabs on every beat, building'),
    ('turn', 'themeC', 47, 48, 'dominant C: stabs and a snare fill on 16ths 0-8, held breath 9-15'),
    ("A'", 'themeA', 48, 50, '= bars 0-1; bar 49 fades out'),
    ('tail', 'tail', 50, 51, 'the decay, near silence'),
]
sections = []
for name, part, b0, b1, note in SECTIONS:
    sections.append({'name': name, 'part': part, 'bar0': b0, 'bar1': b1, 'note': note,
                     'energy': round(float(np.mean(bar_rms[b0:b1]) / mx), 3)})

A = {
    'bpm': BPM, 'offset': OFFSET, 'sixteenth': S16, 'barLength': 16 * S16, 'duration': round(dur, 4),
    'bars': BARS, 'musicEnd': 50, 'barRms': [round(v / mx, 3) for v in bar_rms], 'sections': sections,
    # the A section's gallop: three 16ths on, the fourth off, every beat
    'pattern': [0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14],
    'slots': {k: [round(float(x), 3) for x in v] for k, v in slots.items()},
    'envFps': ENV_FPS, 'env': {k: [round(float(x), 3) for x in v] for k, v in env.items()},
}
out = os.path.join(ROOT, 'src', 'analysis.js')
with open(out, 'w', encoding='utf-8') as f:
    f.write('// Generated by tools/make_analysis.py - do not edit by hand.\n')
    f.write('window.MV_ANALYSIS = ' + json.dumps(A, separators=(',', ':'), ensure_ascii=False) + ';\n')
print('wrote', out, os.path.getsize(out), 'bytes;', nslot, 'slots,', len(env['rms']), 'env frames')
