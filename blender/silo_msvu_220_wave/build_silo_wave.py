"""SILO-WAVE: 64 mm corrugation and a 30 degree roof.

Pitch and roof angle are catalog figures. Wave height 12 mm is not.
Sheet thickness stays the 1-3 mm range and is not a tier measurement.
Run:
    blender --background --factory-startup --python "d:\\autocad project\\blender\\silo_msvu_220_wave\\build_silo_wave.py"
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

DIAMETER_M = 22.0
RADIUS_M = 11.0
TIER_H = 1.152
RING_COUNT = 13
WALL_TOP = 14.976
SPOUT_Z = 21.422
ROOF_DEG = 30.0
ROOF_RISE = RADIUS_M * math.tan(math.radians(ROOF_DEG))
ROOF_PEAK = WALL_TOP + ROOF_RISE
WAVE_PITCH = 0.064
WAVES_PER_RING = 18
WAVE_HEIGHT = 0.012
WAVE_STEPS = 8
CIRCLE_STEPS = 72
TOLERANCE_M = 0.001
FLANGE_WIDTH_M = 0.35
FLANGE_PROTRUSION_M = 0.12
FLANGE_THICK_M = 0.02
HEAD_D_M = 0.12
HEAD_H_M = 0.04
SHANK_D_M = 0.05
SHANK_H_M = 0.03
BOLT_COUNT = 52
ROOF_SECTORS = 8
ROOF_EDGE_STEPS = 16
SPOUT_MAJOR_R = 0.7
SPOUT_TUBE_R = 0.045
LABEL_TEXT = (
    "МСВУ 220.13.В12\n"
    "D = 22.000 м\n"
    "стіна 13 x 1.152 м = 14.976 м\n"
    "хвиля крок 64 мм з каталогу Лубнимаша, 18 на пояс\n"
    "висота хвилі 12 мм — не з каталогу\n"
    "дах 30° з каталогу\n"
    "патрубок 21.422 м, зазор над вершиною короткий\n"
    "товщина стіни 1–3 мм за ярусом, 2 мм лише всередині діапазону"
)
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\times.ttf",
)
OUT = Path(r"d:\autocad project\blender\silo_msvu_220_wave")


def clean(value):
    value = round(float(value), 6)
    if abs(value) < 5e-7:
        return 0.0
    return value


def link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def clear_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for collection in (
        bpy.data.meshes,
        bpy.data.curves,
        bpy.data.cameras,
        bpy.data.lights,
        bpy.data.materials,
    ):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def make_material(name, color, roughness, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.use_backface_culling = False
    bsdf = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    base = bsdf.inputs.get("Base Color")
    if base is None:
        base = bsdf.inputs[0]
    base.default_value = (color[0], color[1], color[2], 1.0)
    rough = bsdf.inputs.get("Roughness")
    if rough is not None:
        rough.default_value = roughness
    metal = bsdf.inputs.get("Metallic")
    if metal is not None:
        metal.default_value = metallic
    return mat


def finish_mesh(bm, mesh, smooth):
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    inward = [face for face in bm.faces if face.normal.dot(face.calc_center_median()) < 0.0]
    if inward:
        bmesh.ops.reverse_faces(bm, faces=inward)
        bm.normal_update()
    for face in bm.faces:
        face.smooth = smooth
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    for poly in mesh.polygons:
        poly.use_smooth = smooth


def wave_radius(phase):
    return RADIUS_M - WAVE_HEIGHT * 0.5 * (1.0 - math.cos(phase))


def add_box(bm, x0, x1, y0, y1, z0, z1):
    verts = {}
    for ix, x_value in enumerate((x0, x1)):
        for iy, y_value in enumerate((y0, y1)):
            for iz, z_value in enumerate((z0, z1)):
                verts[(ix, iy, iz)] = bm.verts.new((x_value, y_value, z_value))

    def quad(*keys):
        bm.faces.new(tuple(verts[key] for key in keys))

    quad((0, 0, 0), (0, 1, 0), (0, 1, 1), (0, 0, 1))
    quad((1, 0, 0), (1, 0, 1), (1, 1, 1), (1, 1, 0))
    quad((0, 0, 0), (0, 0, 1), (1, 0, 1), (1, 0, 0))
    quad((0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1))
    quad((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0))
    quad((0, 0, 1), (0, 1, 1), (1, 1, 1), (1, 0, 1))


def make_ring(index, z0, z1, material):
    name = f"SILO_RING_{index:02d}"
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    rows_n = WAVES_PER_RING * WAVE_STEPS
    grid = []
    for row_index in range(rows_n + 1):
        along = row_index / rows_n
        z_value = z0 + (z1 - z0) * along
        phase = 2.0 * math.pi * WAVES_PER_RING * along
        radius = wave_radius(phase)
        row = []
        for step in range(CIRCLE_STEPS):
            angle = 2.0 * math.pi * step / CIRCLE_STEPS
            row.append(
                bm.verts.new((radius * math.cos(angle), radius * math.sin(angle), z_value))
            )
        grid.append(row)
    for row_index in range(rows_n):
        nxt = row_index + 1
        for step in range(CIRCLE_STEPS):
            step_next = (step + 1) % CIRCLE_STEPS
            bm.faces.new(
                (
                    grid[row_index][step],
                    grid[nxt][step],
                    grid[nxt][step_next],
                    grid[row_index][step_next],
                )
            )
    finish_mesh(bm, mesh, smooth=True)
    mesh.materials.append(material)
    return obj


def make_flange(material):
    mesh = bpy.data.meshes.new("SILO_FLANGE_MESH")
    obj = link(bpy.data.objects.new("SILO_FLANGE", mesh))
    bm = bmesh.new()
    outer = RADIUS_M + FLANGE_PROTRUSION_M
    plate_inner = outer - FLANGE_THICK_M
    half = FLANGE_WIDTH_M * 0.5
    add_box(bm, RADIUS_M, plate_inner - 0.001, -0.045, 0.045, 0.0, WALL_TOP)
    add_box(bm, plate_inner, outer, -half, half, 0.0, WALL_TOP)
    finish_mesh(bm, mesh, smooth=False)
    mesh.materials.append(material)
    return obj


def make_cylinder_object(name, origin, direction, length, radius, material):
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    direction = direction.normalized()
    side = direction.cross(Vector((0.0, 0.0, 1.0)))
    if side.length < 1.0e-6:
        side = direction.cross(Vector((0.0, 1.0, 0.0)))
    side.normalize()
    binormal = direction.cross(side).normalized()
    rings = []
    for distance in (0.0, length):
        center = origin + direction * distance
        ring = []
        for step in range(16):
            angle = 2.0 * math.pi * step / 16
            offset = side * (math.cos(angle) * radius) + binormal * (math.sin(angle) * radius)
            ring.append(bm.verts.new(center + offset))
        rings.append(ring)
    for step in range(16):
        nxt = (step + 1) % 16
        bm.faces.new((rings[0][step], rings[1][step], rings[1][nxt], rings[0][nxt]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[1])
    finish_mesh(bm, mesh, smooth=True)
    mesh.materials.append(material)
    return obj


def make_disk(name, z_value, material):
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    verts = []
    for step in range(64):
        angle = 2.0 * math.pi * step / 64
        verts.append(
            bm.verts.new((RADIUS_M * math.cos(angle), RADIUS_M * math.sin(angle), z_value))
        )
    bm.faces.new(verts)
    finish_mesh(bm, mesh, smooth=False)
    mesh.materials.append(material)
    return obj


def sector_angles(index):
    mid = -math.pi / 2.0 + (index - 1) * (2.0 * math.pi / ROOF_SECTORS)
    half = math.pi / ROOF_SECTORS
    gap = 0.5 * 0.04 / RADIUS_M
    return mid - half + gap, mid + half - gap


def make_roof_sector(index, material):
    angle_0, angle_1 = sector_angles(index)
    name = f"SILO_ROOF_{index:02d}"
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    outer = []
    for step in range(ROOF_EDGE_STEPS + 1):
        angle = angle_0 + (angle_1 - angle_0) * step / ROOF_EDGE_STEPS
        outer.append(
            bm.verts.new((RADIUS_M * math.cos(angle), RADIUS_M * math.sin(angle), WALL_TOP))
        )
    apex = bm.verts.new((0.0, 0.0, ROOF_PEAK))
    for step in range(ROOF_EDGE_STEPS):
        bm.faces.new((outer[step], outer[step + 1], apex))
    finish_mesh(bm, mesh, smooth=False)
    mesh.materials.append(material)
    return obj


def make_spout_mark(material):
    mesh = bpy.data.meshes.new("SILO_SPOUT_MARK_MESH")
    obj = link(bpy.data.objects.new("SILO_SPOUT_MARK", mesh))
    bm = bmesh.new()
    major = 32
    minor = 8
    rings = []
    for step in range(major):
        angle = 2.0 * math.pi * step / major
        ring = []
        for tube in range(minor):
            beta = 2.0 * math.pi * tube / minor
            radius = SPOUT_MAJOR_R + SPOUT_TUBE_R * math.cos(beta)
            z_value = SPOUT_Z + SPOUT_TUBE_R * math.sin(beta)
            ring.append(
                bm.verts.new((radius * math.cos(angle), radius * math.sin(angle), z_value))
            )
        rings.append(ring)
    for step in range(major):
        nxt = (step + 1) % major
        for tube in range(minor):
            tube_next = (tube + 1) % minor
            bm.faces.new(
                (
                    rings[step][tube],
                    rings[nxt][tube],
                    rings[nxt][tube_next],
                    rings[step][tube_next],
                )
            )
    for face in bm.faces:
        face.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    mesh.materials.append(material)
    return obj


def make_ground(material):
    mesh = bpy.data.meshes.new("GROUND_MESH")
    obj = link(bpy.data.objects.new("GROUND", mesh))
    bm = bmesh.new()
    add_box(bm, -40.0, 40.0, -40.0, 40.0, -0.04, -0.02)
    finish_mesh(bm, mesh, smooth=False)
    mesh.materials.append(material)
    return obj


def load_font():
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            return bpy.data.fonts.load(path)
    raise RuntimeError("no Cyrillic font found")


def make_label(material):
    curve = bpy.data.curves.new("SILO_LABEL_CURVE", type="FONT")
    curve.body = LABEL_TEXT
    curve.size = 0.2
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.space_line = 1.12
    curve.extrude = 0.004
    curve.resolution_u = 6
    curve.font = load_font()
    obj = link(bpy.data.objects.new("SILO_LABEL", curve))
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    obj.data.materials.append(material)
    return obj


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_camera(name, location, target, lens):
    data = bpy.data.cameras.new(name + "_DATA")
    obj = link(bpy.data.objects.new(name, data))
    obj.location = Vector(location)
    look_at(obj, target)
    data.clip_start = 0.02
    data.clip_end = 200.0
    data.type = "PERSP"
    data.lens = lens
    return obj


def make_sun(name, location, target, energy):
    data = bpy.data.lights.new(name + "_DATA", type="SUN")
    data.energy = energy
    obj = link(bpy.data.objects.new(name, data))
    obj.location = Vector(location)
    look_at(obj, target)
    return obj


def make_point(name, location, energy):
    data = bpy.data.lights.new(name + "_DATA", type="POINT")
    data.energy = energy
    data.color = (1.0, 0.96, 0.9)
    data.shadow_soft_size = 0.3
    obj = link(bpy.data.objects.new(name, data))
    obj.location = Vector(location)
    return obj


def setup_world(scene):
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("SILO_WORLD")
        scene.world = world
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs[0].default_value = (0.55, 0.62, 0.68, 1.0)
    background.inputs[1].default_value = 1.0


def place_label(label, camera, scene):
    bpy.context.view_layer.update()
    rotation = camera.matrix_world.to_3x3()
    right = Vector(rotation.col[0])
    up = Vector(rotation.col[1])
    forward = -Vector(rotation.col[2])
    label.rotation_euler = camera.rotation_euler.copy()
    label.location = camera.location + forward * 8.6 + right * (-3.55) + up * 0.55
    bpy.context.view_layer.update()
    inverse = camera.matrix_world.inverted()
    tan_h = (camera.data.sensor_width * 0.5) / camera.data.lens
    aspect = scene.render.resolution_x / scene.render.resolution_y
    tan_v = tan_h / aspect
    xs = []
    ys = []
    for corner in label.bound_box:
        local = inverse @ (label.matrix_world @ Vector(corner))
        depth = -local.z
        if depth < 0.05:
            continue
        xs.append((local.x / depth) / tan_h)
        ys.append((local.y / depth) / tan_v)
    print("LABEL_NDC " + json.dumps([round(min(xs), 3), round(max(xs), 3), round(min(ys), 3), round(max(ys), 3)]))


def world_coords(obj):
    matrix = obj.matrix_world
    return [matrix @ vertex.co for vertex in obj.data.vertices]


def near(value, target):
    return abs(float(value) - float(target)) <= TOLERANCE_M


def render_still(scene, path, camera, hidden=()):
    scene.camera = camera
    scene.render.filepath = str(path)
    previous = []
    for obj in hidden:
        previous.append((obj, obj.hide_render))
        obj.hide_render = True
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    for obj, state in previous:
        obj.hide_render = state


def troughs(coords):
    samples = {}
    for coord in coords:
        if abs(coord.y) > 1.0e-4 or coord.x <= 0.0:
            continue
        key = round(coord.z, 5)
        samples[key] = coord.x
    ordered = sorted(samples)
    found = []
    for index in range(1, len(ordered) - 1):
        radius = samples[ordered[index]]
        if radius < samples[ordered[index - 1]] - 1.0e-6 and radius <= samples[ordered[index + 1]] + 1.0e-6:
            found.append(ordered[index])
    return found


def write_report(failed=False):
    text = (
        "blender/silo_msvu_220_wave/measure.json\n"
        "\n"
        "Стіна — 13 поясів по 1.152 м, верх 14.976 м. "
        "На кожному поясі 18 хвиль кроком 64 мм з каталогу Лубнимаша. "
        "Висота хвилі 12 мм не з каталогу. "
        "Дах — конус 30° від верху стіни, вершина біля 21.33 м. "
        "Мітка патрубка на 21.422 м, зазор над вершиною короткий. "
        "Товщина пояса не виміряна: у написі діапазон 1–3 мм. "
        "Хвиля є. blender/silo_msvu_220_tiers/ не перезаписано.\n"
    )
    if failed:
        text += "SILO_FAIL.\n"
    else:
        text += "SILO_PASS.\n"
    (OUT / "build_report.md").write_text(text, encoding="utf-8")


def write_measure(measure):
    (OUT / "measure.json").write_text(json.dumps(measure, indent=2) + "\n", encoding="utf-8")


def main():
    if OUT.name != "silo_msvu_220_wave":
        raise RuntimeError("refusing to write outside silo_msvu_220_wave")
    if abs(TIER_H / WAVE_PITCH - WAVES_PER_RING) > 1.0e-9:
        raise RuntimeError("1.152 / 0.064 is not 18")
    if abs(RING_COUNT * TIER_H - WALL_TOP) > 1.0e-9:
        raise RuntimeError("13 x 1.152 is not 14.976")
    OUT.mkdir(parents=True, exist_ok=True)
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    wall_a = make_material("WallA", (0.78, 0.80, 0.82), 0.42, metallic=0.55)
    wall_b = make_material("WallB", (0.62, 0.66, 0.70), 0.46, metallic=0.5)
    flange_mat = make_material("FlangeSteel", (0.18, 0.20, 0.24), 0.38, metallic=0.4)
    head_mat = make_material("BoltHead", (0.05, 0.05, 0.06), 0.28, metallic=0.85)
    shank_mat = make_material("BoltShank", (0.82, 0.78, 0.68), 0.22, metallic=0.9)
    roof_a = make_material("RoofA", (0.55, 0.30, 0.16), 0.48, metallic=0.25)
    roof_b = make_material("RoofB", (0.28, 0.15, 0.09), 0.52, metallic=0.2)
    spout_mat = make_material("SpoutMark", (0.85, 0.55, 0.18), 0.35, metallic=0.2)
    rings = []
    for index in range(RING_COUNT):
        z0 = index * TIER_H
        z1 = WALL_TOP if index == RING_COUNT - 1 else (index + 1) * TIER_H
        rings.append(make_ring(index + 1, z0, z1, wall_a if index % 2 == 0 else wall_b))
    flange = make_flange(flange_mat)

    outer_x = RADIUS_M + FLANGE_PROTRUSION_M
    heads = []
    bodies = []
    bolt_number = 1
    for index in range(RING_COUNT):
        z0 = index * TIER_H
        z1 = WALL_TOP if index == RING_COUNT - 1 else (index + 1) * TIER_H
        body_low = z0 + 0.18
        body_high = z1 - 0.18
        span = body_high - body_low
        for y_value, tilt in ((-0.11, -0.55), (0.11, 0.55)):
            direction = Vector((math.cos(tilt), math.sin(tilt), 0.0))
            for fraction in (0.32, 0.68):
                origin = Vector((outer_x, y_value, body_low + fraction * span))
                bodies.append(
                    make_cylinder_object(
                        f"SILO_BOLT_{bolt_number:02d}_BODY",
                        origin,
                        direction,
                        SHANK_H_M,
                        SHANK_D_M * 0.5,
                        shank_mat,
                    )
                )
                heads.append(
                    make_cylinder_object(
                        f"SILO_BOLT_{bolt_number:02d}",
                        origin + direction * SHANK_H_M,
                        direction,
                        HEAD_H_M,
                        HEAD_D_M * 0.5,
                        head_mat,
                    )
                )
                bolt_number += 1

    floor = make_disk("SILO_FLOOR", 0.0, make_material("FloorSand", (0.78, 0.66, 0.42), 0.75))
    sectors = []
    for index in range(1, ROOF_SECTORS + 1):
        sectors.append(make_roof_sector(index, roof_a if index % 2 else roof_b))
    spout = make_spout_mark(spout_mat)
    make_ground(make_material("GroundConcrete", (0.72, 0.73, 0.70), 0.9))
    label = make_label(make_material("LabelBlack", (0.02, 0.02, 0.02), 0.4))

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    cam_ext = make_camera(
        "CAM_EXTERIOR",
        (16.4, -9.2, 15.5),
        (1.6, -0.6, 16.4),
        16.0,
    )
    cam_open = make_camera(
        "CAM_OPEN",
        (1.2, -10.5, 24.0),
        (0.0, -1.2, 12.0),
        20.0,
    )
    cam_inside = make_camera(
        "CAM_INSIDE",
        (0.0, -8.4, 1.45),
        (3.2, -6.2, 1.7),
        18.0,
    )
    place_label(label, cam_ext, scene)
    sun_key = make_sun("SUN_KEY", (8.0, -14.0, 22.0), (6.0, -2.0, 12.0), 4.2)
    sun_rake = make_sun("SUN_RAKE", (4.0, 10.0, 18.0), (8.0, 0.0, 10.0), 2.4)
    inside_key = make_point("LIGHT_INSIDE", (-1.5, -4.0, 3.2), 1800.0)
    inside_fill = make_point("LIGHT_FLOOR", (1.0, -5.5, 2.4), 900.0)
    setup_world(scene)

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError as exc:
        raise RuntimeError(f"BLENDER_EEVEE_NEXT unavailable: {exc}") from exc
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 48
    try:
        scene.eevee.use_raytracing = False
    except Exception:
        pass
    transforms = {
        item.identifier
        for item in scene.view_settings.bl_rna.properties["view_transform"].enum_items
    }
    if "Standard" in transforms:
        scene.view_settings.view_transform = "Standard"

    bpy.context.view_layer.update()
    problems = []
    wall_coords = []
    for ring in rings:
        wall_coords.extend(world_coords(ring))
    radii = [math.hypot(coord.x, coord.y) for coord in wall_coords]
    zs = [coord.z for coord in wall_coords]
    z_min = min(zs)
    z_max = max(zs)
    radius_max = max(radii)
    radius_min = min(radii)
    outer_diameter = radius_max * 2.0
    sample = troughs(world_coords(rings[0]))
    if len(sample) != WAVES_PER_RING:
        problems.append(f"troughs {len(sample)}")
    pitches = [sample[index] - sample[index - 1] for index in range(1, len(sample))]
    pitch = sum(pitches) / len(pitches) if pitches else 0.0
    if pitches and abs(pitch - WAVE_PITCH) > 0.001:
        problems.append(f"pitch {pitch:.5f}")
    if not near(z_min, 0.0) or not near(z_max, WALL_TOP):
        problems.append(f"wall {z_min:.4f}..{z_max:.4f}")
    if abs(radius_max - RADIUS_M) > 0.001:
        problems.append(f"crest radius {radius_max:.4f}")
    if abs((radius_max - radius_min) - WAVE_HEIGHT) > 0.001:
        problems.append(f"wave height {radius_max - radius_min:.4f}")
    if len(rings) != RING_COUNT or len(heads) != BOLT_COUNT:
        problems.append("counts")
    flange_top = max(coord.z for coord in world_coords(flange))
    if not near(flange_top, WALL_TOP) or flange_top > WALL_TOP + 0.01:
        problems.append(f"flange {flange_top:.4f}")

    roof_coords = []
    for sector in sectors:
        roof_coords.extend(world_coords(sector))
    roof_peak = max(coord.z for coord in roof_coords)
    roof_base = min(coord.z for coord in roof_coords)
    outer_roof = [coord for coord in roof_coords if math.hypot(coord.x, coord.y) > 10.0]
    outer_point = max(outer_roof, key=lambda coord: math.hypot(coord.x, coord.y))
    apex = max(roof_coords, key=lambda coord: coord.z)
    run = math.hypot(outer_point.x - apex.x, outer_point.y - apex.y)
    rise = apex.z - outer_point.z
    slope = math.degrees(math.atan2(rise, run))
    if roof_peak < WALL_TOP + 5.0:
        problems.append("roof still flat")
    if abs(roof_peak - roof_base) < 1.0:
        problems.append("roof disk")
    if abs(slope - ROOF_DEG) > 0.25:
        problems.append(f"slope {slope:.3f}")
    if not near(roof_base, WALL_TOP):
        problems.append(f"roof base {roof_base:.4f}")

    spout_coords = world_coords(spout)
    spout_z = sum(coord.z for coord in spout_coords) / len(spout_coords)
    if not near(spout_z, SPOUT_Z):
        problems.append(f"spout {spout_z:.4f}")
    gap = spout_z - roof_peak
    if gap < 0.02 or gap > 0.25:
        problems.append(f"peak gap {gap:.4f}")
    if cam_ext.location.z > 16.0:
        problems.append("camera high")
    if "не з каталогу" not in label.data.body or "1–3 мм" not in label.data.body:
        problems.append("label")
    if "64 мм" not in label.data.body or "30°" not in label.data.body:
        problems.append("label catalog")
    floor_z = [coord.z for coord in world_coords(floor)]
    if max(floor_z) - min(floor_z) > 0.001:
        problems.append("floor")

    measure = {
        "pass": not problems,
        "ring_count": RING_COUNT,
        "tier_height_m": TIER_H,
        "wall_z_min_m": clean(z_min),
        "wall_z_max_m": clean(z_max),
        "outer_diameter_m": clean(outer_diameter),
        "wave_pitch_m": clean(pitch) if pitches else None,
        "waves_per_ring": len(sample),
        "wave_height_m": clean(radius_max - radius_min),
        "wave_height_from_catalog": False,
        "roof_slope_deg": clean(slope),
        "roof_peak_z_m": clean(roof_peak),
        "spout_z_m": clean(spout_z),
        "peak_to_spout_m": clean(gap),
        "from_catalog": True,
        "wall_thickness_range_mm": "1-3",
        "wall_thickness_modeled_m": None,
    }
    print("SILO_MEASURE " + json.dumps(measure))
    print(
        "WAVE_FRAME "
        + json.dumps(
            [
                clean(radius_min),
                clean(radius_max),
                clean(pitch) if pitches else None,
                len(sample),
                clean(slope),
                clean(roof_peak),
                clean(gap),
            ]
        )
    )
    if problems:
        print("SILO_PROBLEMS " + " | ".join(problems))
        measure["pass"] = False
        write_measure(measure)
        blend = OUT / "silo_msvu_220_wave.blend"
        if blend.exists():
            blend.unlink()
        write_report(failed=True)
        print("SILO_FAIL")
        sys.exit(2)

    render_still(scene, OUT / "render_exterior.png", cam_ext, hidden=(inside_key, inside_fill))
    render_still(
        scene,
        OUT / "render_open.png",
        cam_open,
        hidden=(sectors[0], label),
    )
    render_still(
        scene,
        OUT / "render_inside.png",
        cam_inside,
        hidden=(label, sun_key, sun_rake, spout),
    )
    for obj in (sectors[0], label, inside_key, inside_fill, sun_key, sun_rake, spout):
        obj.hide_render = False
    scene.camera = cam_ext
    for name in ("render_exterior.png", "render_open.png", "render_inside.png"):
        size = (OUT / name).stat().st_size
        print(f"RENDER_BYTES {name} {size}")
        if size < 20000:
            problems.append(name)
    if problems:
        measure["pass"] = False
        write_measure(measure)
        write_report(failed=True)
        print("SILO_FAIL")
        sys.exit(2)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "silo_msvu_220_wave.blend"))
    backup = OUT / "silo_msvu_220_wave.blend1"
    if backup.exists():
        backup.unlink()
    write_measure(measure)
    write_report()
    print("SILO_PASS")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print("SILO_FAIL", repr(exc))
        sys.exit(2)
