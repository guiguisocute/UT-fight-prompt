"""Cut a Spriters Resource sheet into its cells: every connected patch of the cell colour is one cell;
the cell colour becomes transparent. Writes work/slices/<name>/NN.png, cells.json and a numbered
contact sheet (work/slices/<name>_index.png) to map cells to keys.

usage: python tools/slice_sheet.py <sheet.png> <name> [cell rgb hex, default: most common light colour]
"""
import json
import os
import sys
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

src, name = sys.argv[1], sys.argv[2]
im = np.array(Image.open(src).convert('RGBA'))
H, W = im.shape[:2]
rgb = im[:, :, :3].astype(int)
cnt = Counter(map(tuple, rgb.reshape(-1, 3)))
if len(sys.argv) > 3:
    h = sys.argv[3].lstrip('#')
    cell = tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
else:
    # the sheet's own background is the most common colour; the cells are the next most common
    (bg, _), (cell, _) = cnt.most_common(2)
print('cell colour', cell)
is_cell = np.all(rgb == np.array(cell), axis=2)
# a cell = the cell colour plus everything it encloses (the sprite on it)
lab, n = ndimage.label(ndimage.binary_fill_holes(ndimage.binary_closing(is_cell, iterations=2)))
out = f'work/slices/{name}'
os.makedirs(out, exist_ok=True)
cells = []
for i, sl in enumerate(ndimage.find_objects(lab)):
    y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
    if (y1 - y0) < 4 or (x1 - x0) < 4:
        continue
    crop = im[y0:y1, x0:x1].copy()
    m = np.all(crop[:, :, :3] == np.array(cell), axis=2)
    crop[m, 3] = 0
    # (outside this cell's own patch: clear)
    crop[lab[y0:y1, x0:x1] != i + 1, 3] = 0
    a = crop[:, :, 3] > 0
    if not a.any():
        continue
    ys, xs = np.nonzero(a)
    crop = crop[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    # pixel scale: the shortest run of one colour along rows (2 = the sheet is drawn at 2x)
    runs = []
    for row in crop[:, :, :3].astype(int)[:: max(1, crop.shape[0] // 12)]:
        r = 1
        for k in range(1, len(row)):
            if (row[k] == row[k - 1]).all():
                r += 1
            else:
                runs.append(r)
                r = 1
    idx = len(cells)
    Image.fromarray(crop).save(f'{out}/{idx:02d}.png')
    cells.append({'i': idx, 'x': int(x0 + xs.min()), 'y': int(y0 + ys.min()), 'w': int(crop.shape[1]), 'h': int(crop.shape[0]),
                  'minRun': int(min(runs)) if runs else 0})
json.dump(cells, open(f'{out}/cells.json', 'w'), indent=1)
# the numbered index
sheet = Image.open(src).convert('RGB')
d = ImageDraw.Draw(sheet)
for c in cells:
    d.rectangle([c['x'] - 1, c['y'] - 1, c['x'] + c['w'], c['y'] + c['h']], outline=(255, 255, 0))
    d.text((c['x'] + 1, c['y'] + 1), str(c['i']), fill=(255, 40, 40))
sheet.save(f'work/slices/{name}_index.png')
for c in cells:
    print(c)
