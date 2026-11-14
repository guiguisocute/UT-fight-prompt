"""Fit Muffet's parts (work/muf/parts, the sheet's sprites at 2x) to the recording, frame by frame.

The recording (asset/record.mp4, 1920x1080) is the game's 640x480 screen scaled 2.25x with nearest
neighbour, so sampling it at game-pixel centres gives the game's own frame back
(work/muf/g/game.npy, made by the probe). Each part is matched as a signed mask (+1 white, -1 opaque
black, 0 clear) against the frame (+1 white, -1 black): the score is the mean agreement over the
part's opaque pixels (1 = a perfect match).

usage: python tools/fit_muffet.py peaks [frame]      # every part's best places in one frame
       python tools/fit_muffet.py track               # follow the rig's parts through all frames
"""
import json
import os
import sys

import numpy as np
from PIL import Image
from scipy.signal import fftconvolve

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
G = np.load('work/muf/g/game.npy').astype(np.float32)
F = np.where(G > 128, 1.0, -1.0)
REG = (0, 300, 150, 500)


def part(name, flip=False):
    a = np.array(Image.open(f'work/muf/parts/{name}.png').convert('RGBA'))
    if flip:
        a = a[:, ::-1]
    a = a.repeat(2, 0).repeat(2, 1)
    op = a[:, :, 3] > 0
    white = (a[:, :, 0] > 128) & op
    s = np.zeros(op.shape, np.float32)
    s[op] = -1
    s[white] = 1
    return s, op


def scoremap(frame, s, op):
    y0, y1, x0, x1 = REG
    f = frame[y0:y1, x0:x1]
    m = fftconvolve(f, s[::-1, ::-1], mode='valid') / op.sum()
    return m


def peaks(m, n=4, thr=0.6, rad=6):
    out, mm = [], m.copy()
    for _ in range(n):
        i = np.argmax(mm)
        y, x = np.unravel_index(i, mm.shape)
        v = mm[y, x]
        if v < thr:
            break
        out.append((int(x + REG[2]), int(y + REG[0]), round(float(v), 3)))
        mm[max(0, y - rad): y + rad + 1, max(0, x - rad): x + rad + 1] = -9
    return out


PARTS = [p['name'] for p in json.load(open('work/muf/parts/parts.json'))]
RING = False


def rotated(name, flip, deg, sub=(0.0, 0.0), wonly=False):
    """the part drawn the game's way: scaled 2x and turned by deg about its centre, each screen pixel
    taking the nearest texel (no smoothing) -> signed mask, opaque mask, and where the centre lands
    inside the returned box (cx, cy)"""
    a = np.array(Image.open(f'work/muf/parts/{name}.png').convert('RGBA'))
    if flip:
        a = a[:, ::-1]
    h, w = a.shape[:2]
    th = np.deg2rad(deg)
    c, s = np.cos(th), np.sin(th)
    R = int(np.ceil(np.hypot(w, h))) + 2
    ys, xs = np.mgrid[-R:R, -R:R].astype(np.float32)
    xs += 0.5 - sub[0]
    ys += 0.5 - sub[1]
    u = (c * xs + s * ys) / 2 + w / 2
    v = (-s * xs + c * ys) / 2 + h / 2
    iu, iv = np.floor(u).astype(int), np.floor(v).astype(int)
    ok = (iu >= 0) & (iv >= 0) & (iu < w) & (iv < h)
    px = np.zeros(xs.shape + (4,), np.uint8)
    px[ok] = a[iv[ok], iu[ok]]
    op = px[:, :, 3] > 0
    white = (px[:, :, 0] > 128) & op
    sm = np.zeros(op.shape, np.float32)
    sm[op] = -1
    sm[white] = 1
    if wonly:
        sm[~white] = 0
        op = white
    if RING:
        from scipy.ndimage import binary_dilation
        ring = binary_dilation(op, iterations=2) & ~op
        sm[ring] = -0.5
        op = op | ring
    ys2, xs2 = np.nonzero(op)
    if len(ys2) == 0:
        return sm, op, (R, R)
    y0, y1, x0, x1 = ys2.min(), ys2.max() + 1, xs2.min(), xs2.max() + 1
    return sm[y0:y1, x0:x1], op[y0:y1, x0:x1], (R - x0, R - y0)


