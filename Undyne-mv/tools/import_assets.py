#!/usr/bin/env python3
"""Pack the pictures (and later the sounds) the MV uses into src/assets.js as data URIs, so the
player works from file:// with no loader (the same scheme as ../mtt-neo-mv and ../asgore-mv).

    .venv/Scripts/python tools/import_assets.py

Sources:
  * the bridge room's textures: asset/tiles/*.png (tools/make_tiles.py: cut from the lifted
    original with the recording's watermark painted out)   -> img['tile/<name>']
  * the overworld sprites: Monster Kid, Undyne, the human (Frisk's sheet; it has the original's own
    black silhouettes for the dark) and Chara, cut by tools/slice_npc.py (frame numbers as in
    work/index_<sheet>.png) -> img['kid/<n>'], img['undow/<n>'], img['frisk/<n>'], img['chara/<n>']
  * Monster Kid's battle sprite lifted off the recording: asset/drawn/  -> img['drawn/<name>']
  * Undyne's battle sheet, cut by tools/slice_sheet.py: the blow (her cut, talking) and her melt
    -> img['und/fatal<n>'], img['und/melt<n>']
  * the original battle UI (soul, buttons, HP label, the attack target / cursor / slash, the HUD and
    damage fonts) and its sounds: ../asgore-mv/src/assets.js
  * the desktop (bars 60-71): Windows' own icons, pointers and wallpaper, lifted off this machine by
    tools/win_desktop.ps1 and tools/win_cursors.py -> img['desk/<name>_<size>'], img['desk/cur_...'],
    img['desk/wallpaper'], meta['desk/cursors'] (hotspots, the .ani's frame timing)
"""
import base64, io, json, os, subprocess, sys, tempfile
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import slice_npc, slice_sheet

OUT = 'src/assets.js'
SFXDIR = 'asset/sfx/PC _ Computer - Undertale - Miscellaneous - Sound Effects'
# the original sound effects (key -> file), converted to mono 96k mp3 (Safari cannot play ogg)
SFX = {
    'Txt1': 'SND_TXT1.wav', 'Txt2': 'SND_TXT2.wav', 'TxtUnd': 'snd_txtund.wav', 'TxtUnd2': 'snd_txtund2.wav',
    'Save': 'snd_save.wav', 'Noise': 'snd_noise.wav', 'BattleFall': 'snd_battlefall.wav',
    'UndyneStep': 'snd_undynestep.wav', 'Splash': 'snd_splash.wav', 'SpearAppear': 'snd_spearappear.wav',
    # the refusal (BTERTD + bars 0-12)
    'Sparkle': 'snd_sparkle1.wav', 'Bell': 'snd_bell.wav', 'SpearRise': 'snd_spearrise.wav', 'UndyneDis': 'snd_undynedis.wav',
    'Splash2': 'SND_SPLASH_2.wav', 'Shock': 'snd_shock.wav', 'HeartShot': 'snd_heartshot.wav', 'TxtUnd3': 'snd_txtund3.wav',
    # the battle's rounds (bars 12-27): her arrows, her swing, the glass spear breaking, a struck plank
    'Arrow': 'snd_arrow.wav', 'Swipe': 'mus_sfx_swipe.wav', 'GlassBreak': 'snd_glassbreak.wav', 'EyeFlash': 'mus_sfx_eyeflash.wav',
    'Block': 'snd_block2.wav', 'Swing': 'mus_sfx_a_swipe.wav',
    # the soul broken (bar 60): the crack, then the shards
    'Break1': 'snd_break1.wav', 'Break2': 'snd_break2.wav',
    # the load (60-71): Asgore's voice on the GAME OVER, her grab and her pull
    'TxtAsg': 'snd_txtasg.wav', 'Grab': 'mus_sfx_a_grab.ogg', 'Pullback': 'mus_sfx_a_pullback.wav',
}
# from ../asgore-mv/src/assets.js: the original battle UI
AS_IMG = ['PlayerHeart/Default/0', 'UIFight/Default/0', 'UIFight/Highlight/0', 'UIAct/Default/0', 'UIAct/Highlight/0',
          'UIItem/Default/0', 'UIItem/Highlight/0', 'UIMercy/Default/0', 'UIMercy/Highlight/0', 'HP/Default/0',
          'Target/Default/0', 'TargetChoice/Default/0', 'TargetChoice/Default/1', *[f'Strike/Default/{i}' for i in range(6)],
          'BattleFont', 'DamageFont']
AS_META = ['PlayerHeart', 'UIFight', 'UIAct', 'UIItem', 'UIMercy', 'HP', 'Target', 'TargetChoice', 'Strike']
AS_SFX = ['MenuSelect', 'MenuCursor', 'BattleText', 'PlayerFight', 'Laz', 'Damage', 'HeavyDamage', 'Wind', 'Vaporized',
          'Flash', 'Impact', 'Hurt']
# her battle sheet (work/index_boss.png): 47..56 the blow - her cut, talking; 57..60 her melt;
# 61, 62 her swing's arc (red, green: the soul's colour changing); 63..78 the green soul's arrows
# (blue, light blue, red, yellow; the way each points); 79..81 her spears (long, up, right)
BOSS = {**{47 + i: f'fatal{i}' for i in range(10)}, **{57 + i: f'melt{i}' for i in range(4)},
        61: 'arc_red', 62: 'arc_green',
        63: 'arrow_b_d', 64: 'arrow_b_u', 65: 'arrow_b_r', 66: 'arrow_b_l',
        67: 'arrow_lb_d', 68: 'arrow_lb_r', 69: 'arrow_lb_l', 70: 'arrow_lb_u',
        71: 'arrow_r_d', 72: 'arrow_r_u', 73: 'arrow_r_r', 74: 'arrow_r_l',
        75: 'arrow_y_d', 76: 'arrow_y_u', 77: 'arrow_y_r', 78: 'arrow_y_l',
        79: 'spear_long', 80: 'spear_up', 81: 'spear_right'}
