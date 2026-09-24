"""Shared helpers for the world kit: fast meshes, PBR materials, sky, cameras.

Every kit module builds geometry in metres with real thickness.
"""

import math

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils
import numpy as np
from mathutils import Vector


# ---------------------------------------------------------------- meshes

def mesh_from_arrays(name, verts, faces, material=None, smooth=False, collection=None):
    """Build a mesh object from numpy arrays.

    faces: (n, k) int array, or a list of such arrays with different k (tris, quads, n-gons).
    """
    verts = np.asarray(verts, dtype=np.float32).reshape(-1, 3)
    blocks = faces if isinstance(faces, list) else [faces]
    blocks = [np.asarray(b, dtype=np.int32) for b in blocks if len(b)]
    loops = np.concatenate([b.ravel() for b in blocks])
    totals = np.concatenate([np.full(len(b), b.shape[1], dtype=np.int32) for b in blocks])
    starts = np.concatenate([[0], np.cumsum(totals)[:-1]]).astype(np.int32)
    mesh = bpy.data.meshes.new(name + "_MESH")
    mesh.vertices.add(len(verts))
    mesh.vertices.foreach_set("co", verts.ravel())
    mesh.loops.add(len(loops))
    mesh.loops.foreach_set("vertex_index", loops)
    mesh.polygons.add(len(totals))
    mesh.polygons.foreach_set("loop_start", starts)
    mesh.polygons.foreach_set("loop_total", totals)
    if smooth == "quads":
        flags = totals == 4
    else:
        flags = np.full(len(totals), bool(smooth))
    mesh.polygons.foreach_set("use_smooth", flags)
    mesh.update(calc_edges=True)
    if material is not None:
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def grid_faces(rows, cols, wrap_cols=False, offset=0):
    """Quad indices for a rows x cols vertex grid (row-major)."""
    c_max = cols if wrap_cols else cols - 1
    r = np.arange(rows - 1)[:, None]
    c = np.arange(c_max)[None, :]
    a = r * cols + c
    b = r * cols + (c + 1) % cols
    return (np.stack([a, b, b + cols, a + cols], axis=-1).reshape(-1, 4) + offset).astype(np.int32)


def merge_parts(parts):
    """parts: list of (verts, faces). faces may be an array or a list of arrays.

    Returns (verts, [face arrays grouped by width]).
    """
    verts, groups, base = [], {}, 0
    for v, f in parts:
        v = np.asarray(v, dtype=np.float64).reshape(-1, 3)
        for block in (f if isinstance(f, list) else [f]):
            block = np.asarray(block, dtype=np.int64)
            if len(block):
                groups.setdefault(block.shape[1], []).append(block + base)
        verts.append(v)
        base += len(v)
    return np.concatenate(verts), [np.concatenate(g) for g in groups.values()]


