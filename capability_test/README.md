# Capability test: «ИДЕЯ → ДЕЙСТВИЕ → РЕЗУЛЬТАТ»

A 9.5 s vertical demo (1080×1920, 60 fps, H.264 with sound design). It tests one thing: can I build original, art-directed 3D insert scenes and animate them like @video_1 and @video_2, with @video_3's typography?

No reference frames, people, voices, branding or stock elements are used. Every object, material, light, word animation and sound in the demo is generated from the code in this folder.

```
blender/   common.py · scene_idea.py · scene_action.py · scene_result.py   (procedural Cycles scenes)
comp/      timeline.py · comp.py                                          (60 fps compositor)
audio/     sfx.py                                                         (synthesised SFX, frame-locked)
build.sh   one-command rebuild
deliverables/  final MP4, contact sheet, hero stills
```

---

## 1. Reference analysis

### @video_1: editing rhythm and cinematic inserts
- **Look and frame.** The whole edit sits in a "curved monitor" frame: the top edge bows, there are film-edge markings, heavy vignette, grain and lifted blacks. Everything reads as one dark, desaturated, low-key grade, and only the keywords carry colour.
- **Rhythm.** Captions change on every word or phrase, about every 0.3–0.5 s. A designed insert replaces the speaker roughly every 3–4 s, each held 1–2 s. Hard cuts carry most of it. Real transitions are reserved for emphasis: a **whip pan with heavy horizontal motion blur** (0:02), a **burn-to-white light flash** (0:06, 0:13), and a **zoom/defocus pull**.
- **Insert scenes.** Each one is a single symbolic object in a pool of top light against a black void, with smoke or haze, shallow depth of field, a slow digital push-in, and type locked into the composition:
  - the *ticket* (a paper admission ticket under a spotlight, with ticket micro-typography and a barcode)
  - the *mannequin in a suit* (spotlight cone, floor fog, a two-tier caption with a bold condensed word over a light italic word)
  - the *3D icon tiles* (chrome objects in glass cards)
  - the *falling banknotes* (motion-blurred money behind the caption)
- **Typography.** A bold condensed italic grotesk keyword with a light lead-in line. Glow colour carries meaning: yellow-orange halo for money and intent, green for earning. A text-slam blur reveal brings each word in.
- **Sound.** Whooshes sit under the whips and soft impacts under keyword slams and inserts. The voice stays dominant.

### @video_2: designer objects and 3D illustration
- **The core technique is concept → object.** "Assistant" becomes a chrome humanoid wrapped in orange cloth. "Hire for 80K" becomes a kraft folder that opens to a dossier with a polaroid. "Income 150K" becomes a coin dropping into a blue-lidded jar, with the number standing *behind* the object. "Gave away half" becomes banknotes flying through frame.
- **Craft signals:**
  - physically based materials: chrome, kraft paper, cloth and glossy plastic, each with correct roughness response
  - soft studio key light plus rim light on a light-grey seamless backdrop
  - contact shadows, and a cool and grainy grade
  - **depth layering**, with text between background and object
  - dimensional bold-italic numerals with drop shadows
  - parts of the object animate (a lid opens, paper slides out, a coin drops) while the camera keeps drifting
- **Transitions.** Hard cuts on the beat, a slide-push from a polaroid to a number, a falling-money wipe, and a red-light flash on «ФИЗИЧЕСКИ». The talking head returns with a scale-punch.

### @video_3: typography only
- **Typeface.** A neo-grotesk display face in the Helvetica Now Display / Neue Haas family: bold and semibold weights, **tight negative tracking (about -3 to -5 %)**, compact x-height and clean apertures.
- **Hierarchy.** A small regular or light lead line ("By selling", "last one year, I've made") sits on top of a large bold keyword ("AI websites", "$1.4 million"). Leading is tight and lines are centred.
- **Emphasis.** The keyword gets colour (electric blue) and a soft glow on a dark navy field. Numbers count up ("$20,000").
- **Animation.** A short blur-and-fade rise per word, with no bounce.
- **Font used here: Inter Display** (SIL Open Font License, installed locally). It is the closest licensed match: neo-grotesk construction, a dedicated display optical size, full Cyrillic, and OpenType kerning and tabular figures (shaped with HarfBuzz/RAQM). I set it at -3.5 to -4 % tracking for the big lines and Light or Medium for the lead lines, to match @video_3's typographic voice.

---

## 2. What was built

