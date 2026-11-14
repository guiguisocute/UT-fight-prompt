"""A sprite rig for the film from a tracked idle (tools/rigfit.py track), reduced to the game's own
numbers (tools/make_muf_rig.py, generalised: any parts, any scale, several actors on their own clocks).

Each actor (a run of the spec's parts) runs on one clock: S = sin(w k + ph), C = cos(w k + ph), k the
game frame at 30 fps; w is found from the actor's movers, ph from its reference piece's bob.
  - a piece that does not turn bobs: x, y = a + b S + c C (b, c whole or half px), drawn rounded
  - a piece that turns: angle = d0 + b S + c C (whole degrees) about its origin (whole sprite px: its
    pivot), the origin drawn at a point that bobs
  - a piece drawn from two pictures: which one goes with S's sign
-> <out.js> (window.MV_RIGS[name] = {actors: [{name, w, ph, parts}], img}) and a report.

usage: python -I tools/make_rig.py <track.json> <name> <out.js> --parts=dir [--scale=2]
       --actors=RG01:0-9:04,RG02:10-19:05   (name:first-last part index:reference part name)
"""
import base64
import io
import json
import os
import sys

import numpy as np
from PIL import Image

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
tr = json.load(open(args[0]))
NAME, OUT = args[1], args[2]
PARTS, SCALE = opts['parts'], float(opts.get('scale', 2))
K = np.array([r['k'] for r in tr], float)
K -= K[0]
X = np.array([[p['x'] + p.get('sub', [0, 0])[0] for p in r['parts']] for r in tr], float)
Y = np.array([[p['y'] + p.get('sub', [0, 0])[1] for p in r['parts']] for r in tr], float)
D = np.array([[p.get('d', 0) for p in r['parts']] for r in tr], float)
NAMES = [[p['n'] for p in r['parts']] for r in tr]
parts0 = tr[0]['parts']


def lsq(cols, v):
    A = np.stack(cols, 1)
    c, *_ = np.linalg.lstsq(A, v, rcond=None)
    return c, float(np.sqrt(np.mean((A @ c - v) ** 2)))


def snap(v, q):
    return round(round(v / q) * q, 3)


def bob_exact(v, S, C):
    cands = []
    m0 = round(float(v.mean()) * 2) / 2
    amps = [0] + [s * a for a in np.arange(0.5, 8.01, 0.5) for s in (1, -1)]
    for b in amps:
        for c in amps:
            if b and c:
                continue
            for a in np.arange(m0 - 1.5, m0 + 1.51, 0.5):
                ok = int((np.round(a + b * S + c * C) == v).sum())
                cands.append((ok, -(abs(b) + abs(c)), a, b, c))
    cands.sort(reverse=True)
    ok, _, a, b, c = cands[0]
    out = [round(float(a), 2), float(b), float(c)]
    if b == 0 and c == 0:
        out[0] = float(np.round(a))
    return out, ok


