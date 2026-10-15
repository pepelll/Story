"""Shared Blender (bpy) toolkit for the capability-test scenes.

Everything is procedural: geometry, materials, lights and animation are built
from code so every scene is reproducible from source with no external assets.
"""
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector, Euler

W, H, FPS = 1080, 1920, 60


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = int(os.environ.get("RES_PCT", 100))
    sc.render.fps = FPS
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "16"
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.max_bounces = 8
    sc.cycles.transmission_bounces = 8
    sc.cycles.glossy_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.blur_glossy = 1.0
    sc.render.use_persistent_data = True
    sc.render.use_motion_blur = True
    sc.render.motion_blur_shutter = 0.5
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.film_transparent = False
    world = bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0, 0, 0, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    return sc


def args():
    """Parse `-- key=value` style args after the script name."""
    out = {}
    for a in sys.argv[1:]:
        if "=" in a:
            k, v = a.split("=", 1)
            out[k.lstrip("-")] = v
    return out


# ---------------------------------------------------------------- materials
def _bsdf(mat):
    mat.use_nodes = True
    return mat.node_tree.nodes["Principled BSDF"]


def mat_principled(name, color, metallic=0.0, rough=0.4, spec=0.5, coat=0.0,
                   coat_rough=0.05, transmission=0.0, ior=1.45, emission=None,
                   emission_strength=0.0, aniso=0.0):
    m = bpy.data.materials.new(name)
    b = _bsdf(m)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = ior
    b.inputs["Specular IOR Level"].default_value = spec
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = coat_rough
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["Anisotropic"].default_value = aniso
    if emission is not None:
        b.inputs["Emission Color"].default_value = (*emission, 1)
        b.inputs["Emission Strength"].default_value = emission_strength
    return m


def add_noise_roughness(mat, base, amp, scale=40.0, detail=8.0):
    """Micro-surface variation: noise drives roughness (fingerprints/polish)."""
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = max(0.0, base - amp)
    mr.inputs["To Max"].default_value = base + amp
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
    nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    return mat


def add_bump(mat, strength=0.05, scale=200.0, detail=4.0):
    nt = mat.node_tree
    b = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = detail
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = strength
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nt.links.new(nz.outputs["Fac"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return mat


def mat_emission(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*color, 1)
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs[0])
    return m, em


def floor_material(name="Floor", color=(0.012, 0.012, 0.013), rough=0.18):
    """Polished dark studio floor with subtle smudge variation."""
    m = mat_principled(name, color, rough=rough, spec=0.6)
    add_noise_roughness(m, rough, 0.08, scale=6.0, detail=6.0)
    return m


# ---------------------------------------------------------------- objects
def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def mesh_obj(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return link(bpy.data.objects.new(name, me))


def lathe(name, profile, segments=128, smooth=True):
    """Revolve a list of (r, z) points around Z."""
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=math.tau, steps=segments, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    if smooth:
        for f in bm.faces:
            f.smooth = True
    return mesh_obj(name, bm)


def bevel_box(name, size, bevel=0.02, segs=4):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(scale=True)
    md = o.modifiers.new("bevel", "BEVEL")
    md.width = bevel
    md.segments = segs
    md.limit_method = "NONE"
    bpy.ops.object.shade_smooth()
    return o


def floor(size=60, mat=None, z=0.0):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z))
    o = bpy.context.active_object
    o.name = "Floor"
    if mat:
        o.data.materials.append(mat)
    return o


def backdrop(mat, radius=8.0, height=12.0, depth=12.0, width=40.0, front=8.0):
    """Infinity cove: floor that curves up into a back wall (seamless studio)."""
    pts = [(front, 0.0), (-depth + radius, 0.0)]
    for i in range(1, 25):
        a = i / 24 * math.pi / 2
        pts.append((-depth + radius - math.sin(a) * radius, radius - math.cos(a) * radius))
    pts.append((-depth, height))
    bm = bmesh.new()
    vs = [bm.verts.new((-width / 2, y, z)) for y, z in pts]
    es = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    ret = bmesh.ops.extrude_edge_only(bm, edges=es)
    for g in ret["geom"]:
        if isinstance(g, bmesh.types.BMVert):
            g.co.x = width / 2
    for f in bm.faces:
        f.smooth = True
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    o = mesh_obj("Backdrop", bm)
    o.data.materials.append(mat)
    sub = o.modifiers.new("sub", "SUBSURF")
    sub.levels = sub.render_levels = 1
    return o


