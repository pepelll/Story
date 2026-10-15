"""Single source of truth for timing (global frames @ 60 fps).

Both the compositor (comp.py) and the sound design (../audio/sfx.py) import
this, so every whoosh / impact lands on the exact frame of its visual event.
"""
FPS = 60
TOTAL = 570  # 9.5 s

# --- scene placement: global frame where each 3D scene's local frame 0 sits
IDEA_START = 78        # bulb scene (local 0..156)
ACTION_START = 232     # domino scene (local 0..162)
RESULT_START = 376     # coin scene (local 0..190)

# --- title
TITLE_IN = 4
TITLE_WORDS = [10, 17, 24]          # ИДЕЯ / ДЕЙСТВИЕ / РЕЗУЛЬТАТ land
TITLE_OUT = 66                      # words fly through camera
ZOOM_THROUGH = (66, 86)             # title -> bulb (radial zoom)

# --- idea
IGNITE_LOCAL = 22                   # matches scene_idea.IGN
IGNITE = IDEA_START + IGNITE_LOCAL  # first spark (100)
IDEA_TEXT = IGNITE + 3
WHIP_1 = (220, 240)                 # idea -> action whip pan (centre 232)

# --- action (domino contact frames, local; printed by scene_action.py)
DOMINO_TIP_LOCAL = 14
DOMINO_HITS_LOCAL = [22.6, 32.7, 44.5, 58.4, 74.8, 94.0, 122.4]
DOMINO_HITS = [ACTION_START + h for h in DOMINO_HITS_LOCAL]
ACTION_TEXT = ACTION_START + 16
FLASH = (364, 380, 392)             # start, peak, end of the light-leak flash

# --- result (coin landing frames, local: 10 + col*7 + k*1.55)
COIN_COUNTS = [5, 9, 14, 20, 28]
COIN_LANDS = sorted(RESULT_START + 10 + j * 7 + k * 1.55
                    for j, n in enumerate(COIN_COUNTS) for k in range(n))
COUNT_UP = (RESULT_START + 14, RESULT_START + 86)
RESULT_TEXT = RESULT_START + 8
LOCKUP = 492                        # final ИДЕЯ → ДЕЙСТВИЕ → РЕЗУЛЬТАТ line
