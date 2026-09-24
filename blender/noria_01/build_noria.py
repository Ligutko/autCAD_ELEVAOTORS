"""NORIA-1: bucket elevator beside the accepted wave silo.

Catalog: 100 t/h, tube 33 m, 22 kW.
180 mm and 376 x 256 mm are the 2017 advertisement, not a passport.
Head, boot, bolts and ladder are display only.
Run:
    blender --background --factory-startup --python "d:\\autocad project\\blender\\noria_01\\build_noria.py"
"""

import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

AXIS_X = 18.0
AXIS_Y = 0.0
TUBE_TOP = 33.0
CLEAR_X = 0.376
CLEAR_Y = 0.256
SHEET_T = 0.012
COURSE_H = 1.0
DRUM_R = 0.12
DRUM_W = 0.16
BELT_X = 0.12
BUCKET_PITCH = 0.18
BUCKET_DEPTH = 0.055
BOLT_GAP = 0.22
HEAD_DZ = 0.20
BOOT_DZ = 0.18
SRC = Path(r"d:\autocad project\blender\silo_msvu_220_wave\silo_msvu_220_wave.blend")
OUT = Path(r"d:\autocad project\blender\noria_01")
LABEL_TEXT = (
    "Н-100 / У13-УН175\n"
    "100 т/год, труба 33 м, 22 кВт\n"
    "180 мм і 376×256 мм зі старого оголошення, не з паспорта\n"
    "голова, башмак, болти, драбина — показ, не з паспорта"
)


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
    bm.normal_update()
    for face in bm.faces:
        face.smooth = smooth
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()


def add_box(bm, x0, x1, y0, y1, z0, z1, skip=()):
    verts = {}
    for ix, x_value in enumerate((x0, x1)):
        for iy, y_value in enumerate((y0, y1)):
            for iz, z_value in enumerate((z0, z1)):
                verts[(ix, iy, iz)] = bm.verts.new((x_value, y_value, z_value))

    def quad(keys):
        bm.faces.new(tuple(verts[key] for key in keys))

    faces = {
        "nx": ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)),
        "px": ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
        "ny": ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
        "py": ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
        "nz": ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
        "pz": ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
    }
    for key, order in faces.items():
        if key not in skip:
            quad(order)


def new_mesh(name, builder, material, smooth=False):
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    builder(bm)
    finish_mesh(bm, mesh, smooth)
    mesh.materials.append(material)
    return obj


def append_silo():
    with bpy.data.libraries.load(str(SRC), link=False) as (data_from, data_to):
        data_to.objects = list(data_from.objects)
    for obj in data_to.objects:
        if obj is not None:
            link(obj)


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_camera(name, location, target, lens):
    data = bpy.data.cameras.new(name + "_DATA")
    obj = link(bpy.data.objects.new(name, data))
    obj.location = Vector(location)
    look_at(obj, target)
    data.clip_start = 0.02
    data.clip_end = 300.0
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
    data.shadow_soft_size = 0.15
    obj = link(bpy.data.objects.new(name, data))
    obj.location = Vector(location)
    return obj


def make_cylinder(name, origin, direction, length, radius, material):
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    direction = direction.normalized()
    side = direction.cross(Vector((0.0, 0.0, 1.0)))
    if side.length < 1.0e-6:
        side = direction.cross(Vector((1.0, 0.0, 0.0)))
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
    finish_mesh(bm, mesh, True)
    mesh.materials.append(material)
    return obj


def build_tube(sheet_mat, flange_mat):
    half_x = CLEAR_X * 0.5
    half_y = CLEAR_Y * 0.5
    x0 = AXIS_X - half_x
    x1 = AXIS_X + half_x
    y0 = AXIS_Y - half_y
    y1 = AXIS_Y + half_y
    sheets = []
    count = int(round(TUBE_TOP / COURSE_H))
    for index in range(count):
        z0 = index * COURSE_H
        z1 = TUBE_TOP if index == count - 1 else (index + 1) * COURSE_H

        def build(bm, z0=z0, z1=z1):
            add_box(bm, x0 - SHEET_T, x0, y0, y1, z0, z1)
            add_box(bm, x1, x1 + SHEET_T, y0, y1, z0, z1)
            add_box(bm, x0 - SHEET_T, x1 + SHEET_T, y1, y1 + SHEET_T, z0, z1)

        sheets.append(new_mesh(f"NORIA_SHEET_{index + 1:02d}", build, sheet_mat))
    flange = new_mesh(
        "NORIA_FLANGE",
        lambda bm: add_box(bm, x0 - 0.02, x0, y0 - 0.05, y0, 0.0, TUBE_TOP),
        flange_mat,
    )
    return sheets, flange


