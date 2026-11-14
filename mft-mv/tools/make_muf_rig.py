"""Muffet's rig for the film, as the game moves her: the tracked idle (work/muf/track3.json) reduced
to the game's own numbers.

Everything runs on one clock: S = sin(w k + ph), C = cos(w k + ph) (k the game frame at 30 fps; w =
0.2, the game's sin(siner / 5)). Measured off the recording:
  - a piece that does not turn bobs: x, y = a + b S + c C with b, c whole or half pixels, drawn at
    the rounded position (head: 85 + 4 S, the bow 143 + 2 S, the body 175 + S ... every frame exact)
  - a piece that turns: angle = d0 + b S + c C (whole degrees), about its origin (whole sprite px:
    the pivot - a shoulder, an elbow, a pigtail's root), the origin drawn at a point that bobs
  - the lower arms are two pictures (3_0 while S > 0, 3_1 while not)
  - the blinks: the game's 111-frame blink clock (tools/scan_eyes.py)
-> src/muf_rig.js (window.MV_MUF) and a report of how each piece's model agrees with the tracking.

usage: python tools/make_muf_rig.py [track.json (default work/muf/track3.json)]
"""
import base64
import io
import json
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
tr = json.load(open(sys.argv[1] if len(sys.argv) > 1 else 'work/muf/track3.json'))
K = np.array([r['k'] for r in tr], float)
parts0 = tr[0]['parts']
X = np.array([[p['x'] + p.get('sub', [0, 0])[0] for p in r['parts']] for r in tr], float)
Y = np.array([[p['y'] + p.get('sub', [0, 0])[1] for p in r['parts']] for r in tr], float)
D = np.array([[p.get('d', 0) for p in r['parts']] for r in tr], float)
NAMES = [[p['n'] for p in r['parts']] for r in tr]
W = 0.2


def lsq(cols, v):
    A = np.stack(cols, 1)
    c, *_ = np.linalg.lstsq(A, v, rcond=None)
    return c, float(np.sqrt(np.mean((A @ c - v) ** 2)))


# the clock's phase: the head's bob (its exact fit, every frame: 85 + 4 S rounded)
jh = [j for j, p in enumerate(parts0) if p['n'] == '0_0'][0]
best = None
for ph in np.radians(np.arange(-180, 180, 0.05)):
    m = int((np.round(85 + 4 * np.sin(W * K + ph)) == Y[:, jh]).sum())
    if best is None or m > best[0]:
        best = (m, ph)
PH = round(float(best[1]), 4)
S, C = np.sin(W * K + PH), np.cos(W * K + PH)
print(f'clock: w {W}, phase {np.degrees(PH):.2f} deg (head 85 + 4 S: {best[0]} of {len(K)} frames exact)')


def snap(v, q):
    return round(round(v / q) * q, 3)


def bob_exact(v):
    """a + b S + c C, rounded, against whole-pixel tracking: the simplest that agrees best"""
    cands = []
    m0 = round(float(v.mean()) * 2) / 2
    amps = [0] + [s * a for a in np.arange(0.5, 7.01, 0.5) for s in (1, -1)]
    for b in amps:
        for c in amps:
            if b and c:
                continue
            for a in np.arange(m0 - 1.5, m0 + 1.51, 0.5):
                ok = int((np.round(a + b * S + c * C) == v).sum())
                cands.append((ok, -(abs(b) + abs(c)), a, b, c))
    cands.sort(reverse=True)
    ok, _, a, b, c = cands[0]
    return [round(float(a), 2), float(b), float(c)], ok


