#!/usr/bin/env python3
"""Where does Battle Against a True Hero start in the gameplay recording, and
where does the in-game loop jump back to?

Matches the recording's audio against the mp3 with onset-envelope cross-
correlation (game SFX are sparse enough not to matter).

    .venv/Scripts/python tools/explore_record.py [asset/record.mp4]
"""
import os, subprocess, sys, tempfile
import numpy as np, librosa

REC = sys.argv[1] if len(sys.argv) > 1 else 'asset/record/record.mp4'
SONG = 'asset/music/Toby Fox - Battle Against A True Hero.mp3'
SR, HOP = 11025, 128

def load(path):
    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, 'a.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-ac', '1', '-ar', str(SR), wav], check=True)
        y, _ = librosa.load(wav, sr=SR, mono=True)
    return y

def feat(y):
    o = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    return (o - o.mean()) / (o.std() + 1e-9)

rec, song = load(REC), load(SONG)
fr, fs = feat(rec), feat(song)
fps = SR / HOP

def locate(song_t0, song_t1, rec_lo, rec_hi):
    """best position in the recording of the song excerpt [song_t0, song_t1)"""
    q = fs[int(song_t0 * fps):int(song_t1 * fps)]
    a, b = int(rec_lo * fps), int(rec_hi * fps)
    seg = fr[a:b]
    c = np.correlate(seg, q, mode='valid') / len(q)
    i = int(np.argmax(c))
    return (a + i) / fps - song_t0, float(c[i]), float(np.sort(c)[-50])

start, sc, bg = locate(19.2, 44.8, 60, 140)
print(f'song t=0 is at recording {start:.3f}s ({int(start // 60)}:{start % 60:05.2f})  corr {sc:.3f} (50th best {bg:.3f})')
for a in (44.8, 96.0, 115.2, 140.0):
    s, sc, bg = locate(a, a + 8, start + a - 3, start + a + 11)
    print(f'  check song {a:6.1f}s -> recording {s + a:8.3f}s  drift {(s - start) * 1000:+.1f} ms  corr {sc:.3f}')
# after the first pass: which song position does the recording play?
end1 = start + 153.6
print(f'first pass reaches bar 96 at recording {end1:.2f}s ({int(end1 // 60)}:{end1 % 60:05.2f})')
qa = int((end1 + 2) * fps)
for w in (2, 6, 10, 14):
    q = fr[int((end1 + w) * fps):int((end1 + w + 6) * fps)]
    c = np.correlate(fs, q, mode='valid') / len(q)
    i = int(np.argmax(c))
    pos = i / fps
    print(f'  recording {end1 + w:7.2f}s plays song {pos:7.2f}s = bar {(pos - 0.006) / 1.6:6.2f}  corr {c[i]:.3f}')
