#!/usr/bin/env python3
"""Windows' own mouse pointers (README 场景 · 桌面: "Windows 的白色箭头") off this machine, every size the
.cur / .ani holds, so a zoomed shot can draw the pointer from the frame the system itself would use
at that scale (32 px at 100 %, 64 at 200 % ...).

    .venv/Scripts/python -I tools/win_cursors.py     -> asset/desktop/cur_<name>_<size>[_<frame>].png,
                                                       asset/desktop/cursors.json (hotspots, frame timing)
"""
import json, os, struct, sys
from PIL import Image

SRC = 'C:/Windows/Cursors'
OUT = 'asset/desktop'
# the arrow; the hand over a link; the arrow with the ring (working in the background); the ring alone
CURSORS = {'arrow': 'aero_arrow.cur', 'link': 'aero_link.cur', 'working': 'aero_working.ani', 'busy': 'aero_busy.ani'}


def entries(b):
    """ICONDIR of a .cur / .ico: [(size, hotspot x, y, PIL image)]"""
    _, typ, n = struct.unpack('<HHH', b[:6])
    out = []
    for i in range(n):
        w, h, _, _, hx, hy, size, off = struct.unpack('<BBBBHHII', b[6 + 16 * i:22 + 16 * i])
        w, h, data = w or 256, h or 256, b[off:off + size]
        if data[:4] == b'\x89PNG':
            import io
            im = Image.open(io.BytesIO(data)).convert('RGBA')
        else:
            hs, bw, bh, _, bpp = struct.unpack('<IiiHH', data[:16])
            if bpp != 32:
                raise ValueError(f'{bpp} bpp cursor frame')
            px = data[hs:hs + bw * (bh // 2) * 4]
            im = Image.frombuffer('RGBA', (bw, bh // 2), px, 'raw', 'BGRA', 0, -1).copy()
        out.append((w, hx if typ == 2 else w // 2, hy if typ == 2 else h // 2, im))
    return out


def chunks(b, off, end):
    while off + 8 <= end:
        cid, size = b[off:off + 4], struct.unpack('<I', b[off + 4:off + 8])[0]
        yield cid, off + 8, size
        off += 8 + size + (size & 1)


def ani(b):
    """RIFF ACON: the frames (each a .cur), their order and the time each is shown (jiffies, 1/60 s)"""
    frames, rate, seq, nsteps, jif = [], None, None, 0, 0
    for cid, o, size in chunks(b, 12, len(b)):
        if cid == b'anih':
            _, nframes, nsteps, _, _, _, _, jif, _ = struct.unpack('<9I', b[o:o + 36])
        elif cid == b'rate':
            rate = list(struct.unpack(f'<{size // 4}I', b[o:o + size]))
        elif cid == b'seq ':
            seq = list(struct.unpack(f'<{size // 4}I', b[o:o + size]))
        elif cid == b'LIST' and b[o:o + 4] == b'fram':
            for sid, so, ssize in chunks(b, o + 4, o + size):
                if sid == b'icon':
                    frames.append(entries(b[so:so + ssize]))
    steps = seq or list(range(len(frames)))
    return frames, steps, rate or [jif] * len(steps)


def main():
    os.makedirs(OUT, exist_ok=True)
    meta = {}
    for name, fn in CURSORS.items():
        b = open(os.path.join(SRC, fn), 'rb').read()
        if fn.endswith('.ani'):
            frames, steps, rate = ani(b)
            for i, fr in enumerate(frames):
                for size, hx, hy, im in fr:
                    im.save(f'{OUT}/cur_{name}_{size}_{i}.png')
            sizes = sorted({e[0] for e in frames[0]})
            meta[name] = {'sizes': sizes, 'hot': {s: [hx, hy] for s, hx, hy, _ in frames[0]}, 'frames': len(frames),
                          'steps': steps, 'jiffies': rate}
        else:
            ents = entries(b)
            seen = set()
            for size, hx, hy, im in ents:
                if size in seen:
                    continue
                seen.add(size)
                im.save(f'{OUT}/cur_{name}_{size}.png')
            meta[name] = {'sizes': sorted(seen), 'hot': {s: [hx, hy] for s, hx, hy, _ in ents}}
        print(name, meta[name]['sizes'], meta[name].get('frames', ''))
    json.dump(meta, open(f'{OUT}/cursors.json', 'w'), indent=1)


if __name__ == '__main__':
    sys.exit(main())
