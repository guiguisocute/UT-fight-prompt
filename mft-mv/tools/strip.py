"""A filmstrip of rendered frames (tools/frames.cjs --bars): each frame cut to a region, labelled
bar·16th (SCRIPT.md's notation), side by side; optional guide lines across all of them (world y) so a
bob reads at a glance.

usage: python tools/strip.py <frames dir> <out.png> <bars,...> [--reg=x0,y0,x1,y1] [--guides=y,...]
       [--scale=2] [--cols=9]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--'))
src, out, bars = args[0], args[1], [float(b) for b in args[2].split(',')]
x0, y0, x1, y1 = (int(v) for v in opts.get('reg', '360,40,620,290').split(','))
guides = [int(v) for v in opts['guides'].split(',')] if 'guides' in opts else []
S = int(opts.get('scale', 2))
cols = int(opts.get('cols', len(bars)))
LAB = 18
FONT = ImageFont.load_default(size=13)
tiles = []
for b in bars:
    im = Image.open(os.path.join(src, f'f_{b:.4f}.png')).convert('RGB').crop((x0, y0, x1, y1))
    im = im.resize(((x1 - x0) * S, (y1 - y0) * S), Image.NEAREST)
    t = Image.new('RGB', (im.width, im.height + LAB), (0, 0, 0))
    t.paste(im, (0, LAB))
    d = ImageDraw.Draw(t)
    for g in guides:
        yy = LAB + (g - y0) * S
        for xx in range(0, t.width, 6):
            d.line([(xx, yy), (xx + 2, yy)], fill=(213, 53, 217))
    bar = int(b + 1e-6)
    s16 = round((b - bar) * 16, 2)
    on = abs(s16 - round(s16)) < 1e-3 and round(s16) % 4 == 0
    d.text((6, 2), f'{bar}·{s16:g}' + (f'  (beat {int(round(s16)) // 4 + 1})' if on else ''), fill=(255, 255, 0) if on else (170, 170, 170), font=FONT)
    tiles.append(t)
rows = (len(tiles) + cols - 1) // cols
W, H = tiles[0].width, tiles[0].height
sheet = Image.new('RGB', (cols * W + (cols - 1) * 4, rows * H + (rows - 1) * 4), (60, 60, 60))
for i, t in enumerate(tiles):
    sheet.paste(t, ((i % cols) * (W + 4), (i // cols) * (H + 4)))
sheet.save(out)
print(out, sheet.size)
