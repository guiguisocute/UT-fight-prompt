"""The game's own frames out of a recording. asset/record.mp4 is the 640 x 480 screen scaled 2.25x
(nearest neighbour) into 1920 x 1080 at x 240: sampling each game pixel's centre gives the game's
frame back. Other captures sit differently and are smoothed: --grid=x0,y0,sx,sy puts game pixel
(gx, gy)'s centre at video (x0 + (gx + 0.5) sx, y0 + (gy + 0.5) sy), read bilinearly (the guards'
XEPHIROX captures: 237.55,-2.93,2.2587,2.2626 - measured off the battle box's edges).
-> a .npy (frames x 480 x 640, uint8 grey), on the game's 30 fps clock.

usage: python tools/rec_game.py <t0 s> <t1 s> <out.npy> [y0,y1,x0,x1 (game px crop)] [--video=path]
       [--grid=x0,y0,sx,sy] [--white]
"""
import os
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
opts = dict((a[2:].split('=', 1) + [True])[:2] for a in sys.argv[1:] if a.startswith('--'))
VIDEO = opts.get('video', os.path.join(ROOT, 'asset', 'record', 'record.mp4'))
args = [a for a in sys.argv[1:] if not a.startswith('--')]
t0, t1, out = float(args[0]), float(args[1]), args[2]
gy0, gy1, gx0, gx1 = (int(a) for a in args[3].split(',')) if len(args) > 3 else (0, 480, 0, 640)
W, H = 1920, 1080
# (--white: the darkest of r, g, b instead of grey - only white stays bright; the guards' battle
# grid is green, which grey would count as white)
WHITE = 'white' in opts
CH = 3 if WHITE else 1
# (-r 30: the game's frame rate - a 29.97 fps capture is put back on the game's clock)
cmd = ['ffmpeg', '-v', 'error', '-ss', f'{t0}', '-i', VIDEO, '-t', f'{t1 - t0}', '-r', '30',
       '-f', 'rawvideo', '-pix_fmt', 'rgb24' if WHITE else 'gray', '-']
if 'grid' in opts:
    X0, Y0, SX, SY = (float(v) for v in opts['grid'].split(','))
    xs = np.clip(X0 + (np.arange(gx0, gx1) + 0.5) * SX - 0.5, 0, W - 1.001)
    ys = np.clip(Y0 + (np.arange(gy0, gy1) + 0.5) * SY - 0.5, 0, H - 1.001)
    xi, yi = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = (xs - xi)[None, :], (ys - yi)[:, None]

    def grab(v):
        v = v.astype(np.float32)
        a = v[yi][:, xi] * (1 - fx) + v[yi][:, xi + 1] * fx
        b = v[yi + 1][:, xi] * (1 - fx) + v[yi + 1][:, xi + 1] * fx
        return np.clip(a * (1 - fy) + b * fy, 0, 255).astype(np.uint8)
else:
    xs = (240 + (np.arange(gx0, gx1) + 0.5) * 2.25).astype(int)
    ys = ((np.arange(gy0, gy1) + 0.5) * 2.25).astype(int)

    def grab(v):
        return v[ys][:, xs]
# (frame by frame off the pipe: a long stretch never sits in memory as video)
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
frames = []
while True:
    buf = proc.stdout.read(W * H * CH)
    if len(buf) < W * H * CH:
        break
    v = np.frombuffer(buf, np.uint8).reshape(H, W, CH).min(axis=2)
    frames.append(grab(v))
proc.wait()
g = np.stack(frames)
np.save(out, g)
print(out, g.shape)
