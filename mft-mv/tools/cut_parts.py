"""Cut Muffet's parts (the top of the Spriters Resource sheet: head, body, arms, legs, eyes) by XY cuts:
split into bands at rows that are all sheet colour, then into cells at columns that are all sheet
colour. The cell colour becomes transparent. -> work/muf/parts/<band>_<cell>.png + parts.json +
work/muf/parts_index.png (each cell outlined and numbered, 4x).

usage: python tools/cut_parts.py
"""
import json
import os

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHEET = os.path.join(ROOT, 'asset', 'sprites', 'PC _ Computer - Undertale - Enemies & Bosses - Muffet.png')
OUT = os.path.join(ROOT, 'work', 'muf', 'parts')
os.makedirs(OUT, exist_ok=True)
BG, CELL = (138, 90, 157), (195, 134, 255)
im = np.array(Image.open(SHEET).convert('RGBA'))
Y0, Y1 = 0, 252
reg = im[Y0:Y1]
bg = np.all(reg[:, :, :3] == BG, axis=2)
has_cell = np.any(np.all(reg[:, :, :3] == CELL, axis=2) | np.all(reg[:, :, :3] == (0, 0, 0), axis=2), axis=1)


def runs(mask):
    out, start = [], None
    for i, v in enumerate(mask):
        if v and start is None:
            start = i
        if not v and start is not None:
            out.append((start, i)); start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


parts = []
for bi, (r0, r1) in enumerate(runs(has_cell)):
    band = reg[r0:r1]
    col_used = ~np.all(np.all(band[:, :, :3] == BG, axis=2), axis=0)
    for ci, (c0, c1) in enumerate(runs(col_used)):
        cell = band[:, c0:c1].copy()
        rows_used = ~np.all(np.all(cell[:, :, :3] == BG, axis=2), axis=1)
        rr = np.nonzero(rows_used)[0]
        if len(rr) == 0:
            continue
        cell = cell[rr[0]: rr[-1] + 1]
        keep = cell.copy()
        m = np.all(keep[:, :, :3] == CELL, axis=2) | np.all(keep[:, :, :3] == BG, axis=2)
        keep[m, 3] = 0
        name = f'{bi}_{ci}'
        Image.fromarray(keep).save(os.path.join(OUT, name + '.png'))
        parts.append({'name': name, 'x': int(c0), 'y': int(Y0 + r0 + rr[0]), 'w': int(c1 - c0), 'h': int(len(cell))})
json.dump(parts, open(os.path.join(OUT, 'parts.json'), 'w'), indent=1)
idx = Image.fromarray(im[Y0:Y1, :140]).convert('RGB').resize((560, (Y1 - Y0) * 4), Image.NEAREST)
d = ImageDraw.Draw(idx)
for p in parts:
    if p['x'] >= 140:
        continue
    d.rectangle([p['x'] * 4, (p['y'] - Y0) * 4, (p['x'] + p['w']) * 4 - 1, (p['y'] - Y0 + p['h']) * 4 - 1], outline=(255, 255, 0))
    d.text((p['x'] * 4 + 2, (p['y'] - Y0) * 4 + 2), p['name'], fill=(255, 0, 0))
idx.save(os.path.join(ROOT, 'work', 'muf', 'parts_index.png'))
for p in parts:
    print(p)
