# Example: a 38s hackathon trailer

The reference edit behind the demo GIFs (DeFy'27 hackathon). Use it as a template for any event trailer: re-word the copy and keep the beat map.

**Song:** 90 BPM, so 1 beat = 20 frames at 30fps. The music starts 4 bars before the chorus, and the build-up and drop are remixed from the song with `remix.py`.
**Kick pattern:** strong on beats 1, 2 and 4, weak on 3. No cut lands on beat 3.

| Beats | Time | Scene | Move in |
|---|---|---|---|
| 0-16 | 0.0-10.7s | **Build-up: one continuous shot.** EVERY BIG IDEA / STARTS SMALL. / THEN COMES THE WALL. / FIND YOUR TEAM. / AND BREAK THROUGH. The camera lurches on the stutter towards a distant WEB3 outline, then the world collapses to a point. | fade from black |
| 16-21 | 10.7-14.0s | **DROP: one shot.** A layered lime card: WEB3 slams in, flies past the camera, BUSINESS arrives from depth. The card tips back onto the floor, then HACKATHON rises out of it and a light-cycle draws its underline. | cut on the downbeat |
| 21-25 | 14.0-16.7s | BUILT FOR: FOUNDERS. / PIONEERS. / FUTURE CXOs. (panels roll on beats 21, 23, 24) | horizon-line switch |
| 25-27 | 16.7-18.0s | HYBRID: split screen, online as outline / offline as solid, the seam as a light beam | slide |
| 27-32 | 18.0-21.3s | 2 DAYS. 3 TRACKS.: three light-cycle lanes, one beat apart | horizon-line switch |
| 32-35 | 21.3-23.3s | 1,500+ TEAMS NATIONWIDE: the odometer lands on a kick | punch |
| 35-36 | 23.3-24.0s | TEAMS OF 4-6 | horizon-line switch |
| 36-37 | 24.0-24.7s | ENTRY FREE: a light frame draws on, then fills | horizon-line switch + shake |
| 37-40 | 24.7-26.7s | REGISTER NOW: platform + partner logo tiles, revealed together | slide |
| 40-45 | 26.7-30.0s | DREAM. / BUILD. / SHIP. (SHIP on a lime card) | horizon-line switch, then punches |
| 45-48 | 30.0-32.0s | 3 / 2 / 1 | punch |
| 48-57 | 32.0-38.0s | End card: logo lockup + tagline, held with beat bumps, then CRT-off | slanted wipe |

**Measured:** the drop lands +2.4ms from the audio transient, with no flash frames, and every scene is centred on its ink within 3px.

To reproduce the core of it with your own words and song:

```bash
python3 ../../skills/dropframe/scripts/beatgrid.py track.mp3 --out grid.json
python3 ../../skills/dropframe/scripts/remix.py track.mp3 --grid grid.json --drop-time <chorus seconds> --bars-after 8 --out remix.wav
DROPFRAME_FONT=YourDisplay.otf python3 ../../skills/dropframe/scripts/example.py --audio remix.wav --out trailer.mp4 \
  --lines "EVERY BIG IDEA" "STARTS SMALL." "FIND YOUR TEAM." "BREAK THROUGH." --drop WEB3 BUSINESS --final HACKATHON
```