def area_light(name, loc, rot, size, energy, color=(1, 1, 1), size_y=None, spread=180):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.shape = "RECTANGLE" if size_y else "SQUARE"
    ld.size = size
    if size_y:
        ld.size_y = size_y
    ld.spread = math.radians(spread)
    o = link(bpy.data.objects.new(name, ld))
    o.location = loc
    if isinstance(rot, tuple) and len(rot) == 3 and isinstance(rot[0], (int, float)):
        o.rotation_euler = Euler([math.radians(a) for a in rot])
    else:  # rot given as a target point: aim at it, strip long axis stays vertical
        aim(o, rot[1])
    o.visible_camera = False
    return o


def spot_light(name, loc, target, energy, color=(1, 1, 1), size_deg=30, blend=0.4, radius=0.1):
    ld = bpy.data.lights.new(name, "SPOT")
    ld.energy = energy
    ld.color = color
    ld.spot_size = math.radians(size_deg)
    ld.spot_blend = blend
    ld.shadow_soft_size = radius
    o = link(bpy.data.objects.new(name, ld))
    o.location = loc
    aim(o, target)
    o.visible_camera = False
    return o


def point_light(name, loc, energy, color=(1, 1, 1), radius=0.05):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    o = link(bpy.data.objects.new(name, ld))
    o.location = loc
    o.visible_camera = False
    o.visible_glossy = False
    o.visible_transmission = False
    return o


def aim(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def camera(loc, target, lens=50, fstop=2.8, focus=None, sensor=36):
    cd = bpy.data.cameras.new("Cam")
    cd.lens = lens
    cd.sensor_width = sensor
    cd.sensor_fit = "VERTICAL"
    cd.sensor_height = sensor
    o = link(bpy.data.objects.new("Cam", cd))
    o.location = loc
    aim(o, target)
    bpy.context.scene.camera = o
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
        cd.dof.aperture_blades = 7
        cd.dof.aperture_rotation = math.radians(12)
        cd.dof.focus_distance = focus if focus else (Vector(target) - Vector(loc)).length
    return o


# ---------------------------------------------------------------- animation helpers
def ease_io(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * t * (t * (6 * t - 15) + 10)  # smootherstep


def ease_out(t, p=3):
    t = min(max(t, 0.0), 1.0)
    return 1 - (1 - t) ** p


def ease_in(t, p=2):
    t = min(max(t, 0.0), 1.0)
    return t ** p


def lerp(a, b, t):
    return a + (b - a) * t


def key_every_frame(obj, f0, f1, fn):
    """fn(frame) -> dict(location=..., rotation_euler=..., scale=...)."""
    for f in range(f0, f1 + 1):
        vals = fn(f)
        for attr, v in vals.items():
            setattr(obj, attr, v)
            obj.keyframe_insert(attr, frame=f)
    if obj.animation_data and obj.animation_data.action:
        _linear(obj.animation_data.action)


def _linear(action):
    """Set LINEAR interpolation on every keyframe (works for layered actions too)."""
    curves = []
    if hasattr(action, "fcurves"):
        try:
            curves = list(action.fcurves)
        except Exception:
            curves = []
    if not curves and hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    curves.extend(cb.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"


def render(out_dir, f0, f1, samples=64, step=1):
    sc = bpy.context.scene
    sc.cycles.samples = samples
    os.makedirs(out_dir, exist_ok=True)
    for f in range(f0, f1 + 1, step):
        path = os.path.join(out_dir, f"f{f:04d}.png")
        if os.path.exists(path):
            continue
        sc.frame_set(f)
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        print("RENDERED", path, flush=True)
