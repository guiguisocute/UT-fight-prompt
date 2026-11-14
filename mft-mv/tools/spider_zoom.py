"""Origin refinement by slot-folded envelopes + zoomed 2-bar views (harmonic CQT / percussive STFT).

usage: python tools/spider_zoom.py [bar ...]
writes work/music/origin.json, work/music/zoom_XX.png
"""
import sys
import json
import numpy as np
import soundfile as sf
import librosa
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfiltfilt

ROOT = r"D:\GitHub Cave\mft-mv"
W = ROOT + r"\work\music"
y2, sr = sf.read(W + r"\spider.wav")
y = y2.mean(1)
P = 60 / 115 / 4
T0 = 0.0795


def bp(x, lo=None, hi=None):
    if lo and hi:
        sos = butter(4, [lo, hi], btype="band", fs=sr, output="sos")
    elif lo:
        sos = butter(4, lo, btype="high", fs=sr, output="sos")
    else:
        sos = butter(4, hi, btype="low", fs=sr, output="sos")
    return sosfiltfilt(sos, x)


res = {}
bars_loud = [b for b in list(range(0, 15)) + list(range(16, 32)) + list(range(40, 49))]
for name, (lo, hi) in {"hp4k": (4000, None), "mid": (300, 3000), "full": (40, None)}.items():
    x = bp(y, lo, hi)
    e = np.convolve(x ** 2, np.ones(22) / 22, mode="same")
    win = np.arange(int(-0.04 * sr), int(0.08 * sr))
    acc = np.zeros(len(win))
    n = 0
    for b in bars_loud:
        for s in range(16):
            c = int((T0 + (b * 16 + s) * P) * sr)
            if c + win[0] < 0 or c + win[-1] >= len(e):
                continue
            seg = e[c + win]
            acc += seg / (seg.mean() + 1e-12)
            n += 1
    acc /= n
    t_ms = win / sr * 1000
    base = acc[t_ms < -15].mean()
    peak_i = np.argmax(acc[(t_ms > -20) & (t_ms < 60)]) + np.flatnonzero(t_ms > -20)[0]
    pk = acc[peak_i]
    d = np.gradient(np.convolve(acc, np.ones(9) / 9, mode="same"))
    steep_i = np.argmax(d[(t_ms > -20) & (t_ms < 60)]) + np.flatnonzero(t_ms > -20)[0]

    def cross(frac):
        thr = base + frac * (pk - base)
        i = peak_i
        while i > 0 and acc[i - 1] > thr:
            i -= 1
        return float(t_ms[i])

    res[name] = {"rise10_ms": cross(0.1), "rise50_ms": cross(0.5), "steepest_ms": float(t_ms[steep_i]),
                 "peak_ms": float(t_ms[peak_i]), "peak_over_base": float(pk / base)}
    plt.plot(t_ms, acc, label=name)
plt.axvline(0, color="k")
plt.legend()
plt.xlabel("ms relative to provisional grid (T0=79.5 ms)")
plt.title("slot-folded envelope (loud bars)")
plt.grid(alpha=.3)
plt.savefig(W + r"\origin_fold.png", dpi=70)
plt.close()
json.dump(res, open(W + r"\origin.json", "w"), indent=1)
print(json.dumps(res, indent=1))

bars = [int(a) for a in sys.argv[1:]] or [0, 2, 14, 16, 24, 32, 36, 46, 48]
y22 = librosa.resample(y, orig_sr=sr, target_sr=22050)
yh, yp = librosa.effects.hpss(y22, margin=(1.0, 2.0))
hop = 64
C = np.abs(librosa.cqt(yh, sr=22050, hop_length=hop, fmin=librosa.note_to_hz("C2"), n_bins=12 * 6, bins_per_octave=12))
Cdb = librosa.amplitude_to_db(C, ref=np.max)
Sp = np.abs(librosa.stft(yp, n_fft=1024, hop_length=hop))
Spdb = librosa.amplitude_to_db(Sp, ref=np.max)
freqs = librosa.fft_frequencies(sr=22050, n_fft=1024)
names = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
T0f = T0 + res["hp4k"]["rise10_ms"] / 1000
for b0 in bars:
    ta, tb = T0f + b0 * 16 * P - 0.05, T0f + (b0 + 2) * 16 * P + 0.05
    fa, fb = int(ta * 22050 / hop), int(tb * 22050 / hop)
    fig, ax = plt.subplots(2, 1, figsize=(24, 13), gridspec_kw={"height_ratios": [3, 1.3]}, sharex=True)
    ax[0].imshow(Cdb[:, fa:fb], origin="lower", aspect="auto", cmap="magma", vmin=-50, vmax=0,
                 extent=[ta, tb, 36 - 0.5, 36 + 72 - 0.5], interpolation="nearest")
    ax[0].set_yticks(range(36, 108))
    ax[0].set_yticklabels([names[m % 12] + str(m // 12 - 1) for m in range(36, 108)], fontsize=6)
    lo_f = np.searchsorted(freqs, 30)
    ax[1].imshow(Spdb[lo_f:, fa:fb], origin="lower", aspect="auto", cmap="magma", vmin=-60, vmax=0,
                 extent=[ta, tb, 0, len(freqs) - lo_f], interpolation="nearest")
    ticks = [50, 100, 200, 500, 1000, 2000, 5000, 10000]
    ax[1].set_yticks([np.searchsorted(freqs, f) - lo_f for f in ticks])
    ax[1].set_yticklabels([str(f) for f in ticks], fontsize=7)
    for s in range(b0 * 16, (b0 + 2) * 16 + 1):
        t = T0f + s * P
        for a in ax:
            a.axvline(t, color="cyan", alpha=0.9 if s % 16 == 0 else (0.45 if s % 4 == 0 else 0.15),
                      lw=1.6 if s % 16 == 0 else 0.7)
        if s < (b0 + 2) * 16:
            ax[0].text(t + 0.01, 106, str(s % 16), color="w", fontsize=8)
    ax[0].set_title(f"bars {b0}-{b0 + 1}: harmonic CQT (top) / percussive STFT (bottom); slot numbers on top")
    plt.tight_layout()
    plt.savefig(W + rf"\zoom_{b0:02d}.png", dpi=55)
    plt.close()
print("origin T0 refined (hp4k rise10):", T0f)
