from pathlib import Path
import sys, json, csv
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'work' / 'audio-libs'))
import av
import numpy as np
import librosa
from scipy.optimize import differential_evolution, minimize_scalar
from scipy.signal import butter, sosfilt
import matplotlib.pyplot as plt

SRC = ROOT / 'asset/music/spider dance.mp4'
OUT = ROOT / 'src'
WORK = ROOT / 'work'
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)
SR = 22050
HOP = 256

container = av.open(str(SRC))
metadata = {
    'duration': float(container.duration / av.time_base),
    'streams': [
        {'type': s.type, 'codec': s.codec_context.name, 'duration': float(s.duration * s.time_base) if s.duration else None}
        for s in container.streams
    ],
}
stream = next(s for s in container.streams if s.type == 'audio')
resampler = av.AudioResampler(format='s16', layout='mono', rate=SR)
chunks = []
for frame in container.decode(stream):
    for out in resampler.resample(frame):
        chunks.append(out.to_ndarray().reshape(-1))
for out in resampler.resample(None):
    chunks.append(out.to_ndarray().reshape(-1))
y = np.concatenate(chunks).astype(np.float32) / 32768.0
container.close()
duration = len(y) / SR

onset = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP, n_fft=2048)
times = librosa.times_like(onset, sr=SR, hop_length=HOP)
tempo = librosa.feature.tempo(onset_envelope=onset, sr=SR, hop_length=HOP, aggregate=np.median)
btempo, beats = librosa.beat.beat_track(onset_envelope=onset, sr=SR, hop_length=HOP)

def grid_score(bpm, phase):
    step = 60.0 / bpm / 4.0
    n = int((duration - phase) / step)
    tt = phase + np.arange(n + 1) * step
    vals = np.interp(tt, times, onset, left=0, right=0)
    return float(np.mean(np.sqrt(np.maximum(vals, 0))))

res = differential_evolution(lambda x: -grid_score(x[0], x[1]), [(112, 118), (0, 0.135)], tol=1e-8, seed=59, polish=True)
bpm, phase = map(float, res.x)
fitted_bpm = bpm
bpm = 115.0
s16 = 60.0 / bpm / 4.0
beat = s16 * 4
bar = s16 * 16
phase %= s16
onset_phase = phase
nominal_bars = round((metadata['duration'] - phase) / bar)
phase = metadata['duration'] - nominal_bars * bar

rms_hr = librosa.feature.rms(y=y, frame_length=128, hop_length=32, center=False)[0]
noise = np.median(rms_hr[:min(100, len(rms_hr))])
threshold = max(noise * 8, np.max(rms_hr) * 0.002)
idx = int(np.argmax(rms_hr > threshold))
first_transient = float(idx * 32 / SR)

n_slots = nominal_bars * 16
slot_centers = phase + np.arange(n_slots) * s16
S = np.abs(librosa.stft(y, n_fft=2048, hop_length=HOP))
freqs = librosa.fft_frequencies(sr=SR, n_fft=2048)
power = S * S
bands = {}
for name, lo, hi in [('low', 20, 180), ('mid', 180, 2000), ('high', 2000, 9000), ('full', 20, 11025)]:
    mask = (freqs >= lo) & (freqs < hi)
    curve = np.sqrt(np.sum(power[mask], axis=0))
    bands[name] = np.interp(slot_centers, times, curve, left=0, right=0)
for name, a in bands.items():
    q = np.percentile(a, 99)
    bands[name] = np.clip(a / max(q, 1e-9), 0, 1.2)

n_bars = int(np.ceil(n_slots / 16))
chroma = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
contrast = librosa.feature.spectral_contrast(y=y, sr=SR, hop_length=HOP)
mfcc = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=13, hop_length=HOP)
bar_features, bar_energy = [], []
for b in range(n_bars):
    t0, t1 = phase + b * bar, min(duration, phase + (b + 1) * bar)
    mask = (times >= t0) & (times < t1)
    if not np.any(mask):
        mask = np.argmin(np.abs(times - (t0 + t1) / 2))
    feat = np.concatenate([
        np.mean(chroma[:, mask], axis=1),
        np.mean(mfcc[:, mask], axis=1),
        np.mean(contrast[:, mask], axis=1),
        [np.mean(rms[mask])],
    ])
    bar_features.append(feat)
    bar_energy.append(float(np.sqrt(np.mean(y[int(t0*SR):max(int(t0*SR)+1, int(t1*SR))] ** 2))))
