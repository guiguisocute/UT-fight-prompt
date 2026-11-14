"""Capture every finished speech bubble and battle text box in asset/record.mp4.

Track the amount of "ink" (text pixels) inside the bubble / text box: typing makes it grow, the next
text makes it drop. A capture = the frame with the most ink right before a drop or before the box vanishes.
usage: python tools/record_bubbles.py
writes work/music/lines/bub_all_XX.png, box_all_XX.png and captures.json (timestamps in record.mp4)
"""
import json
import subprocess
import numpy as np
from PIL import Image, ImageDraw

ROOT = r"D:\GitHub Cave\mft-mv"
SRC = ROOT + r"\asset\record\record.mp4"
OUT = ROOT + r"\work\music\lines"
FPS = 10
REGIONS = {"bub": (1120, 30, 560, 250), "box": (300, 560, 1300, 310)}


def frames(x, y, w, h):
    cmd = ["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"fps={FPS},crop={w}:{h}:{x}:{y}",
           "-f", "rawvideo", "-pix_fmt", "gray", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w)


caps = {}
for name, (x, y, w, h) in REGIONS.items():
    F = frames(x, y, w, h)
    s = F[:, ::2, ::2]
    if name == "bub":
        present = (s > 200).mean((1, 2)) > 0.30
        ink = ((s < 90) & present[:, None, None]).mean((1, 2))
    else:
        col = F[:, 20:290, 25:40]
        present = (col > 200).mean((1, 2)) > 0.08
        inner = s[:, 12:-12, 20:-20]
        ink = ((inner > 160) & present[:, None, None]).mean((1, 2))
    keep = []
    run_best, run_ink = None, 0.0
    for t in range(len(F)):
        if not present[t]:
            if run_best is not None and run_ink > 0.002:
                keep.append(run_best)
            run_best, run_ink = None, 0.0
            continue
        if run_best is not None and ink[t] < 0.6 * run_ink and run_ink > 0.002:
            keep.append(run_best)
            run_best, run_ink = None, 0.0
        if ink[t] >= run_ink:
            run_best, run_ink = t, ink[t]
    if run_best is not None and run_ink > 0.002:
        keep.append(run_best)
    caps[name] = [round(k / FPS, 1) for k in keep]
    cols = 4 if name == "bub" else 2
    scale = 1.0 if name == "bub" else 0.62
    tw, th = int(w * scale), int(h * scale)
    per = cols * 7
    for p in range(0, len(keep), per):
        chunk = keep[p: p + per]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("L", (cols * (tw + 6), rows * (th + 24)), 70)
        d = ImageDraw.Draw(sheet)
        for q, k in enumerate(chunk):
            r, c = divmod(q, cols)
            sheet.paste(Image.fromarray(F[k]).resize((tw, th)), (c * (tw + 6), r * (th + 24) + 22))
            d.text((c * (tw + 6) + 4, r * (th + 24) + 4), f"t={k / FPS:.1f}s", fill=255)
        sheet.save(OUT + rf"\{name}_all_{p // per:02d}.png")
    print(name, len(keep), "captures")
json.dump(caps, open(OUT + r"\captures.json", "w"), indent=1)
print(json.dumps(caps))
