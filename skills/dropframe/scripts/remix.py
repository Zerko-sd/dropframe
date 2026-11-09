"""remix — build-up + drop from the song itself. No stock sound effects.

usage: python3 remix.py song.mp3 --grid grid.json (--drop-time SECONDS | --drop-bar N) --bars-after M --out remix.wav [--build-bars 4]

  bars 1..(build-3):  time-varying low-pass sweep, muffled (~260 Hz) -> fully open, gentle level rise
  last build bar:     the bar's downbeat chopped into 16ths then 32nds, rising high-pass + gain, echo tail
  half a beat:        near-silence (the inhale)
  DROP:               the chorus downbeat with a decaying low-shelf boost (~+5 dB -> 0 over 2 bars)
The output starts exactly on a downbeat, so with the grid's frames_per_beat every beat is a frame boundary.
"""
import argparse, json
import numpy as np, subprocess
from scipy.signal import butter, sosfilt

ap = argparse.ArgumentParser()
ap.add_argument('song'); ap.add_argument('--grid', required=True); ap.add_argument('--drop-bar', type=int)
ap.add_argument('--drop-time', type=float, help='seconds in the song where the drop hits (snapped to the beat grid)')
ap.add_argument('--bars-after', type=int, default=8); ap.add_argument('--build-bars', type=int, default=4)
ap.add_argument('--out', default='remix.wav'); ap.add_argument('--shelf-db', type=float, default=5.0)
a = ap.parse_args()
g = json.load(open(a.grid)); P = g['period']; t1 = g['first_downbeat']
SR = 48000
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.song, '-ar', str(SR), '-ac', '2', '-f', 'f32le', '-'], capture_output=True).stdout
x = np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
S = lambda t: int(round(t * SR))
drop_t = (g['offset'] + round((a.drop_time - g['offset']) / P) * P) if a.drop_time is not None else t1 + a.drop_bar * 4 * P
B = a.build_bars * 4                                       # build length in beats
start_t = drop_t - B * P
build = x[S(start_t):S(drop_t)].copy()

def sweep_lpf(sig, f_of_t, block=256):
    out = np.zeros_like(sig); zi = None
    for i in range(0, len(sig), block):
        fc = min(f_of_t(i / SR), 20000)
        if fc >= 19000: out[i:i + block] = sig[i:i + block]; zi = None; continue
        sos = butter(4, fc / (SR / 2), 'low', output='sos')
        if zi is None: zi = np.zeros((sos.shape[0], 2, 2))
        out[i:i + block], zi = sosfilt(sos, sig[i:i + block], axis=0, zi=zi)
    return out
def f_lpf(t):
    b = t / P
    if b < 4: return 260 + 120 * b / 4
    u = min(max((b - 4) / (B - 6), 0), 1)
    return 380 * (19500 / 380) ** u ** 1.6

y = np.zeros((S((B + a.bars_after * 4) * P), 2))
pre = sweep_lpf(build[:S((B - 2) * P)], f_lpf); n = len(pre); tt = np.arange(n) / SR
gain = np.clip(tt / (1.5 * P), 0, 1) ** 2 * 10 ** ((-6 + 6 * np.clip((tt / P - 1.5) / (B - 3.5), 0, 1)) / 20)
y[:n] = pre * gain[:, None]
def chop(beat, slice_beats, reps):
    s0 = S(beat * P); L = S(slice_beats * P); sl = build[s0:s0 + L].copy()
    env = np.ones(L); f = min(240, L // 4); env[:f] = np.linspace(0, 1, f); env[-f:] = np.linspace(1, 0, f)
    return [sl * env[:, None] for _ in range(reps)]
pieces = chop(B - 4, 0.25, 4) + chop(B - 4, 0.125, 4)     # the last bar's downbeat, 16ths then 32nds
pos = S((B - 2) * P)
for i, p in enumerate(pieces):
    hp = 120 * (2200 / 120) ** (i / (len(pieces) - 1))
    p = sosfilt(butter(2, hp / (SR / 2), 'high', output='sos'), p, axis=0) * 10 ** ((1.5 + 2.5 * i / (len(pieces) - 1)) / 20)
    y[pos:pos + len(p)] += p; pos += len(p)
last = pieces[-1]
for r in range(1, 4):                                       # echo tail, dies before the inhale ends
    d = pos + S(r * 0.125 * P) - len(last); e = min(d + len(last), S((B - 0.08) * P))
    if d < e: y[d:e] += (sosfilt(butter(2, 2500 / (SR / 2), 'high', output='sos'), last, axis=0) * 0.35 ** r)[:e - d]
drop = x[S(drop_t):S(drop_t + a.bars_after * 4 * P)].copy()
lows = sosfilt(butter(2, 110 / (SR / 2), 'low', output='sos'), drop, axis=0)
boost = (10 ** (a.shelf_db / 20) - 1) * np.exp(-np.arange(len(drop)) / SR / (2.5 * P))
drop = drop + lows * boost[:, None]
y[S(B * P):S(B * P) + len(drop)] += drop[:len(y) - S(B * P)]
fe = S(0.9); y[-fe:] *= np.linspace(1, 0, fe)[:, None] ** 1.5
y = np.tanh(y / max(np.abs(y).max(), 1e-6) * 1.35) / np.tanh(1.35) * 0.93
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '2', '-i', '-', '-c:a', 'pcm_s24le', a.out],
               input=y.astype(np.float64).tobytes(), check=True)
print(f'{a.out}: {len(y) / SR:.2f}s  | song {start_t:.3f}s -> drop at {B * P:.3f}s in the output ({B} beats in)')
