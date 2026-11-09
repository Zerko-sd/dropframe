"""beatgrid — find the song's beat grid, kick pattern and strongest sections.

usage: python3 beatgrid.py song.mp3 [--fps 30] [--out grid.json]

Prints and saves:
  bpm, period (s), offset (s)       one UNIFORM grid fitted to onset strength (drift-checked)
  frames_per_beat                   at --fps; start the edit on a downbeat so beats land on exact frames
  kick_by_beat_in_bar               mean low-band (kick) energy for beats 1..4 -> cut only on the strong ones
  weak_beats                        beat positions to avoid cutting on
  downbeat_phase                    which grid beat is "1"
  energy_by_bar                     to pick where the song is strongest / where the chorus drops
"""
import argparse, json
import numpy as np, librosa

ap = argparse.ArgumentParser()
ap.add_argument('song'); ap.add_argument('--fps', type=float, default=30); ap.add_argument('--out', default='grid.json')
ap.add_argument('--bpm-hint', type=float, default=None)
ap.add_argument('--downbeat', type=float, default=None, help='a known downbeat time (s); overrides the automatic guess')
a = ap.parse_args()

y, sr = librosa.load(a.song, sr=22050); hop = 128
oenv = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop, aggregate=np.median); fr = sr / hop
tempo, _ = librosa.beat.beat_track(onset_envelope=oenv, sr=sr, hop_length=hop, start_bpm=a.bpm_hint or 120)
P0 = 60.0 / float(np.atleast_1d(tempo)[0])
if a.bpm_hint is None and P0 < 0.45: P0 *= 2          # prefer the felt tempo over double-time
dur = len(y) / sr
def score(P, off, t0=4, t1=None):
    t1 = t1 or dur - 2
    ks = np.arange(np.ceil((t0 - off) / P), np.floor((t1 - off) / P))
    idx = np.round((off + ks * P) * fr).astype(int); idx = idx[idx < len(oenv)]
    return oenv[idx].mean() if len(idx) else 0
best = (0, P0, 0)
for P in np.linspace(P0 * 0.985, P0 * 1.015, 120):
    for off in np.arange(0, P, 0.004):
        s = score(P, off)
        if s > best[0]: best = (s, P, off)
_, P, off = best
# drift check: best local shift in 8 s windows
drift = []
for t0 in np.arange(4, dur - 10, 8):
    sh = np.arange(-0.12, 0.12, 0.005)
    drift.append(round(float(sh[int(np.argmax([score(P, off + d, t0, t0 + 8) for d in sh]))]) * 1000))
# kick / snare per beat-in-bar
S = np.abs(librosa.stft(y, hop_length=hop)); fq = librosa.fft_frequencies(sr=sr)
kick = S[fq < 150].sum(0); kick /= np.percentile(kick, 99)
beats = off + np.arange(0, int((dur - off) / P)) * P
def at(env, t): i = int(t * fr); return float(env[max(0, i - 2):i + 3].max()) if i < len(env) else 0.0
kb = np.array([at(kick, t) for t in beats])
# downbeat phase: the phase with the strongest chroma change on entry
chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
bf = librosa.time_to_frames(beats, sr=sr, hop_length=512); bf = bf[bf < chroma.shape[1]]
cs = librosa.util.sync(chroma, bf, aggregate=np.median); nov = np.r_[0, np.linalg.norm(np.diff(cs, axis=1), axis=0)]
kp = np.array([kb[p::4].mean() for p in range(4)]); nv = np.array([nov[p::4].mean() for p in range(4)])
score_ph = kp / kp.max() + 0.5 * nv / max(nv.max(), 1e-9)          # strongest kick, chroma change as tie-break
phase = int(np.argmax(score_ph))
if a.downbeat is not None: phase = int(round((a.downbeat - off) / P)) % 4
cands = sorted(range(4), key=lambda p: -score_ph[p])
kick_pat = [round(float(kb[(phase + i) % 4::4].mean()), 3) for i in range(4)]
weak = [i + 1 for i, v in enumerate(kick_pat) if v < 0.6 * max(kick_pat)]
rms = librosa.feature.rms(y=y, hop_length=512)[0]; rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
bars = beats[phase::4]
energy = [{'bar': i, 't': round(float(b), 3), 'rms': round(float(rms[(rt >= b) & (rt < b + 4 * P)].mean()), 3)} for i, b in enumerate(bars[:-1])]
res = {'bpm': round(60 / P, 3), 'period': P, 'offset': off, 'frames_per_beat': round(P * a.fps, 3),
       'downbeat_phase': phase, 'first_downbeat': round(float(beats[phase]), 3), 'drift_ms_by_8s': drift,
       'kick_by_beat_in_bar': kick_pat, 'weak_beats': weak, 'energy_by_bar': energy}
json.dump(res, open(a.out, 'w'), indent=1)
print(f"bpm {res['bpm']}  period {P:.4f}s  offset {off:.3f}s  -> {res['frames_per_beat']} frames/beat @ {a.fps:g}fps")
print(f"drift per 8s window (ms): {drift}")
print(f"kick by beat-in-bar: {kick_pat}  -> avoid cutting on beat(s) {weak}")
print(f"first downbeat at {res['first_downbeat']}s; saved {a.out}")
print('downbeat candidates (phase: first beat, score): ' + ', '.join(f"{p}: {beats[p]:.3f}s {score_ph[p]:.2f}" for p in cands))
print('-> if two scores are close, LISTEN: confirm against where the chorus drops and pass --downbeat <seconds>')
