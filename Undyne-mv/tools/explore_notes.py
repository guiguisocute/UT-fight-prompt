#!/usr/bin/env python3
"""Read work/flp_notes.json as a score.

    .venv/Scripts/python tools/explore_notes.py grid            # channels active per bar
    .venv/Scripts/python tools/explore_notes.py bars 0 4 [ch..] # notes of bars 0-3 on a 16th grid

Bars are the song's 150-BPM bars (768 FL ticks); a 16th is 48 ticks = 0.1 s.
"""
import json, sys
from collections import defaultdict

D = json.load(open('work/flp_notes.json'))
BAR, S16 = 768, 48
NAMES = 'C C# D D# E F F# G G# A A# B'.split()
def nm(k):
    return f'{NAMES[k % 12]}{k // 12 - 1}'  # MIDI 60 = C4 (FL's own UI calls it C5)
chn = {int(k): v for k, v in D['channels'].items()}
notes = D['notes']
nbars = max(n['tick'] + n['len'] for n in notes) // BAR + 1

mode = sys.argv[1] if len(sys.argv) > 1 else 'grid'
if mode == 'grid':
    act = defaultdict(lambda: defaultdict(int))
    for n in notes:
        act[n['tick'] // BAR][n['ch']] += 1
    chs = sorted({n['ch'] for n in notes})
    print('bar  t(s)   ' + ' '.join(f'{c:>3d}' for c in chs))
    for c in chs:
        print(f'  ch{c:2d} = {chn[c]}')
    for b in range(nbars):
        print(f'{b:3d} {b * 1.6:6.1f}  ' + ' '.join(f'{act[b][c]:3d}' if act[b][c] else '  .' for c in chs))
    for c in D['clips']:
        print(f"clip {c['inst']} at bar {c['tick'] / BAR:.3f} ({c['t']:.2f}s) dur {c['dur']:.2f}s")
elif mode == 'bars':
    b0, b1 = int(sys.argv[2]), int(sys.argv[3])
    only = {int(x) for x in sys.argv[4:]}
    for b in range(b0, b1):
        print(f'---- bar {b}  t={b * 1.6:.1f}s')
        by = defaultdict(list)
        for n in notes:
            if n['tick'] // BAR == b and (not only or n['ch'] in only):
                by[n['ch']].append(n)
        for c in sorted(by):
            cells = []
            for n in by[c]:
                pos = (n['tick'] - b * BAR) / S16
                ln = n['len'] / S16
                cells.append(f"{pos:g}:{nm(n['key'])}" + (f"/{ln:g}" if ln != 1 else '') + (f"v{n['vel']}" if n['vel'] < 90 else ''))
            print(f'  ch{c:2d} {chn[c][:16]:16s} ' + ' '.join(cells))
