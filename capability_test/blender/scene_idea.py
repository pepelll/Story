"""SCENE A — «ИДЕЯ»: a vintage tungsten-filament bulb on a black stone plinth.

Fully procedural: lathed hand-blown glass envelope, true helical brass screw
thread, squirrel-cage tungsten filament with micro-coil wobble, glass stem and
molybdenum support wires. The filament ignites with an electrical flicker and
then warms the whole set. Studio strip-lights define the glass by reflection.

Run:  python scene_idea.py -- out=/path/frames [samples=64] [f0=0] [f1=155] [matte=1]
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
import bmesh
from mathutils import Vector

import common as C

A = C.args()
OUT = A.get("out", "/tmp/idea")
F0, F1 = int(A.get("f0", 0)), int(A.get("f1", 155))
SAMPLES = int(A.get("samples", 64))

sc = C.reset()
sc.frame_start, sc.frame_end = F0, F1

# ------------------------------------------------------------------ set
cove = C.mat_principled("Cove", (0.018, 0.017, 0.016), rough=0.55, spec=0.3)
C.add_noise_roughness(cove, 0.5, 0.12, scale=3.0)
C.backdrop(cove, radius=6, height=40, depth=9, width=60, front=10)

stone = C.mat_principled("BlackStone", (0.010, 0.010, 0.011), rough=0.08, spec=0.7, coat=0.6, coat_rough=0.03)
C.add_noise_roughness(stone, 0.10, 0.07, scale=9.0, detail=10)
C.add_bump(stone, strength=0.03, scale=120)
brass = C.mat_principled("Brass", (0.86, 0.58, 0.26), metallic=1.0, rough=0.22, aniso=0.3)
C.add_noise_roughness(brass, 0.22, 0.08, scale=60)
gold_line = C.mat_principled("GoldLine", (1.0, 0.70, 0.32), metallic=1.0, rough=0.12)

# plinth: two-step drum with chamfers and an inset gold ring
plinth = C.lathe("Plinth", [
    (0.0, 0.0), (1.30, 0.0), (1.30, 0.16), (1.27, 0.19), (1.02, 0.19),
    (1.0, 0.21), (1.0, 0.46), (0.985, 0.49), (0.96, 0.50), (0.0, 0.50)], segments=192, smooth=False)
plinth.data.materials.append(stone)
bpy.context.view_layer.objects.active = plinth
plinth.select_set(True)
bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
ring = C.lathe("GoldRing", [(1.004, 0.405), (1.012, 0.41), (1.012, 0.425), (1.004, 0.43)], segments=192)
ring.data.materials.append(gold_line)

# ------------------------------------------------------------------ bulb
root = C.link(bpy.data.objects.new("BulbRoot", None))
root.location = (0, 0, 0.97)


def parent(o):
    o.parent = root
    return o


# glass envelope (ST64 silhouette) — Catmull-Rom through control points
ctrl = [(0.29, 0.00), (0.30, 0.10), (0.34, 0.26), (0.48, 0.50), (0.64, 0.80), (0.71, 1.06),
        (0.70, 1.32), (0.60, 1.58), (0.42, 1.78), (0.20, 1.89), (0.0, 1.92)]


def catmull(pts, n=12):
    out = []
    P = [pts[0]] + pts + [pts[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    out.append(pts[-1])
    return out


glass_prof = catmull(ctrl, 14)
glass = parent(C.lathe("Glass", glass_prof, segments=160))
sol = glass.modifiers.new("thick", "SOLIDIFY")
sol.thickness = 0.014
sol.offset = 1.0
glass_m = C.mat_principled("Glass", (1.0, 0.975, 0.94), rough=0.0, transmission=1.0, ior=1.50, spec=0.5)
glass.data.materials.append(glass_m)

# brass screw base with a real helical thread
bm = bmesh.new()
NA, NZ = 128, 140
z0, z1, pitch = -0.40, -0.025, 0.085
rows = []
for iz in range(NZ + 1):
    z = z0 + (z1 - z0) * iz / NZ
    row = []
    for ia in range(NA):
        a = math.tau * ia / NA
        ph = (z / pitch - a / math.tau) * math.tau
        r = 0.305 + 0.022 * (0.5 + 0.5 * math.sin(ph)) ** 0.8
        row.append(bm.verts.new((r * math.cos(a), r * math.sin(a), z)))
    rows.append(row)
for iz in range(NZ):
    for ia in range(NA):
        f = bm.faces.new((rows[iz][ia], rows[iz][(ia + 1) % NA], rows[iz + 1][(ia + 1) % NA], rows[iz + 1][ia]))
        f.smooth = True
thread = parent(C.mesh_obj("Thread", bm))
thread.data.materials.append(brass)

collar = parent(C.lathe("Collar", [(0.0, -0.03), (0.33, -0.03), (0.338, -0.02), (0.338, 0.012), (0.315, 0.03), (0.29, 0.03)], 128))
collar.data.materials.append(brass)
insul_m = C.mat_principled("Insulator", (0.02, 0.02, 0.022), rough=0.05, coat=1.0)
insul = parent(C.lathe("Insulator", [(0.31, -0.40), (0.30, -0.43), (0.22, -0.46), (0.12, -0.47), (0.0, -0.47)], 96))
insul.data.materials.append(insul_m)
contact = parent(C.lathe("Contact", [(0.0, -0.485), (0.07, -0.485), (0.095, -0.47), (0.10, -0.455)], 64))
contact.data.materials.append(brass)

# inner glass stem + flare
stem = parent(C.lathe("Stem", [(0.0, 0.02), (0.20, 0.02), (0.13, 0.12), (0.06, 0.30), (0.05, 0.62), (0.07, 0.66), (0.0, 0.67)], 64))
stem.data.materials.append(glass_m)

# filament + support wires as curves
fil_m, fil_em = C.mat_emission("Tungsten", (1.0, 0.42, 0.10), 0.0)
wire_m = C.mat_principled("Wire", (0.6, 0.6, 0.62), metallic=1.0, rough=0.25)


def curve_obj(name, pts, bevel, mat):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = bevel
    cu.bevel_resolution = 3
    sp = cu.splines.new("POLY")
    sp.points.add(len(pts) - 1)
    for p, co in zip(sp.points, pts):
        p.co = (*co, 1)
    o = parent(C.link(bpy.data.objects.new(name, cu)))
    o.data.materials.append(mat)
    return o


N = 6
zb, zt = 0.74, 1.36
rb, rt = 0.07, 0.30
pts = []
for k in range(N):
    a0 = math.tau * k / N
    a1 = a0 + math.tau / (2 * N)
    a2 = a0 + math.tau / N
    # up-stroke from hub to top, down-stroke back — tight micro-coil wobble
    for seg, (aa, ab, za, zb_, ra, rb_) in enumerate([(a0, a1, zb, zt, rb, rt), (a1, a2, zt, zb, rt, rb)]):
        for i in range(90):
            t = i / 89
            # sag curve so strokes bow outward like real hairpins
            r = ra + (rb_ - ra) * t + 0.05 * math.sin(math.pi * t)
            a = aa + (ab - aa) * t
            z = za + (zb_ - za) * t
            wob = 0.006
            ph = t * 70 * math.tau
            x = r * math.cos(a) + wob * math.cos(ph) * math.cos(a)
            y = r * math.sin(a) + wob * math.cos(ph) * math.sin(a)
            pts.append((x, y, z + wob * math.sin(ph)))
fil = curve_obj("Filament", pts, 0.0035, fil_m)
for k in range(N):
    a = math.tau * k / N + math.tau / (2 * N)
    curve_obj(f"Support{k}", [(0.04 * math.cos(a), 0.04 * math.sin(a), 0.66), (0.20 * math.cos(a), 0.20 * math.sin(a), 1.10),
                              (rt * math.cos(a), rt * math.sin(a), zt + 0.004)], 0.0018, wire_m)
curve_obj("Lead1", [(0.05, 0, 0.02), (0.05, 0, 0.62), (0.06, 0, zb)], 0.004, wire_m)
curve_obj("Lead2", [(-0.05, 0, 0.02), (-0.05, 0, 0.62), (-0.06, 0, zb)], 0.004, wire_m)

core = C.point_light("FilamentLight", (0, 0, 0.97 + 1.06), 0.0, (1.0, 0.55, 0.22), radius=0.22)

# ------------------------------------------------------------------ lighting
C.area_light("StripL", (-3.4, 1.2, 2.3), ("aim", (0, 0, 2.0)), 0.30, 300, (0.85, 0.9, 1.0), size_y=5.0)
C.area_light("StripR", (3.2, 0.6, 2.3), ("aim", (0, 0, 2.0)), 0.22, 220, (1.0, 0.96, 0.92), size_y=5.0)
C.area_light("Top", (0, 0.6, 6.0), (0, 0, 0), 1.6, 230, (1.0, 0.95, 0.88))
C.spot_light("Spot", (0.0, 1.2, 9.0), (0, 0, 0.4), 2600, (1.0, 0.93, 0.82), size_deg=26, blend=0.55, radius=0.3)
C.area_light("Rim", (0, -4.5, 3.5), (-115, 0, 0), 2.5, 260, (0.6, 0.72, 1.0))
# soft wash on the cove so the background reads as a gradient, not void
C.area_light("Wash", (0, -6.5, 7.0), (-150, 0, 0), 6.0, 90, (0.55, 0.62, 0.8))

# ------------------------------------------------------------------ animation
IGN = 22  # first spark (local frame)


def filament_level(f):
    """Electrical flicker on ignition, then a warm ramp with a slight overshoot."""
    seq = {IGN: 0.55, IGN + 1: 0.9, IGN + 2: 0.35, IGN + 3: 0.0, IGN + 4: 0.0, IGN + 5: 0.0, IGN + 6: 0.0,
           IGN + 7: 0.25, IGN + 8: 0.6, IGN + 9: 0.15, IGN + 10: 0.0, IGN + 11: 0.0}
    if f < IGN:
        return 0.0
    if f in seq:
        return seq[f]
    t = (f - (IGN + 12)) / 18.0
    if t <= 1:
        return C.ease_out(t, 3) * 1.12
    return 1.0 + 0.12 * math.exp(-(f - IGN - 30) / 10.0) + 0.015 * math.sin(f * 0.9)


for f in range(F0, F1 + 1):
    lv = filament_level(f)
    fil_em.inputs["Strength"].default_value = 70.0 * lv
    fil_em.inputs["Strength"].keyframe_insert("default_value", frame=f)
    core.data.energy = 55.0 * lv
    core.data.keyframe_insert("energy", frame=f)
    for name in ("Spot",):
        pass

root.keyframe_insert("rotation_euler", frame=F0)
root.rotation_euler = (0, 0, math.radians(-14))
root.keyframe_insert("rotation_euler", frame=F0)
root.rotation_euler = (0, 0, math.radians(16))
root.keyframe_insert("rotation_euler", frame=F1)
C._linear(root.animation_data.action)

target = Vector((0, 0, 1.78))
cam = C.camera((0, 7.0, 1.5), target, lens=55, fstop=2.2)


def cam_at(f):
    t = (f - F0) / max(1, F1 - F0)
    e = C.ease_io(t * 0.85 + 0.15 * t * t)
    dist = C.lerp(8.4, 6.2, e)
    ang = math.radians(C.lerp(-12, 7, e))
    z = C.lerp(1.15, 1.75, e)
    loc = Vector((math.sin(ang) * dist, math.cos(ang) * dist, z))
    tgt = target + Vector((0, 0, C.lerp(-0.12, 0.05, e)))
    rot = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    rot.y += math.radians(C.lerp(-1.5, 1.0, e))  # dutch drift
    return dict(location=loc, rotation_euler=rot)


C.key_every_frame(cam, F0, F1, cam_at)
cam.data.dof.focus_object = None
cam.data.dof.focus_distance = 7.0
for f in range(F0, F1 + 1):
    sc.frame_set(f)
    cam.data.dof.focus_distance = (cam.location - Vector((0, 0, 2.0))).length
    cam.data.dof.keyframe_insert("focus_distance", frame=f)

C.render(OUT, F0, F1, samples=SAMPLES, step=int(A.get("step", 1)))
