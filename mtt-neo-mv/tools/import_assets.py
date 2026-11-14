#!/usr/bin/env python3
"""Pack every sprite / font / sound the MV uses into src/assets.js (data URIs), so
the player works from file:// with no loader.

    ../mtt-mv/.venv/Scripts/python tools/import_assets.py

Sources:
  * Mettaton NEO parts: cut from asset/...Mettaton NEO.png by tools/slice_neo.py,
    named by where they sit in the sheet's own "Fully Assembled" picture (the
    sheet's left "Lights" cell is the wing on the right of the figure). The legs
    cell is split down the middle into a left and a right leg.
  * the box form, Mettaton EX's props (bombs, the plus blast, mini Mettatons,
    lightning, sparkles, REC) and EX's expressive faces: ../mtt-mv/src/assets.js
    (cut there from the Mettaton sheets by its tools/slice_sheet.py)
  * battle UI (soul, buttons, HP label, the knife's target / cursor / red slash,
    HUD / damage / dialogue fonts, UI sounds) and Frisk's overworld frames:
    ../asgore-mv/src/assets.js (c2-sans-fight via bad-time-mv, and the
    overworld sheets)
  * overworld box Mettaton (colour): lifted from asset/record.mp4 by
    tools/extract_ow.py -> asset/drawn/
  * sound effects: the original UNDERTALE effects (../mtt-mv/asset/... Sound
    Effects), converted to mono 96k mp3 with ffmpeg (Safari cannot play ogg)
"""
import base64, io, json, os, subprocess, sys, tempfile
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import slice_neo

OUT = 'src/assets.js'
SFXDIR = 'asset/sfx/PC _ Computer - Undertale - Miscellaneous - Sound Effects'


def load_js(path):
    s = open(path, encoding='utf-8').read()
    return json.loads(s[s.index('{'):s.rindex('}') + 1])


def png_uri(img):
    b = io.BytesIO()
    img.save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def uri_img(u):
    return Image.open(io.BytesIO(base64.b64decode(u.split(',')[1]))).convert('RGBA')


# from ../asgore-mv/src/assets.js
AS_IMG = ['PlayerHeart/Default/0', 'PlayerHeart/Split/0', 'HeartShard/Default/0', 'HeartShard/Default/1',
          'HeartShard/Default/2', 'HeartShard/Default/3', 'UIFight/Default/0', 'UIFight/Highlight/0',
          'UIAct/Default/0', 'UIAct/Highlight/0', 'UIItem/Default/0', 'UIItem/Highlight/0', 'UIMercy/Default/0',
          'UIMercy/Highlight/0', 'HP/Default/0', 'Target/Default/0', 'TargetChoice/Default/0', 'TargetChoice/Default/1',
          *[f'Strike/Default/{i}' for i in range(6)], 'BattleFont', 'DamageFont', 'DefaultFont',
          # Frisk, overworld: back view walking (52-55), front (0-3)
          *[f'frisk/{i}' for i in (0, 1, 2, 3, 52, 53, 54, 55)]]
AS_META = ['PlayerHeart', 'HeartShard', 'UIFight', 'UIAct', 'UIItem', 'UIMercy', 'HP', 'Target', 'TargetChoice', 'Strike']
AS_SFX = ['MenuCursor', 'MenuSelect', 'BattleText', 'Ding', 'Flash', 'Warning', 'Slam', 'HeartShatter', 'HeartSplit',
          'PlayerDamaged', 'PlayerFight', 'Target', 'EyeFlash', 'Impact', 'ScreenShake', 'GlassBreak', 'Break1', 'Break2',
          'BreakBig', 'Damage', 'Hurt', 'HeavyDamage', 'Power', 'SegaPower', 'Sparkles', 'Sparkle', 'Star', 'RainbowBeam',
          'Charge', 'Gunshot', 'Saber', 'Shock', 'Rotate', 'Drone', 'CineCut', 'Hero', 'Save', 'Wind', 'Swipe',
          'SwipeShort', 'Vaporized', 'Laz', 'Explosion', 'Noise', 'Select', 'BattleFall', 'SwordAppear', 'Pullback']

