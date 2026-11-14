"""Hold a rig against its recording (tools/compare_muffet.py, generalised): for each game frame k, the
recording's frame (a .npy of game frames, tools/rec_game.py) beside our render of a lab at lab t =
k / 30 (tools/frames.cjs, 960 x 540, the game screen at +160, +30), and the difference (white only in
the recording: red; only ours: cyan) over a region. -> <out>/cmp_<k>.png, <out>/cmp_sheet.png, and
the count of differing pixels per frame.

usage: python -I tools/compare_rig.py <frames dir> <game frames .npy> <out dir> k1 k2 ...
       [--reg=y0,y1,x0,x1 (game px)] [--scale=3]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--'))
src, G, out, ks = args[0], np.load(args[1]), args[2], [int(v) for v in args[3:]]
os.makedirs(out, exist_ok=True)
Y0, Y1, X0, X1 = (int(v) for v in opts.get('reg', '20,250,0,640').split(','))
S = int(opts.get('scale', 3))
rows = []
for k in ks:
    rec = G[k][Y0:Y1, X0:X1] > 128
    im = np.array(Image.open(os.path.join(src, f'f_{k / 30:.4f}.png')).convert('L'))
    ours = im[30 + Y0:30 + Y1, 160 + X0:160 + X1] > 128
    diff = np.zeros(rec.shape + (3,), np.uint8)
    diff[rec & ours] = (110, 110, 110)
    diff[rec & ~ours] = (255, 60, 60)
    diff[ours & ~rec] = (60, 220, 255)
    gap = np.full((Y1 - Y0, 4, 3), 60, np.uint8)
    row = np.concatenate([np.stack([rec * 255] * 3, -1).astype(np.uint8), gap, np.stack([ours * 255] * 3, -1).astype(np.uint8), gap, diff], 1)
    img = Image.fromarray(row).resize((row.shape[1] * S, row.shape[0] * S), Image.NEAREST)
    d = ImageDraw.Draw(img)
    n_miss, n_extra = int((rec & ~ours).sum()), int((ours & ~rec).sum())
    d.text((6, 6), f'recording  frame {k}', fill=(255, 255, 0))
    d.text(((X1 - X0 + 4) * S + 6, 6), 'ours', fill=(255, 255, 0))
    d.text((2 * (X1 - X0 + 4) * S + 6, 6), f'diff: rec only {n_miss}, ours only {n_extra}', fill=(255, 255, 0))
    img.save(os.path.join(out, f'cmp_{k}.png'))
    rows.append(img)
    print(k, 'white', int(rec.sum()), 'rec only', n_miss, 'ours only', n_extra)
sheet = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)))
y = 0
for r in rows:
    sheet.paste(r, (0, y)); y += r.height
sheet.save(os.path.join(out, 'cmp_sheet.png'))
