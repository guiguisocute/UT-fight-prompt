#!/usr/bin/env python3
"""How the Undying battle sprite moves in the recording (asset/record.mp4).

The game is 640 x 480 scaled 1.5x into the 1080 x 720 video (x offset 60); her sprite pixels are 2
game px = 3 video px. Frames are cut by ffmpeg into a folder first (crop of her region); this prints,
per frame, where bands of her are (the top of the head, the left / right extent per band) so the
idle motion (bob, arms, hair) can be read off as numbers.

    ffmpeg -ss 236 -t 6 -i asset/record.mp4 -vf crop=330:390:375:0 work/review/rec/idle/i_%03d.png
    .venv/Scripts/python tools/explore_undying.py work/review/rec/idle
"""
import os, sys
import numpy as np
from PIL import Image

d = sys.argv[1]
fs = sorted(f for f in os.listdir(d) if f.endswith('.png'))
th = int(sys.argv[2]) if len(sys.argv) > 2 else 60
bands = [(0, 60), (60, 120), (120, 180), (180, 240), (240, 300), (300, 390)]
prev = None
for k, f in enumerate(fs):
    im = np.asarray(Image.open(os.path.join(d, f)).convert('L')).astype(int)
    m = im > th
    ys = np.nonzero(m.any(1))[0]
    top = ys[0] if len(ys) else -1
    row = []
    for y0, y1 in bands:
        xs = np.nonzero(m[y0:y1].any(0))[0]
        row.append(f'{xs[0]:3d}-{xs[-1]:3d}' if len(xs) else '   -   ')
    diff = '' if prev is None else f'{(m ^ prev).sum():5d}'
    # where the frame differs from the previous one: the rows' span
    if prev is not None:
        dy = np.nonzero((m ^ prev).any(1))[0]
        diff += f' rows {dy[0]}-{dy[-1]}' if len(dy) else ''
    print(f'{k:3d} t={236 + k / 30:7.3f} top={top:3d} ' + ' '.join(row) + ' ' + diff)
    prev = m
