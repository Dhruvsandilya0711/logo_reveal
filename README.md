# Cognitrixx logo reveal — ENGINEER '26

**"Assembly"**: a 15-second 9:16 reel that watches the Cognitrixx mark being built, from a glowing blueprint to finished metal, then locks it on the drop of *Pursuit* (Gesaffelstein) and reveals it clean. Made for ENGINEER '26 · Cognitrixx, NITK Surathkal, 23–25 October 2026.

This repo holds the finished cuts, the render pipeline that made them, and the source files it reads.

## Deliverables — [`renders/`](renders/)

| File | Format | What it is |
|---|---|---|
| `cognitrixx-assembly-reel-15s.mp4` | 1080×1920, 24 fps, 15.33 s, with audio | The full reel with Pursuit mixed in |
| `cognitrixx-assembly-reel-15s-silent.mp4` | 1080×1920, 24 fps, no audio | Same reel, for adding the song inside Instagram |
| `cognitrixx-assembly-story-11s.mp4` | 1080×1920, 11.0 s, with audio | Story cut: starts on the close-ups (reel 0:04.33, song 0:48.33), then the lock, reveal and lockup |
| `cognitrixx-assembly-sting-2s.mp4` | 1080×1920, 2.2 s (one bar), with audio | Sting: the last beat of the whip, the lock on the drop (song 0:52.17 → 0:54.38), then the end card. Use it to open or close other ENGINEER '26 videos |
| `cognitrixx-assembly-feed-1x1-15s.mp4` | 1080×1080, 15.33 s, with audio | Square feed version of the full reel |
| `cognitrixx-assembly-cover.jpg` | 1080×1920 | Cover frame: the settled logo plus the lockup, used as the grid thumbnail |
| `cognitrixx-assembly-cover-1x1.jpg` | 1080×1080 | Square cover |

## Posting and song sync

- **Song:** Gesaffelstein, *Pursuit* (album *Aleph*, 2013). The reel uses **0:44.00 → 0:59.33** of the track.
- **Sync point:** at 0:52.47 the build cuts out, leaving a quarter-second gap. The drop then hits at **0:52.725**, with a full-spectrum hit and the first kick of the new pattern. It lands on the lock and the pink core ignition at **0:08.72** in the reel. Measured on the encoded file, the core ignites on the first frame after the hit (+34 ms, under one frame).
- **Instagram:** a video with copyrighted music baked in can get muted or restricted, especially on business accounts. The safe route:
  1. Upload `…-reel-15s-silent.mp4`.
  2. Add *Pursuit* from Instagram's music picker, starting at **0:44**.
  3. Check that the beams lock on the first bass hit.

  If *Pursuit* isn't in the picker, the business-account library has royalty-free "hybrid trailer / cinematic tech build" tracks with the same build-then-hit shape; line up their first big hit to 0:08.72.
- **Cover:** set `cognitrixx-assembly-cover.jpg` as the reel cover, so the grid tile shows the finished logo instead of the black opening frame.

## The plan ("Assembly")

Every stage starts on the beat grid of the track: 108.95 BPM, so 0.551 s per beat and 2.203 s per bar. Bar lines fall at 2.11 / 4.31 / 6.52 / **8.72** / 10.92 / 13.13 / 15.33 s of the reel, and the reel ends on a bar line. Song time = reel time + 44.00 s.

| Reel time | Song time | Stage | What happens |
|---|---|---|---|
| 0:00.00 → 0.46 | 0:44.00 | Spark | The plotter pen ignites on a black frame over a faint grid floor, so something moves from the first frame |
| 0:00.46 → 2.11 | 0:44.46 | **Blueprint** | Low camera at a steep angle. A single cyan line plots the first beam CAD-style (end cap, then extrusion, then far cap), then the second (0:01.01) and the third (0:01.56). Hidden edges show at low intensity |
| 0:02.11 → 4.31 | 0:46.11 | **Frame** | The camera keeps orbiting slowly. The lines thicken into glowing edges, then each beam's faces fill with dark indigo metal from the edges inward, one beam per beat (2.66 / 3.21 / 3.76), with a violet welding front. One caption line: `SOMETHING IS BEING WIRED` |
| 0:04.31 → 5.42 | 0:48.31 | **Detail 1** | Shallow-focus close-up on the V faces. The circuits etch in trace by trace from the bottom tip, with a spark at each growing tip |
| 0:05.42 → 6.52 | 0:49.42 | **Detail 2** | Close-up on the top faces. The network nodes switch on one by one, spreading out from the core |
| 0:06.52 → 7.62 | 0:50.52 | **Detail 3** | Close-up on the right faces. The dot grid fills row by row outward from the core |
| 0:07.62 → 8.72 | 0:51.62 | **Lock** | The camera pulls out and whips to the one angle where the three beams line up (motion-blurred). The build cuts out in the song at 0:52.47, and the beams snap together in that gap |
| **0:08.72** | **0:52.725 (drop)** | **LOCK** | The beams lock and the pink core ignites |
| 0:08.72 → 10.92 | 0:52.72 | **Reveal** | Half a beat on the locked impossible triangle. The finished skin then grows out from the core over the beams (0:09.00 → 9.68). The camera eases round to the hero pose while every glow rises to full, and one light sweep crosses the metal (0:10.23 → 10.79). A still hold follows, with no text |
| 0:10.92 → 15.33 | 0:54.92 | **Lockup** | The ENGINEER '26 lockup fades in below the mark (NITK Surathkal's / ENGINEER'26 / COGNITRIXX / Rewire reality). The logo keeps a faint living pulse. The cut ends on a bar line |

