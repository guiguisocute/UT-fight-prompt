#!/usr/bin/env python3
# contact sheet of one region of each frame (motion checks):
#   python tools/cropsheet.py out.png cols x0 y0 x1 y1 [--scale=2] img1 img2 ...
import sys
from PIL import Image, ImageDraw
args = [a for a in sys.argv[1:] if not a.startswith('--')]
opts = dict(a[2:].split('=', 1) for a in sys.argv[1:] if a.startswith('--') and '=' in a)
out, cols, box, files = args[0], int(args[1]), tuple(int(v) for v in args[2:6]), args[6:]
sc = float(opts.get('scale', 1))
ims = [Image.open(f).convert('RGB').crop(box) for f in files]
if sc != 1:
    ims = [im.resize((round(im.width * sc), round(im.height * sc)), Image.NEAREST) for im in ims]
w, h = ims[0].size
rows = (len(ims) + cols - 1) // cols
sheet = Image.new('RGB', (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), (60, 60, 60))
for i, (f, im) in enumerate(zip(files, ims)):
    x, y = (i % cols) * (w + 4), (i // cols) * (h + 4)
    sheet.paste(im, (x, y))
    ImageDraw.Draw(sheet).text((x + 4, y + 4), f.split('_')[-1].replace('.png', ''), fill=(0, 255, 0))
sheet.save(out)
