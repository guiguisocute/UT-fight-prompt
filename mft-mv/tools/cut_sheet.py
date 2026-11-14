"""Cut a Spriters Resource sheet's parts (tools/cut_parts.py, generalised): a region of the sheet is
split into bands at rows with no cell colour, then into cells at columns that are all sheet colour;
a cell must hold cell colour (labels are left out). The cell colour becomes transparent.
-> <out>/<band>_<cell>.png, <out>/parts.json, <out>_index.png (each cell outlined and numbered, 3x).

usage: python -I tools/cut_sheet.py <sheet.png> <y0> <y1> <out dir> [bg r,g,b] [cell r,g,b]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sheet, Y0, Y1, OUT = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
BG = tuple(int(v) for v in (sys.argv[5] if len(sys.argv) > 5 else '186,255,198').split(','))
CELL = tuple(int(v) for v in (sys.argv[6] if len(sys.argv) > 6 else '255,0,255').split(','))
os.makedirs(OUT, exist_ok=True)
im = np.array(Image.open(sheet).convert('RGBA'))
reg = im[Y0:Y1]
is_bg = np.all(reg[:, :, :3] == BG, axis=2)
is_cell = np.all(reg[:, :, :3] == CELL, axis=2)


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


def cut(y0, y1, x0, x1):
    """recursive XY cut: split at blank rows, else at blank columns, until neither splits"""
    blank = is_bg[y0:y1, x0:x1]
    rr = runs(~blank.all(axis=1))
    if not rr:
        return
    if len(rr) > 1 or rr[0] != (0, y1 - y0):
        for a, b in rr:
            cut(y0 + a, y0 + b, x0, x1)
        return
    cc = runs(~blank.all(axis=0))
    if len(cc) > 1 or cc[0] != (0, x1 - x0):
        for a, b in cc:
            cut(y0, y1, x0 + a, x0 + b)
        return
    if not is_cell[y0:y1, x0:x1].any():
        return
    cell = reg[y0:y1, x0:x1].copy()
    clear = np.all(cell[:, :, :3] == CELL, axis=2) | np.all(cell[:, :, :3] == BG, axis=2)
    cell[clear, 3] = 0
    parts.append({'x': int(x0), 'y': int(Y0 + y0), 'w': int(x1 - x0), 'h': int(y1 - y0), 'img': cell})


cut(0, reg.shape[0], 0, reg.shape[1])
parts.sort(key=lambda p: (p['y'] // 40, p['x']))
for i, p in enumerate(parts):
    p['name'] = f'{i:02d}'
    Image.fromarray(p.pop('img')).save(os.path.join(OUT, p['name'] + '.png'))
json.dump(parts, open(os.path.join(OUT, 'parts.json'), 'w'), indent=1)
S = 3
idx = Image.fromarray(reg).convert('RGB').resize((reg.shape[1] * S, reg.shape[0] * S), Image.NEAREST)
d = ImageDraw.Draw(idx)
for p in parts:
    d.rectangle([p['x'] * S, (p['y'] - Y0) * S, (p['x'] + p['w']) * S - 1, (p['y'] - Y0 + p['h']) * S - 1], outline=(0, 160, 255))
    d.text((p['x'] * S + 2, (p['y'] - Y0) * S + 1), p['name'], fill=(0, 90, 255))
idx.save(OUT.rstrip('/\\') + '_index.png')
for p in parts:
    print(p)