actors = []
for spec in opts['actors'].split(','):
    an, rng, ref = spec.split(':')
    j0, j1 = (int(v) for v in rng.split('-'))
    idx = list(range(j0, j1 + 1))
    jr = [j for j in idx if parts0[j]['n'] == ref][0]
    movers = [j for j in idx if np.ptp(D[:, j]) >= 3] + [jr]
    best = None
    for w in np.arange(0.08, 0.6, 0.0005):
        s, c = np.sin(w * K), np.cos(w * K)
        e = sum(lsq([np.ones_like(K), s, c], D[:, j] if j != jr else Y[:, j])[1] for j in movers)
        if best is None or e < best[0]:
            best = (e, w)
    W = round(float(best[1]), 4)
    for n in range(2, 16):
        if abs(W - 1 / n) / W < 0.006:
            W = round(1 / n, 6)
            break
    cy, _ = lsq([np.ones_like(K), np.sin(W * K), np.cos(W * K)], Y[:, jr])
    amp = round(float(np.hypot(cy[1], cy[2])))
    best = None
    for ph in np.radians(np.arange(-180, 180, 0.05)):
        m = int((np.round(round(float(cy[0])) + amp * np.sin(W * K + ph)) == Y[:, jr]).sum())
        if best is None or m > best[0]:
            best = (m, ph)
    PH = round(float(best[1]), 4)
    S, C = np.sin(W * K + PH), np.cos(W * K + PH)
    print(f'{an}: w {W} rad/frame (period {2 * np.pi / W:.2f} frames = {2 * np.pi / W / 30:.3f} s), phase {np.degrees(PH):.1f} deg; '
          f'{parts0[jr]["n"]} bob {amp} px: {best[0]} of {len(K)} frames exact')
    rig = []
    for j in idx:
        p = parts0[j]
        q = {'n': p['n'], 'f': bool(p.get('f'))}
        w, h = Image.open(os.path.join(PARTS, p['n'] + '.png')).size
        cd, _ = lsq([np.ones_like(K), S, C], D[:, j])
        if float(np.hypot(cd[1], cd[2])) < 1.0:
            q['d'] = [float(round(D[:, j].mean())), 0.0, 0.0]
            q['x'], okx = bob_exact(X[:, j], S, C)
            q['y'], oky = bob_exact(Y[:, j], S, C)
            q['r'] = 1
            print(f'  {j:2d} {p["n"]}{"f" if q["f"] else " "} still  d {q["d"][0]:+.0f}  x {q["x"]} ({okx}/{len(K)})  y {q["y"]} ({oky}/{len(K)})')
        else:
            q['d'] = [float(round(cd[0])), float(snap(cd[1], 1)), float(snap(cd[2], 1))]
            dm = np.radians(q['d'][0] + q['d'][1] * S + q['d'][2] * C)
            co, si = np.cos(dm), np.sin(dm)
            Xc, Yc = X[:, j], Y[:, j]
            z, o = np.zeros_like(K), np.ones_like(K)
            best = None
            for basis in ('S', 'C'):
                B = S if basis == 'S' else C
                A = np.concatenate([np.stack([o, z, B, z, co, -si], 1), np.stack([z, o, z, B, si, co], 1)])
                c, *_ = np.linalg.lstsq(A, np.concatenate([Xc, Yc]), rcond=None)
                res = float(np.sqrt(np.mean((A @ c - np.concatenate([Xc, Yc])) ** 2)))
                if best is None or res < best[0]:
                    best = (res, basis, c)
            res, basis, c = best
            ox, oy = round(w / 2 - c[4] / SCALE), round(h / 2 - c[5] / SCALE)
            vx, vy = SCALE * (w / 2 - ox), SCALE * (h / 2 - oy)
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
            print(f'  {j:2d} {p["n"]}{"f" if q["f"] else " "} turns d {q["d"]} about sprite px ({ox}, {oy}) of {w}x{h}, at ({px}, {py}) + ({bx}, {by}) {basis}  centre error {err:.2f} px')
        ns = [n[j] for n in NAMES]
        if len(set(ns)) > 1:
            pos = max(set(ns), key=lambda n: sum(1 for a, s in zip(ns, S) if a == n and s > 0))
            neg = max(set(ns), key=lambda n: sum(1 for a, s in zip(ns, S) if a == n and s <= 0))
            bad = sum(1 for a, s in zip(ns, S) if a != (pos if s > 0 else neg))
            q['alt'] = [pos, neg]
            print(f'  {j:2d} two pictures: {pos} while S > 0, {neg} otherwise ({bad} of {len(ns)} disagree)')
        rig.append(q)
    actors.append({'name': an, 'w': W, 'ph': PH, 'parts': rig})


def url(name):
    b = io.BytesIO()
    Image.open(os.path.join(PARTS, name + '.png')).convert('RGBA').save(b, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


need = sorted({n for ns in NAMES for n in ns})
out = {'scale': SCALE, 'actors': actors, 'img': {n: url(n) for n in need}}
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(f'// generated by tools/make_rig.py from {os.path.basename(args[0])} - do not edit\n')
    f.write(f'window.MV_RIGS = window.MV_RIGS || {{}};\nwindow.MV_RIGS[{json.dumps(NAME)}] = ' + json.dumps(out, separators=(',', ':')) + ';\n')
print(OUT, os.path.getsize(OUT), 'bytes')
