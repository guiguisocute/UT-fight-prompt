#!/usr/bin/env python3
"""Cut the overworld sprite sheets (asset/... Non-Playable Characters - *.png) into frames.

The sheets sit on a page colour (138, 90, 157); every frame has its own cell, filled with
(195, 134, 255). A cell is a connected region that is not the page; the frame is what in it is not
the cell colour (made transparent), cropped to its pixels. Cells are numbered in reading order
(rows of cells top to bottom, each row left to right).

    .venv/Scripts/python tools/slice_npc.py <kid|undyne> [--index=work/index_kid.png]

As a module: cells(name) -> [{'img': RGBA array, 'box': (x0, y0, x1, y1)}, ...]
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SHEETS = {
    'kid': 'asset/sprites/PC _ Computer - Undertale - Non-Playable Characters - Monster Kid.png',
    'undyne': 'asset/sprites/PC _ Computer - Undertale - Non-Playable Characters - Undyne.png',
    # the player (copied from ../asgore-mv/asset): the overworld human, and Chara's own sheet
    'frisk': 'asset/sprites/PC _ Computer - Undertale - Playable Characters - Frisk.png',
    'chara': 'asset/sprites/PC _ Computer - Undertale - Non-Playable Characters - Chara.png',
    # the heartbeat montage (bars 5-7): who she feels (user 2026-10-17: Alphys, Papyrus into asset/;
    # Asgore copied from ../asgore-mv/asset)
    'alphys': 'asset/sprites/PC _ Computer - Undertale - Non-Playable Characters - Alphys.png',
    'papyrus': 'asset/sprites/PC _ Computer - Undertale - Non-Playable Characters - Papyrus.png',
    'asgore': 'asset/sprites/PC _ Computer - Undertale - Non-Playable Characters - Asgore Dreemurr.png',
}
PAGE = (138, 90, 157)
CELL = (195, 134, 255)


def cells(name):
    im = np.array(Image.open(SHEETS[name]).convert('RGBA'))
    rgb = im[..., :3]
    page = (rgb == PAGE).all(-1)
    lab, n = ndimage.label(~page)
    out = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        y, x = sl
        if (y.stop - y.start) < 6 or (x.stop - x.start) < 6:
            continue
        reg = im[sl].copy()
        own = lab[sl] == i + 1
        cellpx = own & (reg[..., :3] == CELL).all(-1)
        spr = own & ~(reg[..., :3] == CELL).all(-1)
        # (the sheet's titles - "Monster Kid", "Armor" ... - sit on the page, not in a cell)
        if spr.sum() < 12 or cellpx.sum() < 0.2 * own.sum():
            continue
        reg[~spr] = 0
        ys, xs = np.where(spr)
        crop = reg[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
        out.append({'img': crop, 'box': (x.start, y.start, x.stop, y.stop)})
    # reading order: group into rows by the cell's top edge (cells in a row share a band)
    out.sort(key=lambda c: (c['box'][1], c['box'][0]))
    rows, cur = [], []
    for c in out:
        if cur and c['box'][1] >= max(k['box'][3] for k in cur) - 2:
            rows.append(cur); cur = []
        cur.append(c)
    if cur:
        rows.append(cur)
    return [c for r in rows for c in sorted(r, key=lambda c: c['box'][0])]


if __name__ == '__main__':
    name = sys.argv[1]
    idx = next((a.split('=', 1)[1] for a in sys.argv[2:] if a.startswith('--index=')), f'work/index_{name}.png')
    cs = cells(name)
    sheet = Image.open(SHEETS[name]).convert('RGB').resize(
        (Image.open(SHEETS[name]).width * 2, Image.open(SHEETS[name]).height * 2), Image.NEAREST)
    d = ImageDraw.Draw(sheet)
    for i, c in enumerate(cs):
        x0, y0, x1, y1 = c['box']
        d.rectangle([x0 * 2, y0 * 2, x1 * 2 - 1, y1 * 2 - 1], outline=(255, 255, 0))
        d.text((x0 * 2 + 2, y0 * 2 + 1), str(i), fill=(255, 255, 255))
    os.makedirs(os.path.dirname(idx), exist_ok=True)
    sheet.save(idx)
    print(name, len(cs), 'frames ->', idx)
