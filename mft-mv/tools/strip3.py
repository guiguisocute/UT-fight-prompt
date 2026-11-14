"""A filmstrip of ?lab=beat with all three on stage: each tile labelled with its bar and beat and who
is at the bottom of their bob (measured: the crown's lowest row in the frame - Muffet's head at world
x 478-488, the guards' at 222-238 and 716-732).

usage: python -I tools/strip3.py <frames dir> <out.png> <bars,...> [--cols=4] [--reg=x0,y0,x1,y1]
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--'))
src, out, bars = args[0], args[1], [float(b) for b in args[2].split(',')]
cols = int(opts.get('cols', 4))
x0, y0, x1, y1 = (int(v) for v in opts.get('reg', '130,58,870,284').split(','))
FONT = ImageFont.load_default(size=15)
LAB = 22


def crown(a, xa, xb):
    return 30 + int(np.argmax(a[30:200, xa:xb].any(1)))


frames = {b: np.array(Image.open(os.path.join(src, f'f_{b:.4f}.png')).convert('RGB')) for b in bars}
cr = {b: [crown(f.mean(2) > 128, *xs) for xs in ((478, 488), (222, 238), (716, 732))] for b, f in frames.items()}
low = [max(c[i] for c in cr.values()) for i in range(3)]
tiles = []
for b in bars:
    im = Image.fromarray(frames[b]).crop((x0, y0, x1, y1))
    t = Image.new('RGB', (im.width, im.height + LAB), (0, 0, 0))
    t.paste(im, (0, LAB))
    d = ImageDraw.Draw(t)
    bar = int(b + 1e-6)
    beat = (b - bar) * 4 + 1
    d.text((6, 3), f'bar {bar}  beat {beat:g}', fill=(255, 255, 0) if beat == int(beat) else (170, 170, 170), font=FONT)
    m_dn, g_dn = cr[b][0] == low[0], cr[b][1] == low[1]
    d.text((170, 3), 'Muffet DOWN' if m_dn else 'Muffet', fill=(213, 53, 217) if m_dn else (90, 90, 90), font=FONT)
    d.text((300, 3), 'guards DOWN' if g_dn else 'guards', fill=(80, 200, 255) if g_dn else (90, 90, 90), font=FONT)
    if m_dn and g_dn:
        d.text((440, 3), '<- together', fill=(255, 255, 255), font=FONT)
    tiles.append(t)
W, H = tiles[0].size
rows = (len(tiles) + cols - 1) // cols
sheet = Image.new('RGB', (cols * W + (cols - 1) * 4, rows * H + (rows - 1) * 4), (60, 60, 60))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * (W + 4), (i // cols) * (H + 4)))
sheet.save(out)
print(out, sheet.size)