def build_bolts(head_mat, shank_mat):
    heads = []
    bodies = []
    z_value = 0.28
    number = 1
    origin_y = AXIS_Y - CLEAR_Y * 0.5 - 0.02
    x_value = AXIS_X - CLEAR_X * 0.5 - 0.01
    while z_value < TUBE_TOP - 0.12:
        origin = Vector((x_value, origin_y, z_value))
        direction = Vector((0.0, -1.0, 0.0))
        bodies.append(
            make_cylinder(
                f"NORIA_BOLT_{number:03d}_BODY",
                origin,
                direction,
                0.012,
                0.009,
                shank_mat,
            )
        )
        heads.append(
            make_cylinder(
                f"NORIA_BOLT_{number:03d}",
                origin + direction * 0.012,
                direction,
                0.016,
                0.022,
                head_mat,
            )
        )
        number += 1
        z_value += BOLT_GAP
    return heads, bodies


def build_drums(mat):
    head_z = TUBE_TOP - HEAD_DZ
    boot_z = BOOT_DZ + DRUM_R
    head = make_cylinder(
        "NORIA_HEAD_DRUM",
        Vector((AXIS_X, -DRUM_W * 0.5, head_z)),
        Vector((0.0, 1.0, 0.0)),
        DRUM_W,
        DRUM_R,
        mat,
    )
    boot = make_cylinder(
        "NORIA_BOOT_DRUM",
        Vector((AXIS_X, -DRUM_W * 0.5, boot_z)),
        Vector((0.0, 1.0, 0.0)),
        DRUM_W,
        DRUM_R,
        mat,
    )
    return head, boot, head_z, boot_z


def build_housings(mat):
    half_x = CLEAR_X * 0.5 + 0.05
    half_y = CLEAR_Y * 0.5 + 0.04

    def head_box(bm):
        add_box(
            bm,
            AXIS_X - half_x,
            AXIS_X + half_x,
            AXIS_Y - half_y,
            AXIS_Y + half_y,
            TUBE_TOP - 0.85,
            TUBE_TOP + 0.28,
            skip=("ny",),
        )

    def boot_box(bm):
        add_box(
            bm,
            AXIS_X - half_x - 0.04,
            AXIS_X + half_x + 0.04,
            AXIS_Y - half_y - 0.02,
            AXIS_Y + half_y,
            0.0,
            0.78,
            skip=("ny",),
        )

    head = new_mesh("NORIA_HEAD", head_box, mat)
    boot = new_mesh("NORIA_BOOT", boot_box, mat)
    return head, boot


def build_belt(mat, head_z, boot_z):
    belts = []
    thickness = 0.008
    width = 0.14

    def vertical(bm, x_value):
        add_box(
            bm,
            x_value - thickness * 0.5,
            x_value + thickness * 0.5,
            -width * 0.5,
            width * 0.5,
            boot_z,
            head_z,
        )

    belts.append(new_mesh("NORIA_BELT_UP", lambda bm: vertical(bm, AXIS_X + BELT_X), mat))
    belts.append(new_mesh("NORIA_BELT_DOWN", lambda bm: vertical(bm, AXIS_X - BELT_X), mat))
    for name, z_value, sign in (
        ("NORIA_BELT_HEAD", head_z, 1.0),
        ("NORIA_BELT_BOOT", boot_z, -1.0),
    ):
        def arc(bm, z_value=z_value, sign=sign):
            steps = 8
            radius = BELT_X
            for step in range(steps):
                a0 = math.pi * step / steps
                a1 = math.pi * (step + 1) / steps
                if sign < 0.0:
                    a0 += math.pi
                    a1 += math.pi
                points = []
                for angle in (a0, a1):
                    px = AXIS_X + radius * math.cos(angle)
                    pz = z_value + radius * math.sin(angle)
                    points.append((px, pz))
                outer = []
                inner = []
                for px, pz in points:
                    ox = AXIS_X + (px - AXIS_X) * ((radius + thickness) / radius)
                    oz = z_value + (pz - z_value) * ((radius + thickness) / radius)
                    outer.append((ox, oz))
                    inner.append((px, pz))
                y0 = -width * 0.5
                y1 = width * 0.5
                verts = [
                    bm.verts.new((inner[0][0], y0, inner[0][1])),
                    bm.verts.new((inner[1][0], y0, inner[1][1])),
                    bm.verts.new((inner[1][0], y1, inner[1][1])),
                    bm.verts.new((inner[0][0], y1, inner[0][1])),
                    bm.verts.new((outer[0][0], y0, outer[0][1])),
                    bm.verts.new((outer[1][0], y0, outer[1][1])),
                    bm.verts.new((outer[1][0], y1, outer[1][1])),
                    bm.verts.new((outer[0][0], y1, outer[0][1])),
                ]
                bm.faces.new((verts[0], verts[1], verts[2], verts[3]))
                bm.faces.new((verts[4], verts[7], verts[6], verts[5]))
                bm.faces.new((verts[0], verts[4], verts[5], verts[1]))
                bm.faces.new((verts[3], verts[2], verts[6], verts[7]))

        belts.append(new_mesh(name, arc, mat))
    return belts


