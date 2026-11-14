#!/usr/bin/env python3
"""Undyne the Undying's puppet, fitted on the game's own picture and on the recording.

    .venv/Scripts/python tools/fit_undying.py rest
    .venv/Scripts/python tools/fit_undying.py track <frames dir> [t0] [fps]

rest: the sheet's parts (hand 128, spear arm 129, torso 130, arm 131, belt 132, legs 133, head 135)
are placed in 'Undying - Body' (slice_sheet.frames('boss')[0] - the game's own assembled figure)
where most of their pixels agree; which part lies over which is read off their overlaps; what no
part explains is her hair (the white flame). Prints the table; writes work/undying_rest.png (the
figure | rebuilt from the parts | what differs) and work/undying_rest.json.

track: frames of the recording cut by ffmpeg (a crop of her: the game is 1.5x in the 1080 x 720
video, so one sprite px = 3 video px), e.g.
    ffmpeg -ss 236 -t 6 -i asset/record.mp4 -vf crop=330:390:375:0 work/review/rec/idle/i_%03d.png
each part is found near its rest place by correlation; prints per frame every part's offset from
rest (sprite px) and fits each one a sine of the head's period (amplitude, phase).
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy.signal import fftconvolve

sys.path.insert(0, os.path.dirname(__file__))
import slice_sheet as S

PARTS = [('hand', 128), ('spear', 129), ('torso', 130), ('arm', 131), ('belt', 132), ('legs', 133), ('head', 135)]


def classes(img):
    """0 clear, 1 white, 2 black (opaque)"""
    a = img[..., 3] >= 128
    lum = img[..., :3].astype(int).sum(-1) / 3
    c = np.zeros(img.shape[:2], np.int8)
    c[a & (lum >= 128)] = 1
    c[a & (lum < 128)] = 2
    return c


def load():
    cs, _ = S.cells('boss')
    comp = S.frames('boss')[0]['img']
    return cs, comp


def place(C, P):
    """the offset (x, y) of part P in figure C where their white line art agrees most: the figure
    is white lines on black (its outer black cut away as screen), so black and clear count alike;
    the part's white over the figure's dark costs, so does its solid black over the figure's white"""
    ph, pw = P.shape
    H, W = C.shape
    Cw = np.zeros((H + 2 * ph, W + 2 * pw), np.int8)
    Cw[ph:ph + H, pw:pw + W] = C == 1
    Pw, Pk = (P == 1).astype(np.int8), (P == 2).astype(np.int8)
    # (correlations over every offset at once)
    hit = fftconvolve(Cw, Pw[::-1, ::-1], mode='valid')
    miss = Pw.sum() - hit
    over = fftconvolve(Cw, Pk[::-1, ::-1], mode='valid')
    s = hit - 0.5 * miss - 0.5 * over
    oy, ox = np.unravel_index(np.argmax(s), s.shape)
    return (int(ox) - pw, int(oy) - ph), int(round(s[oy, ox]))


