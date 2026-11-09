"""dfkit — the dropframe motion kit.

One module with everything a scene needs so every scene reads as ONE world:
  * eases (expo / cubic / back) — nothing linear
  * the world: black sky, horizon line, flowing perspective grid floor, glossy reflections, bloom
  * type sprites + placement with floor reflections, ink-accurate centring
  * layered "accent cards" (multiplane parallax letters) for the big hits
  * transitions: momentum zoom, horizon-line switch, slanted wipe, CRT power-off
  * an accumulation-motion-blur renderer that pipes frames to ffmpeg

All coordinates are 1920x1080 @ 30 fps by default. Time `t` is in frames.
"""
from __future__ import annotations
import math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

W, H, FPS = 1920, 1080, 30
CX = W / 2
HZ = 660.0                 # horizon height (keep it fixed across every scene)
FOC = 900.0                # focal length in px
CAM_Y = 1.6                # camera height above the floor (world units)

ACCENT = (169, 255, 85)    # override per brand
CARD = (190, 250, 92)      # accent card fill
INK = (14, 20, 8)
WHITE = (238, 238, 234)
BLACK = (1, 2, 1)

# ----------------------------------------------------------------------------- eases
def clamp(x, a=0.0, b=1.0): return min(max(x, a), b)
def ss(x): x = clamp(x); return x * x * (3 - 2 * x)
def expo_out(x): x = clamp(x); return 1.0 if x >= 1 else 1 - 2 ** (-10 * x)
def expo_in(x): x = clamp(x); return 0.0 if x <= 0 else 2 ** (10 * x - 10)
def expo_io(x):
    x = clamp(x)
    if x <= 0: return 0.0
    if x >= 1: return 1.0
    return 2 ** (20 * x - 10) / 2 if x < .5 else (2 - 2 ** (-20 * x + 10)) / 2