rig = []
for j, p in enumerate(parts0):
    eye = p['n'][0] in '567'
    name = p['n'][:2] if eye else p['n']
    q = {'n': name, 'f': bool(p.get('f'))}
    img = Image.open(f"work/muf/parts/{p['n']}.png")
    w, h = img.size
    # the angle
    cd, rd = lsq([np.ones_like(K), S, C], D[:, j])
    amp = float(np.hypot(cd[1], cd[2]))
    if amp < 1.0:
        q['d'] = [float(round(D[:, j].mean())), 0.0, 0.0]
        q['x'], okx = bob_exact(X[:, j])
        q['y'], oky = bob_exact(Y[:, j])
        q['r'] = 1
        # (still on a half pixel: numpy rounds half to even, the browser half up - store the pixel)
        for key in ('x', 'y'):
            if q[key][1] == 0 and q[key][2] == 0:
                q[key][0] = float(np.round(q[key][0]))
        print(f'{j:2d} {p["n"]}{"f" if q["f"] else " "} still  d {q["d"][0]:+.0f}  x {q["x"]} ({okx}/90)  y {q["y"]} ({oky}/90)')
    else:
        q['d'] = [float(round(cd[0])), float(snap(cd[1], 1)), float(snap(cd[2], 1))]
        dm = np.radians(q['d'][0] + q['d'][1] * S + q['d'][2] * C)
        co, si = np.cos(dm), np.sin(dm)
        # the pivot: centre = P + bob + R(d) v (v: the centre seen from the origin, screen px, at d 0)
        Xc, Yc = X[:, j], Y[:, j]
        z, o = np.zeros_like(K), np.ones_like(K)
        best = None
        for basis in ('S', 'C'):
            B = S if basis == 'S' else C
            # unknowns: Px, Py, bx, by, vx, vy
            A = np.concatenate([np.stack([o, z, B, z, co, -si], 1), np.stack([z, o, z, B, si, co], 1)])
            c, *_ = np.linalg.lstsq(A, np.concatenate([Xc, Yc]), rcond=None)
            res = float(np.sqrt(np.mean((A @ c - np.concatenate([Xc, Yc])) ** 2)))
            if best is None or res < best[0]:
                best = (res, basis, c)
        res, basis, c = best
        # the origin in whole sprite px of the picture as drawn (mirrored if f), then the rest again
        ox, oy = round(w / 2 - c[4] / 2), round(h / 2 - c[5] / 2)
        vx, vy = 2 * (w / 2 - ox), 2 * (h / 2 - oy)
        B = S if basis == 'S' else C
        A = np.concatenate([np.stack([o, z, B, z], 1), np.stack([z, o, z, B], 1)])
        rhs = np.concatenate([Xc - (co * vx - si * vy), Yc - (si * vx + co * vy)])
        c2, *_ = np.linalg.lstsq(A, rhs, rcond=None)
        px, py, bx, by = snap(c2[0], 0.5), snap(c2[1], 0.5), snap(c2[2], 0.5), snap(c2[3], 0.5)
        q['x'] = [px, bx, 0.0] if basis == 'S' else [px, 0.0, bx]
        q['y'] = [py, by, 0.0] if basis == 'S' else [py, 0.0, by]
        q['o'] = [ox, oy]
        mx = px + bx * B + co * vx - si * vy
        my = py + by * B + si * vx + co * vy
        err = float(np.sqrt(np.mean((mx - Xc) ** 2 + (my - Yc) ** 2)))
        print(f'{j:2d} {p["n"]}{"f" if q["f"] else " "} turns d {q["d"]} about sprite px ({ox}, {oy}) of {w}x{h}, drawn at ({px}, {py}) + ({bx}, {by}) {basis}  centre error {err:.2f} px')
    rig.append(q)

# pieces drawn from two pictures (the lower arms: 3_0 and 3_1) - which one goes with the sine's sign
for j, p in enumerate(parts0):
    if p['n'][0] in '567':
        continue
    ns = [n[j] for n in NAMES]
    if len(set(ns)) > 1:
        pos = max(set(ns), key=lambda n: sum(1 for a, s in zip(ns, S) if a == n and s > 0))
        neg = max(set(ns), key=lambda n: sum(1 for a, s in zip(ns, S) if a == n and s <= 0))
        bad = sum(1 for a, s in zip(ns, S) if a != (pos if s > 0 else neg))
        rig[j]['alt'] = [pos, neg]
        print(f'{j:2d} two pictures: {pos} while S > 0, {neg} otherwise ({bad} of {len(ns)} frames disagree)')

# the blinks (tools/scan_eyes.py over the whole recording: the same every 111 game frames, 3.7 s, from
# the first frame she is seen to the last): a wave, left to right - big left, middle left, top, middle
# right, big right - each eye 5 frames after the one before; then 70 frames after the wave began, all
# five together. Frames: 0 open, 1, 2, 3 shut. Lab frame 0 = record.mp4 13.0 s: the wave at 13.767 s.
EYE_ORDER = [('5_', False), ('7_', False), ('6_', False), ('7_', True), ('5_', True)]
blinks = {
    'cycle': 111, 'wave': 23, 'all': 93, 'stagger': 5,
    'order': [[j for j, q in enumerate(rig) if q['n'] == n and q['f'] == f][0] for n, f in EYE_ORDER],
    'waveSeq': [1, 1, 2, 2, 3, 3, 3, 3, 3, 3, 3, 2, 1],
    'allSeq': [1, 1, 2, 2] + [3] * 13 + [2, 2, 1, 1],
}


def url(name):
    b = io.BytesIO()
    Image.open(f'work/muf/parts/{name}.png').convert('RGBA').save(b, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


need = sorted({n for ns in NAMES for n in ns if n[0] not in '567'} | {f'{e}_{i}' for e in '567' for i in range(5)})
out = {'w': W, 'ph': PH, 'parts': rig, 'blinks': blinks, 'img': {n: url(n) for n in need}}
with open('src/muf_rig.js', 'w', encoding='utf-8') as f:
    f.write('// generated by tools/make_muf_rig.py from the recording (asset/record.mp4) - do not edit\n')
    f.write('window.MV_MUF = ' + json.dumps(out, separators=(',', ':')) + ';\n')
print('src/muf_rig.js', os.path.getsize('src/muf_rig.js'), 'bytes')