def rest():
    cs, comp = load()
    C = classes(comp)
    H, W = C.shape
    out = {}
    for name, idx in PARTS:
        P = classes(cs[idx]['img'])
        (x, y), s = place(C, P)
        out[name] = dict(cell=idx, x=x, y=y, w=P.shape[1], h=P.shape[0], score=s, n=int((P > 0).sum()))
        print(f'{name:6s} cell {idx}: at ({x:3d}, {y:3d})  {P.shape[1]}x{P.shape[0]}  agree {s} of {(P > 0).sum()}')
    # who lies over whom: in an overlap, the part whose pixels the figure shows is on top
    names = [n for n, _ in PARTS]
    above = {n: set() for n in names}  # above[n]: the parts n lies over
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A = np.zeros((H, W), np.int8); B = np.zeros((H, W), np.int8)
            for n, M in ((a, A), (b, B)):
                o = out[n]; P = classes(cs[o['cell']]['img'])
                y0, x0 = max(0, o['y']), max(0, o['x'])
                y1, x1 = min(H, o['y'] + o['h']), min(W, o['x'] + o['w'])
                M[y0:y1, x0:x1] = P[y0 - o['y']:y1 - o['y'], x0 - o['x']:x1 - o['x']]
            both = (A > 0) & (B > 0)
            if both.sum() == 0:
                continue
            Cw = C == 1
            ka, kb = int((((A == 1) == Cw) & both).sum()), int((((B == 1) == Cw) & both).sum())
            top, low = (a, b) if ka > kb else (b, a)
            above[top].add(low)
            print(f'  {a} / {b}: overlap {both.sum():4d}  {a} agrees {ka}, {b} agrees {kb} -> {top} on top')
    # back to front: a part comes after everything it lies over
    order, todo = [], list(names)
    while todo:
        n = next(n for n in todo if above[n] <= set(order))
        order.append(n); todo.remove(n)
    print('back to front:', order)
    # rebuild, and what is left over (the hair)
    R = np.zeros((H, W), np.int8)
    cover = np.zeros((H, W), bool)
    for n in order:
        o = out[n]; P = classes(cs[o['cell']]['img'])
        y0, x0 = max(0, o['y']), max(0, o['x'])
        y1, x1 = min(H, o['y'] + o['h']), min(W, o['x'] + o['w'])
        sub = P[y0 - o['y']:y1 - o['y'], x0 - o['x']:x1 - o['x']]
        m = sub > 0
        R[y0:y1, x0:x1][m] = sub[m]
        cover[y0:y1, x0:x1] |= m
    left = (C == 1) & ~cover
    wrong = ((R == 1) != (C == 1)) & cover
    print(f'figure px {int((C > 0).sum())}, rebuilt {int((R > 0).sum())}, left over {int(left.sum())}, disagree {int(wrong.sum())}')
    ys, xs = np.nonzero(left)
    if len(ys):
        print(f'left over: x {xs.min()}..{xs.max()}  y {ys.min()}..{ys.max()}')
    pal = np.array([[0, 0, 0], [255, 255, 255], [70, 70, 70]], np.uint8)
    a, b = pal[C], pal[R]
    d = np.zeros((H, W, 3), np.uint8)
    d[left] = [255, 60, 60]
    d[wrong] = [60, 160, 255]
    vis = np.concatenate([a, np.full((H, 4, 3), 90, np.uint8), b, np.full((H, 4, 3), 90, np.uint8), d], 1)
    Image.fromarray(vis).resize((vis.shape[1] * 4, H * 4), Image.NEAREST).save('work/undying_rest.png')
    json.dump(dict(parts=out, order=order, size=[W, H]), open('work/undying_rest.json', 'w'), indent=1)
    # the hair alone (white where the figure has it, clear elsewhere), cropped
    if len(ys):
        y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
        hair = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        hair[left[y0:y1, x0:x1]] = [255, 255, 255, 255]
        print(f'hair box ({x0}, {y0}) {x1 - x0}x{y1 - y0}')