def cubic_io(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back_out(x, s=2.0): x = clamp(x); x -= 1; return x * x * ((s + 1) * x + s) + 1

# ----------------------------------------------------------------------------- fonts / type
_FONT_FALLBACKS = [
    '/usr/share/fonts/opentype/inter/InterDisplay-Light.otf',
    '/usr/share/fonts/opentype/inter/Inter-Light.otf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/Library/Fonts/Arial.ttf', 'C:/Windows/Fonts/arial.ttf',
]
FONT_PATH = os.environ.get('DROPFRAME_FONT')
MONO_PATH = os.environ.get('DROPFRAME_MONO', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf')
def font(size, mono=False):
    path = MONO_PATH if mono else FONT_PATH
    for p in ([path] if path else []) + _FONT_FALLBACKS:
        if p and os.path.exists(p): return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def tw(s, f, tr): return sum(f.getlength(c) + tr for c in s) - tr

def text_sprite(s, f, rgb, tr=10, outline=False, stroke=1):
    """Tracked text as an RGBA sprite, cropped to its INK so it centres optically."""
    asc, desc = f.getmetrics(); w = int(tw(s, f, tr)) + 40
    im = Image.new('RGBA', (w, asc + desc + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 20
    for c in s:
        if outline: d.text((x, 20), c, font=f, fill=(0, 0, 0, 0), stroke_width=3, stroke_fill=rgb + (255,))
        else: d.text((x, 20), c, font=f, fill=rgb + (255,), stroke_width=stroke, stroke_fill=rgb + (255,))
        x += f.getlength(c) + tr
    bb = im.getbbox()
    return im.crop((bb[0] - 4, bb[1] - 4, bb[2] + 4, bb[3] + 4)) if bb else im

def alpha(sp, a):
    if a >= 0.999: return sp
    sp = sp.copy(); al = np.asarray(sp.split()[3]).astype(np.float32) * clamp(a)
    sp.putalpha(Image.fromarray(al.astype(np.uint8))); return sp

def scaled(sp, s): return sp.resize((max(1, int(sp.width * s)), max(1, int(sp.height * s))), Image.BILINEAR)

# ----------------------------------------------------------------------------- world
def proj(X, Y, dz):
    s = FOC / dz
    return CX + X * s, HZ + Y * s, s

def sky(img, glow=0.16, tint=(70, 140, 30)):
    g = Image.new('L', (W, H), 0)
    ImageDraw.Draw(g).ellipse((CX - 1100, HZ - 120, CX + 1100, HZ + 60), fill=int(255 * glow))
    lay = Image.new('RGBA', (W, H), tint + (0,)); lay.putalpha(g.filter(ImageFilter.GaussianBlur(70))); img.alpha_composite(lay)

def horizon(img, half_width=980, a=1.0):
    if half_width >= 1:
        ImageDraw.Draw(img).rectangle((CX - half_width, HZ - 1, CX + half_width, HZ), fill=ACCENT + (int(230 * a),))

def floor(img, zc, a=1.0, spacing=3.0, rails=9):
    """Sparse crisp grid. Pass zc from GLOBAL time so the floor flows continuously across cuts."""
    if a <= 0.01: return
    d = ImageDraw.Draw(img)
    for i in range(-rails, rails + 1):
        x_far, y_far, _ = proj(i * spacing, CAM_Y, 160); x_near, y_near, _ = proj(i * spacing, CAM_Y, 0.5)
        d.line((x_far, y_far + 8, x_near, y_near), fill=ACCENT + (int(a * (150 if i == 0 else 95)),), width=1)
    off = zc % spacing
    for r in range(1, 26):
        dz = r * spacing - off
        if dz < 0.45: continue
        _, y, _ = proj(0, CAM_Y, dz)
        if y - HZ < 12 or y > H: continue
        al = int(a * ss((60 - dz) / 45) * min(1.0, 4.0 / dz) * 210)
        if al > 3: d.line((0, y, W, y), fill=ACCENT + (al,), width=1)

def world(abs_frame, glow=0.16, speed=0.045):
    """The shared environment. abs_frame = frame index in the FINAL edit."""
    img = Image.new('RGBA', (W, H), BLACK + (255,))
    sky(img, glow); floor(img, speed * abs_frame); horizon(img)
    return img

def place(img, sp, cx, cy, a=1.0, reflect=True, refl=0.20):
    """Sprite centred at (cx, cy) plus its mirror in the glossy floor."""
    if a <= 0.01: return
    sp = alpha(sp, a); x0, y0 = int(cx - sp.width / 2), int(cy - sp.height / 2)
    img.alpha_composite(sp, (x0, y0))
    if reflect and y0 + sp.height <= HZ + 4:
        rf = sp.transpose(Image.FLIP_TOP_BOTTOM)
        g = np.linspace(refl, 0.0, rf.height)[:, None]
        rf.putalpha(Image.fromarray((np.asarray(rf.split()[3]).astype(np.float32) * g).astype(np.uint8)))
        img.alpha_composite(rf, (x0, int(2 * HZ - (y0 + sp.height))))

def streak(img, x0, x1, y, p, a=1.0):
    """A light-cycle streak left->right that leaves its trail as an underline (p: 0..1)."""
    if p <= 0: return
    hx = x0 + (x1 - x0) * p; d = ImageDraw.Draw(img)
    d.rectangle((x0, y - 1, hx, y + 1), fill=ACCENT + (int(235 * a),))
    if p < 0.999: d.ellipse((hx - 7, y - 7, hx + 7, y + 7), fill=(240, 255, 225, int(255 * a)))

def bloom(arr):
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    b1 = np.asarray(im.filter(ImageFilter.GaussianBlur(6))).astype(np.float32)
    b2 = np.asarray(im.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(8)).resize((W, H), Image.BILINEAR)).astype(np.float32)
    return arr + 0.55 * b1 + 0.45 * b2

def to_np(img): return np.asarray(img.convert('RGB')).astype(np.float32)

# ----------------------------------------------------------------------------- layered accent card
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_VIG = np.clip(1 - 0.28 * (((_xx - CX) / (W * .62)) ** 2 + ((_yy - H / 2) / (H * .62)) ** 2), 0.62, 1)[..., None]
def card_bg(): return Image.fromarray(np.clip(np.array(CARD, np.float32)[None, None] * _VIG, 0, 255).astype(np.uint8)).convert('RGBA')

def glyph_layers(txt, f, tr=24, cy=525, rgb=INK):
    """Each letter as its own sprite, positioned so the word's real ink is centred on (CX, cy)."""
    tot = tw(txt, f, tr); x = CX - tot / 2; out = []; asc, desc = f.getmetrics()
    for c in txt:
        w = int(f.getlength(c)) + 12
        im = Image.new('RGBA', (w, asc + desc + 12), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((6, 6), c, font=f, fill=rgb + (255,), stroke_width=1, stroke_fill=rgb)
        out.append([im, x + f.getlength(c) / 2, cy]); x += f.getlength(c) + tr
    probe = Image.new('L', (W, H), 0)
    for im, px, py in out: probe.paste(im.split()[3], (int(px - im.width / 2), int(py - im.height / 2)), im.split()[3])
    bx0, by0, bx1, by1 = probe.getbbox()
    return [(im, px + CX - (bx0 + bx1) / 2, py + cy - (by0 + by1) / 2) for im, px, py in out]

def put(canvas, sprite, cx, cy, s, a):
    """Place a sprite at depth scale s about the camera centre (multiplane)."""
    if a <= 0.01 or s <= 0.02: return
    w, h = max(1, int(sprite.width * s)), max(1, int(sprite.height * s))
    if w > 5000: return
    sp = alpha(sprite.resize((w, h), Image.BILINEAR), a)
    canvas.alpha_composite(sp, (int(CX + (cx - CX) * s - w / 2), int(H / 2 + (cy - H / 2) * s - h / 2)))

def scale_layer(img, s):
    if abs(s - 1) < 1e-4: return img
    a = 1 / s
    return img.transform((W, H), Image.AFFINE, (a, 0, CX - CX * a, 0, a, H / 2 - H / 2 * a), resample=Image.BILINEAR)

def card_decor(t):
    """Rules that draw out from centre, corner triangles that slide in, a hatch that draws on."""
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    kr = expo_out((t + 2) / 12)
    for y in (134, 917):
        d.line((CX - 760 * kr, y, CX + 760 * kr, y), fill=INK + (150,), width=2)
        if kr > 0.5:
            for px in (283, 941, 1598): d.ellipse((px - 6, y - 6, px + 6, y + 6), fill=INK + (255,))
    o = (1 - expo_out((t - 1) / 11)) * 260
    d.polygon([(28 - o, 52 - o), (140 - o, 52 - o), (28 - o, 164 - o)], fill=INK + (255,))
    o = (1 - expo_out((t - 3) / 11)) * 320
    d.polygon([(1896 + o, 700 + o), (1896 + o, 1030 + o), (1610 + o, 1030 + o)], fill=INK + (255,))
    for i in range(8):
        kk = expo_out((t - 5 - 0.6 * i) / 8)
        if kk > 0: d.line((1780 + i * 16, 52, 1780 + i * 16 + 70 * kk, 52 + 70 * kk), fill=INK + (170,), width=2)
    return lay

def accent_card(t, words, hold=60):
    """words: list of (glyph_layers, land_frame). Background, decor and letters on different depths.
    Each word's letters arrive from depth (staggered), then fly past the camera when the next word lands."""
    u = clamp(t / hold); slam = 1 - expo_out((t + 3) / 9)
    c = scale_layer(card_bg(), 1.0 + 0.10 * slam + 0.015 * u)
    c.alpha_composite(scale_layer(card_decor(t), 1.0 + 0.16 * slam + 0.04 * u))
    for wi, (layers, land) in enumerate(words):
        nxt = words[wi + 1][1] if wi + 1 < len(words) else None
        for i, (sp, cx, cy) in enumerate(layers):
            d_i = land - 5 + 0.6 * i
            k = expo_out((t - d_i) / 10)
            if k <= 0: continue
            s = 0.45 + 0.55 * k + 0.07 * u
            ex = expo_in((t - (nxt - 7 + 0.8 * abs(i - len(layers) / 2))) / 7) if nxt is not None else 0.0
            put(c, sp, cx, cy, s * (1 + 3.5 * ex), clamp((t - d_i + 3) / 4) * (1 - clamp(ex * 1.6)))
    return c

# ----------------------------------------------------------------------------- transitions
def momentum_scale(t, f0, f1, pre=5, post=8, punch=0.22, out=0.4, push=0.07):
    """Per-shot camera scale: steady push-in, punch arrival that eases out, ease-in acceleration into the next cut."""
    u = (t - f0) / max(f1 - f0, 1)
    s = 1.0 + push * clamp(u, -0.1, 1.1)
    s *= 1.0 + punch * (1 - expo_out((t - f0 + 2) / post))
    if t > f1 - pre: s *= 1.0 + out * expo_in((t - (f1 - pre)) / pre)
    return s

def transform(arr, s=1.0, dx=0.0, dy=0.0):
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); a = 1 / s
    return np.asarray(im.transform((W, H), Image.AFFINE, (a, 0, CX - (CX + dx) * a, 0, a, H / 2 - (H / 2 + dy) * a),
                                   resample=Image.BILINEAR)).astype(np.float32)

def _glow_lines(img, ys, a):
    lay = np.zeros((H, W, 3), np.float32)
    for y in ys:
        yi = int(round(y))
        for dy, g in ((0, 1.0), (1, .7), (-1, .7), (2, .35), (-2, .35), (3, .15), (-3, .15)):
            if 0 <= yi + dy < H: lay[yi + dy] = np.maximum(lay[yi + dy], np.array(ACCENT, np.float32) * g * a)
    return np.maximum(img, lay)

def horizon_switch(arr, q):
    """World switch. q: 0 = full frame, 1 = collapsed into a glowing line on the horizon.
    Outgoing: q = expo_in(...) over ~4 frames before the cut. Incoming: q = 1 - expo_out(...) over ~5 frames,
    starting 1 frame early so the screen is ~70% open on the beat."""
    if q <= 0.001: return arr
    h = max(2, int(round(H * (1 - 0.985 * q))))
    sm = np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W, h), Image.BILINEAR)).astype(np.float32)
    out = np.zeros((H, W, 3), np.float32); y0 = max(0, min(H - h, int(round(HZ - HZ / H * h)))); out[y0:y0 + h] = sm * (1 - 0.35 * q)
    return _glow_lines(out, (y0, y0 + h - 1), min(1.0, 2.2 * q))

