#!/usr/bin/env python3
"""The original bridge room's textures, cut from the lifted overworld (tools/lift_overworld.py).

The recording carries the uploader's watermark: 「老涵Hannnn bilibili」 top right and
「bilibili-老涵Hannnn出品」 across the left of the bridge. It never reaches the MV: the watermark is
painted out of the reference first (black where the room is black, the bridge's own planks where it
crosses the bridge), every tile is cut from outside it, and the cleaned picture is checked to hold
nothing but the room's palette (and the player sprite, which no tile uses).

    .venv/Scripts/python tools/make_tiles.py [work/ref/ow_art.png]

Writes work/ref/ow_art_clean.png (+ _x4 preview) and asset/tiles/*.png (1 art px = 1 px).
"""
import os, sys
import numpy as np
from PIL import Image

SRC = sys.argv[1] if len(sys.argv) > 1 else 'work/ref/ow_art.png'
OUT = 'asset/sprites/tiles'
# the room's palette (lifted): black, purple, blue-purple, indigo, near-black blue, dark indigo
PAL = np.array([[0x01, 0x01, 0x00], [0x3f, 0x31, 0x84], [0x22, 0x20, 0x62], [0x1d, 0x13, 0x4c],
                [0x05, 0x04, 0x16], [0x18, 0x11, 0x38]])
BLACK = PAL[0]
# watermark boxes in art px (x0, y0, x1, y1), found by the off-palette blobs; padded below
WATERMARK = [(246, 5, 320, 25), (0, 114, 96, 126)]
PLAYER = (148, 102, 171, 135)  # the player sprite in the reference (no tile is cut from it)
PAD = 2

a = np.array(Image.open(SRC).convert('RGB')).astype(int)
H, W = a.shape[:2]
mask = np.zeros((H, W), bool)
for x0, y0, x1, y1 in WATERMARK:
    mask[max(0, y0 - PAD):min(H, y1 + PAD), max(0, x0 - PAD):min(W, x1 + PAD)] = True

# ---- paint the watermark out: the bridge's planks repeat every 20 px (three planks, 6 + 7 + 7)
clean = a.copy()
DECK_Y0, DECK_Y1 = 120, 140           # the deck: plank faces 120..138, the front edge 139
PERIOD, CLEAN_X = 20, 101             # a clean period starts on the gap at x = 101
for y in range(H):
    for x in range(W):
        if not mask[y, x]:
            continue
        if DECK_Y0 <= y < DECK_Y1 and x < 208:
            clean[y, x] = a[y, CLEAN_X + (x - CLEAN_X) % PERIOD]
        elif y == 140 and x < 208:
            clean[y, x] = a[y, CLEAN_X + (x - CLEAN_X) % PERIOD]
        else:
            clean[y, x] = BLACK

# ---- check: outside the player sprite, the cleaned picture is the room's palette and nothing else
d = ((clean[:, :, None, :] - PAL[None, None, :, :]) ** 2).sum(-1).min(-1)
off = d > 30 ** 2
px0, py0, px1, py1 = PLAYER
off[py0:py1, px0:px1] = False
assert not off.any(), f'off-palette pixels left at {np.argwhere(off)[:10].tolist()}'
# snap to the palette exactly (the lift is already snapped; this keeps the tiles to six colours)
idx = ((clean[:, :, None, :] - PAL[None, None, :, :]) ** 2).sum(-1).argmin(-1)
snapped = PAL[idx].astype(np.uint8)
snapped[py0:py1, px0:px1] = clean[py0:py1, px0:px1]
Image.fromarray(snapped).save('work/ref/ow_art_clean.png')
Image.fromarray(snapped).resize((W * 4, H * 4), Image.NEAREST).save('work/ref/ow_art_clean_x4.png')


def cut(name, x0, y0, x1, y1, alpha_black=False):
    """a tile from the cleaned picture; refuses anything that touches the watermark or the player"""
    assert not mask[y0:y1, x0:x1].any(), f'{name} overlaps the watermark'
    assert not (x0 < px1 and px0 < x1 and y0 < py1 and py0 < y1), f'{name} overlaps the player sprite'
    t = snapped[y0:y1, x0:x1]
    rgba = np.dstack([t, np.full(t.shape[:2], 255, np.uint8)])
    if alpha_black:
        rgba[(t == BLACK).all(-1), 3] = 0
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(rgba).save(os.path.join(OUT, name + '.png'))
    print(f'{name:10s} {x1 - x0:3d} x {y1 - y0:3d}  from ({x0}, {y0})')


# the deck: two periods of planks (six planks), the faces and the darker front edge
cut('deck', 101, 120, 141, 140)
# a post (rows 150..181 repeat down into the dark)
cut('post', 93, 150, 101, 182)
# the stone pier under the west end: strata, repeating downward
cut('pier', 28, 140, 66, 240)
# the river beside the path: white-less wave lines on the dark (as in the original room)
cut('water', 216, 40, 320, 96)
# the rock of the east shore (speckled), and its rim (the lit ledge, then its shadow)
cut('rock', 213, 100, 320, 153)
cut('rim', 213, 153, 320, 160)
# the stalagmites standing out of the chasm: the tall one behind the bridge, a small one in front
cut('spire', 64, 0, 112, 80, alpha_black=True)
cut('spire_s', 104, 174, 135, 200, alpha_black=True)
print('watermark painted out, cleaned picture holds only the room palette (+ the player sprite)')
