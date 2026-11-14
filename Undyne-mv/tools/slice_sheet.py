#!/usr/bin/env python3
"""Cut the Spriters Resource sheets in asset/ into cells (from ../mtt-neo-mv/tools/slice_neo.py).

The page is purple (138, 90, 157); every frame sits on a lilac cell (195, 134, 255) that
becomes transparent. Each connected non-page region is one cell; cells are sorted
top-to-bottom, left-to-right, so an index is stable.

    .venv/Scripts/python tools/slice_sheet.py boss    # -> work/index_boss.png (numbered cells) + table
    .venv/Scripts/python tools/slice_sheet.py npc
    .venv/Scripts/python tools/slice_sheet.py kid

tools/import_assets.py imports cells() and the NAMES tables below.
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SHEETS = {
    'boss': 'asset/sprites/PC _ Computer - Undertale - Enemies & Bosses - Undyne.png',
    'npc': 'asset/sprites/PC _ Computer - Undertale - Non-Playable Characters - Undyne.png',
    'kid': 'asset/sprites/PC _ Computer - Undertale - Non-Playable Characters - Monster Kid.png',
}
PAGE = (138, 90, 157)
CELL = (195, 134, 255)


def frames(which, min_w=80, min_h=100):
    """The big pictures that sit on black instead of a cell (the assembled Undying, her last melt):
    the black connected to their border is the screen and becomes transparent; stray cell lilac too."""
    im = np.array(Image.open(SHEETS[which]).convert('RGBA'))
    r, g, b = (im[..., i].astype(int) for i in range(3))
    page = (r == PAGE[0]) & (g == PAGE[1]) & (b == PAGE[2])
    lab, n = ndimage.label(~page)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        sub = im[y0:y1, x0:x1].copy()
        m = lab[y0:y1, x0:x1] == i + 1
        black = (sub[..., :3].sum(-1) == 0) & m
        if x1 - x0 < min_w or y1 - y0 < min_h or black.sum() < 0.3 * m.sum():
            continue
        lil = (sub[..., 0] == CELL[0]) & (sub[..., 1] == CELL[1]) & (sub[..., 2] == CELL[2])
        outside = ndimage.label(black | lil | ~m)[0]
        edge = set(np.unique(np.concatenate([outside[0], outside[-1], outside[:, 0], outside[:, -1]]))) - {0}
        sub[np.isin(outside, list(edge)) | lil | ~m] = 0
        out.append(dict(x=x0, y=y0, w=x1 - x0, h=y1 - y0, img=sub))
    out.sort(key=lambda c: (round(c['y'] / 6), c['x']))
    return out


def cells(which):
    im = np.array(Image.open(SHEETS[which]).convert('RGBA'))
    r, g, b = (im[..., i].astype(int) for i in range(3))
    page = (r == PAGE[0]) & (g == PAGE[1]) & (b == PAGE[2])
    lab, n = ndimage.label(~page)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        sub = im[y0:y1, x0:x1].copy()
        m = lab[y0:y1, x0:x1] == i + 1
        cellpx = (sub[..., 0] == CELL[0]) & (sub[..., 1] == CELL[1]) & (sub[..., 2] == CELL[2])
        sub[~m | cellpx] = 0
        out.append(dict(x=x0, y=y0, w=x1 - x0, h=y1 - y0, img=sub, cell=cellpx.sum() > 0.2 * m.sum()))
    out = [c for c in out if c['cell']]  # (the page's labels are not cells)
    out.sort(key=lambda c: (round(c['y'] / 6), c['x']))
    return out, im


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'boss'
    cs, im = cells(which)
    k2 = 2
    vis = Image.fromarray(im).convert('RGB').resize((im.shape[1] * k2, im.shape[0] * k2), Image.NEAREST)
    d = ImageDraw.Draw(vis)
    for k, c in enumerate(cs):
        d.rectangle([c['x'] * k2, c['y'] * k2, (c['x'] + c['w']) * k2 - 1, (c['y'] + c['h']) * k2 - 1], outline=(0, 255, 0))
        d.text((c['x'] * k2 + 2, c['y'] * k2 + 1), str(k), fill=(255, 0, 0))
    os.makedirs('work', exist_ok=True)
    vis.save(f'work/index_{which}.png')
    for k, c in enumerate(cs):
        print(k, c['x'], c['y'], c['w'], c['h'])
