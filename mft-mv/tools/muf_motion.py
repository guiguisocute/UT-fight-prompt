"""What moves in Muffet's idle: the tracked rig (work/muf/track.json, tools/zfit_muffet.py track) per
part over the frames -> a table (x, y, deg per frame) and work/muf/motion_plot.png (each part's x, y
and angle against the frame number, offset from its mean).

usage: python tools/muf_motion.py [track.json]
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
tr = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'work/muf/track.json'))
N = len(tr)
P = len(tr[0]['parts'])
lab = []
for p in tr[0]['parts']:
    lab.append(p['n'][:2] + ('f' if p.get('f') else ' ') + f"@{p['x']}")
X = np.array([[p['x'] + p.get('sub', [0, 0])[0] for p in r['parts']] for r in tr], float)
Y = np.array([[p['y'] + p.get('sub', [0, 0])[1] for p in r['parts']] for r in tr], float)
D = np.array([[p.get('d', 0) for p in r['parts']] for r in tr], float)
names = [[p['n'] for p in r['parts']] for r in tr]
np.set_printoptions(linewidth=250)
for j in range(P):
    print(f'{j:2d} {lab[j]:10s} x {X[:, j].min():6.1f}..{X[:, j].max():6.1f}  y {Y[:, j].min():6.1f}..{Y[:, j].max():6.1f}  d {D[:, j].min():5.0f}..{D[:, j].max():5.0f}')
    print('    y', ' '.join(f'{v:.0f}' for v in Y[:, j]))
    if np.ptp(D[:, j]) > 0:
        print('    d', ' '.join(f'{v:.0f}' for v in D[:, j]))
    if np.ptp(X[:, j]) > 1:
        print('    x', ' '.join(f'{v:.0f}' for v in X[:, j]))
    vs = sorted(set(n[j] for n in names))
    if len(vs) > 1:
        print('    frames', ' '.join(n[j][-1] for n in names))
# the plot: one strip per part, y (red), x (green), angle/3 (blue)
S, H = 6, 40
img = Image.new('RGB', (N * S + 90, P * H), (0, 0, 0))
dr = ImageDraw.Draw(img)
for j in range(P):
    y0 = j * H + H // 2
    dr.line([(90, y0), (90 + N * S, y0)], fill=(40, 40, 40))
    dr.text((2, y0 - 6), lab[j], fill=(200, 200, 200))
    for arr, col, sc in ((Y[:, j], (255, 80, 80), 2), (X[:, j], (80, 255, 80), 2), (D[:, j], (90, 140, 255), 0.7)):
        a = (arr - arr.mean()) * sc
        pts = [(90 + i * S, y0 - a[i]) for i in range(N)]
        dr.line(pts, fill=col)
img.save('work/muf/motion_plot.png')