| # | Scene | Concept → object | Production |
|---|-------|------------------|------------|
| 0 | Title (0.0–1.4 s) | «формула ИДЕЯ / ДЕЙСТВИЕ / РЕЗУЛЬТАТ» | Procedural light beam with scrolling haze and dust motes. Per-glyph blur-rise reveal, a gold keyword with an underline draw-on, then a radial **zoom-through** into scene A |
| A | «ИДЕЯ» (1.3–3.9 s) | an idea = a tungsten filament igniting | Cycles. Lathed ST64 glass envelope with real refraction, a **true helical brass screw thread**, black glass insulator, glass stem, molybdenum supports and a squirrel-cage filament with micro-coil wobble, on a black stone plinth with a gold ring. Strip lights shape the glass by reflection. The filament **flickers on** (an electrical stutter, then a warm ramp) and the keyword's glow flickers in sync |
| B | «ДЕЙСТВИЕ» (3.9–6.3 s) | one small action → a growing chain reaction | Cycles. Seven black-lacquer dominoes with inlaid gold pips and divider bars, **each 1.38× larger** than the last. The topple is solved analytically: each piece pivots on its edge, takes about √height to fall, and strikes the next at the exact geometric contact angle. Sub-frame keys give true motion blur. The camera framing scales with the active piece and cranes up for the final impact. Impact-synced shake and keyword pulse. **Whip pan** in, **burn-out light-leak flash** out |
| C | «РЕЗУЛЬТАТ» (6.3–9.5 s) | result = a growing bar chart minted from coins | Cycles. Each coin is a lathed profile (milled rim, recessed field) with a procedural reeded edge and an **embossed ₽ extruded from Inter Display**. 76 coins cascade into a diagonal staircase chart with gravity drops and damped settles. A gold counter counts up to "+1 000 000 ₽", then the closing lock-up «ИДЕЯ → ДЕЙСТВИЕ → РЕЗУЛЬТАТ» lights word by word |

**Finishing (all scenes):** multi-scale bloom with a warm halation skirt, a soft film-shoulder tonemap, edge chromatic aberration, vignette, luminance-weighted animated grain, and a 16-bit pipeline into x264 (CRF 12, `aq-mode=3`) to avoid banding in the dark gradients.

**Sound:** fully synthesised in `audio/sfx.py` and frame-locked through `comp/timeline.py`:
- spectral-sweep whooshes with a muted top end
- pitched sub-drop impacts with felt transients
- lacquered-wood domino knocks that get deeper and heavier with each piece
- a soft ignition crackle and a warm power-on bloom for the filament
- muted, non-ringing coin taps
- warm low tonal blooms on payoffs

Everything passes through a dark synthetic room reverb, a 28 Hz–9 kHz band limit and a soft-knee master.

There is no piercing top end: the spectrum sits essentially below 4 kHz.

## 3. How the designer scenes were made (technical)
1. **Modelling is 100 % code** (`bpy`, Blender 5.2 as a Python module):
   - lathe/spin profiles through Catmull-Rom control points (bulb, plinth, coins)
   - a parametric helix mesh for the screw thread
   - poly-curves with bevel for the filament and wires
   - beveled boxes joined with inlay meshes (dominoes)
   - extruded font curves (₽)
   - a procedural infinity-cove backdrop
2. **Materials:** Principled BSDF with physically plausible values: glass (IOR 1.5, zero roughness), brass and gold with anisotropy, black lacquer with a clear coat. Each gets a noise-driven roughness breakup and micro-bump so surfaces don't look CG-clean. The reeded coin edge is a shader trick: a radial gradient → sine → bump, masked to the rim.
3. **Lighting:** product-photography rigs. Strip area lights give the glass and metal their highlights. A top spot makes the light pool. Cool rim lights separate the silhouettes. There is real emissive bokeh far behind the subject. Lights are hidden from camera, glossy and transmission rays so only their *effect* shows.
4. **Animation** is computed per frame and keyed with LINEAR interpolation (plus sub-frame keys on fast moves) so Cycles motion blur is physically correct. Cameras get low-passed paths, focus pulls and a slight dutch drift.
5. **Render:** Cycles CPU with adaptive sampling (20–24 spp) and OpenImageDenoise, at 864×1536 *on twos* (30 unique fps).
6. **Compositor** (`comp/comp.py`, NumPy and OpenCV):
   - Lanczos upscale to 1080×1920 with a light unsharp
   - odd frames synthesised from **bidirectional DIS optical flow** so the 3D runs at a true 60 fps cadence
   - typography, transitions, digital camera and shakes rendered natively at 60 fps

## 4. Honest limitations
- **Compute:** this environment has 4 CPU cores and no GPU. Rendering every frame at full 1080×1920 / 60 fps in Cycles would take about 6–8 h, so the 3D was rendered at 80 % resolution on twos and then upscaled and flow-interpolated. On a GPU workstation the same scripts render native 1080p60 by changing two arguments (`RES_PCT=100`, `step=1`). Expect sharper micro-detail on the coin reeding and filament.
- **What a procedural pipeline doesn't do as well:** organic, hero-detail subjects like @video_2's draped orange cloth or a sculpted humanoid face. Those need sculpting, cloth simulation or photographic and AI-generated plates. A Higgsfield connector is available in this session (image, video and 3D generation), but it consumes credits, so per your instructions I did **not** use it. With approval it could supply such hero plates, which I would then integrate with the same compositing, typography and sound system.
- **No volumetric fog in 3D:** the beams and haze are composited 2D layers, a deliberate render-time trade-off.
