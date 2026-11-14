"""Independent cross-checks of the tempo of spider dance.mp4.

1. robust regression of onset times onto a 16th grid  -> P, t0 with residuals
2. long-lag autocorrelation of the attack function (8 / 16 bars)
3. librosa beat tracker (no prior forcing)
4. fold images (bar-period folding) for 114.74 vs 115 BPM -> work/music/fold_*.png
"""
import json
import numpy as np
import soundfile as sf
import librosa
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt, find_peaks

ROOT = r"D:\GitHub Cave\mft-mv"
W = ROOT + r"\work\music"
y, sr = sf.read(W + r"\spider.wav")
y = y.mean(1)
hop = sr // 1000
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
    e = (x[: n * hop] ** 2).reshape(n, hop).mean(1)
    L = 10 * np.log10(e + 1e-10)
    c = np.cumsum(np.r_[0, L])
    idx = np.arange(n)
    a = np.maximum(0, idx - 12)
    prev = np.where(idx > 0, (c[idx] - c[a]) / np.maximum(1, idx - a), L[0])
    return np.maximum(0, L - prev)


D = attack(bp(y, 150, 2500)) + attack(bp(y, 5000))
tf = (np.arange(len(D)) + 0.5) * FR
pk, pr = find_peaks(D, prominence=4, distance=40)
ot = tf[pk]
ow = pr["prominences"]

out = {}

P = 15 / 115.0
for it in range(4):
    z = np.sum(ow * np.exp(2j * np.pi * ot / P))
    t0 = (np.angle(z) / (2 * np.pi) * P) % P
    k = np.round((ot - t0) / P)
    res = ot - (t0 + k * P)
    m = np.abs(res) < 0.025
    A = np.c_[np.ones(m.sum()), k[m]]
    sol, *_ = np.linalg.lstsq(A * ow[m, None], (ot[m]) * ow[m], rcond=None)
    t0, P = sol
    res = ot[m] - (t0 + k[m] * P)
out["regression"] = {
    "bpm": 15 / P,
    "sixteenth": P,
    "t0_mod": t0 % P,
    "t0_raw": t0,
    "n_used": int(m.sum()),
    "n_total": len(ot),
    "resid_ms_median_abs": float(np.median(np.abs(res)) * 1000),
}
for name, sel in (("first_half", ot[m] < 53), ("second_half", ot[m] >= 53)):
    kk = k[m][sel]
    tt = ot[m][sel]
    ww = ow[m][sel]
    s, *_ = np.linalg.lstsq(np.c_[np.ones(len(kk)), kk] * ww[:, None], tt * ww, rcond=None)
    out["regression"][name + "_bpm"] = 15 / s[1]

Dz = D - D.mean()
ac = {}
for bars in (4, 8, 16):
    for bpm in (114.74, 115.0):
        lag = bars * 4 * 60 / bpm
        lo, hi = int((lag - 0.15) / FR), int((lag + 0.15) / FR)
        vals = np.array([np.dot(Dz[:-L], Dz[L:]) for L in range(lo, hi)])
        best = (lo + np.argmax(vals)) * FR
        ac[f"{bars}bars_search_near_{bpm}"] = round(best, 4)
    ac[f"{bars}bars_expected_114.74"] = round(bars * 4 * 60 / 114.74, 4)
    ac[f"{bars}bars_expected_115"] = round(bars * 4 * 60 / 115, 4)
out["autocorr_lag_s"] = ac

oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=256)
tempo, beats = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=256, start_bpm=120, tightness=400)
bt = librosa.frames_to_time(beats, sr=sr, hop_length=256)
ib = np.diff(bt)
out["librosa"] = {
    "tempo": float(np.atleast_1d(tempo)[0]),
    "median_ibi": float(np.median(ib)),
    "bpm_from_median_ibi": float(60 / np.median(ib)),
    "bpm_from_span": float(60 * (len(bt) - 1) / (bt[-1] - bt[0])),
    "n_beats": len(bt),
}

json.dump(out, open(W + r"\tempo_check.json", "w"), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))

for bpm in (115.0, 114.82):
    bar = 240 / bpm
    t00 = out["regression"]["t0_mod"]
    nb = int((len(D) * FR - t00) / bar)
    cols = int(bar / FR)
    img = np.zeros((nb, cols))
    for b in range(nb):
        s = int((t00 + b * bar) / FR)
        seg = D[s: s + cols]
        img[b, : len(seg)] = seg
    plt.figure(figsize=(12, 6))
    plt.imshow(img, aspect="auto", cmap="magma", vmax=np.percentile(img, 99), interpolation="nearest",
               extent=[0, 16, nb, 0])
    plt.xticks(range(17))
    plt.xlabel("16th slot within bar")
    plt.ylabel("bar")
    plt.title(f"attack function folded at {bpm:.4f} BPM (t0={t00*1000:.1f} ms)")
    plt.grid(axis="x", color="w", alpha=0.25)
    plt.tight_layout()
    plt.savefig(W + rf"\fold_{bpm:.2f}.png", dpi=80)
    plt.close()
print("fold images written")
