#!/usr/bin/env python3
"""Lift the overworld sprites of the prologue out of the reference recording
(asset/record.mp4, 1440x900: the 640x480 game is drawn at 1.875x from x = 120;
the game itself draws the 320x240 room at 2x, so one sprite pixel is 3.75
video px). Each sprite pixel is sampled at its centre, snapped to a small
palette, and the black that touches the edge of the crop becomes transparent
(enclosed black stays: the gaps between the LEDs, the dials' insides).

    ../mtt-mv/.venv/Scripts/python tools/extract_ow.py     # -> asset/drawn/mtt_ow_*.png

Frames: 20 s (idle: the box form in the corridor, arms down), 37 s (arms up).
"""
import subprocess, os, tempfile
import numpy as np
from PIL import Image
from scipy import ndimage

S, X0 = 1.875, 120
PAL = {
    'black': (0, 0, 0), 'gray': (133, 128, 104), 'teal': (57, 100, 101), 'tan': (191, 155, 84),
    'white': (255, 255, 255), 'red': (226, 19, 1), 'redB': (253, 48, 35),
}
OUT = 'asset/sprites/drawn'


def frame(t):
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, 'f.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(t), '-i', 'asset/record/record.mp4', '-frames:v', '1', p], check=True)
        return np.array(Image.open(p).convert('RGB')).astype(int)


def sample(im, gx0, gy0, w, h):
    out = np.zeros((h, w, 3), int)
    for j in range(h):
        for i in range(w):
            vx = X0 + (gx0 + 2 * i + 1) * S
            vy = (gy0 + 2 * j + 1) * S
            out[j, i] = im[int(round(vy - 0.5)), int(round(vx - 0.5))]
    return out


def snap(a):
    names = list(PAL)
    P = np.array([PAL[n] for n in names])
    d = ((a[:, :, None, :] - P[None, None]) ** 2).sum(-1)
    idx = d.argmin(-1)
    rgb = P[idx]
    black = idx == 0
    lab, _ = ndimage.label(black)
    edge = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    outside = np.isin(lab, list(edge))
    rgba = np.zeros(a.shape[:2] + (4,), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = np.where(outside, 0, 255)
    return rgba


def crop_alpha(rgba):
    ys, xs = np.where(rgba[..., 3] > 0)
    return rgba[ys.min():ys.max() + 1, xs.min():xs.max() + 1], (xs.min(), ys.min())


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, t in (('mtt_ow_idle', 20), ('mtt_ow_arms', 37)):
        im = frame(t)
        a = snap(sample(im, 250, 164, 70, 52))  # game x 250..390, y 164..268
        c, (ox, oy) = crop_alpha(a)
        Image.fromarray(c).save(f'{OUT}/{name}.png')
        print(name, c.shape[1], 'x', c.shape[0], 'origin in crop', ox, oy, '(game px:', 250 + 2 * ox, 164 + 2 * oy, ')')
