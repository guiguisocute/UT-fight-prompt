#!/usr/bin/env python3
"""Third pass: tuning, the real bass note (range down to A0), and bar-gridded
spectrogram / CQT images (work/spec_XX.png) to read the arrangement by eye.

    ../mtt-mv/.venv/Scripts/python tools/explore_spectro.py [music.mp3]
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa
from PIL import Image, ImageDraw

SRC = sys.argv[1] if len(sys.argv) > 1 else 'asset/music/power_of_neo_unfinished_wip.mp3'
OFF, BPM, SR = 0.028, 145.0, 22050
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, _ = librosa.load(wav, sr=SR, mono=True)
dur = len(y) / SR
s16 = 60 / BPM / 4
bar = 16 * s16
nb = int(np.ceil((dur - OFF) / bar))
print('tuning (fraction of a semitone):', round(float(librosa.estimate_tuning(y=y, sr=SR)), 3))

yh, yp = librosa.effects.hpss(y)
HOP = 256
C = np.abs(librosa.cqt(yh, sr=SR, hop_length=HOP, fmin=librosa.note_to_hz('A0'), n_bins=12 * 7 + 3, bins_per_octave=12))
Cd = librosa.amplitude_to_db(C, ref=np.max)
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=SR, hop_length=HOP)
A0 = int(librosa.note_to_midi('A0'))
def note(m):
    return librosa.midi_to_note(m, unicode=False)
def pitch(t0, t1, lo, hi, floor=-50):
    m = (ct >= t0) & (ct < t1)
    seg = Cd[lo - A0:hi - A0, m].mean(1)
    i = int(np.argmax(seg))
    return '-' if seg[i] < floor else note(lo + i)

print('\nbass per beat, range A0..E3 (bars 0-17, 64-82, 88-97):')
for b in list(range(0, 18)) + list(range(64, 82)) + list(range(88, 98)):
    t0 = OFF + b * bar
    bs = ' '.join(f'{pitch(t0 + k * 4 * s16, t0 + (k + 1) * 4 * s16, int(librosa.note_to_midi("A0")), int(librosa.note_to_midi("E3"))):4s}' for k in range(4))
    print(f'  {b:2d} {bs}')

# sub-bass fundamental strength per pitch class over sections
print('\nlowest-octave energy by note, A0..A2 (dB, section mean):')
for a, b in [(0, 8), (10, 18), (18, 34), (34, 42), (66, 82), (90, 98)]:
    m = (ct >= OFF + a * bar) & (ct < OFF + b * bar)
    seg = Cd[0:24, m].mean(1)
    top = np.argsort(seg)[::-1][:4]
    print(f'  bars {a:2d}-{b:2d}: ' + ', '.join(f'{note(A0 + i)} {seg[i]:.1f}' for i in top))

# images: log-frequency spectrogram (full mix) with bar / beat lines, 8 bars per image
os.makedirs('work', exist_ok=True)
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
Sd = librosa.amplitude_to_db(S, ref=np.max)
f = librosa.fft_frequencies(sr=SR, n_fft=2048)
st = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=HOP)
# map rows to log-frequency 30 Hz .. 11 kHz
H = 300
fl = np.geomspace(30, 11000, H)[::-1]
rows = np.searchsorted(f, fl).clip(0, len(f) - 1)
PX = 16 * 6  # pixels per bar (6 per 16th)
for g in range(0, nb, 8):
    b0, b1 = g, min(nb, g + 8)
    W = (b1 - b0) * PX
    img = np.zeros((H + 160, W, 3), np.uint8)
    for x in range(W):
        t = OFF + b0 * bar + x / PX * bar
        j = min(len(st) - 1, int(t / (HOP / SR)))
        col = Sd[rows, j]
        v = np.clip((col + 70) / 70, 0, 1)
        img[:H, x, 0] = (v ** 1.2 * 255).astype(np.uint8)
        img[:H, x, 1] = (v ** 2.0 * 255).astype(np.uint8)
        img[:H, x, 2] = (v ** 0.7 * 160).astype(np.uint8)
        # CQT strip (C2..C7) under the spectrogram, 2 px per semitone
        jc = min(len(ct) - 1, int(t / (HOP / SR)))
        cq = Cd[(36 - A0 - 0 + 0):(96 - A0), jc]  # C2..C7 rel. A0 index (MIDI 36..95)
        vv = np.clip((cq + 45) / 45, 0, 1)[::-1]
        for k, val in enumerate(vv):
            img[H + 10 + 2 * k:H + 12 + 2 * k, x, :] = int(val ** 1.5 * 255)
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    for k in range(b1 - b0 + 1):
        x = k * PX
        d.line([(x, 0), (x, H + 160)], fill=(0, 255, 0), width=1)
        if k < b1 - b0:
            d.text((x + 2, 2), str(b0 + k), fill=(0, 255, 0))
            for q in range(1, 4):
                xq = x + q * PX // 4
                d.line([(xq, H - 8), (xq, H)], fill=(0, 160, 0), width=1)
    # frequency guides
    for fr in (60, 120, 250, 500, 1000, 2000, 4000, 8000):
        yy = int(np.argmin(np.abs(fl - fr)))
        d.line([(0, yy), (6, yy)], fill=(255, 255, 0))
        d.text((8, yy - 5), str(fr), fill=(255, 255, 0))
    im = im.resize((W * 2, (H + 160) * 2), Image.NEAREST) if W < 500 else im
    p = f'work/spec_{b0:02d}.png'
    im.save(p)
    print('wrote', p)
