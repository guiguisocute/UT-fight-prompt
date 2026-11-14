#!/usr/bin/env python3
"""Her frames for the load scene (README 第四幕: drawn by codex, the user 2026-10-19: 动画精灵帧为了表现力可以
让codex逐帧画), snapped to true pixel art on her own sprite's grid: area-averaged down to the art size,
thresholded to the original's 1-bit white, stray pixels dropped, the inside of her outline filled with the
original's opaque black and the outside made transparent (as the game's own sprites are).

    .venv/Scripts/python -I tools/her_frames.py      -> asset/her/<set>_<i>.png, work/her/sheet_<set>.png

Sources: ../_codex_undyne/<job>/<set>_<i>.png (codex's own folder, outside the repo).
"""
import glob, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

SRC = '../_codex_undyne'
OUT = 'asset/sprites/her'
# set -> (codex job folder, art size, which borders the outside is reached from: her full figure stands
# inside the frame; the close-up's shoulders run off the bottom and its fins off the sides low down)
SETS = {
    'grip': ('grip', (112, 176), 'tlr'),
    'yank': ('grip', (112, 176), 'tlr'),
    'face': ('face', (208, 160), 'tLR'),
}
TH = 0.5


def snap(path, size):
    im = Image.open(path).convert('L')
    a = np.asarray(im.resize(size, Image.BOX), dtype=np.float32) / 255
    white = a > TH
    # (a white pixel with no white neighbour is noise, not a line)
    p = np.pad(white, 1)
    n = sum(np.roll(np.roll(p, dy, 0), dx, 1) for dy in (-1, 0, 1) for dx in (-1, 0, 1))[1:-1, 1:-1] - white
    return white & (n > 0)


def outside(white, seeds, grow=2):
    """the black reached from the frame's edges without crossing white: t/b/l/r whole edges; L/R only the
    upper 60 % of the side (the close-up's shoulders fill the lower sides). The drawn outline has small gaps
    after the snap, so the flood runs against the lines grown by `grow` px, and is given back up to the
    lines afterwards"""
    h, w = white.shape
    wall = ndimage.binary_dilation(white, iterations=grow)
    # (a shaft running off the top edge: closed across its top so its inside stays solid)
    top = np.where(white[0])[0]
    if 't' in seeds and len(top) >= 2 and top[-1] - top[0] <= 12:
        wall[0, top[0]:top[-1] + 1] = True
    lab, n = ndimage.label(~wall)
    edge = set()
    if 't' in seeds: edge |= set(lab[0, :])
    if 'b' in seeds: edge |= set(lab[-1, :])
    if 'l' in seeds: edge |= set(lab[:, 0])
    if 'r' in seeds: edge |= set(lab[:, -1])
    if 'L' in seeds: edge |= set(lab[: int(h * 0.6), 0])
    if 'R' in seeds: edge |= set(lab[: int(h * 0.6), -1])
    edge.discard(0)
    out = np.isin(lab, list(edge))
    return ndimage.binary_dilation(out, iterations=grow) & ~white


def eye_of(white):
    """the glowing eye (her left: on the viewer's right): the biggest solid white blob in the upper half,
    right of the middle -> its middle (art px)"""
    h, w = white.shape
    lab, n = ndimage.label(white)
    best, at = 0, None
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        ys, xs = sl
        area = (lab[sl] == i).sum(), (ys.stop - ys.start) * (xs.stop - xs.start)
        cy, cx = (ys.start + ys.stop) / 2, (xs.start + xs.stop) / 2
        if cy > h * 0.55 or cx < w * 0.5 or area[0] < 5 or area[0] / area[1] < 0.45:
            continue
        if area[0] > best:
            best, at = area[0], [round(cx, 1), round(cy, 1)]
    return at


def shaft_of(white):
    """the spear's shaft where it leaves the top edge: the middle of its outline there (art px)"""
    xs = np.where(white[0])[0]
    return round(float(xs.min() + xs.max()) / 2, 1) if len(xs) and xs.max() - xs.min() <= 12 else None


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs('work/her', exist_ok=True)
    meta = {}
    for name, (job, size, seeds) in SETS.items():
        files = sorted(glob.glob(f'{SRC}/{job}/{name}_*.png'))
        if not files:
            print(name, ': nothing yet')
            continue
        frames = []
        for f in files:
            white = snap(f, size)
            out = outside(white, seeds)
            rgba = np.zeros(size[::-1] + (4,), np.uint8)
            rgba[white] = (255, 255, 255, 255)
            rgba[~white & ~out] = (0, 0, 0, 255)
            im = Image.fromarray(rgba, 'RGBA')
            key = os.path.basename(f)[:-4]
            im.save(f'{OUT}/{key}.png')
            meta[key] = {'size': list(size), 'eye': eye_of(white), 'shaft': shaft_of(white)}
            frames.append(im)
        # (the review sheet: each frame at 4x on a grey ground - transparent shows grey)
        k = 4
        sheet = Image.new('RGBA', ((size[0] * k + 8) * len(frames), size[1] * k), (70, 70, 80, 255))
        for i, im in enumerate(frames):
            sheet.alpha_composite(im.resize((size[0] * k, size[1] * k), Image.NEAREST), (i * (size[0] * k + 8), 0))
        sheet.save(f'work/her/sheet_{name}.png')
        print(name, len(frames), 'frame(s)', size)
    # (where each frame's eye and shaft are: src/load.js anchors her light and the spear to them)
    import json
    json.dump(meta, open(f'{OUT}/frames.json', 'w'), indent=1)
    for k, v in meta.items():
        print(' ', k, 'eye', v['eye'], 'shaft', v['shaft'])


if __name__ == '__main__':
    sys.exit(main())
