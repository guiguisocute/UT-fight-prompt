"""Where exactly a capture's game pixels are: sample a video frame on a grid (x0 + (gx + 0.5) s,
y0 + (gy + 0.5) s) for small changes of x0, y0, s, and keep the grid on which a fitted rig (rigfit spec)
agrees best with what is sampled - a capture scaled with smoothing, or a pixel off, shows in the fit
as 1 px fringes along every line.

usage: python -I tools/calib_grid.py <frame.png (full video frame)> <spec.json> --parts=dir [--scale=2]
       [--reg=x0,y0,x1,y1 (game px)]
"""
import json
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, __file__.rsplit('\\', 1)[0].rsplit('/', 1)[0])
import rigfit

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
V = np.array(Image.open(args[0]).convert('L')).astype(np.float32)
spec = json.load(open(args[1]))
P = rigfit.Parts(opts['parts'], float(opts.get('scale', 2)))
rx0, ry0, rx1, ry1 = (int(v) for v in opts.get('reg', '0,20,250,250').split(','))
v, _ = rigfit.composite(P, spec, (480, 640))
want = v[ry0:ry1, rx0:rx1]
gx, gy = np.arange(rx0, rx1) + 0.5, np.arange(ry0, ry1) + 0.5


def sample(x0, y0, s, sy=None):
    xs = np.clip(x0 + gx * s, 0, V.shape[1] - 1.001)
    ys = np.clip(y0 + gy * (sy or s), 0, V.shape[0] - 1.001)
    xi, yi = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = xs - xi, ys - yi
    a = V[yi][:, xi] * (1 - fx) + V[yi][:, xi + 1] * fx
    b = V[yi + 1][:, xi] * (1 - fx) + V[yi + 1][:, xi + 1] * fx
    return (a * (1 - fy[:, None]) + b * fy[:, None]) > 128


best = []
for s in np.arange(2.245, 2.2601, 0.0025):
    for x0 in np.arange(238, 242.01, 0.25):
        for sy in np.arange(2.245, 2.2601, 0.0025):
            for y0 in np.arange(-3, 1.01, 0.25):
                err = int((sample(x0, y0, s, sy) != want).sum())
                best.append((err, round(float(x0), 2), round(float(y0), 2), round(float(s), 4), round(float(sy), 4)))
best.sort()
print('grid (err, x0, y0, sx, sy):', best[:6])
print('the usual grid (240, 0, 2.25):', [b for b in best if b[1:] == (240.0, 0.0, 2.25, 2.25)])
