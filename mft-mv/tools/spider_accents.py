"""Per-section 16th-slot accent profiles + stop-time detection + click-track check file.

usage: python tools/spider_accents.py
writes work/music/accents.json, work/music/click_check.wav
"""
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

ROOT = r"D:\GitHub Cave\mft-mv"
W = ROOT + r"\work\music"
y2, sr = sf.read(W + r"\spider.wav")
y = y2.mean(1)
P = 60 / 115 / 4
T0 = 0.08453
hop = 44
FR = hop / sr


def bp(x, lo=None, hi=None):
    if lo and hi:
        sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    elif lo:
        sos = butter(4, lo, btype="high", fs=sr, output="sos")
    else:
        sos = butter(4, hi, btype="low", fs=sr, output="sos")
    return sosfiltfilt(sos, x)


def attack(x):
    n = len(x) // hop
    e = 10 * np.log10((x[: n * hop] ** 2).reshape(n, hop).mean(1) + 1e-12)
    c = np.cumsum(np.r_[0, e])
    i = np.arange(n)
    a = np.maximum(0, i - 12)
    prev = np.where(i > 0, (c[i] - c[a]) / np.maximum(1, i - a), e[0])
    return np.maximum(0, e - prev)


D = {"low": attack(bp(y, 30, 150)), "mid": attack(bp(y, 150, 2500)), "high": attack(bp(y, 5000))}
nslot = int((len(y) / sr - T0) / P)
A = {}
for k, d in D.items():
    v = np.zeros(nslot)
    for s in range(nslot):
        t = T0 + s * P
        a, b = int((t - 0.010) / FR), int((t + 0.025) / FR)
        v[s] = d[max(0, a): b].max()
    A[k] = v

sections = {
    "A (0-14, no stop bars)": [b for b in range(15) if b not in (3, 7, 11)],
    "A stop-time bars 3/7/11": [3, 7, 11],
    "break 15": [15],
    "B1 16-23": list(range(16, 24)),
    "B2 24-31": list(range(24, 32)),
    "C1a 32-35": list(range(32, 36)),
    "C1b 36-39": list(range(36, 40)),
    "C2 40-46": list(range(40, 47)),
    "turnaround 47": [47],
    "A' 48": [48],
}
out = {"origin": T0, "sixteenth": P, "profiles": {}, "bar_high_attack": [], "bar_low_attack": []}
for name, bars in sections.items():
    prof = {}
    for k in A:
        m = np.array([A[k][b * 16: b * 16 + 16] for b in bars]).mean(0)
        prof[k] = [round(float(x), 1) for x in m]
        order = np.argsort(m)[::-1]
        prof[k + "_top"] = [int(i) for i in order[:6]]
    out["profiles"][name] = prof
for b in range(nslot // 16):
    out["bar_high_attack"].append(round(float(A["high"][b * 16: b * 16 + 16].mean()), 1))
    out["bar_low_attack"].append(round(float(A["low"][b * 16: b * 16 + 16].mean()), 1))
json.dump(out, open(W + r"\accents.json", "w"), indent=1)
for name, pr in out["profiles"].items():
    print(f"== {name}")
    for k in ("low", "mid", "high"):
        print(f"   {k:4s} " + " ".join(f"{x:4.0f}" for x in pr[k]) + f"   top {pr[k + '_top']}")
print("bar high-band attack:", out["bar_high_attack"])
print("bar low-band attack:", out["bar_low_attack"])

click = np.zeros_like(y)
for s in range(nslot + 1):
    t = T0 + s * P
    i = int(round(t * sr))
    if i >= len(y):
        break
    if s % 16 == 0:
        f, amp, L = 1600, 0.5, 0.03
    elif s % 4 == 0:
        f, amp, L = 1000, 0.35, 0.02
    elif s % 2 == 0:
        f, amp, L = 2500, 0.12, 0.01
    else:
        continue
    n = int(L * sr)
    tt = np.arange(n) / sr
    burst = amp * np.sin(2 * np.pi * f * tt) * np.exp(-tt / (L / 4))
    click[i: i + n] += burst[: max(0, len(y) - i)]
mix = np.c_[0.6 * y2[:, 0] + click, 0.6 * y2[:, 1] + click]
mix /= max(1.0, np.abs(mix).max())
sf.write(W + r"\click_check.wav", mix, sr)
print("click track written")