def box(p0, p1):
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    v = np.array([[x, y, z] for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])
    f = np.array([(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])
    return v, f


def cylinder(radius, z0, z1, steps=16, center=(0.0, 0.0), capped=True):
    a = np.linspace(0, 2 * math.pi, steps, endpoint=False)
    ring = np.stack([center[0] + radius * np.cos(a), center[1] + radius * np.sin(a)], axis=-1)
    v = np.concatenate([np.column_stack([ring, np.full(steps, z0)]),
                        np.column_stack([ring, np.full(steps, z1)])])
    faces = [grid_faces(2, steps, wrap_cols=True)]
    if capped:
        faces.append(np.arange(steps)[::-1][None, :])
        faces.append(np.arange(steps, 2 * steps)[None, :])
    return v, faces


def transform(verts, rot_z=0.0, offset=(0.0, 0.0, 0.0)):
    c, s = math.cos(rot_z), math.sin(rot_z)
    m = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return verts @ m.T + np.asarray(offset)


# ---------------------------------------------------------------- materials

def _node(nodes, kind, loc, **inputs):
    n = nodes.new(kind)
    n.location = loc
    for key, value in inputs.items():
        n.inputs[key].default_value = value
    return n


def _bsdf(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def _sheet_index(nodes, links, tex, sheets, tier_h):
    """Vector (sector, tier, 0) from object coords: which sheet a point lies on."""
    sep = _node(nodes, "ShaderNodeSeparateXYZ", (-1400, 700))
    links.new(tex.outputs["Object"], sep.inputs[0])
    atan = _node(nodes, "ShaderNodeMath", (-1250, 750))
    atan.operation = "ARCTAN2"
    links.new(sep.outputs["Y"], atan.inputs[0])
    links.new(sep.outputs["X"], atan.inputs[1])
    sector = _node(nodes, "ShaderNodeMath", (-1100, 750))
    sector.operation = "MULTIPLY"
    sector.inputs[1].default_value = sheets / (2 * math.pi)
    links.new(atan.outputs[0], sector.inputs[0])
    tier = _node(nodes, "ShaderNodeMath", (-1100, 650))
    tier.operation = "DIVIDE"
    tier.inputs[1].default_value = tier_h
    links.new(sep.outputs["Z"], tier.inputs[0])
    comb = _node(nodes, "ShaderNodeCombineXYZ", (-950, 700))
    for src, dst in ((sector, "X"), (tier, "Y")):
        fl = _node(nodes, "ShaderNodeMath", (-1000, 700))
        fl.operation = "FLOOR"
        links.new(src.outputs[0], fl.inputs[0])
        links.new(fl.outputs[0], comb.inputs[dst])
    return comb.outputs[0]


def mat_galvanized(name="GALV", age=0.35, spangle_scale=90.0, sheets=20, tier_h=1.152):
    """Hot-dip galvanized S350GD: zinc spangle, vertical rain streaks, dust near ground.

    Spangle and streaks are in object space, offset per object by Object Info random.
    """
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nodes, links = nt.nodes, nt.links
    bsdf = _bsdf(mat)
    bsdf.inputs["Metallic"].default_value = 0.92

    tex = _node(nodes, "ShaderNodeTexCoord", (-1400, 0))
    info = _node(nodes, "ShaderNodeObjectInfo", (-1400, -300))
    shift = _node(nodes, "ShaderNodeVectorMath", (-1200, 0))
    shift.operation = "ADD"
    links.new(tex.outputs["Object"], shift.inputs[0])
    rand = _node(nodes, "ShaderNodeMath", (-1200, -300))
    rand.operation = "MULTIPLY"
    rand.inputs[1].default_value = 100.0
    links.new(info.outputs["Random"], rand.inputs[0])
    links.new(rand.outputs[0], shift.inputs[1])

    # zinc spangle: large flat crystals with slightly different reflectance
    spangle = _node(nodes, "ShaderNodeTexVoronoi", (-900, 200), Scale=spangle_scale)
    links.new(shift.outputs[0], spangle.inputs["Vector"])
    sp_ramp = _node(nodes, "ShaderNodeMapRange", (-650, 200))
    sp_ramp.inputs["To Min"].default_value = 0.22
    sp_ramp.inputs["To Max"].default_value = 0.42
    links.new(spangle.outputs["Color"], sp_ramp.inputs["Value"])

    # rain streaks: noise stretched along Z
    stretch = _node(nodes, "ShaderNodeMapping", (-900, -100))
    stretch.inputs["Scale"].default_value = (6.0, 6.0, 0.25)
    links.new(shift.outputs[0], stretch.inputs["Vector"])
    streak = _node(nodes, "ShaderNodeTexNoise", (-700, -100), Scale=3.0, Detail=6.0, Roughness=0.6)
    links.new(stretch.outputs[0], streak.inputs["Vector"])
    st_ramp = _node(nodes, "ShaderNodeValToRGB", (-500, -100))
    st_ramp.color_ramp.elements[0].position = 0.45
    st_ramp.color_ramp.elements[1].position = 0.75
    links.new(streak.outputs["Fac"], st_ramp.inputs["Fac"])

    # ground dust: stronger in the first 1.5 m above the object's base
    sep = _node(nodes, "ShaderNodeSeparateXYZ", (-900, -400))
    links.new(tex.outputs["Object"], sep.inputs[0])
    dust = _node(nodes, "ShaderNodeMapRange", (-700, -400))
    dust.inputs["From Min"].default_value = 0.0
    dust.inputs["From Max"].default_value = 1.8
    dust.inputs["To Min"].default_value = 1.0
    dust.inputs["To Max"].default_value = 0.0
    links.new(sep.outputs["Z"], dust.inputs["Value"])

    dirt = _node(nodes, "ShaderNodeMath", (-300, -250))
    dirt.operation = "MAXIMUM"
    links.new(st_ramp.outputs["Color"], dirt.inputs[0])
    links.new(dust.outputs["Result"], dirt.inputs[1])
    dirt_amt = _node(nodes, "ShaderNodeMath", (-150, -250))
    dirt_amt.operation = "MULTIPLY"
    dirt_amt.inputs[1].default_value = age
    links.new(dirt.outputs[0], dirt_amt.inputs[0])

    # every sheet is a slightly different batch of zinc: index by angle sector and tier
    sheet_id = _sheet_index(nodes, links, tex, sheets, tier_h)
    sheet_noise = _node(nodes, "ShaderNodeTexWhiteNoise", (-900, 500))
    sheet_noise.noise_dimensions = "3D"
    links.new(sheet_id, sheet_noise.inputs["Vector"])
    sheet_shade = _node(nodes, "ShaderNodeMapRange", (-650, 500))
    sheet_shade.inputs["To Min"].default_value = 0.93
    sheet_shade.inputs["To Max"].default_value = 1.04
    links.new(sheet_noise.outputs["Value"], sheet_shade.inputs["Value"])

    clean_col = _node(nodes, "ShaderNodeMix", (-300, 350))
    clean_col.data_type = "RGBA"
    clean_col.blend_type = "MULTIPLY"
    clean_col.inputs["Factor"].default_value = 1.0
    clean_col.inputs[6].default_value = (0.56, 0.58, 0.60, 1.0)
    sheet_rgb = _node(nodes, "ShaderNodeCombineColor", (-450, 500))
    for k in ("Red", "Green", "Blue"):
        links.new(sheet_shade.outputs["Result"], sheet_rgb.inputs[k])
    links.new(sheet_rgb.outputs[0], clean_col.inputs[7])
    dirty_col = _node(nodes, "ShaderNodeRGB", (-300, 150))
    dirty_col.outputs[0].default_value = (0.26, 0.24, 0.21, 1.0)
    base = _node(nodes, "ShaderNodeMix", (0, 250))
    base.data_type = "RGBA"
    links.new(dirt_amt.outputs[0], base.inputs["Factor"])
    links.new(clean_col.outputs[2], base.inputs[6])
    links.new(dirty_col.outputs[0], base.inputs[7])
    links.new(base.outputs[2], bsdf.inputs["Base Color"])

    rough = _node(nodes, "ShaderNodeMath", (0, 0))
    rough.operation = "ADD"
    links.new(sp_ramp.outputs["Result"], rough.inputs[0])
    links.new(dirt_amt.outputs[0], rough.inputs[1])
    links.new(rough.outputs[0], bsdf.inputs["Roughness"])
    return mat


def mat_painted(name, color, roughness=0.5, grime=0.25):
    """Painted steel or machinery: flat colour with a little noise in roughness."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _bsdf(mat)
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    tex = _node(nodes, "ShaderNodeTexCoord", (-900, 0))
    noise = _node(nodes, "ShaderNodeTexNoise", (-700, 0), Scale=4.0, Detail=8.0)
    links.new(tex.outputs["Object"], noise.inputs["Vector"])
    rng = _node(nodes, "ShaderNodeMapRange", (-450, 0))
    rng.inputs["To Min"].default_value = roughness - 0.1
    rng.inputs["To Max"].default_value = roughness + 0.15
    links.new(noise.outputs["Fac"], rng.inputs["Value"])
    links.new(rng.outputs["Result"], bsdf.inputs["Roughness"])
    darken = _node(nodes, "ShaderNodeMix", (-200, 250))
    darken.data_type = "RGBA"
    darken.inputs[6].default_value = (*color, 1.0)
    darken.inputs[7].default_value = (color[0] * 0.55, color[1] * 0.55, color[2] * 0.5, 1.0)
    fac = _node(nodes, "ShaderNodeMath", (-400, 250))
    fac.operation = "MULTIPLY"
    fac.inputs[1].default_value = grime
    links.new(noise.outputs["Fac"], fac.inputs[0])
    links.new(fac.outputs[0], darken.inputs["Factor"])
    links.new(darken.outputs[2], bsdf.inputs["Base Color"])
    return mat


def mat_concrete(name="CONCRETE", tint=(0.33, 0.32, 0.30)):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _bsdf(mat)
    tex = _node(nodes, "ShaderNodeTexCoord", (-1000, 0))
    fine = _node(nodes, "ShaderNodeTexNoise", (-800, 100), Scale=40.0, Detail=10.0, Roughness=0.7)
    blotch = _node(nodes, "ShaderNodeTexNoise", (-800, -150), Scale=1.5, Detail=4.0)
    links.new(tex.outputs["Object"], fine.inputs["Vector"])
    links.new(tex.outputs["Object"], blotch.inputs["Vector"])
    mix = _node(nodes, "ShaderNodeMix", (-450, 100))
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (*tint, 1.0)
    mix.inputs[7].default_value = (tint[0] * 0.7, tint[1] * 0.7, tint[2] * 0.68, 1.0)
    links.new(blotch.outputs["Fac"], mix.inputs["Factor"])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.88
    bump = _node(nodes, "ShaderNodeBump", (-300, -250), Strength=0.25, Distance=0.004)
    links.new(fine.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def mat_ground(name="GROUND"):
    """Compacted gravel with patches of dry grass, seen from 2-200 m."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = _bsdf(mat)
    tex = _node(nodes, "ShaderNodeTexCoord", (-1100, 0))
    stones = _node(nodes, "ShaderNodeTexVoronoi", (-850, 200), Scale=45.0)
    links.new(tex.outputs["Object"], stones.inputs["Vector"])
    patches = _node(nodes, "ShaderNodeTexNoise", (-850, -150), Scale=0.08, Detail=6.0, Roughness=0.65)
    links.new(tex.outputs["Object"], patches.inputs["Vector"])
    patch_ramp = _node(nodes, "ShaderNodeValToRGB", (-600, -150))
    patch_ramp.color_ramp.elements[0].position = 0.52
    patch_ramp.color_ramp.elements[1].position = 0.62
    links.new(patches.outputs["Fac"], patch_ramp.inputs["Fac"])
    gravel = _node(nodes, "ShaderNodeMix", (-450, 250))
    gravel.data_type = "RGBA"
    gravel.inputs[6].default_value = (0.20, 0.19, 0.17, 1.0)
    gravel.inputs[7].default_value = (0.12, 0.115, 0.105, 1.0)
    links.new(stones.outputs["Distance"], gravel.inputs["Factor"])
    grass = _node(nodes, "ShaderNodeMix", (-200, 150))
    grass.data_type = "RGBA"
    links.new(patch_ramp.outputs["Color"], grass.inputs["Factor"])
    links.new(gravel.outputs[2], grass.inputs[6])
    grass.inputs[7].default_value = (0.16, 0.15, 0.07, 1.0)
    links.new(grass.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.95
    bump = _node(nodes, "ShaderNodeBump", (-200, -250), Strength=0.6, Distance=0.02)
    links.new(stones.outputs["Distance"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def mat_rubber(name="RUBBER"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = _bsdf(mat)
    bsdf.inputs["Base Color"].default_value = (0.03, 0.03, 0.03, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    return mat


# ---------------------------------------------------------------- scene

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def setup_render(scene, samples=96, res=(1920, 1080)):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.use_adaptive_sampling = True
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = -0.6
    scene.unit_settings.system = "METRIC"


def setup_sky(scene, sun_elevation_deg=28.0, sun_rotation_deg=215.0, strength=0.35):
    """Physical Nishita sky plus a matching sun lamp for crisp shadows."""
    world = bpy.data.worlds.new("SKY")
    scene.world = world
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    bg = next(n for n in nodes if n.type == "BACKGROUND")
    sky = nodes.new("ShaderNodeTexSky")
    sky.sky_type = "NISHITA"
    sky.sun_elevation = math.radians(sun_elevation_deg)
    sky.sun_rotation = math.radians(sun_rotation_deg)
    sky.altitude = 150.0
    sky.air_density = 1.0
    sky.dust_density = 1.6
    sky.sun_disc = False
    links.new(sky.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength

    sun_data = bpy.data.lights.new("SUN", type="SUN")
    sun_data.energy = 3.2
    sun_data.angle = math.radians(0.53)
    sun_data.color = (1.0, 0.95, 0.88)
    sun = bpy.data.objects.new("SUN", sun_data)
    scene.collection.objects.link(sun)
    # Blender sky rotation 0 = sun along +Y? The sky node measures rotation from +X toward +Y.
    el = math.radians(sun_elevation_deg)
    az = math.radians(sun_rotation_deg)
    direction = Vector((math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)))
    sun.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    return sun


def camera(name, location, target, lens=35.0, collection=None):
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    data.clip_start = 0.05
    data.clip_end = 3000.0
    data.sensor_width = 36.0
    obj = bpy.data.objects.new(name, data)
    (collection or bpy.context.scene.collection).objects.link(obj)
    obj.location = Vector(location)
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()
    return obj


def render(scene, cam, path):
    scene.camera = cam
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


# ---------------------------------------------------------------- labels

LABEL_OFFSETS = [(0.0, -0.9, 0.55), (0.0, -0.9, -0.45), (-0.8, -0.7, 0.3), (0.8, -0.7, 0.45),
                 (-0.8, -0.7, -0.35), (0.8, -0.7, -0.4), (0.0, -1.1, 0.95), (0.0, -1.1, -0.9)]


def _label_materials():
    text = bpy.data.materials.get("LABEL_TEXT")
    if text is None:
        text = bpy.data.materials.new("LABEL_TEXT")
        text.use_nodes = True
        nodes, links = text.node_tree.nodes, text.node_tree.links
        emit = nodes.new("ShaderNodeEmission")
        emit.inputs["Color"].default_value = (1.0, 0.97, 0.9, 1.0)
        emit.inputs["Strength"].default_value = 2.0
        out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
        links.new(emit.outputs[0], out.inputs["Surface"])
        plate = bpy.data.materials.new("LABEL_PLATE")
        plate.use_nodes = True
        b = next(n for n in plate.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (0.01, 0.012, 0.015, 1.0)
        b.inputs["Roughness"].default_value = 0.6
        lead = bpy.data.materials.new("LABEL_LEADER")
        lead.use_nodes = True
        b = next(n for n in lead.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (0.95, 0.75, 0.1, 1.0)
        b.inputs["Emission Color"].default_value = (0.95, 0.75, 0.1, 1.0)
        b.inputs["Emission Strength"].default_value = 1.0
    return bpy.data.materials["LABEL_TEXT"], bpy.data.materials["LABEL_PLATE"], bpy.data.materials["LABEL_LEADER"]


def labels(items, tag, collection=None, size=0.06):
    """Annotation labels: (text, anchor xyz) -> billboard text on a dark plate + leader line.

    Labels live in their own collection LABELS_<tag> so they can be switched off.
    Location of the owning objects is applied by the caller through `parent`.
    """
    mat_text, mat_plate, mat_lead = _label_materials()
    col = bpy.data.collections.new(f"LABELS_{tag}")
    (collection or bpy.context.scene.collection).children.link(col)
    root = bpy.data.objects.new(f"LABELS_{tag}_ROOT", None)
    col.objects.link(root)
    out = [root]
    for i, (text, anchor) in enumerate(items):
        anchor = np.asarray(anchor, float)
        pos = anchor + np.asarray(LABEL_OFFSETS[i % len(LABEL_OFFSETS)])
        pivot = bpy.data.objects.new(f"LBL_{tag}_{i:02d}", None)
        pivot.empty_display_size = 0.05
        pivot.location = Vector(pos)
        col.objects.link(pivot)
        pivot.parent = root
        pivot["anchor"] = [float(x) for x in anchor]
        pivot["plate_w"] = size * 0.56 * len(text) + 0.08
        curve = bpy.data.curves.new(f"LBL_{tag}_{i:02d}_TXT", type="FONT")
        curve.body = text
        curve.size = size
        curve.align_x = "CENTER"
        curve.align_y = "CENTER"
        curve.extrude = 0.001
        txt = bpy.data.objects.new(f"LBL_{tag}_{i:02d}_TXT", curve)
        txt.data.materials.append(mat_text)
        col.objects.link(txt)
        txt.parent = pivot
        txt.location = (0.0, 0.0, 0.004)
        w = size * 0.56 * len(text) + 0.08
        h = size * 1.6
        v = np.array([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)])
        plate = mesh_from_arrays(f"LBL_{tag}_{i:02d}_PLATE", v, np.array([(0, 1, 2, 3)]), mat_plate, collection=col)
        plate.parent = pivot
        a = anchor
        b = pos - np.array([0, 0, h / 2]) if pos[2] > a[2] else pos + np.array([0, 0, h / 2])
        d = b - a
        length = float(np.linalg.norm(d))
        lead = bpy.data.meshes.new(f"LBL_{tag}_{i:02d}_LEAD_MESH")
        lead_obj = bpy.data.objects.new(f"LBL_{tag}_{i:02d}_LEAD", lead)
        col.objects.link(lead_obj)
        steps = 6
        ang = np.linspace(0, 2 * math.pi, steps, endpoint=False)
        dn = d / length
        side = np.cross(dn, [0, 0, 1.0]) if abs(dn[2]) < 0.99 else np.array([1.0, 0, 0])
        side /= np.linalg.norm(side)
        up = np.cross(side, dn)
        ring = 0.004 * (np.cos(ang)[:, None] * side + np.sin(ang)[:, None] * up)
        verts = np.concatenate([a + ring, b + ring, [a]])
        faces = [tuple(int(x) for x in q) for q in grid_faces(2, steps, wrap_cols=True)]
        lead.from_pydata([tuple(p) for p in verts], [], faces)
        lead.materials.append(mat_lead)
        lead_obj.parent = root
        # anchor dot
        dot = bpy.data.meshes.new(f"LBL_{tag}_{i:02d}_DOT_MESH")
        bm_verts, bm_faces = cylinder(0.018, -0.01, 0.01, steps=12)
        dot_obj = mesh_from_arrays(f"LBL_{tag}_{i:02d}_DOT", bm_verts + a, bm_faces, mat_lead, collection=col)
        bpy.data.meshes.remove(dot)
        dot_obj.parent = root
        pivot["parts"] = [txt.name, plate.name, lead_obj.name, dot_obj.name]
        out += [pivot, txt, plate, lead_obj, dot_obj]
    return out


def face_labels(label_objs, cam, max_dist=7.0, lift=0.38):
    """Place labels for this camera: beside the anchor on screen, facing the camera.

    Labels whose anchor is out of frame, behind the camera or farther than max_dist are hidden.
    Leaders are rebuilt from the anchor to the new label position.
    """
    from bpy_extras.object_utils import world_to_camera_view

    scene = bpy.context.scene
    cam_m = cam.matrix_world
    right = cam_m.to_3x3() @ Vector((1, 0, 0))
    up = cam_m.to_3x3() @ Vector((0, 1, 0))
    placed = []
    pivots = [o for o in label_objs if o.type == "EMPTY" and "anchor" in o.keys()]
    for o in pivots:
        root = o.parent
        anchor = root.matrix_world @ Vector(o["anchor"])
        view = world_to_camera_view(scene, cam, anchor)
        dist = (anchor - cam_m.translation).length
        visible = 0.03 < view.x < 0.97 and 0.03 < view.y < 0.97 and view.z > 0 and dist < max_dist
        parts = [bpy.data.objects[n] for n in o["parts"]]
        for p in parts:
            p.hide_render = not visible
            p.hide_viewport = not visible
        if not visible:
            continue
        scale = max(0.5, dist / 4.0)
        side = -1.0 if view.x < 0.5 else 1.0
        half_w = o["plate_w"] / 2 * scale
        pos = anchor + up * lift * scale + right * side * (0.12 * scale + half_w)
        for _ in range(12):                           # keep the whole plate inside the frame
            left = world_to_camera_view(scene, cam, pos - right * half_w).x
            rgt = world_to_camera_view(scene, cam, pos + right * half_w).x
            if left < 0.02:
                pos += right * half_w * 0.25
            elif rgt > 0.98:
                pos -= right * half_w * 0.25
            else:
                break
        half_h = 0.06 * 1.6 / 2 * scale

        def rect(p):
            a = world_to_camera_view(scene, cam, p - right * half_w - up * half_h)
            b = world_to_camera_view(scene, cam, p + right * half_w + up * half_h)
            return min(a.x, b.x), max(a.x, b.x), min(a.y, b.y), max(a.y, b.y)

        for _ in range(20):                           # step up on screen until it clears placed labels
            r = rect(pos)
            hit = any(r[0] < q[1] and q[0] < r[1] and r[2] < q[3] + 0.006 and q[2] - 0.006 < r[3] for q in placed)
            if not hit:
                break
            pos += up * half_h * 2.4
        placed.append(rect(pos))
        o.location = root.matrix_world.inverted() @ pos
        o.scale = (scale, scale, scale)
        o.rotation_euler = (cam_m.translation - pos).to_track_quat("Z", "Y").to_euler()
        lead = parts[2]
        a = root.matrix_world.inverted() @ anchor
        b = root.matrix_world.inverted() @ pos
        d = b - a
        if d.length < 1e-6:
            continue
        dn = d.normalized()
        side_v = dn.cross(Vector((0, 0, 1))) if abs(dn.z) < 0.99 else Vector((1, 0, 0))
        side_v.normalize()
        up_v = side_v.cross(dn)
        verts = []
        for end in (a, b):
            for k in range(6):
                ang = 2 * math.pi * k / 6
                verts.append(end + 0.004 * (math.cos(ang) * side_v + math.sin(ang) * up_v))
        for i, vtx in enumerate(lead.data.vertices[:12]):
            vtx.co = verts[i]
        lead.data.update()


def render_with_labels(scene, cam, path, label_objs):
    """Render the scene without labels, then only the labels on a transparent film,
    and lay the labels over the frame so geometry never hides them."""
    import os

    from PIL import Image

    path = str(path)
    tmp_main, tmp_lbl = path + ".main.png", path + ".labels.png"
    label_set = {o.name for o in label_objs}
    label_parts = [o for o in label_objs if o.type != "EMPTY"]
    shown = [o for o in label_parts if not o.hide_render]
    for o in label_parts:
        o.hide_render = True
    render(scene, cam, tmp_main)
    others = [o for o in scene.objects if o.name not in label_set and o.type != "CAMERA" and not o.hide_render]
    for o in others:
        o.hide_render = True
    for o in shown:
        o.hide_render = False
    old = (scene.render.film_transparent, scene.cycles.samples, scene.render.image_settings.color_mode)
    scene.render.film_transparent = True
    scene.cycles.samples = 16
    scene.render.image_settings.color_mode = "RGBA"
    render(scene, cam, tmp_lbl)
    scene.render.film_transparent, scene.cycles.samples, scene.render.image_settings.color_mode = old
    for o in others:
        o.hide_render = False
    base = Image.open(tmp_main).convert("RGBA")
    top = Image.open(tmp_lbl).convert("RGBA")
    Image.alpha_composite(base, top).convert("RGB").save(path)
    os.remove(tmp_main)
    os.remove(tmp_lbl)