Rules the edit follows:

- **Slow, fast, still.** The camera is slow through the build, makes one fast move into the lock, then stays still for the reveal.
- **Colour by stage.** Cyan for the blueprint lines, violet for the metal, pink only for the core.
- **Little text.** One caption line during the build; the build itself tells the story.

## The look

- **Logo:** *Mind circuit, fading dots*, rendered on the traced Engineer mark:
  - node network on the top faces;
  - etched circuits on the V faces;
  - a grid of glowing dots on the right faces, fading out from the core;
  - a hot-pink light in the centre gap.
- **Hero pose:** matched to the approved v2 end card (`assets/source/cognitrixx-reel-v2-12s.mp4`). The mark is a thick slab turned slightly, about −12.6° yaw and +5.7° pitch, sized and placed like the v2 frame, with the darker anodised indigo finish.
- **Lockup:** lifted directly from the approved v2 end card, so the letterforms, sizes and spacing are exactly the approved ones. Output: `assets/derived/lockup_add.png`.
- **Caption type:** Orbitron in wide-tracked caps with thin rules on each side, the same style as the v2 captions.

Palette used:

| Role | Colour |
|---|---|
| Blueprint lines | `#35C6FF` cyan |
| Metal body | `#1E1958` → `#5B52A8` indigo / violet |
| Circuits | `#35C6FF` → `#8A5CFF` |
| Network | `#6A4DFF` links, `#35C6FF` nodes |
| Dots | `#8A5CFF` → `#FF5CC8` |
| Rim light | `#E05CFF` fuchsia |
| Core | `#FF5CC8` hot pink (core only) |
| Background | `#080920` → `#0F0B2F` navy-violet (sampled from v2) |

## How it's made — [`pipeline/`](pipeline/)

The renderer is the WebGL2 renderer from the published concept board *"Cognitrixx mark, lit"* (`pipeline/base.html`), driven frame by frame in headless Chromium. It has two views:

- **Trick view:** three ray-marched beams under an orthographic camera. They form the impossible triangle only from one exact angle, which is the lock.
- **Relief view:** the traced mark, shaded as a lit 3D slab, carrying the network, circuit and dot textures.

Python adds everything the renderer doesn't do: the blueprint lines, the edge-inward metal fill, shallow focus, motion blur, skin growth, reflection, caption and lockup.

| Step | Command (run inside `pipeline/`) | Output |
|---|---|---|
| 1. Patch the renderer | `python3 patch_renderer.py` | `reel_tpl.html` with boot-up sparks, beam thickness, pan, light sweep and a frame harness |
| 2. Inject textures | `python3 build_reel.py 1024` | `reel1024.html` (uses `tex1024/`, the textures from the published page) |
| 3. Plan the shots | `python3 plan.py all_jobs.jsonl` | 483 render jobs; all timings and cameras live in `plan.py` |
| 4. Render layers | `node render_server.js all_jobs.jsonl 1024` | `renders/*.png`, cached by parameter hash so only changed shots re-render |
| 5. Composite | `python3 compose.py 9x16 frames/9x16` and `python3 compose.py 1x1 frames/1x1` | 368 frames per format |
| 6. Encode | `python3 encode.py` | every cut in `../renders/` |
| Lockup (once) | `python3 lockup.py` | `../assets/derived/lockup_add.png` |
| Audio check | `python3 analyze_audio.py` | tempo (108.95 BPM), the drop hit (0:52.725) and the kick grid after it |

Supporting modules:

- `trickcam.py` is a Python copy of the beam camera. Its projected edges line up pixel for pixel with the rendered beams, which is what lets the blueprint lines and fills sit exactly on the 3D beams.
- `render_server.js` loads the page once and renders every job in a JSON-lines file.

Requirements:

- Node with Playwright and a Chromium build (rendered here on SwiftShader, about 3 s per 1080×1920 layer).
- Python 3 with `numpy`, `opencv-python`, `pillow`, plus `librosa` for the audio analysis.
- `ffmpeg` with libx264.

**Changing things:**
- **Song offset or timings:** `DROP`, `LEAD_FRAMES` and the `T_*` constants at the top of `plan.py`. The `T_*` constants are on the animation clock, and reel time = animation time + 0.25 s.
- **Caption text:** `caption_layer()` in `compose.py`.
- **Hero lighting and material:** `MAT` in `plan.py`.

## Source files — [`assets/source/`](assets/source/)

| File | Use |
|---|---|
| `Pursuit.mp3` | The track (Gesaffelstein, *Pursuit*). Used for beat analysis and the mix. Copyrighted; keep this repo private |
| `cognitrixx-reel-v2-12s.mp4`, `cognitrixx-reel-v2-cover.jpg` | The approved v2 reel. Reference for the finished logo look, and the source of the lockup |
| `engineer-mark-lineart-399px.png` | The Engineer mark line art (small reference copy) |

## Known limits

- **Texture resolution:** the logo textures are 1024 px, taken from the published concept board. The original full-size line art wasn't available, so the close-ups rely on shallow focus. With the original `engilogo.jpeg`, the texture generators from the earlier sessions can produce a 2048 px set for sharper close-ups.
- **Plain beams during the swing:** in the whip into the lock, the beams are plain metal. The detail lives on the relief and arrives with the skin growth after the lock.
- **Audio rights:** the copyrighted track is mixed into three of the files. Use the silent version if a platform flags it.
