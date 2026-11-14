#!/usr/bin/env python3
"""Flatten the FL Studio deconstruction into an absolute note list.

    .venv/Scripts/python tools/flp_notes.py [project.flp] [work/flp_notes.json]

The project is a note-for-note remake of the soundtrack: playlist track 1 is the
original FLAC (no stretching, starts at tick 0), the other tracks are MIDI
transcriptions laid against it. FL runs at 300 BPM, 4/4, PPQ 96, so one tick is
1/480 s, an FL bar is 0.8 s, and the song's real 150-BPM bar is 2 FL bars
(768 ticks, a 16th = 48 ticks). Playlist clip offsets are (0, length) everywhere
(pyflp reads them as denormal floats), so a clip simply plays its pattern from 0
up to its length.

Keys are the raw FL keys = MIDI numbers AS WRITTEN; see analyze_music.py for the
sounding transposition of each channel. pyflp 2.2.1 needs Python <= 3.10.
"""
import json, sys
import pyflp
from pyflp.arrangement import ChannelPLItem, PatternPLItem


def flatten(path):
    p = pyflp.parse(path)
    sec = 60 / p.tempo / p.ppq  # seconds per tick
    chname = {ch.iid: ch.display_name for ch in p.channels}
    notes, clips = [], []
    for tr in p.arrangements[0].tracks:
        for it in tr:
            if isinstance(it, PatternPLItem):
                for n in it.pattern.notes:
                    if n.position >= it.length:
                        continue
                    # n['key'] is the raw FL key (FL calls 60 "C5", scientific pitch says C4)
                    notes.append(dict(tick=it.position + n.position, len=min(n.length, it.length - n.position),
                                      key=n['key'], vel=n.velocity, ch=n.rack_channel, pat=it.pattern.iid))
            elif isinstance(it, ChannelPLItem) and it.channel.iid != 0:  # 0 = the original FLAC
                clips.append(dict(tick=it.position, len=it.length, ch=it.channel.iid))
    notes.sort(key=lambda n: (n['tick'], n['ch'], n['key']))
    for n in notes + clips:
        n['t'] = round(n['tick'] * sec, 4)
        n['dur'] = round(n['len'] * sec, 4)
    return dict(ppq=p.ppq, tempo=p.tempo, secPerTick=sec, channels=chname, notes=notes, clips=clips)


if __name__ == '__main__':
    SRC = sys.argv[1] if len(sys.argv) > 1 else 'asset/music/Deconstruction-Battle Against a True HeroFL20.flp'
    OUT = sys.argv[2] if len(sys.argv) > 2 else 'work/flp_notes.json'
    d = flatten(SRC)
    with open(OUT, 'w') as f:
        json.dump(d, f, indent=0)
    print(f"{len(d['notes'])} notes, {len(d['clips'])} audio clips -> {OUT}")