def track(d, t0=0.0, fps=30.0):
    cs, comp = load()
    rest = json.load(open('work/undying_rest.json'))
    fs = sorted(f for f in os.listdir(d) if f.endswith('.png'))
    grey = lambda f: np.asarray(Image.open(os.path.join(d, f)).convert('L')).astype(float) / 255
    tmpl = lambda C: np.kron(np.where(C == 1, 1.0, np.where(C == 2, -0.7, 0.0)), np.ones((3, 3)))
    # where the figure sits in the first frame (its rest origin, video px), from the torso
    G0 = grey(fs[0])
    tp = rest['parts']['torso']
    sc = fftconvolve(G0 - G0.mean(), tmpl(classes(cs[tp['cell']]['img']))[::-1, ::-1], mode='valid')
    oy, ox = np.unravel_index(np.argmax(sc), sc.shape)
    ox, oy = int(ox) - 3 * tp['x'], int(oy) - 3 * tp['y']
    print(f'figure origin in the crop: ({ox}, {oy}) video px')
    names = [n for n, _ in PARTS]
    T = {n: tmpl(classes(cs[rest['parts'][n]['cell']]['img'])) for n in names}
    R = 15  # search radius, video px
    rows = []
    for k, f in enumerate(fs):
        G = grey(f)
        G = G - G.mean()
        row = {}
        for n in names:
            p = rest['parts'][n]
            ex, ey = ox + 3 * p['x'], oy + 3 * p['y']
            x0, y0 = max(0, ex - R), max(0, ey - R)
            th, tw = T[n].shape
            win = G[y0:ey + R + th, x0:ex + R + tw]
            s = fftconvolve(win, T[n][::-1, ::-1], mode='valid')
            j, i = np.unravel_index(np.argmax(s), s.shape)
            # (sub-pixel: a parabola through the peak's neighbours)
            def sub(a, m):
                return 0.0 if m <= 0 or m >= len(a) - 1 else 0.5 * (a[m - 1] - a[m + 1]) / (a[m - 1] - 2 * a[m] + a[m + 1] + 1e-9)
            fx = i + sub(s[j], i)
            fy = j + sub(s[:, i], j)
            row[n] = ((x0 + fx - ex) / 3, (y0 + fy - ey) / 3)
        rows.append(row)
        print(f'{k:3d} t={t0 + k / fps:8.3f} ' + ' '.join(f'{n}({row[n][0]:+5.2f},{row[n][1]:+5.2f})' for n in names))
    # the period from the head's height, then a sine per coordinate
    hy = np.array([r['head'][1] for r in rows])
    hy = hy - hy.mean()
    ac = np.correlate(hy, hy, 'full')[len(hy) - 1:]
    lag = int(np.argmax(ac[8:60])) + 8
    per = lag / fps
    print(f'period ~ {per:.3f} s ({lag} frames)')
    tt = np.arange(len(rows)) / fps
    w = 2 * np.pi / per
    M = np.stack([np.sin(w * tt), np.cos(w * tt), np.ones_like(tt)], 1)
    fit = {}
    for n in names:
        for c, ax in ((0, 'x'), (1, 'y')):
            v = np.array([r[n][c] for r in rows])
            (a, b, m), *_ = np.linalg.lstsq(M, v, rcond=None)
            amp, ph = float(np.hypot(a, b)), float(np.arctan2(b, a))
            res = float(np.sqrt(np.mean((M @ np.array([a, b, m]) - v) ** 2)))
            fit[f'{n}.{ax}'] = dict(amp=round(amp, 3), phase=round(ph, 3), mean=round(float(m), 3), rms=round(res, 3))
            print(f'{n:6s} {ax}: amp {amp:5.2f} px  phase {ph:+5.2f} rad  mean {m:+5.2f}  residual {res:4.2f}')
    json.dump(dict(period=per, fit=fit, rows=rows), open('work/undying_track.json', 'w'), indent=1)


def hair(d, n=12):
    """her hair per frame, sampled at sprite px (the centre of each 3 x 3 video block), riding on
    the head: printed as rows of '#' so its animation can be read (after `track` on the same dir)"""
    cs, comp = load()
    rest = json.load(open('work/undying_rest.json'))
    tr = json.load(open('work/undying_track.json'))
    fs = sorted(f for f in os.listdir(d) if f.endswith('.png'))
    G0 = np.asarray(Image.open(os.path.join(d, fs[0])).convert('L')).astype(float) / 255
    tp = rest['parts']['torso']
    T = np.kron(np.where(classes(cs[tp['cell']]['img']) == 1, 1.0, np.where(classes(cs[tp['cell']]['img']) == 2, -0.7, 0.0)), np.ones((3, 3)))
    sc = fftconvolve(G0 - G0.mean(), T[::-1, ::-1], mode='valid')
    oy, ox = np.unravel_index(np.argmax(sc), sc.shape)
    ox, oy = int(ox) - 3 * tp['x'], int(oy) - 3 * tp['y']
    X0, X1, Y0, Y1 = 4, 52, 12, 40  # the box round the hair, sprite px (composite space)
    out = []
    for k, f in enumerate(fs[:n]):
        G = np.asarray(Image.open(os.path.join(d, f)).convert('L')).astype(float)
        hx, hy = tr['rows'][k]['head']
        hy -= tr['rows'][k]['legs'][1]
        rows = []
        for y in range(Y0, Y1):
            s = ''
            for x in range(X0, X1):
                vx, vy = ox + 3 * x + 1, oy + int(round(3 * (y + hy))) + 1
                v = G[vy, vx] if 0 <= vy < G.shape[0] and 0 <= vx < G.shape[1] else 0
                s += '#' if v > 110 else '.'
            rows.append(s)
        out.append(rows)
        print(f'frame {k} (head dy {hy:+.2f})')
        print('\n'.join(rows))