def build_buckets(mat):
    mesh = bpy.data.meshes.new("NORIA_BUCKET_MESH")
    bm = bmesh.new()
    add_box(bm, 0.0, BUCKET_DEPTH, -0.07, 0.07, -0.04, 0.04, skip=("px",))
    finish_mesh(bm, mesh, False)
    mesh.materials.append(mat)
    buckets = []
    z_value = 0.62
    top = TUBE_TOP - HEAD_DZ - DRUM_R - 0.08
    index = 0
    while z_value < top:
        up = link(bpy.data.objects.new(f"NORIA_BUCKET_UP_{index:03d}", mesh))
        up.location = (AXIS_X + BELT_X, 0.0, z_value)
        down = link(bpy.data.objects.new(f"NORIA_BUCKET_DOWN_{index:03d}", mesh))
        down.location = (AXIS_X - BELT_X, 0.0, z_value + BUCKET_PITCH * 0.5)
        down.rotation_euler = (0.0, 0.0, math.pi)
        buckets.append(up)
        buckets.append(down)
        index += 1
        z_value += BUCKET_PITCH
    return [item for item in buckets if item.name.startswith("NORIA_BUCKET_UP_")]


def build_ladder(mat):
    rails = []
    x_rail = AXIS_X + CLEAR_X * 0.5 + 0.28
    for offset, name in ((-0.16, "A"), (0.16, "B")):
        rails.append(
            new_mesh(
                f"NORIA_LADDER_RAIL_{name}",
                lambda bm, offset=offset: add_box(
                    bm,
                    x_rail - 0.015,
                    x_rail + 0.015,
                    offset - 0.012,
                    offset + 0.012,
                    0.15,
                    31.85,
                ),
                mat,
            )
        )
    rung_mesh = bpy.data.meshes.new("NORIA_RUNG_MESH")
    bm = bmesh.new()
    add_box(bm, x_rail - 0.012, x_rail + 0.012, -0.16, 0.16, -0.01, 0.01)
    finish_mesh(bm, rung_mesh, False)
    rung_mesh.materials.append(mat)
    z_value = 0.35
    while z_value < 31.7:
        rung = link(bpy.data.objects.new(f"NORIA_RUNG_{int(z_value * 100):04d}", rung_mesh))
        rung.location = (0.0, 0.0, z_value)
        z_value += 0.30
    deck_z = 31.55

    def deck(bm):
        add_box(bm, AXIS_X + 0.22, AXIS_X + 1.15, -0.42, 0.42, deck_z, deck_z + 0.03)
        add_box(bm, AXIS_X + 0.22, AXIS_X + 1.15, -0.42, -0.39, deck_z + 0.03, deck_z + 0.85)
        add_box(bm, AXIS_X + 0.22, AXIS_X + 1.15, 0.39, 0.42, deck_z + 0.03, deck_z + 0.85)
        add_box(bm, AXIS_X + 1.12, AXIS_X + 1.15, -0.42, 0.42, deck_z + 0.03, deck_z + 0.85)

    platform = new_mesh("NORIA_PLATFORM", deck, mat)
    return rails, platform


def make_label(mat):
    curve = bpy.data.curves.new("NORIA_LABEL_CURVE", type="FONT")
    curve.body = LABEL_TEXT
    curve.size = 0.42
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.space_line = 1.12
    curve.extrude = 0.01
    curve.font = bpy.data.fonts.load(r"C:\Windows\Fonts\arial.ttf")
    obj = link(bpy.data.objects.new("NORIA_LABEL", curve))
    obj.data.materials.append(mat)
    return obj


