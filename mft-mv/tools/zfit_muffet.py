"""Fit Muffet's whole rig to one recording frame by rendering it and comparing (tools/fit_muffet.py
fits parts one at a time; this one knows the draw order, so a part hidden behind another is not
blamed for what it cannot show).

The spec is a JSON list in draw order (back to front); each entry: n (part name), f (mirrored), d
(degrees), x, y (where its centre lands, game px), sub ([dx, dy] half-pixel offset), optional alt
(other part names to try in its place: the eyes' frames), fixd (never turned), wide (search far:
+-14 px, every angle by 3). Each round, every part in turn takes the placement that makes the
rendered rig agree best with the frame, the others held still.

usage: python tools/zfit_muffet.py <spec.json> [frame] [rounds] [out.json]
       -> work/muf/zfit_<frame>.png (frame white the rig misses: red; rig white the frame lacks: blue)
"""
import json
import sys

import numpy as np
from PIL import Image

import fit_muffet as fm

Y0, Y1, X0, X1 = 20, 248, 150, 500
_cache = {}


def shape(n, f, d, sub):
    key = (n, bool(f), round(d, 2), tuple(sub))
    if key not in _cache:
        sm, op, c = fm.rotated(n, f, d, sub)
        _cache[key] = (sm > 0, op, c)
    return _cache[key]


def place(p, **over):
    q = dict(p, **over)
    val, op, (cx, cy) = shape(q['n'], q.get('f', False), q.get('d', 0), tuple(q.get('sub', (0, 0))))
    return val, op, int(round(q['x'] - cx)) - X0, int(round(q['y'] - cy)) - Y0


def composite(parts):
    v = np.zeros((Y1 - Y0, X1 - X0), bool)
    o = np.zeros_like(v)
    for p in parts:
        val, op, x, y = place(p)
        h, w = op.shape
        sl = (slice(y, y + h), slice(x, x + w))
        v[sl][op] = val[op]
        o[sl] |= op
    return v, o


def fit_part(spec, i, frame):
    p = spec[i]
    bv, _ = composite(spec[:i])
    av, ao = composite(spec[i + 1:])
    val, op, x, y = place(p)
    h, w = op.shape
    wide = p.get('wide', False)
    m = 14 if wide else 4
    pad = m + 24
    wy0, wy1 = max(0, y - pad), min(Y1 - Y0, y + h + pad)
    wx0, wx1 = max(0, x - pad), min(X1 - X0, x + w + pad)
    fwin, bwin = frame[wy0:wy1, wx0:wx1], bv[wy0:wy1, wx0:wx1]
    awin, aowin = av[wy0:wy1, wx0:wx1], ao[wy0:wy1, wx0:wx1]
    d0 = p.get('d', 0)
    if p.get('fixd'):
        angles = [d0]
    elif wide:
        angles = list(range(-180, 180, 3))
    else:
        angles = [d0 + k for k in range(-8, 9)]
    subs = [(0, 0)] if wide else [(0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)]
    best = None
    for n in p.get('alt', [p['n']]):
        for d in angles:
            for sub in subs:
                cv, co, (cx, cy) = shape(n, p.get('f', False), d, sub)
                ch, cw = co.shape
                for dy in range(-m, m + 1):
                    for dx in range(-m, m + 1):
                        tx = int(round(p['x'] + dx - cx)) - X0 - wx0
                        ty = int(round(p['y'] + dy - cy)) - Y0 - wy0
                        if tx < 0 or ty < 0 or tx + cw > wx1 - wx0 or ty + ch > wy1 - wy0:
                            continue
                        canvas = bwin.copy()
                        sl = (slice(ty, ty + ch), slice(tx, tx + cw))
                        canvas[sl][co] = cv[co]
                        canvas[aowin] = awin[aowin]
                        err = int(np.count_nonzero(canvas != fwin))
                        if best is None or err < best[0]:
                            best = (err, n, d, sub, p['x'] + dx, p['y'] + dy)
    if best:
        err, n, d, sub, bx, by = best
        changed = (n, d, list(sub), bx, by) != (p['n'], d0, list(p.get('sub', (0, 0))), p['x'], p['y'])
        p.update(n=n, d=d, sub=list(sub), x=int(bx), y=int(by))
        p.pop('wide', None)
        return changed
    return False


def report(spec, frame, k):
    v, o = composite(spec)
    miss = frame & ~v
    extra = v & ~frame
    img = np.zeros(frame.shape + (3,), np.uint8)
    img[frame & v] = (120, 120, 120)
    img[miss] = (255, 60, 60)
    img[extra] = (60, 120, 255)
    Image.fromarray(img).resize(((X1 - X0) * 3, (Y1 - Y0) * 3), Image.NEAREST).save(f'work/muf/zfit_{k}.png')
    return int(miss.sum()), int(extra.sum())


def track(spec, k0, k1, out):
    """every frame from k0 to k1, each starting from the frame before's fit -> out (a list of specs)"""
    res = []
    for k in range(k0, k1):
        frame = fm.G[k][Y0:Y1, X0:X1] > 128
        for r in range(3):
            if not sum(fit_part(spec, i, frame) for i in range(len(spec))):
                break
        miss, extra = report(spec, frame, k) if k % 15 == 0 else (0, 0)
        v, _ = composite(spec)
        miss, extra = int((frame & ~v).sum()), int((v & ~frame).sum())
        res.append({'k': k, 'miss': miss, 'extra': extra, 'parts': json.loads(json.dumps(spec))})
        print(k, miss, extra, flush=True)
        json.dump(res, open(out, 'w'))


if __name__ == '__main__':
    if sys.argv[1] == 'track':
        track(json.load(open(sys.argv[2])), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
        sys.exit()
    spec = json.load(open(sys.argv[1]))
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    rounds = int(sys.argv[3]) if len(sys.argv) > 3 else 2
    out = sys.argv[4] if len(sys.argv) > 4 else sys.argv[1]
    frame = fm.G[k][Y0:Y1, X0:X1] > 128
    print('start: missed %d, extra %d' % report(spec, frame, k))
    for r in range(rounds):
        moved = 0
        for i in range(len(spec)):
            moved += fit_part(spec, i, frame)
        print(f'round {r + 1}: moved {moved}, missed %d, extra %d' % report(spec, frame, k))
        if not moved:
            break
    for p in spec:
        print(f"{p['n']}{' flip' if p.get('f') else ''} d={p.get('d', 0)} sub={p.get('sub', [0, 0])} ({p['x']},{p['y']})")
    json.dump(spec, open(out, 'w'), indent=0)
