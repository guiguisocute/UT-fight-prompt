"""Pack the game's own sound effects (the Undertale pack in ../mtt-mv/asset) into src/assets.js, next to
what tools/import_assets.py put there: each chosen file trimmed to the part that is used, mono 44.1 kHz,
mp3 - keyed by its name in the game (snd_b, mus_rimshot ...; a trimmed variant gets a suffix). Only the
sfx entries named here are added or replaced; the rest of assets.js is left as it is.

usage: python -I tools/import_sfx.py
"""
import base64
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(ROOT, 'asset', 'sfx', 'PC _ Computer - Undertale - Miscellaneous - Sound Effects')
OUT = os.path.join(ROOT, 'src', 'assets.js')

SFX = {
    'snd_b': ('snd_b', 0, 0.6),
    'snd_noise': ('snd_noise', 0, None),
    'snd_battlefall': ('snd_battlefall', 0, None),
    'snd_bombfall': ('snd_bombfall', 0, None),
    'snd_bomb': ('snd_bomb', 0, None),
    'snd_impact': ('snd_impact', 0, None),
    'snd_screenshake': ('snd_screenshake', 0, None),
    'snd_heartshot': ('snd_heartshot', 0, None),
    'mus_f_orchhit': ('mus_f_orchhit', 0, None),
    'snd_power': ('snd_power', 0, None),
    'snd_txt2': ('SND_TXT2', 0, 0.14),
    'snd_tem': ('snd_tem', 0, None), 'snd_tem2': ('snd_tem2', 0, None), 'snd_tem3': ('snd_tem3', 0, None),
    'mus_sfx_oh': ('mus_sfx_oh', 0, None),
    'mus_sfx_ahh': ('mus_sfx_ahh', 0, None),
    'mus_mt_yeah': ('mus_mt_yeah', 0, None),
    'snd_bluh': ('snd_bluh', 0, None),
    'snd_hurtsmall': ('snd_hurtsmall', 0, None),
    'mus_mett_cheer': ('mus_mett_cheer', 0, None),
    'mus_rimshot': ('mus_rimshot', 0, 1.2),
    'mus_wawa': ('mus_wawa', 0, 2.2),
    'mus_whoopee': ('mus_whoopee', 0, 1.0),
    'snd_slidewhist': ('snd_slidewhist', 0, None),
    'snd_squeak': ('snd_squeak', 0, None),
    'mus_cymbal_swell': ('mus_cymbal', 3.9, None),
    'snd_drumroll': ('snd_drumroll', 0, None),
    'mus_dununnn': ('mus_dununnn', 0, None),
    'mus_sfx_frypan': ('mus_sfx_frypan', 0, 0.8),
    'snd_punchstrong': ('snd_punchstrong', 0, 0.6),
    'snd_punchweak': ('snd_punchweak', 0, None),
    'mus_sfx_gigapunch': ('mus_sfx_gigapunch', 0, None),
    'mus_sfx_swipe': ('mus_sfx_swipe', 0, None),
    'mus_sfx_a_pullback': ('mus_sfx_a_pullback', 0, None),
    'mus_sfx_a_grab': ('mus_sfx_a_grab', 0, None),
    'mus_sfx_a_swordappear': ('mus_sfx_a_swordappear', 0, None),
    'mus_sfx_star': ('mus_sfx_star', 0, None),
    'mus_sfx_eyeflash': ('mus_sfx_eyeflash', 0, None),
    'snd_tearcard_rip': ('snd_tearcard', 0, 0.42),
    'snd_knock_1': ('snd_knock', 0, 0.2),
    'mus_crickets': ('mus_crickets', 0, 5.0),
    'mus_dooropen': ('mus_dooropen', 0, None),
    'snd_lightswitch': ('snd_lightswitch', 0, None),
    'snd_escaped': ('snd_escaped', 0, 0.8),
    'mus_note1': ('mus_note1', 0, None), 'mus_note3': ('mus_note3', 0, None), 'mus_note6': ('mus_note6', 0, None),
    'mus_mettsmash': ('mus_mettsmash', 0, None),
    'snd_splash': ('snd_splash', 0, 0.5),
    'snd_hurt1': ('snd_hurt1', 0, None),
    'snd_bell': ('snd_bell', 0, None),
    'mus_sfx_cinematiccut': ('mus_sfx_cinematiccut', 0, None),
    'snd_select': ('snd_select', 0, None), 'snd_movemenu': ('snd_movemenu', 0, None),
    'snd_swallow': ('snd_swallow', 0, None), 'snd_heal_c': ('snd_heal_c', 0, None),
    'snd_buyitem': ('snd_buyitem', 0, None),
    'snd_break1': ('snd_break1', 0, None), 'snd_break2': ('snd_break2', 0, None),
    'mus_sfx_segapower': ('mus_sfx_segapower', 0, None),
    'snd_heavydamage': ('snd_heavydamage', 0, 1.0),
    'mus_sfx_a_swipe': ('mus_sfx_a_swipe', 0, 0.6),
    'mus_mett_applause': ('mus_mett_applause', 0, 2.4),
}


def mp3(stem, ss, dur):
    src = next(os.path.join(PACK, f) for f in os.listdir(PACK) if os.path.splitext(f)[0] == stem)
    cmd = ['ffmpeg', '-v', 'error', '-ss', str(ss), '-i', src]
    if dur:
        cmd += ['-t', str(dur)]
    cmd += ['-af', 'afade=t=out:st=%.3f:d=0.012' % max(0, dur - 0.012) if dur else 'anull', '-ac', '1', '-ar', '44100', '-c:a', 'libmp3lame', '-b:a', '96k', '-f', 'mp3', '-']
    return subprocess.run(cmd, capture_output=True, check=True).stdout


s = open(OUT, encoding='utf-8').read()
head = s[: s.index('{')]
assets = json.loads(s[s.index('{'): s.rindex('}') + 1])
total = 0
for k, (stem, ss, dur) in SFX.items():
    b = mp3(stem, ss, dur)
    total += len(b)
    assets['sfx'][k] = 'data:audio/mpeg;base64,' + base64.b64encode(b).decode()
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(head + json.dumps(assets, separators=(',', ':')) + ';\n')
print(len(SFX), 'sounds,', total, 'bytes of mp3 ->', os.path.getsize(OUT), 'bytes', '(sfx now:', len(assets['sfx']), ')')
