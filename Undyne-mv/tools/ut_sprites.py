#!/usr/bin/env python3
"""The original game's own sprites, read out of the installed UNDERTALE's data.win (GameMaker 1.4): each
sprite by its name in the game, every frame laid out on its own canvas the size the game draws it - no
sheet, no recording, no watermark. (README 第四幕: the GAME OVER that the spear splits.)

    .venv/Scripts/python -I tools/ut_sprites.py --list gameover        names containing "gameover"
    .venv/Scripts/python -I tools/ut_sprites.py spr_gameoverbg          -> asset/ut/spr_gameoverbg_<i>.png

data.win: FORM, then chunks (4-char name, u32 length). SPRT: a pointer list of sprites - name (pointer to
the string's characters), width, height, four margins, transparent / smooth / preload, bbox mode, separate
masks, origin, then a pointer list of texture page items. TPAG item: source x y w h on its page, target x y
w h on the sprite's canvas, bounding w h, page index. TXTR: a pointer list of pages - a u32, then a
pointer to the page's PNG.
"""
import io, os, struct, sys
from PIL import Image

GAME = 'D:/SteamLibrary/steamapps/common/Undertale/data.win'
OUT = 'asset/sprites/ut'


def chunks(b):
    if b[:4] != b'FORM':
        raise ValueError('not a GameMaker data file')
    o, end, out = 8, 8 + struct.unpack_from('<I', b, 4)[0], {}
    while o < end:
        name, n = b[o:o + 4].decode('ascii'), struct.unpack_from('<I', b, o + 4)[0]
        out[name] = (o + 8, n)
        o += 8 + n
    return out


def ptrs(b, at):
    n = struct.unpack_from('<I', b, at)[0]
    return list(struct.unpack_from(f'<{n}I', b, at + 4))


def cstr(b, p):
    return b[p:b.index(b'\0', p)].decode('utf-8', 'replace')


def png_at(b, p):
    if b[p:p + 8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('no PNG at %x' % p)
    q = b.index(b'IEND', p) + 8
    return Image.open(io.BytesIO(b[p:q])).convert('RGBA')


def sprites(b, C):
    """name -> (width, height, [tpag pointers])"""
    out = {}
    for p in ptrs(b, C['SPRT'][0]):
        name = cstr(b, struct.unpack_from('<I', b, p)[0])
        w, h = struct.unpack_from('<II', b, p + 4)
        # (name, w, h, 4 margins, 3 bools, bbox mode, sep masks, origin x y = 14 u32s; then the textures)
        tex = ptrs(b, p + 14 * 4)
        out[name] = (w, h, tex)
    return out


def pages(b, C):
    cache, lst = {}, ptrs(b, C['TXTR'][0])

    def page(i):
        if i not in cache:
            cache[i] = png_at(b, struct.unpack_from('<I', b, lst[i] + 4)[0])
        return cache[i]
    return page


def frames(b, C, name):
    S, page = sprites(b, C), pages(b, C)
    w, h, tex = S[name]
    out = []
    for t in tex:
        sx, sy, sw, sh, tx, ty, tw, th, bw, bh, pg = struct.unpack_from('<11H', b, t)
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        im.paste(page(pg).crop((sx, sy, sx + sw, sy + sh)).resize((tw, th), Image.NEAREST), (tx, ty))
        out.append(im)
    return out


def main(argv):
    b = open(GAME, 'rb').read()
    C = chunks(b)
    if argv and argv[0] == '--list':
        key = argv[1] if len(argv) > 1 else ''
        for name, (w, h, tex) in sorted(sprites(b, C).items()):
            if key in name:
                print(f'{name:40s} {w}x{h}  {len(tex)} frame(s)')
        return
    os.makedirs(OUT, exist_ok=True)
    for name in argv:
        for i, im in enumerate(frames(b, C, name)):
            im.save(f'{OUT}/{name}_{i}.png')
        print(name, len(frames(b, C, name)), 'frame(s) ->', OUT)


if __name__ == '__main__':
    main(sys.argv[1:])