# Undyne the Undying (src/undyne.js; placed by src/und_data.js, tools/fit_undying.py): the parts,
# the eye beam, her heads (128..149), and the big pictures on black - the game's composite and her
# last melt (stored at 2x on the sheet: halved back to sprite px)
UNDYING = {128: 'u_hand', 129: 'u_spear', 130: 'u_torso', 131: 'u_arm', 132: 'u_belt', 133: 'u_legs', 134: 'u_beam',
           **{135 + i: f'u_head{i}' for i in range(9)}, **{144 + i: f'u_mouth{i}' for i in range(5)}, 149: 'u_hurt'}
UNDYING_FRAMES = {0: ('u_body', 1), 1: ('u_melt0', 2), 2: ('u_melt1', 2)}


def load_js(path):
    s = open(path, encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def png_uri(img):
    b = io.BytesIO()
    img.save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def main():
    assets = dict(img={}, meta={}, sfx={}, size={})
    asg = load_js('../asgore-mv/src/assets.js')
    for k in AS_IMG:
        assets['img'][k] = asg['img'][k]
    for k in AS_META:
        assets['meta'][k] = asg['meta'][k]
    for k in AS_SFX:
        assets['sfx'][k] = asg['sfx'][k]
    cs, _ = slice_sheet.cells('boss')
    for i, name in BOSS.items():
        assets['img']['und/' + name] = png_uri(Image.fromarray(cs[i]['img']))
    for i, name in UNDYING.items():
        assets['img']['und/' + name] = png_uri(Image.fromarray(cs[i]['img']))
    fr = slice_sheet.frames('boss')
    for i, (name, k) in UNDYING_FRAMES.items():
        assets['img']['und/' + name] = png_uri(Image.fromarray(fr[i]['img'][::k, ::k]))
    for fn in sorted(os.listdir('asset/sprites/tiles')):
        if fn.endswith('.png'):
            assets['img']['tile/' + fn[:-4]] = png_uri(Image.open(os.path.join('asset/sprites/tiles', fn)).convert('RGBA'))
    # (alphys / pap / asg: the heartbeat montage's mirrors, bars 5-7 - work/index_<sheet>.png)
    for sheet, key in (('kid', 'kid'), ('undyne', 'undow'), ('frisk', 'frisk'), ('chara', 'chara'),
                       ('alphys', 'alphys'), ('papyrus', 'pap'), ('asgore', 'asg')):
        for i, c in enumerate(slice_npc.cells(sheet)):
            assets['img'][f'{key}/{i}'] = png_uri(Image.fromarray(c['img']))
    for fn in sorted(os.listdir('asset/sprites/drawn')):
        if fn.endswith('.png'):
            assets['img']['drawn/' + fn[:-4]] = png_uri(Image.open(os.path.join('asset/sprites/drawn', fn)).convert('RGBA'))
    # (the desktop: the 20 px icons are not drawn anywhere; the wallpaper stays a JPEG)
    for fn in sorted(os.listdir('asset/desktop')):
        stem, ext = os.path.splitext(fn)
        if ext == '.png' and not stem.endswith('_20'):
            assets['img']['desk/' + stem] = png_uri(Image.open(os.path.join('asset/desktop', fn)).convert('RGBA'))
        elif ext == '.jpg':
            assets['img']['desk/' + stem] = 'data:image/jpeg;base64,' + base64.b64encode(open(os.path.join('asset/desktop', fn), 'rb').read()).decode()
    assets['meta']['desk/cursors'] = json.load(open('asset/desktop/cursors.json'))
    # (the game's own sprites, out of the installed game's data.win - tools/ut_sprites.py. asset/her - the
    # frames codex drew for the load scene's first version, tools/her_frames.py - is not packed: the rework
    # uses only her own sprites, README 第四幕 · 返工)
    for d, key in (('asset/sprites/ut', 'ut'),):
        for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if fn.endswith('.png'):
                assets['img'][f'{key}/' + fn[:-4]] = png_uri(Image.open(os.path.join(d, fn)).convert('RGBA'))
    for k, u in assets['img'].items():
        if k in ('BattleFont', 'DamageFont'):
            continue
        im = Image.open(io.BytesIO(base64.b64decode(u.split(',')[1])))
        assets['size'][k] = [im.width, im.height]
    with tempfile.TemporaryDirectory() as td:
        for key, fn in SFX.items():
            dst = os.path.join(td, key + '.mp3')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', os.path.join(SFXDIR, fn), '-ac', '1', '-b:a', '96k', dst], check=True)
            assets['sfx'][key] = 'data:audio/mpeg;base64,' + base64.b64encode(open(dst, 'rb').read()).decode()
    with open(OUT, 'w') as f:
        f.write('// Generated by tools/import_assets.py - do not edit.\n')
        f.write('window.MV_ASSETS = ')
        json.dump(assets, f, separators=(',', ':'))
        f.write(';\n')
    print('images', len(assets['img']), 'sounds', len(assets['sfx']), 'bytes', os.path.getsize(OUT))


if __name__ == '__main__':
    main()
