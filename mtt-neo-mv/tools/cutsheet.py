#!/usr/bin/env python3
"""Lay out tools/cutaudit.cjs's frames: one row per cut, the shot before | the shot after, with
the soul (yellow) and him (pink) marked where they are in each picture, and the numbers.

    ../mtt-mv/.venv/Scripts/python tools/cutsheet.py work/cuts          # -> work/cuts/sheet_N.png
"""
import json
import os
import sys

from PIL import Image, ImageDraw

d = sys.argv[1]
R = json.load(open(os.path.join(d, 'cuts.json'), encoding='utf8'))
cuts = R['cuts']
W, H, PAD, TXT = 480, 270, 6, 34
PER = 8
for page in range(0, len(cuts), PER):
    rows = cuts[page:page + PER]
    sheet = Image.new('RGB', (W * 2 + PAD * 3, (H + TXT + PAD) * len(rows) + PAD), (24, 24, 30))
    dr = ImageDraw.Draw(sheet)
    for k, c in enumerate(rows):
        i = page + k
        y = PAD + k * (H + TXT + PAD)
        for j, (tag, side) in enumerate((('a', c['A']), ('b', c['B']))):
            x = PAD + j * (W + PAD)
            im = Image.open(os.path.join(d, f'cut_{i:02d}_{tag}.png')).convert('RGB')
            sheet.paste(im, (x, y + TXT))
            for key, col in (('soul', (255, 240, 0)), ('neo', (255, 80, 220))):
                p = side.get(key)
                if p:
                    px, py = x + p[0] / 2, y + TXT + p[1] / 2
                    dr.ellipse([px - 7, py - 7, px + 7, py + 7], outline=col, width=2)
            g = side.get('go')
            if g:
                cx, cy = x + W / 2, y + TXT + H - 20
                dr.line([cx, cy, cx + g[0] * 0.6, cy + g[1] * 0.6], fill=(120, 255, 120), width=3)
        warn = []
        if c['A']['side'] and c['B']['side'] and c['A']['side'] != c['B']['side']:
            warn.append('LINE CROSSED')
        ga, gb = c['A'].get('go'), c['B'].get('go')
        if ga and gb and abs(ga[0]) > 15 and abs(gb[0]) > 15 and (ga[0] > 0) != (gb[0] > 0):
            warn.append('DIRECTION FLIP')
        txt = f"#{i} bar {c['bar']:.3f}  {c['cam']}  shot {c['before']} -> {c['after']} bars  turn {c['turn']} deg  roll {c['A']['roll']}->{c['B']['roll']}"
        dr.text((PAD, y + 2), txt, fill=(230, 230, 230))
        if warn:
            dr.text((PAD, y + 16), '  '.join(warn), fill=(255, 110, 110))
    sheet.save(os.path.join(d, f'sheet_{page // PER}.png'))
print('ok')
