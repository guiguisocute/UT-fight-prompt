#!/usr/bin/env python3
"""Lift the original overworld (the bridge at the end of asset/record.mp4) at art-pixel resolution.

The recording shows the 640x480 game at 1.5x (960x720, pillarboxed to 1080x720 at +60), and the
overworld is drawn at 2x, so one art pixel is a 3x3 block of the recording. The grid phase is the
one whose blocks are most uniform; each block's centre gives the art pixel. The colours are then
snapped to the frame's own palette (the few colours the room is painted in, found by clustering).

    .venv/Scripts/python tools/lift_overworld.py <t (s)> <out.png> [--k=N]

Writes out.png (320x240, 1 art px = 1 px), out_x4.png (a preview) and prints the palette.
"""
import os, subprocess, sys, tempfile
import numpy as np
from PIL import Image

t, out = float(sys.argv[1]), sys.argv[2]
K = next((int(a.split('=')[1]) for a in sys.argv[3:] if a.startswith('--k=')), 14)
with tempfile.TemporaryDirectory() as td:
    f = os.path.join(td, 'f.png')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', 'asset/record/record.mp4', '-frames:v', '1', f], check=True)
    im = np.array(Image.open(f).convert('RGB')).astype(float)
game = im[:, 60:1020]  # 960x720
best = None
for oy in range(3):
    for ox in range(3):
        g = game[oy:oy + 717, ox:ox + 957]
        h, w = g.shape[0] // 3, g.shape[1] // 3
        b = g[:h * 3, :w * 3].reshape(h, 3, w, 3, 3)
        var = b.var(axis=(1, 3)).mean()
        if best is None or var < best[0]:
            best = (var, ox, oy)
_, ox, oy = best
h, w = 240, 320
art = np.zeros((h, w, 3))
for j in range(h):
    for i in range(w):
        y, x = oy + 3 * j + 1, ox + 3 * i + 1
        if y < 720 and x < 960:
            art[j, i] = game[y, x]
# palette: k-means on the art pixels (the room is painted in a handful of colours)
px = art.reshape(-1, 3)
rng = np.random.default_rng(1)
cent = px[rng.choice(len(px), K, replace=False)]
for _ in range(40):
    d = ((px[:, None, :] - cent[None, :, :]) ** 2).sum(-1)
    lab = d.argmin(1)
    for k in range(K):
        m = lab == k
        if m.any():
            cent[k] = px[m].mean(0)
# merge near-duplicates
pal = []
for c in cent:
    if all(((c - p) ** 2).sum() > 12 ** 2 for p in pal):
        pal.append(c)
pal = np.array(pal)
d = ((px[:, None, :] - pal[None, :, :]) ** 2).sum(-1)
lab = d.argmin(1)
q = pal[lab].reshape(h, w, 3).round().clip(0, 255).astype(np.uint8)
Image.fromarray(q).save(out)
root, ext = os.path.splitext(out)
Image.fromarray(q).resize((w * 4, h * 4), Image.NEAREST).save(root + '_x4' + ext)
cnt = np.bincount(lab, minlength=len(pal))
print(f'phase ({ox}, {oy}), block variance {best[0]:.1f}')
for i in np.argsort(-cnt):
    r, g, b = pal[i].round().astype(int)
    print(f'#{r:02x}{g:02x}{b:02x}  {cnt[i]:6d} px')
