"""Full music analysis of asset/music/spider dance.mp4 on the verified 115 BPM grid.

writes work/music/music.json, work/music/bars.txt, work/music/roll_*.png, work/music/overview.png
usage: python tools/spider_music.py
"""
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
NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]


def nn(m):
    return NAMES[int(m) % 12] + str(int(m) // 12 - 1) if m >= 0 else "."


y2, sr = sf.read(W + r"\spider.wav")
y = y2.mean(1)
side = (y2[:, 0] - y2[:, 1]) / 2
dur = len(y) / sr
BPM = 115.0
P = 60 / BPM / 4


def bp(x, lo=None, hi=None, order=4):
    if lo and hi:
        sos = butter(order, [lo, hi], btype="band", fs=sr, output="sos")
    elif lo:
        sos = butter(order, lo, btype="high", fs=sr, output="sos")
    else:
        sos = butter(order, hi, btype="low", fs=sr, output="sos")
    return sosfiltfilt(sos, x)


hp = bp(y, 1500)
env = np.convolve(np.abs(hp), np.ones(13) / 13, mode="same")
t0_guess = 0.0795
offs, strength = [], []
k = 0
while True:
    t = t0_guess + k * P
    if t + 0.05 > dur:
        break
    a, b = int((t - 0.035) * sr), int((t + 0.045) * sr)
    if a > int(0.045 * sr):
        seg = env[a:b]
        pk = np.argmax(seg)
        floor = np.median(env[int((t - 0.045) * sr): int((t - 0.012) * sr)])
        peak = seg[pk]
        if peak > 6 * floor and peak > 0.01:
            thr = floor + 0.15 * (peak - floor)
            q = pk
            while q > 0 and seg[q - 1] > thr:
                q -= 1
            offs.append((a + q) / sr - t)
            strength.append(peak / (floor + 1e-9))
    k += 1
offs = np.array(offs)
st = np.array(strength)
good = st > np.percentile(st, 50)
t0 = 0.08453
first_attack = None
i = np.flatnonzero(env > 0.005)
first_attack = i[0] / sr if len(i) else None
grid_info = {
    "bpm": BPM,
    "sixteenth": P,
    "beat": 4 * P,
    "bar": 16 * P,
    "origin": t0,
    "origin_offsets_ms_median": float(np.median(offs[good]) * 1000),
    "origin_offsets_ms_iqr": [float(np.percentile(offs[good], 25) * 1000), float(np.percentile(offs[good], 75) * 1000)],
    "n_attacks_used": int(good.sum()),
    "first_attack_hp": first_attack,
}
nbar = int(np.floor((dur - t0) / (16 * P) + 1e-6))
nslot = int(np.floor((dur - t0) / P))
grid_info["bars_whole"] = nbar
grid_info["remainder_after_bars_s"] = dur - (t0 + nbar * 16 * P)
slot_t = t0 + np.arange(nslot) * P


def seg_db(x, a, b):
    s = x[max(0, int(a * sr)): int(b * sr)]
    return 10 * np.log10(np.mean(s ** 2) + 1e-12)


bands = {"low": bp(y, 25, 180), "mid": bp(y, 180, 3000), "high": bp(y, 5000)}
full_db = np.array([seg_db(y, t, t + P) for t in slot_t])
side_db = np.array([seg_db(side, t, t + P) for t in slot_t])
band_db = {k2: np.array([seg_db(x, t, t + P) for t in slot_t]) for k2, x in bands.items()}

y22 = librosa.resample(y, orig_sr=sr, target_sr=22050)
sr2 = 22050
yh, yp = librosa.effects.hpss(y22, margin=(1.0, 2.0))
hop = 128
fr_t = librosa.frames_to_time(np.arange(1 + len(y22) // hop), sr=sr2, hop_length=hop)


def attack_curve(x, lo, hi):
    if hi and hi >= sr2 / 2:
        hi = None
    if lo and hi:
        sos = butter(4, [lo, hi], btype="band", fs=sr2, output="sos")
    elif lo:
        sos = butter(4, lo, btype="high", fs=sr2, output="sos")
    else:
        sos = butter(4, hi, btype="low", fs=sr2, output="sos")
    z = sosfiltfilt(sos, x)
    n = len(z) // hop
    e = 10 * np.log10((z[: n * hop] ** 2).reshape(n, hop).mean(1) + 1e-12)
    prev = np.convolve(e, np.ones(4) / 4, mode="full")[:n]
    prev = np.r_[e[0], prev[:-1]]
    return np.maximum(0, e - prev), e


drum_def = {"kick": (35, 110), "snare": (160, 320), "snap": (1800, 5000), "hat": (7000, None)}
drum_att = {}
for name, (lo, hi) in drum_def.items():
    d, _ = attack_curve(yp, lo, hi)
    vals = np.zeros(nslot)
    for s, t in enumerate(slot_t):
        a, b = int((t - 0.012) * sr2 / hop), int((t + 0.03) * sr2 / hop)
        vals[s] = d[max(0, a): b].max() if b > a else 0
    drum_att[name] = vals
harm_att = np.zeros(nslot)
dh, _ = attack_curve(yh, 200, 4000)
for s, t in enumerate(slot_t):
    a, b = int((t - 0.012) * sr2 / hop), int((t + 0.03) * sr2 / hop)
    harm_att[s] = dh[max(0, a): b].max()

fmin = librosa.note_to_hz("C1")
C = np.abs(librosa.cqt(yh, sr=sr2, hop_length=hop, fmin=fmin, n_bins=36 * 8, bins_per_octave=36))
tuning = librosa.estimate_tuning(y=yh, sr=sr2)
Cs = C.reshape(8 * 12, 3, -1).max(1)
midi0 = 24
Cdb = librosa.amplitude_to_db(Cs, ref=np.max)
Sal = np.zeros_like(Cs)
for h, wgt in zip(range(1, 7), [1, 0.8, 0.64, 0.5, 0.4, 0.33]):
    sh = int(round(12 * np.log2(h)))
    Sal[: Cs.shape[0] - sh] += wgt * Cs[sh:]


def slot_frames(t, a=0.01, b=0.85):
    return int((t + a * P) * sr2 / hop), int((t + b * P) * sr2 / hop)


chroma = librosa.feature.chroma_cqt(C=C, bins_per_octave=36, n_chroma=12)
slot_chroma = np.zeros((nslot, 12))
lead = np.full(nslot, -1)
lead_conf = np.zeros(nslot)
bass = np.full(nslot, -1)
for s, t in enumerate(slot_t):
    a, b = slot_frames(t)
    b = max(b, a + 1)
    slot_chroma[s] = chroma[:, a:b].mean(1)
    sal = Sal[:, a:b].mean(1)
    lo, hi = 60 - midi0, 96 - midi0
    v = sal[lo:hi]
    j = np.argmax(v)
    lead[s] = midi0 + lo + j
    lead_conf[s] = v[j] / (np.median(v) + 1e-9)
    cb = Cs[28 - midi0: 56 - midi0, a:b].mean(1)
    bass[s] = 28 + np.argmax(cb)

tmpl = {}
for r in range(12):
    for q, ivs in {"": (0, 4, 7), "m": (0, 3, 7), "dim": (0, 3, 6), "7": (0, 4, 7, 10), "m7": (0, 3, 7, 10),
                   "maj7": (0, 4, 7, 11), "sus4": (0, 5, 7), "5": (0, 7)}.items():
        v = np.zeros(12)
        for iv in ivs:
            v[(r + iv) % 12] = 1
        v[r] += 0.5
        tmpl[NAMES[r] + q] = v / np.linalg.norm(v)
tn = list(tmpl)
TM = np.array([tmpl[k2] for k2 in tn])
nbeat = nslot // 4
beat_chord, beat_score = [], []
for bt in range(nbeat):
    c = slot_chroma[bt * 4: bt * 4 + 4].mean(0)
    c = c / (np.linalg.norm(c) + 1e-9)
    sc = TM @ c
    j = np.argmax(sc)
    beat_chord.append(tn[j])
    beat_score.append(float(sc[j]))
bar_chord = []
for b in range(nbar):
    c = slot_chroma[b * 16: b * 16 + 16].mean(0)
    c = c / (np.linalg.norm(c) + 1e-9)
    sc = TM @ c
    order = np.argsort(sc)[::-1][:2]
    bar_chord.append([tn[order[0]], round(float(sc[order[0]]), 3), tn[order[1]], round(float(sc[order[1]]), 3)])

KKmaj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KKmin = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def key_of(ch):
    best = []
    for r in range(12):
        best.append((np.corrcoef(np.roll(KKmaj, r), ch)[0, 1], NAMES[r] + " major"))
        best.append((np.corrcoef(np.roll(KKmin, r), ch)[0, 1], NAMES[r] + " minor"))
    best.sort(reverse=True)
    return [(b[1], round(float(b[0]), 3)) for b in best[:3]]


key_all = key_of(slot_chroma[: nbar * 16].sum(0))

feat = []
for b in range(nbar):
    s0 = b * 16
    ch = slot_chroma[s0: s0 + 16]
    ch = ch / (np.linalg.norm(ch, axis=1, keepdims=True) + 1e-9)
    dr = np.c_[drum_att["kick"][s0: s0 + 16], drum_att["snare"][s0: s0 + 16], drum_att["hat"][s0: s0 + 16]]
    dr = dr / (np.linalg.norm(dr) + 1e-9)
    f = np.r_[ch.ravel(), 2 * dr.ravel()]
    feat.append(f / np.linalg.norm(f))
feat = np.array(feat)
SSM = feat @ feat.T
similar = []
for b in range(nbar):
    order = [j for j in np.argsort(SSM[b])[::-1] if j != b][:4]
    similar.append([(int(j), round(float(SSM[b, j]), 3)) for j in order])


def novelty(S, L):
    n = len(S)
    kern = np.kron(np.array([[1, -1], [-1, 1]]), np.ones((L, L)))
    out = np.zeros(n)
    for i in range(L, n - L + 1):
        out[i] = np.sum(S[i - L: i + L, i - L: i + L] * kern)
    return out


nov2, nov4 = novelty(SSM, 2), novelty(SSM, 4)

loud_ref = np.percentile(full_db, 99)
bars = []
for b in range(nbar):
    s0 = b * 16
    sl = slice(s0, s0 + 16)
    bdb = 10 * np.log10(np.mean(10 ** (full_db[sl] / 10)))

    def hits(name, rel=0.55):
        v = drum_att[name][sl]
        thr = max(rel * np.percentile(drum_att[name], 98), 2.0)
        return [int(i) for i in np.flatnonzero(v > thr)]

    bars.append({
        "bar": b,
        "t": round(float(t0 + b * 16 * P), 3),
        "db": round(float(bdb - loud_ref), 1),
        "low": round(float(10 * np.log10(np.mean(10 ** (band_db["low"][sl] / 10))) - loud_ref), 1),
        "mid": round(float(10 * np.log10(np.mean(10 ** (band_db["mid"][sl] / 10))) - loud_ref), 1),
        "high": round(float(10 * np.log10(np.mean(10 ** (band_db["high"][sl] / 10))) - loud_ref), 1),
        "side": round(float(10 * np.log10(np.mean(10 ** (side_db[sl] / 10))) - loud_ref), 1),
        "kick": hits("kick"),
        "snare": hits("snare"),
        "snap": hits("snap"),
        "hat": hits("hat"),
        "harm_on": [int(i) for i in np.flatnonzero(harm_att[sl] > max(0.55 * np.percentile(harm_att, 98), 2.0))],
        "chord": bar_chord[b],
        "beats": beat_chord[b * 4: b * 4 + 4],
        "bass": [nn(m) for m in bass[sl][::2]],
        "lead": [nn(m) if c > 2.2 else "." for m, c in zip(lead[sl], lead_conf[sl])],
        "similar": similar[b],
        "nov2": round(float(nov2[b]), 2),
        "nov4": round(float(nov4[b]), 2),
    })

res = {"grid": grid_info, "tuning_semitones": float(tuning), "key": key_all, "bars": bars,
       "slot_db": [round(float(v - loud_ref), 2) for v in full_db]}
json.dump(res, open(W + r"\music.json", "w"), indent=1, ensure_ascii=False)
np.savez(W + r"\music_arrays.npz", Sal=Sal, Cdb=Cdb, chroma=chroma, slot_chroma=slot_chroma, lead=lead,
         lead_conf=lead_conf, bass=bass, full_db=full_db, SSM=SSM, fr_t=fr_t, slot_t=slot_t,
         **{"att_" + k2: v for k2, v in drum_att.items()}, harm_att=harm_att)

with open(W + r"\bars.txt", "w", encoding="utf-8") as f:
    f.write(json.dumps(grid_info, indent=1) + "\n")
    f.write("key: %s  tuning %.2f\n\n" % (key_all, tuning))
    for r in bars:
        f.write("bar %2d  t=%7.3f  dB %5.1f (L %5.1f M %5.1f H %5.1f S %5.1f)  nov %.1f/%.1f  chord %s | beats %s\n" % (
            r["bar"], r["t"], r["db"], r["low"], r["mid"], r["high"], r["side"], r["nov2"], r["nov4"],
            r["chord"], r["beats"]))
        f.write("   kick %s | snare %s | snap %s | hat %s | harm %s\n" % (r["kick"], r["snare"], r["snap"], r["hat"], r["harm_on"]))
        f.write("   bass(8ths) %s\n" % " ".join(r["bass"]))
        f.write("   lead(16ths) %s\n" % " ".join(r["lead"]))
        f.write("   similar %s\n" % r["similar"])
print(json.dumps(grid_info, indent=1))
print("key", key_all, "tuning", tuning)

fig, ax = plt.subplots(3, 1, figsize=(14, 12), gridspec_kw={"height_ratios": [1, 1, 2.2]})
xb = np.arange(nbar)
ax[0].plot(xb, [r["db"] for r in bars], "k-o", label="full")
for k2, c in (("low", "tab:red"), ("mid", "tab:green"), ("high", "tab:blue"), ("side", "tab:purple")):
    ax[0].plot(xb, [r[k2] for r in bars], "-", color=c, label=k2)
ax[0].set_xticks(xb)
ax[0].grid(alpha=.3)
ax[0].legend(ncol=5, fontsize=8)
ax[0].set_title("per-bar level (dB rel. 99th pct 16th)")
ax[1].plot(xb, nov2, label="novelty L=2")
ax[1].plot(xb, nov4, label="novelty L=4")
ax[1].set_xticks(xb)
ax[1].grid(alpha=.3)
ax[1].legend()
ax[2].imshow(SSM, cmap="viridis", interpolation="nearest")
ax[2].set_xticks(xb[::2])
ax[2].set_yticks(xb[::2])
ax[2].set_title("bar self-similarity (chroma x16 + drums)")
plt.tight_layout()
plt.savefig(W + r"\overview.png", dpi=72)
plt.close()

for blk in range(0, nbar, 8):
    ta, tb = t0 + blk * 16 * P, t0 + min(nbar, blk + 8) * 16 * P
    fa, fb = int(ta * sr2 / hop), int(tb * sr2 / hop)
    lo, hi = 33 - midi0, 97 - midi0
    img = librosa.amplitude_to_db(Sal[lo:hi, fa:fb], ref=np.max(Sal))
    fig, axx = plt.subplots(2, 1, figsize=(22, 9), gridspec_kw={"height_ratios": [4, 1]}, sharex=True)
    axx[0].imshow(img, origin="lower", aspect="auto", cmap="magma", vmin=-38, vmax=0,
                  extent=[ta, tb, 33 - 0.5, 97 - 0.5], interpolation="nearest")
    for s in range(blk * 16, min(nbar, blk + 8) * 16 + 1):
        tt = t0 + s * P
        axx[0].axvline(tt, color="w", alpha=0.6 if s % 16 == 0 else (0.25 if s % 4 == 0 else 0.07), lw=1.2 if s % 16 == 0 else 0.6)
    for m in range(36, 97, 12):
        axx[0].axhline(m - 0.5, color="c", alpha=0.3, lw=0.5)
    axx[0].set_yticks(range(33, 97, 3))
    axx[0].set_yticklabels([nn(m) for m in range(33, 97, 3)], fontsize=7)
    axx[0].set_title(f"harmonic salience bars {blk}-{min(nbar, blk + 8) - 1}")
    ss = np.arange(blk * 16, min(nbar, blk + 8) * 16)
    for nm, c in (("kick", "r"), ("snare", "g"), ("hat", "b"), ("snap", "orange")):
        axx[1].plot(slot_t[ss], drum_att[nm][ss], "-", color=c, label=nm, lw=0.8)
    axx[1].legend(ncol=4, fontsize=7)
    for b in range(blk, min(nbar, blk + 8) + 1):
        axx[1].axvline(t0 + b * 16 * P, color="k", alpha=0.5)
        if b < min(nbar, blk + 8):
            axx[0].text(t0 + b * 16 * P + 0.03, 95, str(b), color="w", fontsize=10)
    plt.tight_layout()
    plt.savefig(W + rf"\roll_{blk:02d}.png", dpi=60)
    plt.close()
print("done")