bar_features = np.array(bar_features)
bar_energy = np.array(bar_energy)
bf = bar_features.copy()
bf = (bf - bf.mean(axis=0)) / (bf.std(axis=0) + 1e-6)
boundaries = librosa.segment.agglomerative(bf.T, 12)
boundaries = sorted(set([0] + [int(x) for x in boundaries] + [n_bars]))

chroma_mean = np.mean(chroma, axis=1)
pitch_names = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
major = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
minor = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
def corr(a,b): return float(np.corrcoef(a,b)[0,1])
keys = []
for root in range(12):
    keys.append((corr(chroma_mean, np.roll(major, root)), pitch_names[root] + ' major'))
    keys.append((corr(chroma_mean, np.roll(minor, root)), pitch_names[root] + ' minor'))
keys.sort(reverse=True)

slots = {'full': bands['full'].round(5).tolist(), 'low': bands['low'].round(5).tolist(), 'mid': bands['mid'].round(5).tolist(), 'high': bands['high'].round(5).tolist()}
onset_slots = np.interp(slot_centers, times, onset, left=0, right=0)
slot_profile = [float(np.mean(onset_slots[np.arange(n_slots) % 16 == i])) for i in range(16)]
analysis = {
    'source': SRC.name,
    'duration': duration,
    'metadata': metadata,
    'sampleRate': SR,
    'bpm': bpm,
    'fittedBpm': fitted_bpm,
    'librosaTempo': float(np.atleast_1d(tempo)[0]),
    'beatTrackTempo': float(np.atleast_1d(btempo)[0]),
    'offset': phase,
    'fittedOnsetPhase': onset_phase,
    'firstTransient': first_transient,
    'sixteenth': s16,
    'beatLength': beat,
    'barLength': bar,
    'bars': n_bars,
    'keyEstimate': [{'key': k, 'correlation': round(c, 4)} for c,k in keys[:5]],
    'chromaMean': {pitch_names[i]: round(float(v), 5) for i,v in enumerate(chroma_mean)},
    'automaticSectionBoundaries': boundaries,
    'barEnergy': np.round(bar_energy / np.percentile(bar_energy, 99), 5).tolist(),
    'onsetSlotProfile': np.round(slot_profile, 5).tolist(),
    'slots': slots,
    'notes': 'Visual offset uses the exact 51-bar container duration. Centered STFT onset phase is retained only as a detection diagnostic.'
}
(OUT / 'analysis.json').write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding='utf-8')
with (OUT / 'music_grid.csv').open('w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['bar','beat','sixteenth','time','full','low','mid','high'])
    for i,t in enumerate(slot_centers):
        w.writerow([i//16, (i%16)//4, i%4, round(float(t),6), *[round(float(bands[k][i]),5) for k in ['full','low','mid','high']]])

fig, axes = plt.subplots(4, 1, figsize=(18, 11), sharex=True)
t_wave = np.arange(len(y))/SR
axes[0].plot(t_wave[::50], y[::50], lw=.35, color='#745186')
axes[0].set_title(f'Spider Dance — waveform | {bpm:.4f} BPM, fitted onset phase {phase:.4f}s')
axes[1].plot(times, onset, lw=.6, color='#d46a9f')
axes[1].set_title('Onset strength')
axes[2].imshow(chroma, aspect='auto', origin='lower', extent=[0,duration,0,12], cmap='magma')
axes[2].set_yticks(np.arange(12)+.5, pitch_names)
axes[2].set_title('Chromagram')
axes[3].plot(phase + (np.arange(n_bars)+.5)*bar, bar_energy/np.percentile(bar_energy,99), marker='o', ms=3, color='#5c86c9')
axes[3].set_title('Bar RMS (normalized)')
axes[3].set_xlabel('Seconds')
for ax in axes:
    for b in range(n_bars+1):
        ax.axvline(phase+b*bar, color='white' if ax==axes[2] else 'gray', alpha=.13, lw=.4)
    for b in boundaries:
        ax.axvline(phase+b*bar, color='#ffcc55', alpha=.8, lw=1)
fig.tight_layout()
fig.savefig(WORK / 'spider-analysis.png', dpi=150)

print(json.dumps({k:v for k,v in analysis.items() if k not in ['slots','barEnergy','chromaMean']}, ensure_ascii=False, indent=2))
print('BAR ENERGY')
for b,e in enumerate(bar_energy/np.percentile(bar_energy,99)):
    print(f'{b:02d} {phase+b*bar:7.3f}-{phase+(b+1)*bar:7.3f} {e:.3f}')
print('Wrote', OUT / 'analysis.json', OUT / 'music_grid.csv', WORK / 'spider-analysis.png')
