---
name: dropframe
description: Make or re-edit a beat-synced, After-Effects-quality motion video (trailer, promo, reel, launch) from your footage, brand assets and a song, with frame-exact sync and no AI look.
---

# dropframe

*Every cut on the kick. Every drop on the frame.*

Turn a song, some footage and a brand kit into a motion video that looks hand-animated in After Effects: every hit lands on the music, motion has real easing and motion blur, and the whole piece reads as one continuous flow in one visual world.

Everything is rendered in code (Python + PIL + numpy, piped to ffmpeg), so every cut, ease and frame is re-timeable and verifiable. No browser renderer, no templates, no stock sound effects.

Use it for event and hackathon trailers, product launches, brand promos, social reels, title sequences, and for **re-editing an existing video** onto a new song.

## Toolkit (in `scripts/` next to this file)

| Script | What it does |
|---|---|
| `beatgrid.py song.mp3` | Fits one uniform beat grid (drift-checked), kick pattern per beat-in-bar, weak beats to avoid, downbeat candidates, energy per bar. Writes `grid.json`. |
| `remix.py song.mp3 --grid grid.json --drop-time S` | Build-up from the song itself: filter sweep, 16th/32nd stutter, half-beat inhale, drop with a decaying low-shelf. Output starts on a downbeat. |
| `dfkit.py` | The motion kit: eases, world (horizon, flowing grid floor, reflections, bloom), ink-centred type, layered accent cards, momentum zoom, horizon-line switch, slanted wipe, shake, CRT-off, motion-blur renderer. |
| `example.py` | A complete 8-bar sequence (build-up -> drop card -> world -> CRT-off) to copy and re-word. |
| `verify.py` | `sync` (transient vs cut in ms), `grid`, `centre` (ink bbox vs frame centre), `flashes`, `sheet`. |

Requirements: Python 3.10+, ffmpeg, `pip install numpy pillow scipy librosa`. Set `DROPFRAME_FONT` to the brand's display font (`.ttf`/`.otf`).

## Working agreement

- **Don't render until told.** While the user is giving notes, make the code changes, check them on a few stills or numerically, and stop. Render only on an explicit "render" or "go". Run full renders in the background.
- **Every render is a new version** (v1, v2, ...) in its own folder next to the source; never overwrite an earlier version. Back up a script before big edits.
- **Verify before sending:** contact sheet, the drop and every transition frame by frame, A/V sync measured, centring measured. Say in one line what was checked.
- **Keep replies short:** what changed, any decision the user must make, one next step.
- **Ask only when the answer changes the build** (e.g. two sources disagree on a date). Otherwise make the call and state it.
- **Missing or blocked assets:** say so in one line, use a clean placeholder, and give the exact file name and folder to drop the real asset into; the next render picks it up automatically.
- When the user approves a scene, keep it. Don't "improve" approved scenes unless asked.

## Story and length

- Default ~30s; ±5-10s is fine. Never pad.
- Start the music where the song is strongest (or where the user says), snapped to the nearest downbeat.
- Shape: **cinematic build-up -> DROP -> fast informational run -> countdown or final beat -> logo / end card -> power-off.**
- Cut anything that isn't selling: filler mood shots, redundant title cards, dead air. Credits go on the opening or end card, not their own scene.
- Copy must be **readable and flow like a sentence**, one line on screen at a time, held long enough to read. No square brackets, no gimmick punctuation, no stray full stops. Rewrite copy freely when it reads better.
- Facts must be right (dates, duration, prices). Never imply something the event or product isn't.
- For an event trailer, cover: hook, who it's for, format, tracks or themes, scale, team size, price, where to register and partners, the build arc, a countdown, logo + tagline.

## Music and beat sync

1. Run `beatgrid.py`. It fits **one uniform grid** to onset strength and reports drift (should be ~0). Start the audio on a downbeat so beats fall on exact frames (at 90 BPM and 30fps, 1 beat = 20 frames). Downbeat detection can be ambiguous; when two candidates score close, confirm against where the chorus actually drops and pass `--downbeat`.
2. Use the kick pattern. **Cut only on strong kicks; never on the weak beat** (often beat 3 in a half-time groove). Big hits land on bar downbeats.
3. **Cut on action:** start each shot ~3 frames into its own animation, so the beat frame already shows a crisp, readable result. Never let the beat frame be a blurred wash.
4. Re-time animation baked into source clips (counters, glitches, slams) so the key moment lands on a kick; trim glitch pre-rolls and flash frames (`verify.py flashes`).
5. **Kick pulse** on held shots after the drop: 1-2% scale bump plus a small brightness lift per kick, decaying over ~3 frames, larger on downbeats.
6. Verify with numbers (`verify.py sync`): audio transient vs video cut at the drop and the logo should be within ~10ms. If something "feels late", it's usually readability on the beat frame, not A/V offset. Prove which.

### Build-up and drop, remixed from the song itself (`remix.py`)