def place_label(label, camera):
    bpy.context.view_layer.update()
    rotation = camera.matrix_world.to_3x3()
    right = Vector(rotation.col[0])
    up = Vector(rotation.col[1])
    forward = -Vector(rotation.col[2])
    label.rotation_euler = camera.rotation_euler.copy()
    label.location = camera.location + forward * 22.0 + right * (-5.2) + up * (-4.6)
    bpy.context.view_layer.update()


def world_coords(obj):
    matrix = obj.matrix_world
    return [matrix @ vertex.co for vertex in obj.data.vertices]


def render_still(scene, path, camera, hidden=()):
    scene.camera = camera
    scene.render.filepath = str(path)
    previous = [(obj, obj.hide_render) for obj in hidden]
    for obj, _state in previous:
        obj.hide_render = True
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    for obj, state in previous:
        obj.hide_render = state


def write_measure(measure):
    (OUT / "measure.json").write_text(json.dumps(measure, indent=2) + "\n", encoding="utf-8")


def write_report(failed=False):
    text = (
        "blender/noria_01/measure.json\n"
        "\n"
        "Норія Н-100 стоїть на X = 18 м, башмак на Z = 0, верх труби на 33 м. "
        "100 т/год і 22 кВт з каталогу. "
        "180 мм і 376×256 мм зі старого оголошення, не з паспорта. "
        "Голова, башмак, болти і драбина — показ. "
        "Силос зі сцени хвилі не зрушено. Той blend не перезаписано.\n"
    )
    text += "NORIA_FAIL.\n" if failed else "NORIA_PASS.\n"
    (OUT / "build_report.md").write_text(text, encoding="utf-8")


