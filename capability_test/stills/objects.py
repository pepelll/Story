"""Static object renders for the style-approval frames (no animation).

Monochrome, graphic, slightly stylised objects rendered over a transparent
shadow catcher, so the grey/white shimmering background and the typography
are layered in 2D (text can sit *behind* the object, like the 150K reference).

Usage: python objects.py -- obj=bulb|dominoes|coins|clip out=file.png [samples=96] [pct=100]
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender"))
import bpy
from mathutils import Vector

import common as C

A = C.args()
OBJ = A.get("obj", "bulb")
OUT = A.get("out", f"/tmp/{OBJ}.png")

sc = C.reset()
sc.render.film_transparent = True
sc.render.image_settings.color_mode = "RGBA"
sc.render.resolution_percentage = int(A.get("pct", 100))
sc.render.use_motion_blur = False
try:
    sc.view_settings.look = "AgX - Base Contrast"
except Exception:
    pass

# soft neutral studio environment so polished surfaces have something to reflect
wn = sc.world.node_tree.nodes
wl = sc.world.node_tree.links
bg = wn["Background"]
grad = wn.new("ShaderNodeTexGradient")
tc = wn.new("ShaderNodeTexCoord")
sep = wn.new("ShaderNodeSeparateXYZ")
ramp = wn.new("ShaderNodeValToRGB")
wl.new(tc.outputs["Generated"], sep.inputs[0])
wl.new(sep.outputs["Z"], ramp.inputs["Fac"])
ramp.color_ramp.elements[0].position = 0.45
ramp.color_ramp.elements[0].color = (0.10, 0.10, 0.10, 1)
ramp.color_ramp.elements[1].position = 0.75
ramp.color_ramp.elements[1].color = (0.85, 0.85, 0.85, 1)
wl.new(ramp.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.9

# materials: everything in one grey family
pearl = C.mat_principled("Pearl", (0.62, 0.62, 0.63), metallic=0.85, rough=0.13, coat=0.6, coat_rough=0.05)
chrome = C.mat_principled("Chrome", (0.78, 0.78, 0.79), metallic=1.0, rough=0.08)
C.add_noise_roughness(chrome, 0.09, 0.04, scale=30)
porcelain = C.mat_principled("Porcelain", (0.86, 0.86, 0.86), rough=0.22, coat=1.0, coat_rough=0.04)
graphite = C.mat_principled("Graphite", (0.05, 0.05, 0.055), rough=0.3, coat=0.5)


def catcher(size=40):
    bpy.ops.mesh.primitive_plane_add(size=size)
    p = bpy.context.active_object
    p.is_shadow_catcher = True
    return p


def strip(name, loc, tgt, energy, w=0.6, h=4.0):
    o = C.area_light(name, loc, ("aim", tgt), w, energy, (1, 1, 1), size_y=h)
    o.visible_glossy = True  # strip highlights on the polished surfaces
    return o


# ------------------------------------------------------------------ objects
if OBJ == "bulb":
    # sculptural bulb: one polished grey material, no glass realism
    prof = [(0.29, 0.00), (0.30, 0.10), (0.34, 0.26), (0.48, 0.50), (0.64, 0.80), (0.71, 1.06),
            (0.70, 1.32), (0.60, 1.58), (0.42, 1.78), (0.20, 1.89), (0.0, 1.92)]
    import importlib
    pts = []
    P = [prof[0]] + prof + [prof[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(14):
            t = k / 14
            pts.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(2)))
    pts.append(prof[-1])
    root = C.link(bpy.data.objects.new("Bulb", None))
    env = C.lathe("Envelope", pts, 160)
    env.data.materials.append(pearl)
    rings = []
    for k in range(6):  # stylised thread: stacked torus-like rings
        z = -0.06 - k * 0.062
        r = C.lathe(f"Ring{k}", [(0.0, z - 0.03), (0.30, z - 0.03), (0.33, z), (0.30, z + 0.03), (0.0, z + 0.03)], 96)
        r.data.materials.append(chrome)
        rings.append(r)
    cap = C.lathe("Cap", [(0.0, -0.46), (0.12, -0.46), (0.24, -0.43), (0.30, -0.40), (0.30, -0.36), (0.0, -0.36)], 96)
    cap.data.materials.append(graphite)
    collar = C.lathe("Collar", [(0.0, -0.03), (0.33, -0.03), (0.34, 0.0), (0.30, 0.03), (0.0, 0.03)], 96)
    collar.data.materials.append(chrome)
    for o in [env, cap, collar] + rings:
        o.parent = root
    root.location = (0, 0, 0.46)
    root.rotation_euler = (math.radians(-6), math.radians(-14), 0)
    catcher()
    cam = C.camera((0.0, 3.9, 1.5), (0.18, 0, 1.25), lens=52, fstop=None)
    strip("StripL", (-2.6, 1.2, 2.4), (0, 0, 1.3), 220)
    strip("StripR", (2.4, 0.4, 2.6), (0, 0, 1.3), 160, 0.4)
    C.area_light("Key", (-2.5, 2.5, 4.5), ("aim", (0, 0, 1)), 3.0, 380)
    C.area_light("Fill", (2.5, 3.5, 1.0), ("aim", (0, 0, 1)), 3.0, 90)
    C.area_light("Top", (0, -0.5, 5.0), ("aim", (0, 0, 0)), 2.0, 260)

elif OBJ == "dominoes":
    import random
    random.seed(4)
    N = 6
    angles = [62, 34, 12, 0, 0, 0]
    for i in range(N):
        s = 1.0
        h, w, d = 1.0, 0.5, 0.16
        dm = C.bevel_box(f"D{i}", (d, w, h), bevel=0.03, segs=5)
        for v in dm.data.vertices:
            v.co.x -= d / 2
            v.co.z += h / 2
        dm.data.materials.append(porcelain)
        bpy.context.view_layer.objects.active = dm
        for m in list(dm.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
        # graphite pips + divider on the back face
        parts = [dm]
        bar = C.bevel_box(f"B{i}", (0.012, w * 0.7, 0.022), bevel=0.006, segs=2)
        bar.location = (0.004, 0, h / 2)
        bar.data.materials.append(graphite)
        parts.append(bar)
        for half, zc in ((random.randint(1, 6), h * 0.75), (random.randint(1, 6), h * 0.25)):
            lay = {1: [(0, 0)], 2: [(-1, 1), (1, -1)], 3: [(-1, 1), (0, 0), (1, -1)], 4: [(-1, 1), (1, 1), (-1, -1), (1, -1)],
                   5: [(-1, 1), (1, 1), (0, 0), (-1, -1), (1, -1)], 6: [(-1, 1), (1, 1), (-1, 0), (1, 0), (-1, -1), (1, -1)]}[half]
            for (u, v) in lay:
                bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=0.05, depth=0.012,
                                                    location=(0.004, u * 0.12, zc + v * 0.12), rotation=(0, math.pi / 2, 0))
                pp = bpy.context.active_object
                pp.data.materials.append(graphite)
                parts.append(pp)
        for p in parts:
            bpy.context.view_layer.objects.active = p
            for m in list(p.modifiers):
                bpy.ops.object.modifier_apply(modifier=m.name)
            p.select_set(True)
        bpy.context.view_layer.objects.active = dm
        bpy.ops.object.join()
        dm.select_set(False)
        dm.location = (-i * 0.62, 0, 0)
        dm.rotation_euler = (0, math.radians(-angles[i]), 0)
        dm.scale = (1, 1, 1)
    catcher()
    cam = C.camera((1.6, 3.4, 2.2), (-1.5, 0, 0.45), lens=46, fstop=None)
    C.area_light("Key", (2.5, 2.0, 5.0), ("aim", (-1.5, 0, 0)), 4.0, 650)
    C.area_light("Fill", (-1.0, 5.0, 1.5), ("aim", (-1.5, 0, 0.5)), 5.0, 120)
    strip("Strip", (3.0, -1.0, 2.0), (-1.5, 0, 0.5), 200)

elif OBJ == "coins":
    R, T = 0.5, 0.075
    prof = [(0.0, 0.0), (0.44, 0.0), (0.49, 0.008), (0.50, 0.018), (0.50, T - 0.018), (0.49, T - 0.008),
            (0.44, T - 0.004), (0.42, T - 0.012), (0.0, T - 0.012)]
    master = C.lathe("CoinM", prof, 128)
    master.data.materials.append(chrome)
    font = bpy.data.fonts.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "RobotoCondensed-ExtraBoldItalic.ttf"))
    tcu = bpy.data.curves.new("G", "FONT")
    tcu.body = "₽"
    tcu.font = font
    tcu.size = 0.5
    tcu.extrude = 0.008
    tcu.align_x = tcu.align_y = "CENTER"
    g = C.link(bpy.data.objects.new("Glyph", tcu))
    g.location = (0, 0, T - 0.012)
    bpy.context.view_layer.objects.active = g
    g.select_set(True)
    bpy.ops.object.convert(target="MESH")
    g = bpy.context.active_object
    g.data.materials.clear()
    g.data.materials.append(chrome)
    master.select_set(True)
    bpy.context.view_layer.objects.active = master
    bpy.ops.object.join()
    master.select_set(False)
    import random
    random.seed(2)
    for k in range(9):  # stack
        o = C.link(bpy.data.objects.new(f"S{k}", master.data))
        o.location = (random.uniform(-0.012, 0.012), random.uniform(-0.012, 0.012), k * T)
        o.rotation_euler = (0, 0, random.uniform(0, 6.28))
    hero = C.link(bpy.data.objects.new("Hero", master.data))  # coin landing on the stack, on edge
    hero.location = (0.05, 0.02, 9 * T + 0.55)
    hero.rotation_euler = (math.radians(-74), math.radians(10), math.radians(14))
    master.hide_render = True
    catcher()
    cam = C.camera((0.0, 3.3, 0.55), (0.0, 0, 0.78), lens=55, fstop=None)
    strip("StripL", (-2.2, 1.0, 2.0), (0, 0, 0.7), 260)
    strip("StripR", (2.2, 0.6, 2.4), (0, 0, 0.7), 200, 0.4)
    C.area_light("Key", (-1.5, 2.8, 3.5), ("aim", (0, 0, 0.6)), 3.0, 320)
    C.area_light("Top", (0, 0, 5), ("aim", (0, 0, 0)), 2.0, 220)

elif OBJ == "clip":
    pts = []
    # classic gem paperclip as a 2D path, then a beveled curve
    L1, L2, L3, r1, r2, r3 = 1.0, 0.82, 0.62, 0.16, 0.12, 0.085
    path = [(-r2, -0.35), (-r2, L2 - 0.35)]
    def arc(cx, cy, r, a0, a1, n=24):
        return [(cx + r * math.cos(a0 + (a1 - a0) * i / n), cy + r * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]
    path = [(r3, 0.15), (r3, L2 - 0.2)] + arc(0, L2 - 0.2, r3, 0, math.pi) + [(-r3, -0.2)] + arc(0.035, -0.2, r1 - 0.0 + 0.0 - 0.04, math.pi, 2 * math.pi) \
        + [(r1 - 0.005 + 0.0, L1 - 0.25)] + arc(0.0, L1 - 0.25, r1, 0, math.pi) + [(-r1, -0.05)]
    cu = bpy.data.curves.new("Clip", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.014
    cu.bevel_resolution = 6
    sp = cu.splines.new("POLY")
    sp.points.add(len(path) - 1)
    for p, (x, y) in zip(sp.points, path):
        p.co = (x, y, 0, 1)
    o = C.link(bpy.data.objects.new("Clip", cu))
    o.data.materials.append(chrome)
    o.rotation_euler = (0, 0, math.radians(-12))
    catcher()
    cam = C.camera((0, 0, 3.2), (0, 0.2, 0), lens=60, fstop=None)
    C.area_light("Key", (-1.5, 1.5, 3), ("aim", (0, 0, 0)), 2.0, 160)
    strip("Strip", (1.5, 0.5, 2), (0, 0, 0), 120, 0.3, 3)
    sc.render.resolution_x, sc.render.resolution_y = 600, 900

sc.cycles.samples = int(A.get("samples", 96))
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("WROTE", OUT)
