"""SCENE B — «ДЕЙСТВИЕ»: a growing domino chain (one small action → outsized effect).

Seven black-lacquer dominoes with inlaid brushed-gold pips and divider bars,
each 1.38x taller than the one before. The fall is solved analytically: each
piece pivots on its front-bottom edge, accelerates like a toppling slab
(duration ~ sqrt(height)), strikes the next piece at the exact geometric
contact angle, then keeps leaning as its successor goes down.

Run:  python scene_action.py -- out=/path/frames [samples=24] [f0=0] [f1=162] [step=2]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import bmesh
from mathutils import Vector

import common as C

A = C.args()
OUT = A.get("out", "/tmp/action")
F0, F1 = int(A.get("f0", 0)), int(A.get("f1", 162))
SAMPLES = int(A.get("samples", 24))

sc = C.reset()
sc.frame_start, sc.frame_end = F0, F1
random.seed(7)

# ------------------------------------------------------------------ set
cove = C.mat_principled("Cove", (0.014, 0.015, 0.018), rough=0.5, spec=0.3)
C.add_noise_roughness(cove, 0.45, 0.12, scale=2.0)
cv = C.backdrop(cove, radius=10, height=80, depth=22, width=140, front=30)
cv.location.x = -6

lacquer = C.mat_principled("Lacquer", (0.008, 0.008, 0.009), rough=0.06, spec=0.6, coat=1.0, coat_rough=0.02)
C.add_noise_roughness(lacquer, 0.07, 0.05, scale=4)
gold = C.mat_principled("Gold", (1.0, 0.72, 0.36), metallic=1.0, rough=0.2, aniso=0.5)
C.add_noise_roughness(gold, 0.2, 0.07, scale=80)

# ------------------------------------------------------------------ dominoes
GROW = 1.38
N = 7
BASE_H, BASE_W, BASE_D = 1.0, 0.5, 0.17
PIPS = {
    0: [], 1: [(0, 0)], 2: [(-1, 1), (1, -1)], 3: [(-1, 1), (0, 0), (1, -1)],
    4: [(-1, 1), (1, 1), (-1, -1), (1, -1)], 5: [(-1, 1), (1, 1), (0, 0), (-1, -1), (1, -1)],
    6: [(-1, 1), (1, 1), (-1, 0), (1, 0), (-1, -1), (1, -1)],
}


def make_domino(i, s):
    """Mesh spans x∈[-d,0] so the object origin is the front-bottom pivot edge."""
    h, w, d = BASE_H * s, BASE_W * s, BASE_D * s
    body = C.bevel_box(f"Dom{i}", (d, w, h), bevel=0.035 * s, segs=5)
    for v in body.data.vertices:
        v.co.x -= d / 2
        v.co.z += h / 2
    body.data.materials.append(lacquer)
    parts = [body]
    # inlay on the back face (x = -d) — the face the camera sees as it tips away
    fx = -d - 0.004 * s
    bar = C.bevel_box(f"Bar{i}", (0.01 * s, w * 0.72, 0.028 * s), bevel=0.008 * s, segs=3)
    bar.location = (fx, 0, h / 2)
    bar.data.materials.append(gold)
    parts.append(bar)
    for half, zc in ((random.randint(1, 6), h * 0.75), (random.randint(0, 6), h * 0.25)):
        for (u, v) in PIPS[half]:
            bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=0.055 * s, depth=0.014 * s,
                                                location=(fx, u * 0.13 * s, zc + v * 0.13 * s),
                                                rotation=(0, math.pi / 2, 0))
            p = bpy.context.active_object
            p.data.materials.append(gold)
            bpy.ops.object.shade_smooth()
            parts.append(p)
    for p in parts:
        p.select_set(False)
    # apply modifiers then join into one object
    for p in parts:
        bpy.context.view_layer.objects.active = p
        for m in list(p.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    body.select_set(False)
    return body, h, d


doms = []
x = 0.0
for i in range(N):
    s = GROW ** i
    o, h, d = make_domino(i, s)
    doms.append(dict(obj=o, h=h, d=d, x=x))
    x += 0.62 * h
# the chain is built along +x and mirrored (parent scale x=-1) so on screen it
# reads left -> right while the camera looks at the inlaid back faces
chain = C.link(bpy.data.objects.new("Chain", None))
chain.scale = (-1, 1, 1)
for dm in doms:
    dm["obj"].location = (dm["x"] + dm["d"] / 2, 0, 0)
    dm["obj"].parent = chain

# ------------------------------------------------------------------ fall kinematics
START = 14  # frame the first domino is tipped
K = 0.15 * C.FPS  # frames per sqrt(height)
for i, dm in enumerate(doms):
    if i < N - 1:
        nx = doms[i + 1]
        gap = (nx["x"] - nx["d"] / 2) - (dm["x"] + dm["d"] / 2) + nx["d"] / 2
        gap = (nx["x"]) - (dm["x"] + dm["d"] / 2)  # tip reaches next piece's back face
        dm["theta_c"] = math.asin(min(1.0, gap / dm["h"]))
        dm["theta_rest"] = max(dm["theta_c"] + 0.15, math.acos(min(1.0, 1.4 * nx["d"] / dm["h"])) * 0.82)
    else:
        dm["theta_c"] = math.pi / 2
        dm["theta_rest"] = math.pi / 2
    dm["T"] = K * math.sqrt(dm["h"]) * min(1.2, (dm["theta_c"] / 0.62) ** 0.5)
t = START
for dm in doms:
    dm["t0"] = t
    t += dm["T"]
    dm["t1"] = t
END_HIT = doms[-1]["t1"]
print("domino contact frames:", [round(d["t1"], 1) for d in doms])


def angle(i, f):
    dm = doms[i]
    if f <= dm["t0"]:
        return 0.0
    if f <= dm["t1"]:
        u = (f - dm["t0"]) / dm["T"]
        a = dm["theta_c"] * (u ** 2.1)
        if i == N - 1:  # last one: lands with a small damped settle
            return a
        return a
    if i == N - 1:
        k = f - dm["t1"]
        return math.pi / 2 - math.radians(2.4) * math.exp(-k / 3.0) * abs(math.sin(k * 0.9))
    nxt = angle(i + 1, f) / (math.pi / 2)
    return dm["theta_c"] + (dm["theta_rest"] - dm["theta_c"]) * C.ease_out(min(1.0, nxt * 1.1), 2)


for i, dm in enumerate(doms):
    o = dm["obj"]
    C.key_every_frame(o, F0, F1, lambda f, i=i: dict(rotation_euler=(0, angle(i, f), 0)))
    # subframe keys for correct motion blur on the fast phases
    for f in range(F0, F1):
        for sub in (0.25, 0.5, 0.75):
            o.rotation_euler = (0, angle(i, f + sub), 0)
            o.keyframe_insert("rotation_euler", frame=f + sub)
    C._linear(o.animation_data.action)

# warm bokeh lights far behind (real DOF bokeh)
bk_m, _ = C.mat_emission("Bokeh", (1.0, 0.62, 0.28), 6)
bk_c, _ = C.mat_emission("BokehCool", (0.45, 0.6, 1.0), 3.5)
for k in range(34):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.3, 0.6),
                                         location=(-random.uniform(-8, 26), random.uniform(-21, -16), random.uniform(1.5, 16)))
    b = bpy.context.active_object
    b.data.materials.append(bk_m if k % 3 else bk_c)
    b.visible_glossy = False

# ------------------------------------------------------------------ lighting
C.area_light("Key", (3, 4, 14), ("aim", (-5, 0, 0)), 6.0, 2200, (1.0, 0.94, 0.86))
C.area_light("StripL", (6, -3, 6), ("aim", (-4, 0, 3)), 0.6, 1100, (0.7, 0.8, 1.0), size_y=12)
C.area_light("Rim", (-14, -10, 9), ("aim", (-5, 0, 3)), 4.0, 3500, (0.62, 0.74, 1.0), size_y=2)
C.area_light("Front", (-4, 16, 3), ("aim", (-4, 0, 2)), 10.0, 500, (1.0, 0.9, 0.78))
C.spot_light("Spot", (-9, 3, 22), (-8, 0, 0), 26000, (1.0, 0.86, 0.62), size_deg=34, blend=0.7, radius=0.6)

# ------------------------------------------------------------------ camera
cam = C.camera((3, 5, 1.2), (-0.5, 0, 0.5), lens=40, fstop=1.8)
cam.data.sensor_fit = "VERTICAL"


def focus_x(f):
    """Camera follows the active domino with a smooth lag."""
    xs = []
    for i, dm in enumerate(doms):
        w = math.exp(-((f - (dm["t0"] + dm["T"] * 0.6)) / 12.0) ** 2)
        xs.append((w, i))
    tot = sum(w for w, _ in xs) + 1e-9
    return sum(w * i for w, i in xs) / tot


def cam_at(f):
    # continuous "chain index" the camera tracks (0..N-1)
    lead = 0.0
    for i, dm in enumerate(doms):
        if f >= dm["t0"]:
            lead = i + min(1.0, (f - dm["t0"]) / dm["T"])
    lead = min(lead, N - 1 + 0.35)
    # framing scales with the size of the piece currently in motion
    i0 = min(int(lead), N - 1)
    fr = lead - i0
    hl = GROW ** (lead + 0.35)
    xl = doms[i0]["x"] + (doms[min(i0 + 1, N - 1)]["x"] - doms[i0]["x"]) * fr
    tx = -(xl + 0.30 * hl)
    up = C.ease_io((lead - 4.3) / 2.0)  # finale: crane up and look down on the impact
    tz = C.lerp(0.48 * hl, 0.16 * hl, up)
    dist = C.lerp(3.6 * hl + 1.4, 2.3 * hl + 1.0, up)
    tx -= up * 0.35 * hl
    e = min(1.0, lead / (N - 1))
    az = math.radians(C.lerp(42, 30, e))
    tgt = Vector((tx, 0, tz))
    loc = tgt + Vector((math.sin(az) * dist, math.cos(az) * dist, C.lerp(-0.25 * hl + 0.1, 0.95 * hl, up)))
    rot = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    rot.y += math.radians(C.lerp(-3.0, 2.0, e))
    return dict(location=loc, rotation_euler=rot), (loc - tgt).length


# smooth the camera path: evaluate on a dense grid then low-pass
raw = [cam_at(f) for f in range(F0 - 20, F1 + 21)]
import numpy as np
L = np.array([[*r[0]["location"]] for r in raw])
R = np.array([[*r[0]["rotation_euler"]] for r in raw])
D = np.array([r[1] for r in raw])
ker = np.exp(-np.linspace(-2.5, 2.5, 25) ** 2)
ker /= ker.sum()
sm = lambda a: np.stack([np.convolve(np.pad(a[:, k], 12, mode="edge"), ker, "valid") for k in range(a.shape[1])], 1)
L, R = sm(L), sm(R)
D = np.convolve(np.pad(D, 12, mode="edge"), ker, "valid")
for j, f in enumerate(range(F0 - 20, F1 + 21)):
    if F0 <= f <= F1:
        cam.location = L[j]
        cam.rotation_euler = R[j]
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cam.data.dof.focus_distance = float(D[j])
        cam.data.dof.keyframe_insert("focus_distance", frame=f)
C._linear(cam.animation_data.action)

C.render(OUT, F0, F1, samples=SAMPLES, step=int(A.get("step", 1)))