# from ../mtt-mv/src/assets.js (its slices of the Mettaton / Mettaton EX sheets)
MTT_IMG = ['box/idle0', 'box/idle1', 'box/idle2', 'box/idle3', 'box/blast0', 'box/blast1', 'box/zap0', 'box/zap1',
           'box/zap2', 'box/phone',
           'mtt/bomb', 'mtt/bombB', *[f'mtt/boom{i}' for i in range(7)], 'mtt/bolt', 'mtt/heartW', 'mtt/heartB',
           *[f'mtt/spark{i}' for i in range(3)], *[f'mtt/twinkle{i}' for i in range(5)], 'mtt/rec', 'mtt/rew',
           *[f'mtt/mini{i}' for i in range(12)], 'mtt/smoke', 'mtt/spotOff',
           *[f'mtt/face{i}' for i in range(11)], *[f'mtt/hurt{i}' for i in range(3)], *[f'mtt/defeat{i}' for i in range(8)]]
MTT_SFX = [*[f'Mtt{i}' for i in range(1, 10)], 'Burst', 'MttHit', 'PreBomb', 'Bomb', 'BombFall', 'BombSplode',
           'HeartShot', 'Phone', 'LightSwitch', 'OrchHit', 'Cymbal', 'LevelUp', 'Buzzing', 'Escaped', 'Item',
           'LitHit', 'LitHit2', 'ABreak', 'ABullet', 'Alarm', 'SegaPower2', 'Spellcast', 'Generate', 'Victor',
           'DoorOpen', 'DoorShut', 'Txt1', 'Txt2', 'Applause', 'Cheer']

# converted here from the original effects (key -> file)
SFX = {
    'LazC': 'snd_laz_c.wav', 'BeamHold': 'mus_sfx_rainbowbeam_hold.ogg', 'Elevator': 'mus_elevator.ogg',
    'ElecDoorClose': 'snd_elecdoor_close.wav', 'TextNoise': 'snd_textnoise.wav', 'InstaNoise': 'snd_instanoise.wav',
    'HurtBuzz': 'snd_hurtbuzz.wav', 'FNoise': 'mus_f_noise.wav', 'IntroNoise': 'mus_intronoise.ogg',
}


def neo_parts():
    cs, _ = slice_neo.cells()
    parts = {}
    for name, k in (('body', 4), ('assembled', 18), ('armC', 23), ('armB', 24), ('wingL', 121), ('wingR', 120)):
        parts[name] = Image.fromarray(cs[k]['img'])
    for i in range(7):
        parts[f'face{i}'] = Image.fromarray(cs[127 + i]['img'])
    legs = cs[29]['img']
    parts['legL'] = Image.fromarray(legs[:, :56].copy())
    parts['legR'] = Image.fromarray(legs[:, 56:].copy())
    return parts


def main():
    asg = load_js('../asgore-mv/src/assets.js')
    mtt = load_js('../mtt-mv/src/assets.js')
    assets = dict(img={}, meta={}, sfx={}, size={})
    for k in AS_IMG:
        assets['img'][k] = asg['img'][k]
    for k in AS_META:
        assets['meta'][k] = asg['meta'][k]
    for k in AS_SFX:
        assets['sfx'][k] = asg['sfx'][k]
    for k in MTT_IMG:
        assets['img'][k] = mtt['img'][k]
    for k in MTT_SFX:
        assets['sfx'][k] = mtt['sfx'][k]
    for name, img in neo_parts().items():
        assets['img']['neo/' + name] = png_uri(img)
    for fn in sorted(os.listdir('asset/sprites/drawn')):
        if fn.endswith('.png'):
            assets['img']['drawn/' + fn[:-4]] = png_uri(Image.open(os.path.join('asset/sprites/drawn', fn)).convert('RGBA'))
    for k, u in assets['img'].items():
        if k not in ('BattleFont', 'DamageFont', 'DefaultFont'):
            im = uri_img(u)
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
