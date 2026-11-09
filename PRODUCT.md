# dropframe

**One line:** an agent skill that edits like a motion designer. It turns your footage, brand kit and a song into a beat-synced, After-Effects-quality video, with sync you can measure and no AI look.

## Who it's for

People who need a trailer, promo or reel that actually hits: event and hackathon organisers, founders launching a product, brand and social teams, and motion designers who want a fast first cut.

## The problem

AI and template video tools produce motion that reads as AI: frame-blended slow motion, linear moves, cuts near the beat rather than on it, stock whooshes on every transition, and scenes that feel stitched together.

## What dropframe does differently

1. **Music-first.** It fits one exact beat grid to the song, finds the kick pattern, and cuts only on strong kicks.
2. **Verified.** It measures A/V sync in milliseconds, audits centring on the actual ink, and detects flash frames.
3. **The build-up comes from the user's own track.** Filter sweep, stutter, silence, drop. No stock SFX.
4. **After Effects motion.** Expo eases, accumulation motion blur, momentum cuts, multiplane depth, cut-on-action.
5. **One world.** A single visual system and connective transitions (the horizon-line switch, CRT power-off).
6. **A collaborator's workflow.** It plans in beats, previews on stills, renders only when told, versions every render, and keeps approved scenes.

## Non-goals

- Generating footage or stock imagery.
- Narration and voiceover.
- Shipping music or fonts. Users bring licensed tracks and their own brand fonts.

## Stack

Python 3.10+, numpy, Pillow, SciPy, librosa, ffmpeg. No browser renderer and no external service.
