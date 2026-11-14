#!/usr/bin/env python3
"""Cut the Mettaton NEO sprite sheet (asset/...Mettaton NEO.png) into parts.

The page is dark purple (153,51,153); every frame sits on a pink cell
(255,102,255); the art itself is black and white. Each connected non-page
region is one cell; the cell colour becomes transparent.

    ../mtt-mv/.venv/Scripts/python tools/slice_neo.py            # -> work/neo_index.png (numbered cells) + table
    ../mtt-mv/.venv/Scripts/python tools/slice_neo.py --export   # -> work/parts/neo/<name>.png

The index is stable (cells sorted top-to-bottom, left-to-right).
"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SHEET = 'asset/sprites/PC _ Computer - Undertale - Enemies & Bosses - Mettaton NEO.png'
CELL = (255, 102, 255)


def cells(sheet=SHEET):
    im = np.array(Image.open(sheet).convert('RGBA'))
    r, g, b = im[..., 0].astype(int), im[..., 1].astype(int), im[..., 2].astype(int)
    page = (abs(r - 153) <= 1) & (abs(g - 51) <= 1) & (abs(b - 153) <= 1)
    lab, n = ndimage.label(~page)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        sub = im[y0:y1, x0:x1].copy()
        m = lab[y0:y1, x0:x1] == i + 1
        cellpx = (sub[..., 0] == CELL[0]) & (sub[..., 1] == CELL[1]) & (sub[..., 2] == CELL[2])
        sub[~m | cellpx] = 0
        out.append(dict(x=x0, y=y0, w=x1 - x0, h=y1 - y0, img=sub, cell=cellpx.sum() > 0.2 * m.sum()))
    out.sort(key=lambda c: (round(c['y'] / 6), c['x']))
    return out, im


# cell index -> part name (see work/neo_index.png); filled in after the first run
NAMES = {}

if __name__ == '__main__':
    cs, im = cells()
    if '--export' in sys.argv:
        os.makedirs('work/parts/neo', exist_ok=True)
        for k, name in NAMES.items():
            Image.fromarray(cs[k]['img']).save(f'work/parts/neo/{name}.png')
        print(len(NAMES), 'parts -> work/parts/neo')
    else:
        vis = Image.fromarray(im).convert('RGB').resize((im.shape[1] * 2, im.shape[0] * 2), Image.NEAREST)
        d = ImageDraw.Draw(vis)
        for k, c in enumerate(cs):
            if not c['cell']:
                continue
            d.rectangle([c['x'] * 2, c['y'] * 2, (c['x'] + c['w']) * 2 - 1, (c['y'] + c['h']) * 2 - 1], outline=(0, 255, 0))
            d.text((c['x'] * 2 + 2, c['y'] * 2 + 1), str(k), fill=(255, 0, 0))
        os.makedirs('work', exist_ok=True)
        vis.save('work/neo_index.png')
        for k, c in enumerate(cs):
            if c['cell']:
                print(k, c['x'], c['y'], c['w'], c['h'])