def rot_search(frame, name, flip, angles, reg=None, wonly=False):
    """best (score, deg, centre x, centre y) over the angles, anywhere in reg (y0, y1, x0, x1)"""
    global REG
    keep = REG
    if reg:
        REG = reg
    best = []
    for d in angles:
        sm, op, (cx, cy) = rotated(name, flip, d, wonly=wonly)
        if op.sum() < 20 or sm.shape[0] > REG[1] - REG[0] or sm.shape[1] > REG[3] - REG[2]:
            continue
        m = scoremap(frame, sm, op)
        for x, y, v in peaks(m, n=3, thr=0.55, rad=5):
            best.append((v, d, x + cx, y + cy))
    REG = keep
    best.sort(reverse=True)
    out = []
    for b in best:
        if all(abs(b[2] - o[2]) > 6 or abs(b[3] - o[3]) > 6 for o in out):
            out.append(b)
        if len(out) == 4:
            break
    return out


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'peaks'
    if mode == 'peaks':
        k = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        for name in PARTS:
            for flip in (False, True):
                s, op = part(name, flip)
                if op.sum() < 20:
                    continue
                p = peaks(scoremap(F[k], s, op))
                if p:
                    print(f'{name}{" flip" if flip else ""}  {s.shape[1]}x{s.shape[0]}  ', p)
    elif mode == 'rot':
        k = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        names = sys.argv[3].split(',') if len(sys.argv) > 3 else ['3_0', '3_1', '3_2', '3_3', '3_4', '3_5', '3_6']
        SIDES = {'L': (95, 235, 195, 312), 'R': (95, 235, 328, 445)}
        for name in names:
            for flip in (False, True):
                for side, reg in SIDES.items():
                    r = rot_search(F[k], name, flip, range(-180, 180, 3), reg)
                    print(f'{name}{" flip" if flip else ""} {side}:', [(round(v, 3), d, int(x), int(y)) for v, d, x, y in r[:3]])
    elif mode == 'rotw':
        k = int(sys.argv[2]); name = sys.argv[3]; reg = tuple(int(v) for v in sys.argv[4].split(','))
        w = len(sys.argv) > 5 and sys.argv[5] == 'w'
        for flip in (False, True):
            r = rot_search(F[k], name, flip, range(-180, 180, 2), reg, wonly=w)
            print(f'{name}{" flip" if flip else ""}:', [(round(v, 3), d, int(x), int(y)) for v, d, x, y in r[:4]])
    elif mode == 'compose':
        spec = json.load(open(sys.argv[2]))
        k = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        f = G[k] > 128
        cover = np.zeros(f.shape, bool)
        img = np.zeros(f.shape + (3,), np.uint8)
        img[f] = (70, 70, 70)
        pal = [(255, 80, 80), (80, 255, 80), (80, 140, 255), (255, 220, 60), (255, 80, 255), (60, 255, 255), (255, 150, 60), (180, 120, 255)]
        for i, p in enumerate(spec):
            sm, op, (cx, cy) = rotated(p['n'], p.get('f', False), p.get('d', 0), tuple(p.get('sub', (0, 0))))
            x0, y0 = int(round(p['x'] - cx)), int(round(p['y'] - cy))
            ys, xs = np.nonzero(sm > 0)
            ys, xs = ys + y0, xs + x0
            ok = (ys >= 0) & (xs >= 0) & (ys < f.shape[0]) & (xs < f.shape[1])
            col = np.array(pal[i % len(pal)])
            img[ys[ok], xs[ok]] = np.where(f[ys[ok], xs[ok]][:, None], col, col // 3)
            cover[ys[ok], xs[ok]] = True
        y0, y1, x0, x1 = REG
        miss = f[y0:y1, x0:x1] & ~cover[y0:y1, x0:x1]
        print('white pixels', int(f[y0:y1, x0:x1].sum()), 'unexplained', int(miss.sum()))
        out = Image.fromarray(img[y0:y1, x0:x1]).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.NEAREST)
        out.save(f'work/muf/compose_{k}.png')
    elif mode == 'refine':
        spec = json.load(open(sys.argv[2]))
        k = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        out_path = sys.argv[4] if len(sys.argv) > 4 else sys.argv[2]
        fr = F[k]
        for p in spec:
            names = p.get('alt', [p['n']])
            best = None
            d0 = p.get('d', 0)
            angles = [d0] if p.get('fixd') else [d0 + i for i in range(-6, 7)]
            for n in names:
                for d in angles:
                    for sub in ((0, 0), (0.5, 0), (0, 0.5), (0.5, 0.5)):
                        sm, op, (cx, cy) = rotated(n, p.get('f', False), d, sub, wonly=p.get('w', False))
                        X0, Y0 = int(round(p['x'] - cx)), int(round(p['y'] - cy))
                        h, w = sm.shape
                        win = fr[Y0 - 4: Y0 + h + 4, X0 - 4: X0 + w + 4]
                        if win.shape != (h + 8, w + 8):
                            continue
                        m = fftconvolve(win, sm[::-1, ::-1], mode='valid') / op.sum()
                        j = np.unravel_index(np.argmax(m), m.shape)
                        v = float(m[j])
                        if best is None or v > best[0]:
                            best = (v, n, d, sub, p['x'] + j[1] - 4, p['y'] + j[0] - 4)
            v, n, d, sub, x, y = best
            p.update(n=n, d=d, sub=list(sub), x=int(x), y=int(y), score=round(v, 3))
            print(f"{n}{' flip' if p.get('f') else ''} d={d} sub={sub} at ({x},{y})  {v:.3f}")
        json.dump(spec, open(out_path, 'w'), indent=0)
    elif mode == 'resid':
        spec = json.load(open(sys.argv[2]))
        k = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        f = G[k] > 128
        cover = np.zeros(f.shape, bool)
        who = np.full(f.shape, -1)
        for i, p in enumerate(spec):
            sm, op, (cx, cy) = rotated(p['n'], p.get('f', False), p.get('d', 0), tuple(p.get('sub', (0, 0))))
            x0, y0 = int(round(p['x'] - cx)), int(round(p['y'] - cy))
            ys, xs = np.nonzero(op)
            cover[ys + y0, xs + x0] = True
            ys, xs = np.nonzero(sm > 0)
            who[ys + y0, xs + x0] = i
        reg = [int(v) for v in sys.argv[4].split(',')] if len(sys.argv) > 4 else (100, 240, 220, 430)
        y0, y1, x0, x1 = reg
        img = np.zeros((y1 - y0, x1 - x0, 3), np.uint8)
        ff, cc = f[y0:y1, x0:x1], cover[y0:y1, x0:x1]
        pal = np.array([(110, 110, 110), (70, 110, 150), (150, 110, 70), (90, 140, 90), (140, 90, 140), (80, 140, 140)])
        ww = who[y0:y1, x0:x1]
        img[ff & cc] = pal[ww[ff & cc] % len(pal)]
        img[ff & cc & (ww < 0)] = (60, 60, 60)
        img[ff & ~cc] = (255, 60, 60)
        out = Image.fromarray(img).resize(((x1 - x0) * 4, (y1 - y0) * 4), Image.NEAREST)
        from PIL import ImageDraw
        dr = ImageDraw.Draw(out)
        for gx in range(x0, x1, 10):
            dr.line([((gx - x0) * 4, 0), ((gx - x0) * 4, 6)], fill=(0, 200, 255))
            if gx % 50 == 0:
                dr.text(((gx - x0) * 4 + 2, 8), str(gx), fill=(0, 200, 255))
        for gy in range(y0, y1, 10):
            dr.line([(0, (gy - y0) * 4), (6, (gy - y0) * 4)], fill=(0, 200, 255))
            if gy % 50 == 0:
                dr.text((8, (gy - y0) * 4 + 2), str(gy), fill=(0, 200, 255))
        out.save(f'work/muf/resid_{k}.png')
        print('unexplained', int((ff & ~cc).sum()))
    elif mode == 'hair':
        k = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        for flip in (False, True):
            for side, reg in {'L': (15, 95, 235, 305), 'R': (15, 95, 335, 405)}.items():
                r = rot_search(F[k], '0_1', flip, range(-180, 180, 3), reg)
                print(f'0_1{" flip" if flip else ""} {side}:', [(round(v, 3), d, int(x), int(y)) for v, d, x, y in r[:3]])
