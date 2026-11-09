"""example — a complete 8-bar dropframe sequence you can copy and re-word.

usage: python3 example.py --out demo.mp4 [--audio remix.wav] [--fpb 20]

  bars 1-4  one continuous camera glide through the grid world; copy flies past, one line per bar
  last bar  the camera lurches on 16ths/32nds toward a distant outline of the drop word
  inhale    the world fades, the horizon collapses to a point
  DROP      a layered accent card: the drop word slams in, swaps to the second word through depth
  bar 7     horizon-line switch back into the world; a word rises out of the floor, a streak underlines it
  bar 8     CRT power-off
fpb = frames per beat from beatgrid.py (20 at 90 BPM / 30 fps).
"""
import argparse, os, sys, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dfkit import *

ap = argparse.ArgumentParser(); ap.add_argument('--out', default='demo.mp4'); ap.add_argument('--audio'); ap.add_argument('--fpb', type=int, default=20)
ap.add_argument('--lines', nargs='*', default=['EVERY BIG IDEA', 'STARTS SMALL.', 'FIND YOUR TEAM.', 'BREAK THROUGH.'])
ap.add_argument('--drop', nargs=2, default=['WEB3', 'BUSINESS']); ap.add_argument('--final', default='HACKATHON')
a = ap.parse_args()
B = a.fpb; DROP = 16 * B; SWITCH = 24 * B; END = 30 * B; TOTAL = 32 * B

# ---------- build-up: camera z over time (steady acceleration, then stepped lurches on the stutter)
def z_cam(b):
    z = 1.6 * min(b, 14) + 0.008 * min(b, 14) ** 3
    for i in range(4):
        if b >= 14 + i * .25: z += 2.2 * expo_out((b - (14 + i * .25)) / .175)
    for i in range(4):
        if b >= 15 + i * .125: z += 1.4 * expo_out((b - (15 + i * .125)) / .0875)
    return z
F_LINE = font(140); F_DROP_OUT = font(380)
LINES = [(text_sprite(s, F_LINE, WHITE if i % 2 == 0 else ACCENT, tr=12), (2.6 + 3 * i, 2.6 + 3 * i + 2.7)) for i, s in enumerate(a.lines)]
OUTLINE = text_sprite(a.drop[0], F_DROP_OUT, ACCENT, tr=30, outline=True)

def buildup(t):
    b = t / B; zc = z_cam(b); gap = ss((b - 15.5) / 0.32); w_ = 1 - gap
    img = Image.new('RGBA', (W, H), BLACK + (255,)); sky(img, (0.06 + 0.2 * clamp(b / 14)) * w_)
    floor(img, zc, ss((b - 0.8) / 3) * w_)
    hw = 980 * ss((b - 0.1) / 2.6)
    if b > 15.5: hw = 980 * (1 - expo_in((b - 15.5) / 0.5))
    horizon(img, hw)
    for sp, (bi, bo) in LINES:                            # one line at a time, readable, drifting toward camera
        if bi - .05 < b < bo + .05:
            dz = 6.0 + (bo - b) * 1.4
            place(img, scaled(sp, 6.0 / dz), CX, proj(0, -1.1, dz)[1], ss((b - bi) / .45) * (1 - ss((b - (bo - .3)) / .3)) * w_)
    if b > 13.8:                                           # the drop word's outline glowing in the distance
        dz = max(1.0, z_cam(15.5) + 7.0 - zc)
        place(img, scaled(OUTLINE, min(4, 6.0 / dz)), CX, proj(0, -1.0, dz)[1], ss((b - 13.8) / .8) * .9 * w_)
    return to_np(img)

# ---------- drop: layered accent card, two words swapping through depth
F_D = font(360)
def fit(txt, width, tr):
    s = 400
    while tw(txt, font(s), tr) > width: s -= 4
    return font(s)
WORDS = [(glyph_layers(a.drop[0], fit(a.drop[0], 1420, 30), 30), 0), (glyph_layers(a.drop[1], fit(a.drop[1], 1500, 18), 18), 2 * B)]
def drop(t): return accent_card(t, WORDS, hold=SWITCH - DROP)

# ---------- final word rising out of the floor + streak underline
F_FIN = fit(a.final, 1500, 18)
def final(t, abs_f):
    img = world(abs_f, 0.18)
    sp = text_sprite(a.final, F_FIN, WHITE, tr=18); base = HZ - 110
    k = expo_out((t + 3) / 12)
    place(img, sp, CX, base - sp.height / 2 + (sp.height + 40) * (1 - k), k)
    streak(img, CX - sp.width / 2 - 40, CX + sp.width / 2 + 40, base + 34, expo_io((t - B + 5) / 12))
    return to_np(img)

def frame(f):
    if f < DROP: return bloom(buildup(f))
    if f < SWITCH:
        c = drop(f - DROP)
        img = np.asarray(c.convert('RGB')).astype(np.float32)
        img = transform(img, momentum_scale(f, DROP, SWITCH, post=8, punch=0.0))
        if SWITCH - 5 <= f: img = horizon_switch(img, expo_in((f - (SWITCH - 5) + .5) / 4))
        return shake(img, f - DROP, 1.5)
    img = bloom(final(f - SWITCH, f))
    if f < SWITCH + 4: img = horizon_switch(img, 1 - expo_out((f - (SWITCH - 1) + .5) / 5))
    return crt_off(img, f - END)

tmp = a.out if not a.audio else a.out + '.video.mp4'
render(tmp, TOTAL, lambda t: frame(t + 3), samples=lambda u: 6 if 14 * B <= u <= 17 * B else 3, lead=3, post=None)
if a.audio:
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-i', a.audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '320k', '-shortest', '-movflags', '+faststart', a.out], check=True)
    os.remove(tmp)
print('wrote', a.out)
