"""Her five eyes through the whole recording: which frame each shows (0 open .. 3 shut, 4 the round
one), every game frame - to learn when and how she blinks. The face is cut out of asset/record.mp4
by ffmpeg (the head's region only), sampled at game-pixel centres; the head's bob found by the best
vertical offset of all five eyes together; each eye then takes its best-matching frame.
-> work/muf/eyes.json ([t, dy, score, [frame per eye]] per video frame) and a printout of the runs.

usage: python tools/scan_eyes.py [t0] [t1]
"""
import json
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fit_muffet as fm

t0 = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0
t1 = float(sys.argv[2]) if len(sys.argv) > 2 else 257.0
GY0, GY1, GX0, GX1 = 40, 112, 284, 362
VX0, VY0 = int(240 + GX0 * 2.25) // 2 * 2, int(GY0 * 2.25) // 2 * 2
VW, VH = (int((GX1 - GX0) * 2.25) + 5) // 2 * 2, (int((GY1 - GY0) * 2.25) + 5) // 2 * 2
cmd = ['ffmpeg', '-v', 'error', '-ss', f'{t0}', '-i', 'asset/record/record.mp4', '-t', f'{t1 - t0}',
       '-vf', f'crop={VW}:{VH}:{VX0}:{VY0}', '-f', 'rawvideo', '-pix_fmt', 'gray', '-']
raw = subprocess.run(cmd, capture_output=True, check=True).stdout
n = len(raw) // (VW * VH)
v = np.frombuffer(raw[: n * VW * VH], np.uint8).reshape(n, VH, VW)
xs = (240 + (np.arange(GX0, GX1) + 0.5) * 2.25).astype(int) - VX0
ys = ((np.arange(GY0, GY1) + 0.5) * 2.25).astype(int) - VY0
g = np.where(v[:, ys][:, :, xs] > 128, 1.0, -1.0)
print('frames', n)

EYES = [('5', False, 307, 86), ('5', True, 337, 86), ('6', False, 322, 67), ('7', False, 311, 72), ('7', True, 333, 72)]
MASKS = []
for e, f, cx, cy in EYES:
    vs = []
    for i in range(5):
        sm, op, (ox, oy) = fm.rotated(f'{e}_{i}', f, 0)
        vs.append((sm, op.sum(), cx - ox - GX0, cy - oy - GY0))
    MASKS.append(vs)

res = []
for k in range(n):
    fr = g[k]
    best = None
    for dy in range(-9, 10):
        tot, pick = 0.0, []
        for vs in MASKS:
            sc = []
            for sm, cnt, x0, y0 in vs:
                y = y0 + dy
                h, w = sm.shape
                if y < 0 or y + h > fr.shape[0]:
                    sc.append(-1); continue
                sc.append(float((fr[y:y + h, x0:x0 + w] * sm).sum() / cnt))
            j = int(np.argmax(sc))
            tot += sc[j]; pick.append(j)
        if best is None or tot > best[0]:
            best = (tot, dy, pick)
    res.append([round(t0 + k / 30, 4), best[1], round(best[0] / 5, 3), best[2]])
json.dump(res, open('work/muf/eyes.json', 'w'))
cur = None
for t, dy, s, p in res:
    if s < 0.9:
        if cur != 'gone':
            print(f'{t:8.3f}  (not her: {s})'); cur = 'gone'
        continue
    key = ''.join(map(str, p))
    if key != cur:
        print(f'{t:8.3f}  dy {dy:+d}  eyes {key}  {s}')
        cur = key