- Start the music 4 bars before the chorus.
- Bars 1-3: time-varying low-pass sweep from muffled (~260 Hz) to fully open, with a gentle level rise.
- Last bar: chop the bar's downbeat into 16ths, then 32nds, with a rising high-pass and gain, click-free envelopes and a short decaying echo tail.
- Half a beat of near-silence: the inhale.
- DROP on the chorus downbeat with a decaying low-shelf boost (~+5 dB to 0 over 2 bars). Soft-limit the master and fade the tail cleanly.
- Match the picture to the audio: camera lurches on each chop, a zoom ramp with growing chroma split, then the world collapses to a point before the drop.
- **No stock sound effects, ever.**

## Visual world: one theme, one flow

- Pick **one world** and keep it: e.g. black sky, a single accent-colour horizon line at a fixed height, a sparse perspective grid floor that keeps flowing on global time (continuous across cuts), glossy floor reflections of type, faint haze at the horizon, bloom on the world. Every scene lives there (`dfkit.world`, `place`).
- Use the brand palette: one accent colour + near-black + white (set `dfkit.ACCENT`, `CARD`, `INK`). **Solid accent cards only for the big hits** (drop words, the final "ship" beat, one countdown digit, end card).
- Accent cards are **layered, never flat photos** (`dfkit.accent_card`): background, decor and each letter sit on their own depth layers with staggered arrival and different push speeds (multiplane parallax). Swap words through depth: the old word flies past the camera while the new one arrives from behind. A card can tip back onto the floor (a perspective transform about its bottom edge) to hand off into the 3D world in a single shot.
- **No HUD clutter** unless asked: no fake terminal readouts, REC timers, tick rulers, progress bars, scrolling ticker strips or "[01/03]" counters.
- **Logos:** use official assets (Figma export, supplied PNG or SVG). Never glow or bloom a logo; composite logos after the bloom pass. Partner logos are small equal tiles in their own colours, revealed together, under a clear CTA (e.g. REGISTER NOW) with short labels.
- Take lockup proportions, spacing and secondary elements (e.g. a ghost outline) from the brand file.
- **Centre on actual ink, not font boxes** (`text_sprite` and `glyph_layers` already crop to ink). Run `verify.py centre` and fix anything over ~3px (trailing punctuation needs an optical offset). Give taglines breathing room; smaller is usually better.

## Motion: what makes it read as After Effects

- Eases: expo-out for arrivals, expo-in for exits, expo or cubic in-out for camera moves, back-out with a small overshoot for pops. Nothing linear.
- **Accumulation motion blur** on everything that moves (`dfkit.render`): average 4-8 sub-frame samples across a 180-degree shutter. Use analytic blur for hard edges like wipes.
- **Never slow footage with frame blending**; that soft ghosting is the AI look. Play clips at 1x or faster, and hold the last frame if short.
- Every shot keeps a steady, visible push-in for its whole length.
- **Momentum transitions** (`dfkit.momentum_scale`): the outgoing shot accelerates its zoom into the cut (ease-in), the incoming shot arrives already moving the same way and eases out to rest, and the settle finishes on the beat. Slides finish on the beat, not centred on it.
- Zoom-through on the biggest hits; decaying camera shake and a brief chroma split (`dfkit.shake`) on only 2-3 hits.
- Connective tissue: lines that draw on (trim paths), light streaks that race across and leave an underline (`dfkit.streak`).
- **Switching worlds** (3D scene to flat scene): the horizon-line switch (`dfkit.horizon_switch`). The outgoing frame collapses vertically into a glowing line on the horizon (CRT-style) and the next scene powers on out of that line, ~70% open on the beat.
- Countdown to logo: the last digit races to a point on the horizon and the end card bursts open from that point (or `dfkit.slant_wipe`).
- Last frame: CRT power-off (`dfkit.crt_off`).

## Workflow

1. **Take stock.** Get access to the project folder; gather clips, brand assets, fonts and the song. Read any linked Figma file early (free plans rate-limit): metadata for layer positions, screenshots of key frames, lockup ratios.
2. **Analyse** the song (`beatgrid.py`) and the clips (per-frame luminance and difference to find flash frames, glitches and baked-in hits).
3. **Plan in beats:** a shot list with start and end beats, intro type (punch, push, zoom, line, cut), source frame ranges, and which beat each internal hit lands on. Share the plan plus suggestions briefly.
4. **Build scenes as scripts** on `dfkit`. Each custom scene renders to its own clip; a master timeline assembles shots, transitions, camera finishing (shake, kick pulse, grain, vignette) and the end card. `example.py` shows the pattern.
5. **Check on stills first** with internal contact sheets.
6. **Render on instruction**, mux with the remix (`remix.py`), verify (`verify.py`), deliver the new version to its folder and send it.
7. Ship a markers CSV (cuts + beat grid in seconds) and the remixed WAV with the video, so the edit can be rebuilt in After Effects.

## Review checklist before sending

- [ ] Every cut on a strong kick; drop and logo on downbeats; beat frames readable.
- [ ] A/V offset at the drop and logo measured within ~10ms.
- [ ] No flash frames, glitch pre-rolls or blown-out first frames.
- [ ] One world: same horizon height, flowing floor, reflections; accent cards only on big hits.
- [ ] No HUD clutter or brackets; copy reads as a sentence; facts right.
- [ ] Logos crisp, unglowed, small, revealed together.
- [ ] Ink-centred within a few px; taglines have breathing room.
- [ ] Length within target ±5-10s; music ends cleanly with the power-off.
