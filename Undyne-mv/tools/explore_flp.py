#!/usr/bin/env python3
"""Dump the FL Studio project (channels, patterns, playlist) as text.

    .venv-flp/Scripts/python tools/explore_flp.py [project.flp] > work/flp_dump.txt

pyflp 2.2.1 needs Python <= 3.10 (its EventEnum breaks on 3.12), hence .venv-flp.
"""
import sys
import pyflp
from pyflp.arrangement import ChannelPLItem, PatternPLItem

SRC = sys.argv[1] if len(sys.argv) > 1 else 'asset/music/Deconstruction-Battle Against a True HeroFL20.flp'
p = pyflp.parse(SRC)
ppq = p.ppq
print(f'version={p.version} ppq={ppq} tempo={p.tempo} title={p.title!r} artists={p.artists!r} genre={p.genre!r}')
print(f'comments={p.comments!r}')

print('\n== channels ==')
for ch in p.channels:
    plug = getattr(ch, 'plugin', None)
    print(f'  #{ch.iid:3d} {type(ch).__name__:10s} name={ch.display_name!r} '
          f'internal={getattr(ch, "internal_name", None)!r} plugin={type(plug).__name__ if plug else None} '
          f'insert={getattr(ch, "insert", None)} color={getattr(ch, "color", None)}')

print('\n== mixer inserts ==')
for ins in p.mixer:
    if ins.name:
        print(f'  insert {ins.iid}: {ins.name!r}')

print('\n== patterns ==')
for pat in p.patterns:
    notes = list(pat.notes)
    if not notes:
        print(f'  P{pat.iid:3d} {pat.name!r} (empty)')
        continue
    end = max(n.position + n.length for n in notes)
    rack = {}
    for n in notes:
        rack.setdefault(n.rack_channel, []).append(n)
    print(f'  P{pat.iid:3d} {pat.name!r} len={pat.length} notes={len(notes)} end={end / ppq:.2f} beats '
          f'channels={ {k: len(v) for k, v in sorted(rack.items())} }')

print('\n== arrangements ==')
for arr in p.arrangements:
    print(f'arrangement {arr.iid} {arr.name!r}')
    for tm in arr.timemarkers:
        print(f'  marker {tm.name!r} pos={tm.position} ({tm.position / ppq / 4:.2f} bars) type={tm.type}')
    for tr in arr.tracks:
        items = list(tr)
        if not items:
            continue
        print(f'  track {tr.iid:3d} {tr.name!r} items={len(items)}')
        for it in items:
            pos, ln = it.position / ppq / 4, it.length / ppq / 4
            if isinstance(it, PatternPLItem):
                what = f'pattern P{it.pattern.iid} {it.pattern.name!r}'
            elif isinstance(it, ChannelPLItem):
                what = f'channel #{it.channel.iid} {it.channel.display_name!r}'
            else:
                what = type(it).__name__
            print(f'      bar {pos:7.2f} +{ln:6.2f} {what} offsets={it.offsets}')
