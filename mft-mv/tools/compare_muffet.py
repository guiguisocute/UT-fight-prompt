"""Hold the rig against the recording: for each game frame k, the recording (work/muf/g/game.npy,
the 640 x 480 game screen) beside our render of ?lab=muffet at lab t = k / 30 (tools/frames.cjs,
960 x 540, the game screen at +160, +30), and the difference (white only in the recording: red; only
ours: cyan) - over her (y 20-248, x 200-450). -> work/muf/cmp/cmp_<k>.png, cmp_sheet.png, and the
count of differing pixels per frame.

usage: python tools/compare_muffet.py <frames dir> k1 k2 ...
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
G = np.load('work/muf/g/game.npy')
src, ks = sys.argv[1], [int(v) for v in sys.argv[2:]]
os.makedirs('work/muf/cmp', exist_ok=True)
Y0, Y1, X0, X1 = 20, 248, 200, 450
S = 3
rows = []
for k in ks:
    rec = G[k][Y0:Y1, X0:X1] > 128
    im = np.array(Image.open(os.path.join(src, f'f_{k / 30:.4f}.png')).convert('L'))
    ours = im[30 + Y0:30 + Y1, 160 + X0:160 + X1] > 128
    diff = np.zeros(rec.shape + (3,), np.uint8)
    diff[rec & ours] = (110, 110, 110)
    diff[rec & ~ours] = (255, 60, 60)
    diff[ours & ~rec] = (60, 220, 255)
    a = (rec * 255).astype(np.uint8)
    b = (ours * 255).astype(np.uint8)
    row = np.concatenate([np.stack([a] * 3, -1), np.full((Y1 - Y0, 4, 3), 60, np.uint8), np.stack([b] * 3, -1), np.full((Y1 - Y0, 4, 3), 60, np.uint8), diff], 1)
    img = Image.fromarray(row).resize((row.shape[1] * S, row.shape[0] * S), Image.NEAREST)
    d = ImageDraw.Draw(img)
    n_miss, n_extra = int((rec & ~ours).sum()), int((ours & ~rec).sum())
    d.text((6, 6), f'recording  frame {k}', fill=(255, 255, 0))
    d.text(((X1 - X0 + 4) * S + 6, 6), 'ours (?lab=muffet)', fill=(255, 255, 0))
    d.text((2 * (X1 - X0 + 4) * S + 6, 6), f'diff: rec only {n_miss}, ours only {n_extra}', fill=(255, 255, 0))
    img.save(f'work/muf/cmp/cmp_{k}.png')
    rows.append(img)
    print(k, 'white', int(rec.sum()), 'rec only', n_miss, 'ours only', n_extra)
sheet = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)))
y = 0
for r in rows:
    sheet.paste(r, (0, y)); y += r.height
sheet.save('work/muf/cmp/cmp_sheet.png')
