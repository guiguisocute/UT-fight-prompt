"""Tempo / phase / downbeat fit for asset/music/spider dance.mp4 (independent of analyze_spider.py).

Time-domain transient detection (1 ms frames, zero-phase band filters) -> circular-statistics
fit of a constant 16th-note grid -> per-window drift -> per-slot accent profiles.

usage: python tools/spider_grid.py   (reads work/music/spider.wav, writes work/music/grid.json)
"""
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfiltfilt, find_peaks

ROOT = r"D:\GitHub Cave\mft-mv"
WAV = ROOT + r"\work\music\spider.wav"
OUT = ROOT + r"\work\music\grid.json"

y, sr = sf.read(WAV)
y = y.mean(1)
dur = len(y) / sr
hop = 44
FR = hop / sr


def bandpass(x, lo=None, hi=None, order=4):
    if lo and hi:
        sos = butter(order, [lo, hi], btype="band", fs=sr, output="sos")
    elif lo:
        sos = butter(order, lo, btype="high", fs=sr, output="sos")
    else:
        sos = butter(order, hi, btype="low", fs=sr, output="sos")
    return sosfiltfilt(sos, x)


def attack_fn(x):
    """1 ms log-energy, rise against the previous 12 ms -> attack detection function."""
    n = len(x) // hop
    e = (x[: n * hop] ** 2).reshape(n, hop).mean(1)
    L = 10 * np.log10(e + 1e-10)
    past = np.full(n, -100.0)
    for k in range(1, 13):
        past = np.maximum(past, np.r_[np.full(k, -100.0), L[:-k]]) if k == 1 else past
    c = np.cumsum(np.r_[0, L])
    prev = np.empty(n)
    for i in range(n):
        a = max(0, i - 12)
        prev[i] = (c[i] - c[a]) / max(1, i - a) if i > 0 else L[0]
    d = np.maximum(0, L - prev)
    return d, L


bands = {
    "low": bandpass(y, 30, 150),
    "mid": bandpass(y, 150, 2500),
    "high": bandpass(y, 5000, None),
    "full": bandpass(y, 30, None),
}
det = {}
lev = {}
for k, x in bands.items():
    det[k], lev[k] = attack_fn(x)
tframes = (np.arange(len(det["full"])) + 0.5) * FR


def onsets(d, prom=3.0, dist_ms=40):
    pk, pr = find_peaks(d, prominence=prom, distance=dist_ms)
    times = []
    for p in pk:
        h = d[p] / 2
        q = p
        while q > 0 and p - q < 6 and d[q - 1] >= h:
            q -= 1
        times.append(tframes[q])
    return np.array(times), pr["prominences"]


ons = {k: onsets(det[k]) for k in det}


def circ(times, w, period):
    z = np.sum(w * np.exp(2j * np.pi * times / period))
    return np.abs(z) / np.sum(w), np.angle(z)


t_all = np.r_[ons["high"][0], ons["mid"][0]]
w_all = np.r_[ons["high"][1], ons["mid"][1]]
bpms = np.arange(100, 130, 0.0025)
R = np.array([circ(t_all, w_all, 15 / b)[0] for b in bpms])
best = bpms[np.argmax(R)]
fine = np.arange(best - 0.05, best + 0.05, 0.0001)
Rf = np.array([circ(t_all, w_all, 15 / b)[0] for b in fine])
bpm = fine[np.argmax(Rf)]
P = 15 / bpm
r, ang = circ(t_all, w_all, P)
phase16 = (ang / (2 * np.pi) * P) % P
top = np.argsort(R)[::-1]
cands = []
for i in top:
    if all(abs(bpms[i] - c) > 0.5 for c, _ in cands):
        cands.append((bpms[i], R[i]))
    if len(cands) == 6:
        break

drift = []
for t0 in np.arange(0, dur - 6, 6):
    m = (t_all >= t0) & (t_all < t0 + 12)
    if m.sum() < 20:
        continue
    rr, aa = circ(t_all[m], w_all[m], P)
    ph = (aa / (2 * np.pi) * P) % P
    dph = (ph - phase16 + P / 2) % P - P / 2
    drift.append([round(t0, 1), round(dph * 1000, 2), round(rr, 3), int(m.sum())])

P115 = 15 / 115
r115, a115 = circ(t_all, w_all, P115)
ph115 = (a115 / (2 * np.pi) * P115) % P115
drift115 = []
for t0 in np.arange(0, dur - 6, 6):
    m = (t_all >= t0) & (t_all < t0 + 12)
    if m.sum() < 20:
        continue
    rr, aa = circ(t_all[m], w_all[m], P115)
    ph = (aa / (2 * np.pi) * P115) % P115
    drift115.append([round(t0, 1), round(((ph - ph115 + P115 / 2) % P115 - P115 / 2) * 1000, 2)])

band_phase = {}
for k in ons:
    rr, aa = circ(ons[k][0], ons[k][1], P115)
    band_phase[k] = [round(((aa / (2 * np.pi) * P115) % P115) * 1000, 2), round(rr, 3), len(ons[k][0])]

nslot = int(np.floor((dur - ph115) / P115)) + 1
acc = {k: np.zeros(nslot) for k in det}
for k in det:
    d = det[k]
    for s in range(nslot):
        t = ph115 + s * P115
        a, b = int((t - 0.012) / FR), int((t + 0.020) / FR)
        a, b = max(0, a), min(len(d), b)
        acc[k][s] = d[a:b].max() if b > a else 0
first_sound = 0.079342
first_slot = int(np.round((first_sound - ph115) / P115))

profiles = {}
for k in ("low", "mid", "high", "full"):
    a = acc[k][: (nslot // 16) * 16]
    prof = []
    for s0 in range(16):
        seg = a[s0: s0 + ((len(a) - s0) // 16) * 16].reshape(-1, 16).mean(0)
        prof.append(seg)
    profiles[k] = np.array(prof)

res = {
    "duration_wav": dur,
    "first_sound": first_sound,
    "bpm_fit": round(float(bpm), 4),
    "R_fit": round(float(r), 4),
    "candidates": [[round(float(b), 3), round(float(v), 4)] for b, v in cands],
    "phase16_fit_ms": round(float(phase16) * 1000, 3),
    "phase16_115_ms": round(float(ph115) * 1000, 3),
    "R_115": round(float(r115), 4),
    "drift_fit_ms": drift,
    "drift_115_ms": drift115,
    "band_phase_115_ms": band_phase,
    "first_sound_slot": first_slot,
    "n_onsets": {k: len(v[0]) for k, v in ons.items()},
}
json.dump(res, open(OUT, "w"), indent=1)
np.savez(ROOT + r"\work\music\grid_acc.npz", **{k: acc[k] for k in acc}, ph=ph115, P=P115)

print(json.dumps({k: v for k, v in res.items() if not k.startswith("drift")}, indent=1))
print("drift @fit (t0, dphase ms, R, n):", drift)
print("drift @115 (t0, dphase ms):", drift115)
print("first sound slot (rel. ph115):", first_slot, " slot time:", ph115 + first_slot * P115)
for k in ("low", "mid", "high"):
    a = acc[k][first_slot: first_slot + ((nslot - first_slot) // 16) * 16].reshape(-1, 16)
    print(k, "mean accent by slot (bar starts at first sound):", np.round(a.mean(0), 1).tolist())
