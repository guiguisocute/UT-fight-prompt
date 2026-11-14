#!/usr/bin/env python3
"""Find the sounding transposition of every FLP channel against the mp3.

The soundfont channels carry a -200 cent channel pitch; the NES VST channels show
0 but have their own (opaque) tuning. For each channel and each shift 0..11,
correlate the channel's time-resolved pitch-class roll with the audio chroma.

    .venv/Scripts/python tools/explore_transpose.py
"""
import json
import numpy as np, librosa

D = json.load(open('work/flp_notes.json'))
y, sr = librosa.load('asset/music/Toby Fox - Battle Against A True Hero.mp3', sr=22050, mono=True)
hop = 512
yh = librosa.effects.harmonic(y)
chroma = librosa.feature.chroma_cqt(y=yh, sr=sr, hop_length=hop)
ct = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=hop)
chroma = chroma / (np.linalg.norm(chroma, axis=0, keepdims=True) + 1e-9)

DRUMS = {16, 17, 18}
for ch in sorted({n['ch'] for n in D['notes']} - DRUMS):
    roll = np.zeros_like(chroma)
    for n in D['notes']:
        if n['ch'] != ch:
            continue
        m = (ct >= n['t']) & (ct < n['t'] + max(n['dur'], 0.08))
        roll[n['key'] % 12, m] += 1
    act = roll.sum(0) > 0
    sc = []
    for s in range(12):
        r = np.roll(roll, s, axis=0)[:, act]
        r = r / (np.linalg.norm(r, axis=0, keepdims=True) + 1e-9)
        sc.append(float((r * chroma[:, act]).sum(0).mean()))
    best = int(np.argmax(sc))
    order = np.argsort(sc)[::-1]
    print(f"ch{ch:2d} {D['channels'][str(ch)]:22s} best shift {best - 12 if best > 6 else best:+d} "
          f"score {sc[best]:.3f}  next {order[1] - 12 if order[1] > 6 else order[1]:+d} {sc[order[1]]:.3f}  frames {act.sum()}")