def main():
    if OUT.name != "noria_01":
        raise RuntimeError("refusing to write outside noria_01")
    if not SRC.is_file():
        raise RuntimeError("wave blend missing")
    OUT.mkdir(parents=True, exist_ok=True)
    clear_scene()
    append_silo()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    bpy.context.view_layer.update()
    floor = bpy.data.objects.get("SILO_FLOOR")
    ring = bpy.data.objects.get("SILO_RING_01")
    if floor is None or ring is None:
        raise RuntimeError("appended silo is missing SILO_FLOOR or SILO_RING_01")
    floor_before = floor.matrix_world.translation.copy()
    ring_before = world_coords(ring)

    sheet_mat = make_material("NoriaSheet", (0.62, 0.66, 0.70), 0.45, 0.35)
    flange_mat = make_material("NoriaFlange", (0.22, 0.25, 0.30), 0.4, 0.3)
    head_mat = make_material("NoriaBolt", (0.08, 0.08, 0.09), 0.3, 0.8)
    shank_mat = make_material("NoriaShank", (0.75, 0.72, 0.62), 0.25, 0.85)
    drum_mat = make_material("NoriaDrum", (0.28, 0.30, 0.34), 0.35, 0.55)
    housing_mat = make_material("NoriaHousing", (0.50, 0.54, 0.58), 0.48, 0.25)
    belt_mat = make_material("NoriaBelt", (0.12, 0.12, 0.13), 0.7, 0.0)
    bucket_mat = make_material("NoriaBucket", (0.78, 0.62, 0.28), 0.5, 0.15)
    ladder_mat = make_material("NoriaLadder", (0.32, 0.36, 0.40), 0.45, 0.4)

    sheets, flange = build_tube(sheet_mat, flange_mat)
    heads, bodies = build_bolts(head_mat, shank_mat)
    head_drum, boot_drum, head_z, boot_z = build_drums(drum_mat)
    housing_head, housing_boot = build_housings(housing_mat)
    build_belt(belt_mat, head_z, boot_z)
    up_buckets = build_buckets(bucket_mat)
    build_ladder(ladder_mat)
    label = make_label(make_material("LabelBlack", (0.02, 0.02, 0.02), 0.4))

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    cam_both = make_camera("CAM_BOTH", (9.0, -54.0, 15.0), (8.0, 0.0, 14.0), 30.0)
    cam_cut = make_camera("CAM_CUTAWAY", (17.48, -0.95, 32.35), (17.92, 0.02, 32.62), 22.0)
    cam_boot = make_camera("CAM_BOOT", (18.35, -1.55, 0.72), (18.02, 0.0, 0.42), 26.0)
    place_label(label, cam_both)
    sun = make_sun("SUN_BOTH", (12.0, -30.0, 28.0), (8.0, 0.0, 12.0), 4.5)
    light_head = make_point("LIGHT_HEAD", (18.1, -0.7, 32.3), 40.0)
    light_boot = make_point("LIGHT_BOOT", (18.1, -0.75, 0.55), 25.0)
    world = scene.world or bpy.data.worlds.new("NORIA_WORLD")
    scene.world = world
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs[0].default_value = (0.68, 0.74, 0.80, 1.0)
    background.inputs[1].default_value = 1.0

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError as exc:
        raise RuntimeError(f"BLENDER_EEVEE_NEXT unavailable: {exc}") from exc
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 32
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
    tube_z = []
    for sheet in sheets:
        tube_z.extend(coord.z for coord in world_coords(sheet))
    tube_z.extend(coord.z for coord in world_coords(flange))
    z_min = min(tube_z)
    z_max = max(tube_z)
    tube_height = z_max - z_min
    if abs(tube_height - 33.0) > 0.01:
        problems.append(f"tube {tube_height:.4f}")
    if abs(z_min) > 0.01 or abs(z_max - 33.0) > 0.01:
        problems.append(f"tube ends {z_min:.4f}..{z_max:.4f}")

    bucket_z = sorted(obj.matrix_world.translation.z for obj in up_buckets)
    gaps = [bucket_z[index] - bucket_z[index - 1] for index in range(1, len(bucket_z))]
    pitch = sum(gaps) / len(gaps) if gaps else 0.0
    if not gaps or abs(pitch - BUCKET_PITCH) > 0.001:
        problems.append(f"pitch {pitch:.4f}")
    head_zs = [coord.z for coord in world_coords(head_drum)]
    boot_zs = [coord.z for coord in world_coords(boot_drum)]
    if max(head_zs) < 32.5 or min(boot_zs) > 0.5:
        problems.append("drums")
    floor_after = floor.matrix_world.translation
    ring_after = world_coords(ring)
    moved = (floor_after - floor_before).length > 0.001
    if ring_before and ring_after:
        before_x = max(coord.x for coord in ring_before)
        after_x = max(coord.x for coord in ring_after)
        if abs(before_x - after_x) > 0.001:
            moved = True
    if moved:
        problems.append("silo moved")
    if "не з паспорта" not in label.data.body or "180 мм" not in label.data.body:
        problems.append("label")
    if bpy.data.objects.get("NORIA_PLATFORM") is None:
        problems.append("platform")
    if cam_both.location.z > 20.0:
        problems.append("both camera high")

    measure = {
        "pass": not problems,
        "tube_height_m": clean(tube_height),
        "tube_z_min_m": clean(z_min),
        "tube_z_max_m": clean(z_max),
        "bucket_pitch_m": clean(pitch) if gaps else None,
        "bucket_pitch_from_passport": False,
        "shaft_clear_x_m": CLEAR_X,
        "shaft_clear_y_m": CLEAR_Y,
        "shaft_from_passport": False,
        "head_boot_from_passport": False,
        "silo_moved": moved,
        "axis_x_m": AXIS_X,
        "capacity_tph": 100,
        "power_kw": 22,
    }
    print("NORIA_MEASURE " + json.dumps(measure))
    if problems:
        print("NORIA_PROBLEMS " + " | ".join(problems))
        measure["pass"] = False
        write_measure(measure)
        write_report(failed=True)
        print("NORIA_FAIL")
        sys.exit(2)

    render_still(
        scene,
        OUT / "render_both.png",
        cam_both,
        hidden=(light_head, light_boot),
    )
    render_still(scene, OUT / "render_cutaway.png", cam_cut, hidden=(label, light_boot, sun))
    render_still(scene, OUT / "render_boot.png", cam_boot, hidden=(label, light_head, sun))
    for obj in (label, light_head, light_boot, sun):
        obj.hide_render = False
    scene.camera = cam_both
    for name in ("render_both.png", "render_cutaway.png", "render_boot.png"):
        size = (OUT / name).stat().st_size
        print(f"RENDER_BYTES {name} {size}")
        if size < 20000:
            problems.append(name)
    if problems:
        measure["pass"] = False
        write_measure(measure)
        write_report(failed=True)
        print("NORIA_FAIL")
        sys.exit(2)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "noria_01.blend"))
    backup = OUT / "noria_01.blend1"
    if backup.exists():
        backup.unlink()
    write_measure(measure)
    write_report()
    print("NORIA_PASS")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print("NORIA_FAIL", repr(exc))
        sys.exit(2)