def data():
    """src/und_data.js: the rest placements and their order, the hair (what no part explains, its
    own picture: asset/drawn/und_hair.png), her eye, and one cycle of the idle (game px from rest,
    the legs held still: the median over every cycle tracked) - from work/undying_rest.json and
    work/undying_track.json"""
    cs, comp = load()
    rest = json.load(open('work/undying_rest.json'))
    tr = json.load(open('work/undying_track.json'))
    C = classes(comp)
    H, W = C.shape
    cover = np.zeros((H, W), bool)
    for n, o in rest['parts'].items():
        P = classes(cs[o['cell']]['img'])
        y0, x0 = max(0, o['y']), max(0, o['x'])
        y1, x1 = min(H, o['y'] + o['h']), min(W, o['x'] + o['w'])
        cover[y0:y1, x0:x1] |= P[y0 - o['y']:y1 - o['y'], x0 - o['x']:x1 - o['x']] > 0
    left = (C == 1) & ~cover
    ys, xs = np.nonzero(left)
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    hair = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
    hair[left[y0:y1, x0:x1]] = [255, 255, 255, 255]
    os.makedirs('asset/sprites/drawn', exist_ok=True)
    Image.fromarray(hair).save('asset/sprites/drawn/und_hair.png')
    head = rest['parts']['head']
    # one cycle of the idle: per part, (dx, dy) in game px (= world px at the game's 2x), relative to
    # the legs, the median of every tracked cycle
    rows, per = tr['rows'], tr['period']
    n = int(round(per * 30))
    names = [p for p, _ in PARTS]
    idle = {}
    for p in names:
        cyc = []
        for k in range(n):
            vs = [(rows[j][p][0] - rows[j]['legs'][0], rows[j][p][1] - rows[j]['legs'][1]) for j in range(k, len(rows), n)]
            dx = float(np.median([v[0] for v in vs])) * 2
            dy = float(np.median([v[1] for v in vs])) * 2
            cyc.append([int(round(dx)), int(round(dy))])
        # (relative to the cycle's own mean: rest is where the sheet's composite has it)
        mx = round(np.mean([c[0] for c in cyc])); my = round(np.mean([c[1] for c in cyc]))
        idle[p] = [[c[0] - mx, c[1] - my] for c in cyc]
    legs = rest['parts']['legs']
    out = dict(
        size=[W, H],
        parts={p: dict(img=f'und/u_{p}', x=o['x'], y=o['y']) for p, o in rest['parts'].items()},
        order=rest['order'],
        hair=dict(img='drawn/und_hair', x=x0, y=y0, on='head'),
        # her left eye (the patch's side, on screen the right one): where the recording's beam starts
        # - the middle of that socket, head px (26, 15) (work/review/rec/beam_grid.png, 1:33.6)
        eye=[head['x'] + 26, head['y'] + 15],
        feet=[legs['x'] + legs['w'] // 2, legs['y'] + legs['h']],
        idle=dict(period=round(per, 4), n=n, parts=idle),
    )
    with open('src/und_data.js', 'w') as f:
        f.write('// Generated by tools/fit_undying.py data - do not edit. Undyne the Undying\'s puppet: the sheet\'s\n')
        f.write('// parts where the game\'s own composite has them (sprite px), back to front; her hair (the part no\n')
        f.write('// sheet cell explains); her eye; and one cycle of her idle measured off the recording (game px).\n')
        f.write('window.MV_UND = ')
        json.dump(out, f, separators=(',', ':'))
        f.write(';\n')
    print('src/und_data.js: hair', (x0, y0, x1 - x0, y1 - y0), 'idle frames', n)
    for p in names:
        print(f'{p:6s}', ' '.join(f'{a:+d},{b:+d}' for a, b in idle[p]))


if __name__ == '__main__':
    if sys.argv[1] == 'rest':
        rest()
    elif sys.argv[1] == 'data':
        data()
    elif sys.argv[1] == 'hair':
        hair(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 12)
    else:
        track(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0.0, float(sys.argv[4]) if len(sys.argv) > 4 else 30.0)
