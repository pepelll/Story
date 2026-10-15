"""Prison-bars concept: one still per stage (no animation).

Graphic, reduced jail door: satin dark-chrome round bars, flat riveted
straps. Rendered over a transparent shadow catcher so the pearl background
and typography are layered in 2D (bars can sit in front of the text, and the
stage-4 bar shadows fall across the wall *and* the words).

Usage: python bars.py -- stage=1..5 out=file.png [samples=96] [pct=100]
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blender"))
import bpy
from mathutils import Vector

import common as C

A = C.args()
STAGE = int(A.get("stage", 3))
OUT = A.get("out", f"/tmp/bars{STAGE}.png")

sc = C.reset()
sc.render.film_transparent = True
sc.render.image_settings.color_mode = "RGBA"
sc.render.resolution_percentage = int(A.get("pct", 100))
sc.render.use_motion_blur = False

# neutral studio world for reflections (dark floor, bright sky)
wn, wl = sc.world.node_tree.nodes, sc.world.node_tree.links
tc = wn.new("ShaderNodeTexCoord")
sep = wn.new("ShaderNodeSeparateXYZ")
ramp = wn.new("ShaderNodeValToRGB")
wl.new(tc.outputs["Generated"], sep.inputs[0])
wl.new(sep.outputs["Z"], ramp.inputs["Fac"])
ramp.color_ramp.elements[0].position = 0.45
ramp.color_ramp.elements[0].color = (0.08, 0.08, 0.08, 1)
ramp.color_ramp.elements[1].position = 0.8
ramp.color_ramp.elements[1].color = (0.9, 0.9, 0.9, 1)
wl.new(ramp.outputs["Color"], wn["Background"].inputs["Color"])
wn["Background"].inputs["Strength"].default_value = 0.8

steel = C.mat_principled("DarkChrome", (0.30, 0.30, 0.31), metallic=1.0, rough=0.22)
C.add_noise_roughness(steel, 0.22, 0.06, scale=20)
strap_m = C.mat_principled("Strap", (0.20, 0.20, 0.21), metallic=1.0, rough=0.32)

N = 7
SP = 0.46            # bar spacing
R = 0.065            # bar radius
HGT = 5.2
X = [(i - (N - 1) / 2) * SP for i in range(N)]


def bar(x, h, z0=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=R, depth=h, location=(x, 0, z0 + h / 2))
    o = bpy.context.active_object
    bpy.ops.object.shade_smooth()
    o.data.materials.append(steel)
    # rounded caps so each bar ends cleanly when it is still "growing"
    for zc in (z0, z0 + h):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=R, location=(x, 0, zc), segments=32, ring_count=16)
        c = bpy.context.active_object
        bpy.ops.object.shade_smooth()
        c.data.materials.append(steel)
    return o


def strap(z, w=None):
    w = w or (X[-1] - X[0] + 0.5)
    s = C.bevel_box(f"Strap{z}", (w, 0.07, 0.24), bevel=0.02, segs=3)
    s.location = (0, 0.0, z)
    s.data.materials.append(strap_m)
    for x in X:  # rivets where each bar passes through the strap
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.045, location=(x, 0.05, z), segments=24, ring_count=12)
        r = bpy.context.active_object
        r.scale = (1, 0.55, 1)
        bpy.ops.object.shade_smooth()
        r.data.materials.append(steel)


def catcher_floor():
    bpy.ops.mesh.primitive_plane_add(size=60)
    bpy.context.active_object.is_shadow_catcher = True


def catcher_wall(y):
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, y, 10), rotation=(math.pi / 2, 0, 0))
    bpy.context.active_object.is_shadow_catcher = True


def strip(name, loc, tgt, energy, w=0.5, h=6.0):
    o = C.area_light(name, loc, ("aim", tgt), w, energy, (1, 1, 1), size_y=h)
    o.visible_glossy = True
    return o


# ------------------------------------------------------------------ stages
# Layout rule: bars live ONLY in the lower half of the 9:16 frame; the top
# half is reserved for typography. Cameras stay level (no keystoning) and use
# lens shift to push the subject down.
def frame_low(cam, shift):
    cam.data.shift_y = shift


if STAGE in (1, 2, 3):  # same locked frontal camera for the first three beats
    if STAGE == 1:      # a single bar rises from the floor
        bar(0.0, 1.9)
    elif STAGE == 2:    # bars grow in a staggered rhythm
        for x, h in zip(X, [1.2, 2.3, 3.4, 4.4, 3.1, 2.0, 1.0]):
            bar(x, h)
    else:               # the grid closes: full door with straps + rivets
        for x in X:
            bar(x, HGT)
        for z in (0.55, 2.7, 4.75):
            strap(z)
    catcher_floor()
    cam = C.camera((0, 18.5, 2.6), (0, 0, 2.6), lens=50, fstop=None)
    frame_low(cam, 0.25)
elif STAGE == 4:        # 3/4 view, back light: long bar shadows run toward camera
    for x in X:
        bar(x, HGT)
    for z in (0.55, 2.7, 4.75):
        strap(z)
    catcher_floor()
    cam = C.camera((7.0, 20.0, 7.0), (0.6, 0, 2.6), lens=50, fstop=None)
    cam.rotation_euler.x = math.radians(80)  # slight look-down shows the floor stripes
    frame_low(cam, 0.17)
elif STAGE == 5:        # wide bleed of bars along the bottom edge, cropped by frame
    N5 = 13
    for i in range(N5):
        bar((i - (N5 - 1) / 2) * SP, HGT)
    for z in (0.55, 2.7, 4.75):
        strap(z, (N5 - 1) * SP + 0.5)
    catcher_floor()
    cam = C.camera((0, 9.0, 3.0), (0, 0, 3.0), lens=35, fstop=None)
    frame_low(cam, 0.33)

# lights: soft key + strip highlights so the round bars read as polished tubes
if STAGE == 4:
    sun = bpy.data.lights.new("Sun", "SUN")
    sun.energy = 5.0
    sun.angle = math.radians(1.5)
    so = C.link(bpy.data.objects.new("Sun", sun))
    so.location = (-2.0, -9.0, 6.5)
    C.aim(so, (0.5, 0, 0))  # from behind-left: stripes stretch forward-right
    C.area_light("Fill", (3, 10, 4), ("aim", (0, 0, 2.5)), 8, 260)
else:
    C.area_light("Key", (-3, 6, 7), ("aim", (0, 0, 2.5)), 4.0, 700)
    C.area_light("Fill", (4, 7, 2), ("aim", (0, 0, 2.5)), 5.0, 160)
strip("StripL", (-4.0, 3.0, 3.0), (0, 0, 2.5), 320)
strip("StripR", (4.0, 2.0, 3.0), (0, 0, 2.5), 220, 0.35)

sc.cycles.samples = int(A.get("samples", 96))
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("WROTE", OUT)