def slant_wipe(a, b, p, slant=600.0, blur_px=40.0):
    """Wipe from frame a to frame b with a leaning, motion-blurred edge (p: 0..1)."""
    x = -500 + (W + 1000) * p
    m = np.clip((x + (H / 2 - _yy[:, :1]) / H * slant - _xx[:1, :]) / blur_px, 0, 1)[..., None]
    return a * (1 - m) + b * m

def crt_off(arr, t, dur=12):
    """CRT power-off: squash to a line (7f), then to a dot (5f), then black."""
    if t <= 0: return arr
    out = np.zeros((H, W, 3), np.float32)
    if t >= dur: return out
    if t < 7:
        k = expo_in(t / 7); h = max(int(H * (1 - k)), 3)
        sm = np.asarray(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).resize((W, h), Image.BILINEAR)).astype(np.float32)
        out[(H - h) // 2:(H - h) // 2 + h] = sm + (255 - sm) * 0.7 * k
    else:
        k = expo_out((t - 7) / 5); w = max(int(W * (1 - k)), 4); out[537:543, (W - w) // 2:(W - w) // 2 + w] = 255 * (1 - 0.6 * k)
    return out

def shake(arr, u, amp=1.0, seed=7):
    """Decaying camera shake + brief chroma split. u = frames since the hit. Use on 2-3 hits only."""
    if u < 0 or u >= 14: return arr
    rng = np.random.default_rng(seed + int(math.floor(u))); a = 16 * amp * math.exp(-u / 3.2)   # u may be a sub-frame time
    arr = transform(arr, 1.02, a * rng.uniform(-1, 1), a * rng.uniform(-1, 1))
    ca = int(round(6 * amp * (1 - u / 4))) if u < 4 else 0
    if ca > 0:
        o = arr.copy(); o[:, ca:, 0] = arr[:, :-ca, 0]; o[:, :-ca, 2] = arr[:, ca:, 2]; arr = o
    return arr

# ----------------------------------------------------------------------------- renderer
def render(out, n_frames, frame_fn, samples=4, lead=3, post=bloom, crf=14):
    """Accumulation motion blur: average `samples` sub-frames across a 180-degree shutter, then post (bloom).
    `lead` = cut-on-action: the clip starts `lead` frames into the scene's own timeline (t = u - lead)."""
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                            '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', str(crf), '-pix_fmt', 'yuv420p', out],
                           stdin=subprocess.PIPE)
    for u in range(n_frames):
        K = samples(u) if callable(samples) else samples
        acc = np.zeros((H, W, 3), np.float32)
        for k in range(K): acc += frame_fn(u - lead - 0.25 + 0.5 * (k + 0.5) / K if K > 1 else u - lead)
        img = acc / K
        if post: img = post(img)
        enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    enc.stdin.close(); enc.wait()
