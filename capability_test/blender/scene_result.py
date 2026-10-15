"""SCENE C — «РЕЗУЛЬТАТ»: a rising bar chart built from minted gold coins.

Coin = lathed profile (milled rim, recessed field, chamfers) + procedural
reeded edge (radial-gradient-driven bump) + embossed ₽ glyph extruded from the
Inter Display font. Five columns (5→28 coins) cascade in left→right; each coin
drops with gravity easing, a 1-frame squash-settle and a residual wobble, so
the stacks end slightly irregular like real stacked coins.

Run:  python scene_result.py -- out=/path/frames [samples=20] [f0=0] [f1=190] [step=2]
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector

import common as C

A = C.args()
OUT = A.get("out", "/tmp/result")
F0, F1 = int(A.get("f0", 0)), int(A.get("f1", 190))
SAMPLES = int(A.get("samples", 20))

sc = C.reset()
sc.frame_start, sc.frame_end = F0, F1
random.seed(11)

# ------------------------------------------------------------------ set
cove = C.mat_principled("Cove", (0.016, 0.013, 0.010), rough=0.5, spec=0.3)
C.add_noise_roughness(cove, 0.45, 0.12, scale=2.0)
C.backdrop(cove, radius=6, height=40, depth=10, width=60, front=12)

gold = C.mat_principled("CoinGold", (1.0, 0.74, 0.36), metallic=1.0, rough=0.16, aniso=0.25)
C.add_noise_roughness(gold, 0.17, 0.08, scale=25)
# reeded edge: radial gradient (angle) -> sine -> bump, masked to the coin edge
nt = gold.node_tree
b = nt.nodes["Principled BSDF"]
tc = nt.nodes.new("ShaderNodeTexCoord")
grad = nt.nodes.new("ShaderNodeTexGradient")
grad.gradient_type = "RADIAL"
mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = 220 * math.pi
sn = nt.nodes.new("ShaderNodeMath"); sn.operation = "SINE"
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ln = nt.nodes.new("ShaderNodeVectorMath"); ln.operation = "LENGTH"
mask = nt.nodes.new("ShaderNodeMapRange")
mask.inputs["From Min"].default_value = 0.47
mask.inputs["From Max"].default_value = 0.495
m2 = nt.nodes.new("ShaderNodeMath"); m2.operation = "MULTIPLY"
bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.12
nt.links.new(tc.outputs["Object"], grad.inputs["Vector"])
nt.links.new(grad.outputs["Fac"], mul.inputs[0])
nt.links.new(mul.outputs[0], sn.inputs[0])
comb = nt.nodes.new("ShaderNodeCombineXYZ")
nt.links.new(tc.outputs["Object"], sep.inputs[0])
nt.links.new(sep.outputs["X"], comb.inputs["X"])
nt.links.new(sep.outputs["Y"], comb.inputs["Y"])
nt.links.new(comb.outputs[0], ln.inputs[0])
nt.links.new(ln.outputs["Value"], mask.inputs["Value"])
nt.links.new(sn.outputs[0], m2.inputs[0])
nt.links.new(mask.outputs["Result"], m2.inputs[1])
nt.links.new(m2.outputs[0], bump.inputs["Height"])
nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])

# ------------------------------------------------------------------ coin master mesh
R, T = 0.5, 0.075
prof = [(0.0, 0.0), (0.40, 0.0), (0.44, 0.004), (0.47, 0.004), (0.49, 0.008), (0.50, 0.016),
        (0.50, T - 0.016), (0.49, T - 0.008), (0.47, T - 0.004), (0.44, T - 0.004), (0.43, T - 0.012),
        (0.30, T - 0.014), (0.0, T - 0.014)]
coin = C.lathe("CoinMaster", prof, segments=128)
bpy.context.view_layer.objects.active = coin
coin.select_set(True)
bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
coin.select_set(False)
coin.data.materials.append(gold)

# embossed ₽ on the top face
font = bpy.data.fonts.load("/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf")
tcu = bpy.data.curves.new("Glyph", "FONT")
tcu.body = "₽"
tcu.font = font
tcu.size = 0.48
tcu.extrude = 0.006
tcu.bevel_depth = 0.003
tcu.align_x = "CENTER"
tcu.align_y = "CENTER"
glyph = C.link(bpy.data.objects.new("Glyph", tcu))
glyph.location = (0, 0, T - 0.014 + 0.006)
bpy.context.view_layer.objects.active = glyph
glyph.select_set(True)
bpy.ops.object.convert(target="MESH")
glyph = bpy.context.active_object
glyph.data.materials.clear()
glyph.data.materials.append(gold)
glyph.select_set(True)
coin.select_set(True)
bpy.context.view_layer.objects.active = coin
bpy.ops.object.join()
coin.select_set(False)
coin_mesh = coin.data
coin.hide_render = True
coin.location = (0, 0, -50)

# ------------------------------------------------------------------ columns
COUNTS = [5, 9, 14, 20, 28]
SPACING = 1.22
coins = []
for j, n in enumerate(COUNTS):
    # diagonal staircase receding to screen-right/back: fits a vertical frame
    cx = -(j - 2) * SPACING * 0.62
    cyj = -(j - 2) * 1.05
    for k in range(n):
        o = C.link(bpy.data.objects.new(f"C{j}_{k}", coin_mesh))
        land = 10 + j * 7 + k * 1.55
        coins.append(dict(obj=o, cx=cx + random.uniform(-0.018, 0.018), cy=cyj + random.uniform(-0.018, 0.018),
                          z=k * T, land=land, rz=random.uniform(0, math.tau),
                          tilt=(random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)),
                          spin=random.uniform(-2.5, 2.5)))
LAST_LAND = max(c["land"] for c in coins)
print("last coin lands at", LAST_LAND)

DROP = 8.0  # frames of free fall
H0 = 2.2


def coin_state(c, f):
    t = f - c["land"]
    if t < -DROP:
        return dict(location=(c["cx"], c["cy"], c["z"] + H0 + 30), rotation_euler=(0, 0, 0))  # parked off-screen
    if t < 0:
        u = 1 + t / DROP  # 0..1
        z = c["z"] + H0 * (1 - u * u)
        k = 1 - u
        return dict(location=(c["cx"], c["cy"], z),
                    rotation_euler=(c["tilt"][0] * k, c["tilt"][1] * k, c["rz"] + c["spin"] * k))
    # settle: tiny bounce + damped wobble
    w = math.exp(-t / 2.5)
    z = c["z"] + 0.012 * w * abs(math.sin(t * 1.6))
    return dict(location=(c["cx"], c["cy"], z),
                rotation_euler=(0.05 * w * math.sin(t * 2.1), 0.05 * w * math.cos(t * 1.7), c["rz"]))


for c in coins:
    o = c["obj"]
    for f in range(F0, F1 + 1):
        for sub in ((0.0, 0.5) if abs(f - c["land"]) < DROP + 2 else (0.0,)):
            st = coin_state(c, f + sub)
            o.location = st["location"]
            o.rotation_euler = st["rotation_euler"]
            o.keyframe_insert("location", frame=f + sub)
            o.keyframe_insert("rotation_euler", frame=f + sub)
    C._linear(o.animation_data.action)

# plinth-like glossy base strip under the chart
base_m = C.mat_principled("Base", (0.012, 0.011, 0.010), rough=0.07, coat=1.0, coat_rough=0.03)
base = C.bevel_box("Base", (1.6, 6.6, 0.12), bevel=0.04, segs=4)
base.location = (0, 0, -0.06)
base.rotation_euler = (0, 0, math.atan2(0.62 * SPACING, 1.05))
base.hide_render = True
base.data.materials.append(base_m)
for o in bpy.data.objects:
    if o.name.startswith("C") and "_" in o.name:
        o.location.z  # noqa (keyed)

# warm bokeh
bk, _ = C.mat_emission("Bokeh", (1.0, 0.66, 0.30), 5)
bkc, _ = C.mat_emission("BokehC", (1.0, 0.85, 0.6), 3)
for k in range(40):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=random.uniform(0.12, 0.3),
                                         location=(random.uniform(-9, 9), random.uniform(-9.5, -6), random.uniform(0.5, 9)))
    o = bpy.context.active_object
    o.data.materials.append(bk if k % 3 else bkc)
    o.visible_glossy = False

# ------------------------------------------------------------------ lights
C.area_light("Key", (-4, 5, 7), ("aim", (0, 0, 0.8)), 4.0, 900, (1.0, 0.9, 0.78))
C.area_light("StripL", (-5, 1, 2.5), ("aim", (0, 0, 1)), 0.25, 450, (1.0, 0.95, 0.9), size_y=5)
C.area_light("StripR", (5, 2, 2.5), ("aim", (0, 0, 1)), 0.25, 520, (1.0, 0.93, 0.85), size_y=5)
C.area_light("Rim", (2, -5, 5), ("aim", (0, 0, 1)), 3.0, 900, (0.7, 0.8, 1.0))
C.spot_light("Spot", (1.5, 2, 11), (1.2, 0, 0.5), 9000, (1.0, 0.85, 0.6), size_deg=30, blend=0.6, radius=0.4)

# ------------------------------------------------------------------ camera
cam = C.camera((0, 7, 1.0), (0, 0, 0.8), lens=42, fstop=2.4)


def cam_at(f):
    t = (f - F0) / (F1 - F0)
    e = C.ease_io(t)
    az = math.radians(C.lerp(-34, 14, e))
    dist = C.lerp(4.3, 7.4, C.ease_out(t, 2))
    tgt = Vector((C.lerp(0.9, -0.1, e), 0, C.lerp(0.75, 1.35, e)))
    loc = tgt + Vector((math.sin(az) * dist, math.cos(az) * dist, C.lerp(-0.35, 0.2, e)))
    rot = (tgt - loc).to_track_quat("-Z", "Y").to_euler()
    rot.y += math.radians(C.lerp(2.5, -1.0, e))
    return dict(location=loc, rotation_euler=rot)


C.key_every_frame(cam, F0, F1, cam_at)
for f in range(F0, F1 + 1):
    sc.frame_set(f)
    cam.data.dof.focus_distance = (cam.location - Vector((-0.3, 0, 0.9))).length
    cam.data.dof.keyframe_insert("focus_distance", frame=f)

C.render(OUT, F0, F1, samples=SAMPLES, step=int(A.get("step", 1)))
