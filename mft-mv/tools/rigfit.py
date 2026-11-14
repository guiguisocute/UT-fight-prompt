"""Fit a sprite rig to frames by rendering it and comparing (tools/zfit_muffet.py, generalised: any
parts folder, any scale, frames from a .npy of game frames or from a picture's white pixels).

A spec is a JSON list in draw order (back to front); each entry: n (part name in the parts folder), f
(mirrored), d (degrees), x, y (where its centre lands, frame px), sub ([dx, dy]), optional alt (other
part names to try in its place), fixd (never turned), wide (search far: +-R px, every angle by 3;
R from the entry's "wide" if a number, else 14). Each round every part in turn takes the placement
that makes the whole rendered rig agree best with the frame (white = 1), the others held still.

usage: python -I tools/rigfit.py fit <spec.json> --frames=<.npy|.png> [--k=0] [--parts=dir] [--scale=2]
           [--rounds=3] [--out=spec.json] [--png=report.png]
       python -I tools/rigfit.py find <name> --frames=... [--parts=dir] [--scale=2] [--rot]
           (one part's best places anywhere in the frame; --rot: every angle by 3)
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy.signal import fftconvolve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_frames(path):
    """-> bool array (n, h, w): white"""
    if path.endswith('.npy'):
        return np.load(path) > 128
    a = np.array(Image.open(path).convert('RGB'))
    return (np.all(a == 255, axis=2))[None]


class Parts:
    def __init__(self, folder, scale=2):
        self.folder, self.scale, self.cache, self.img = folder, scale, {}, {}

    def rgba(self, n):
        if n not in self.img:
            self.img[n] = np.array(Image.open(os.path.join(self.folder, n + '.png')).convert('RGBA'))
        return self.img[n]

    def shape(self, n, f=False, d=0.0, sub=(0, 0)):
        """the part drawn the game's way: scaled, turned by d about its centre, nearest texel ->
        (white mask, opaque mask, centre (cx, cy) inside the returned box)"""
        key = (n, bool(f), round(float(d), 2), tuple(sub))
        if key in self.cache:
            return self.cache[key]
        a = self.rgba(n)
        if f:
            a = a[:, ::-1]
        h, w = a.shape[:2]
        sc = self.scale
        th = np.deg2rad(d)
        c, s = np.cos(th), np.sin(th)
        R = int(np.ceil(np.hypot(w, h) * sc / 2)) + 2
        ys, xs = np.mgrid[-R:R, -R:R].astype(np.float32)
        xs += 0.5 - sub[0]
        ys += 0.5 - sub[1]
        u = (c * xs + s * ys) / sc + w / 2
        v = (-s * xs + c * ys) / sc + h / 2
        iu, iv = np.floor(u).astype(int), np.floor(v).astype(int)
        ok = (iu >= 0) & (iv >= 0) & (iu < w) & (iv < h)
        px = np.zeros(xs.shape + (4,), np.uint8)
        px[ok] = a[iv[ok], iu[ok]]
        op = px[:, :, 3] > 0
        white = (px[:, :, 0] > 128) & (px[:, :, 1] > 128) & op
        yy, xx = np.nonzero(op)
        if len(yy) == 0:
            out = (white, op, (R, R))
        else:
            y0, y1, x0, x1 = yy.min(), yy.max() + 1, xx.min(), xx.max() + 1
            out = (white[y0:y1, x0:x1], op[y0:y1, x0:x1], (R - x0, R - y0))
        self.cache[key] = out
        return out


def place(P, p):
    val, op, (cx, cy) = P.shape(p['n'], p.get('f', False), p.get('d', 0), tuple(p.get('sub', (0, 0))))
    return val, op, int(round(p['x'] - cx)), int(round(p['y'] - cy))


def composite(P, parts, shape):
    v = np.zeros(shape, bool)
    o = np.zeros(shape, bool)
    H, W = shape
    for p in parts:
        val, op, x, y = place(P, p)
        h, w = op.shape
        ys, xs = slice(max(0, y), min(H, y + h)), slice(max(0, x), min(W, x + w))
        vs = (slice(ys.start - y, ys.stop - y), slice(xs.start - x, xs.stop - x))
        m = op[vs]
        v[ys, xs][m] = val[vs][m]
        o[ys, xs] |= m
    return v, o


def fit_part(P, spec, i, frame):
    p = spec[i]
    H, W = frame.shape
    bv, _ = composite(P, spec[:i], frame.shape)
    av, ao = composite(P, spec[i + 1:], frame.shape)
    val, op, x, y = place(P, p)
    h, w = op.shape
    wide = p.get('wide', False)
    m = (wide if isinstance(wide, (int, float)) and not isinstance(wide, bool) else 14) if wide else 4
    pad = m + 24
    wy0, wy1, wx0, wx1 = max(0, y - pad), min(H, y + h + pad), max(0, x - pad), min(W, x + w + pad)
    fwin, bwin, awin, aowin = frame[wy0:wy1, wx0:wx1], bv[wy0:wy1, wx0:wx1], av[wy0:wy1, wx0:wx1], ao[wy0:wy1, wx0:wx1]
    d0 = p.get('d', 0)
    angles = [d0] if p.get('fixd') else (list(range(-180, 180, 3)) if wide else [d0 + k for k in range(-8, 9)])
    subs = [(0, 0)] if wide else [(0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)]
    best = None
    for n in p.get('alt', [p['n']]):
        for d in angles:
            for sub in subs:
                cv, co, (cx, cy) = P.shape(n, p.get('f', False), d, sub)
                ch, cw = co.shape
                for dy in range(-m, m + 1):
                    for dx in range(-m, m + 1):
                        tx = int(round(p['x'] + dx - cx)) - wx0
                        ty = int(round(p['y'] + dy - cy)) - wy0
                        # (clipped to the window: a piece reaching off the screen - RG02's sword - is
                        # judged by what is on it)
                        ya, yb, xa, xb = max(0, ty), min(wy1 - wy0, ty + ch), max(0, tx), min(wx1 - wx0, tx + cw)
                        if yb - ya < ch // 2 or xb - xa < cw // 2:
                            continue
                        canvas = bwin.copy()
                        sco = co[ya - ty:yb - ty, xa - tx:xb - tx]
                        canvas[ya:yb, xa:xb][sco] = cv[ya - ty:yb - ty, xa - tx:xb - tx][sco]
                        canvas[aowin] = awin[aowin]
                        err = int(np.count_nonzero(canvas != fwin))
                        if best is None or err < best[0]:
                            best = (err, n, d, sub, p['x'] + dx, p['y'] + dy)
    if not best:
        return False
    err, n, d, sub, bx, by = best
    changed = (n, d, list(sub), bx, by) != (p['n'], d0, list(p.get('sub', (0, 0))), p['x'], p['y'])
    p.update(n=n, d=d, sub=list(sub), x=int(bx), y=int(by))
    p.pop('wide', None)
    return changed


def report(P, spec, frame, png=None, scale=3):
    v, _ = composite(P, spec, frame.shape)
    miss, extra = frame & ~v, v & ~frame
    if png:
        img = np.zeros(frame.shape + (3,), np.uint8)
        img[frame & v] = (120, 120, 120)
        img[miss] = (255, 60, 60)
        img[extra] = (60, 120, 255)
        Image.fromarray(img).resize((frame.shape[1] * scale, frame.shape[0] * scale), Image.NEAREST).save(png)
    return int(miss.sum()), int(extra.sum())


def find(P, frame, n, rot=False, flips=(False, True), top=4):
    """a part's best places anywhere: (score, flip, deg, centre x, centre y); score = mean agreement
    over its opaque pixels (white +1, black -1 against the frame's white +1 / not -1)"""
    F = np.where(frame, 1.0, -1.0)
    out = []
    for f in flips:
        for d in (range(-180, 180, 3) if rot else [0]):
            val, op, (cx, cy) = P.shape(n, f, d)
            if op.sum() < 10 or op.shape[0] > F.shape[0] or op.shape[1] > F.shape[1]:
                continue
            s = np.where(val, 1.0, -1.0) * op
            m = fftconvolve(F, s[::-1, ::-1], mode='valid') / op.sum()
            mm = m.copy()
            for _ in range(top):
                j = np.unravel_index(np.argmax(mm), mm.shape)
                out.append((round(float(mm[j]), 3), f, d, int(j[1] + cx), int(j[0] + cy)))
                mm[max(0, j[0] - 6): j[0] + 7, max(0, j[1] - 6): j[1] + 7] = -9
    out.sort(reverse=True)
    keep = []
    for o in out:
        if all(abs(o[3] - k[3]) > 6 or abs(o[4] - k[4]) > 6 for k in keep):
            keep.append(o)
        if len(keep) == top:
            break
    return keep


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    opts = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
    P = Parts(opts.get('parts', 'work/muf/parts'), float(opts.get('scale', 2)))
    frames = load_frames(opts['frames'])
    frame = frames[int(opts.get('k', 0))]
    if args[0] == 'find':
        for name in args[1].split(','):
            print(name, find(P, frame, name, rot='rot' in opts))
    elif args[0] == 'fit':
        spec = json.load(open(args[1]))
        out = opts.get('out', args[1])
        print('start: missed %d, extra %d' % report(P, spec, frame))
        for r in range(int(opts.get('rounds', 3))):
            moved = sum(fit_part(P, spec, i, frame) for i in range(len(spec)))
            print(f'round {r + 1}: moved {moved}, missed %d, extra %d' % report(P, spec, frame, opts.get('png')))
            if not moved:
                break
        for p in spec:
            print(f"{p['n']}{' flip' if p.get('f') else ''} d={p.get('d', 0)} sub={p.get('sub', [0, 0])} ({p['x']},{p['y']})")
        json.dump(spec, open(out, 'w'), indent=0)
    elif args[0] == 'track':
        # rigfit.py track <spec.json> --frames=.npy --out=track.json [--k0 --k1]: every frame, each
        # starting from the one before's fit
        spec = json.load(open(args[1]))
        k0, k1 = int(opts.get('k0', 0)), int(opts.get('k1', len(frames)))
        res = []
        for k in range(k0, k1):
            fr = frames[k]
            for r in range(3):
                if not sum(fit_part(P, spec, i, fr) for i in range(len(spec))):
                    break
            miss, extra = report(P, spec, fr)
            res.append({'k': k, 'miss': miss, 'extra': extra, 'parts': json.loads(json.dumps(spec))})
            print(k, miss, extra, flush=True)
            json.dump(res, open(opts['out'], 'w'))
