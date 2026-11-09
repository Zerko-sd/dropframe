"""verify — prove the edit instead of eyeballing it.

  python3 verify.py sync    video.mp4 --hits 10.667 24.0 32.0      audio transient vs each video cut, in ms
  python3 verify.py grid    video.mp4 --period 0.6667 --offset 0    best global offset of onsets vs the beat grid
  python3 verify.py centre  video.mp4 --at 11.9:dark 13.7:light     ink bbox centre vs frame centre, per moment
  python3 verify.py flashes video.mp4                               single-frame luminance spikes (flash frames)
  python3 verify.py sheet   video.mp4 --fps 2 --out sheet.png       contact sheet

centre modes: light = white type on dark, dark = ink on an accent card.
"""
import argparse, subprocess, sys
import numpy as np

def audio(path, sr=48000):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vn', '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.float32), sr
def frame(path, t, w=1920, h=1080):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', path, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(int)

ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('video')
ap.add_argument('--hits', nargs='*', type=float, default=[]); ap.add_argument('--period', type=float); ap.add_argument('--offset', type=float, default=0)
ap.add_argument('--at', nargs='*', default=[]); ap.add_argument('--fps', type=float, default=2); ap.add_argument('--out', default='sheet.png')
a = ap.parse_args()

if a.cmd == 'sync':
    y, sr = audio(a.video); e = np.convolve(np.abs(y), np.ones(48) / 48, 'same')
    for hit in a.hits:
        lo = max(0, hit - 0.12); seg = e[int(lo * sr):int((hit + 0.25) * sr)]; base = seg[:int(0.04 * sr)].mean()
        i = int(np.argmax(seg > base + 0.5 * (seg.max() - base))); t = lo + i / sr
        print(f'cut {hit * 1000:9.1f} ms | audio transient {t * 1000:9.1f} ms | offset {(t - hit) * 1000:+7.1f} ms')
elif a.cmd == 'grid':
    import librosa
    y, sr = audio(a.video, 22050); hop = 128
    o = librosa.onset.onset_strength(y=y.astype(np.float32), sr=sr, hop_length=hop, aggregate=np.median); fr = sr / hop
    ks = np.arange(1, int(len(y) / sr / a.period) - 1); res = []
    for d in np.arange(-0.05, 0.051, 0.005):
        idx = np.round((a.offset + d + ks * a.period) * fr).astype(int); idx = idx[idx < len(o)]; res.append((o[idx].mean(), d))
    print(f'best offset vs grid: {max(res)[1] * 1000:+.0f} ms (0 = perfectly on the grid)')
elif a.cmd == 'centre':
    for spec in a.at:
        t, mode = spec.split(':'); im = frame(a.video, float(t))
        m = (im.min(2) > 165) if mode == 'light' else (im.max(2) < 70)
        m[:, :150] = False; m[:, -150:] = False
        if mode == 'dark': m[:200] = False; m[860:] = False
        ys, xs = np.where(m)
        if not len(xs): print(f'{t}s: no ink found'); continue
        x0, x1 = np.percentile(xs, .5), np.percentile(xs, 99.5)
        off = (x0 + x1) / 2 - 960
        print(f'{t:>7}s {mode:5s} ink x {x0:6.0f}-{x1:6.0f}  centre offset {off:+6.1f}px  {"OK" if abs(off) <= 3 else "FIX"}')
elif a.cmd == 'flashes':
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.video, '-vf', 'scale=192:108', '-f', 'rawvideo', '-pix_fmt', 'gray', '-'], capture_output=True).stdout
    lum = np.frombuffer(raw, np.uint8).reshape(-1, 108, 192).mean((1, 2))
    sp = [i for i in range(1, len(lum) - 1) if lum[i] - max(lum[i - 1], lum[i + 1]) > 15]
    print('single-frame flashes at frames:', sp or 'none')
elif a.cmd == 'sheet':
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.video, '-vf', f'fps={a.fps},scale=320:-1,tile=10x8', '-frames:v', '1', a.out], check=True)
    print('wrote', a.out)
else:
    sys.exit(__doc__)
