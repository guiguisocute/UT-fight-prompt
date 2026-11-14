#!/usr/bin/env python3
"""Piano-roll (CQT of the harmonic part) per 8 bars on the 145 BPM grid, to read
melodies and bass lines by eye: work/roll_XX.png. Each column is one 16th
(4 px), each row one semitone (5 px), C4..C7 on top, C1..C4 below; bar lines
green, beats dark green, note names on the left.

    ../mtt-mv/.venv/Scripts/python tools/plot_music.py [music.mp3] [bar0 bar1 ...]
"""
import subprocess, sys, tempfile, os
import numpy as np
import librosa
from PIL import Image, ImageDraw

SRC = 'asset/music/power_of_neo_unfinished_wip.mp3'
OFF, BPM, SR = 0.028, 145.0, 22050
starts = [int(a) for a in sys.argv[1:]] or list(range(0, 98, 8))
with tempfile.TemporaryDirectory() as td:
    wav = os.path.join(td, 'm.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', SRC, '-ac', '1', '-ar', str(SR), wav], check=True)
    y, _ = librosa.load(wav, sr=SR, mono=True)
s16 = 60 / BPM / 4
bar = 16 * s16
yh, _ = librosa.effects.hpss(y)
HOP = 128
lo_midi = int(librosa.note_to_midi('C1'))
C = np.abs(librosa.cqt(yh, sr=SR, hop_length=HOP, fmin=librosa.note_to_hz('C1'), n_bins=72, bins_per_octave=12))
Cd = librosa.amplitude_to_db(C, ref=np.max)
ct = librosa.frames_to_time(np.arange(C.shape[1]), sr=SR, hop_length=HOP)
NOTES = 'C C# D D# E F F# G G# A A# B'.split()
PX, PY, LBL = 4, 5, 34
os.makedirs('work', exist_ok=True)
for b0 in starts:
    nbar = 8
    W = nbar * 16 * PX
    rows = 72
    img = np.zeros((rows * PY, W, 3), np.uint8)
    for x in range(W):
        t0 = OFF + b0 * bar + x / PX * s16
        m = (ct >= t0) & (ct < t0 + s16 / PX)
        if not m.any():
            continue
        col = Cd[:, m].mean(1)
        # separate normalisation for the bass (C1..C4) and the upper voices (C4..C7)
        for lo, hi, floor in ((0, 36, 40.0), (36, 72, 38.0)):
            seg = col[lo:hi]
            v = np.clip((seg - (seg.max() - floor)) / floor, 0, 1) ** 2.2
            for k in range(lo, hi):
                yy = (rows - 1 - k) * PY
                c = int(v[k - lo] * 255)
                img[yy:yy + PY - 1, x] = (c, c, int(c * 0.6) if lo else c)
    im = Image.new('RGB', (W + LBL, rows * PY + 14), (0, 0, 0))
    im.paste(Image.fromarray(img), (LBL, 14))
    d = ImageDraw.Draw(im)
    for k in range(rows):
        n = NOTES[(lo_midi + k) % 12]
        yy = 14 + (rows - 1 - k) * PY
        if n in ('C', 'D#', 'G#', 'E', 'B'):
            col = (255, 80, 80) if n == 'D#' else (120, 120, 255) if n == 'C' else (90, 90, 90)
            d.line([(LBL, yy + PY // 2), (LBL + W, yy + PY // 2)], fill=(28, 28, 28))
            d.text((0, yy - 4), f'{n}{(lo_midi + k) // 12 - 1}', fill=col)
    d.line([(LBL, 14 + 36 * PY), (LBL + W, 14 + 36 * PY)], fill=(80, 0, 80))
    for k in range(nbar * 4 + 1):
        x = LBL + k * 4 * PX
        d.line([(x, 14), (x, 14 + rows * PY)], fill=(0, 200, 0) if k % 4 == 0 else (0, 70, 0))
        if k % 4 == 0 and k < nbar * 4:
            d.text((x + 2, 1), str(b0 + k // 4), fill=(0, 255, 0))
    p = f'work/roll_{b0:02d}.png'
    im.save(p)
    print('wrote', p, im.size)
