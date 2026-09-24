"""SILO-ROOF: accepted seam wall plus 8 flat roof sectors.

Roof gap, center hole and sector split are display only. No roof slope.
Run:
    blender --background --factory-startup --python "d:\\autocad project\\blender\\silo_msvu_220_roof\\build_silo_roof.py"
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
HEIGHT_M = 21.422
RING_COUNT = 14
SEGMENTS = 48
TOLERANCE_M = 0.0001
LAP_M = 0.08
HEM_H_M = 0.04
SKIRT_R = 11.04
HEM_R = 11.09
FLANGE_WIDTH_M = 0.35
FLANGE_PROTRUSION_M = 0.12
FLANGE_THICK_M = 0.02
HEAD_D_M = 0.12
HEAD_H_M = 0.04
SHANK_D_M = 0.05
SHANK_H_M = 0.03
BOLT_COUNT = 56
ROOF_SECTORS = 8
ROOF_GAP_M = 0.04
ROOF_HOLE_R = 0.4
ROOF_ARC_STEPS = 10
# Display cornice so the sector split reads from the eye-level camera.
# The cap stays flat at wall height. This is not a slope and not sheet thickness.
SKIRT_OUTER = 11.22
SKIRT_H = 0.9
LABEL_TEXT = (
    "МСВУ 220.13.В12\n"
    "D = 22.000 м\n"
    "H = 21.422 м\n"
    "днище плоске\n"
    "фланець і болти — показ, розмір не з паспорта\n"
    "напуск поясів — показ, не з паспорта\n"
    "дах — 8 плоских секторів, ухил не з паспорта\n"
    "немає факту: хвиля гофри, товщина листа"
)
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\times.ttf",
)
OUT = Path(r"d:\autocad project\blender\silo_msvu_220_roof")


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


def circle_row(bm, radius, z_value):
    row = []
    for step in range(SEGMENTS):
        angle = 2.0 * math.pi * step / SEGMENTS
        row.append(
            bm.verts.new((radius * math.cos(angle), radius * math.sin(angle), z_value))
        )
    return row


def connect_rows(bm, lower, upper):
    for step in range(SEGMENTS):
        nxt = (step + 1) % SEGMENTS
        bm.faces.new((lower[step], upper[step], upper[nxt], lower[nxt]))


def ring_bounds():
    height = (HEIGHT_M + (RING_COUNT - 1) * LAP_M) / RING_COUNT
    bounds = []
    z0 = 0.0
    for index in range(RING_COUNT):
        z1 = HEIGHT_M if index == RING_COUNT - 1 else z0 + height
        bounds.append((z0, z1))
        z0 = z1 - LAP_M
    return bounds


def make_ring(index, z0, z1, wall_mat, hem_mat, skirt_mat):
    name = f"SILO_RING_{index:02d}"
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    rows = []
    if index > 1:
        rows.append(circle_row(bm, SKIRT_R, z0))
        rows.append(circle_row(bm, SKIRT_R, z0 + LAP_M - HEM_H_M))
        rows.append(circle_row(bm, RADIUS_M, z0 + LAP_M - HEM_H_M))
    else:
        rows.append(circle_row(bm, RADIUS_M, z0))
    rows.append(circle_row(bm, RADIUS_M, z1 - HEM_H_M))
    rows.append(circle_row(bm, HEM_R, z1 - HEM_H_M))
    rows.append(circle_row(bm, HEM_R, z1))
    for lower, upper in zip(rows, rows[1:]):
        connect_rows(bm, lower, upper)
    finish_mesh(bm, mesh, smooth=True)
    mesh.materials.append(wall_mat)
    mesh.materials.append(hem_mat)
    mesh.materials.append(skirt_mat)
    for poly in mesh.polygons:
        center = Vector((0.0, 0.0, 0.0))
        for vertex_index in poly.vertices:
            center += mesh.vertices[vertex_index].co
        center /= len(poly.vertices)
        radius = math.hypot(center.x, center.y)
        if radius > RADIUS_M + 0.07:
            poly.material_index = 1
        elif radius > RADIUS_M + 0.02:
            poly.material_index = 2
        else:
            poly.material_index = 0
    return obj


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


def make_flange(material):
    mesh = bpy.data.meshes.new("SILO_FLANGE_MESH")
    obj = link(bpy.data.objects.new("SILO_FLANGE", mesh))
    bm = bmesh.new()
    outer = RADIUS_M + FLANGE_PROTRUSION_M
    plate_inner = outer - FLANGE_THICK_M
    half = FLANGE_WIDTH_M * 0.5
    add_box(bm, RADIUS_M, plate_inner - 0.001, -0.045, 0.045, 0.0, HEIGHT_M)
    add_box(bm, plate_inner, outer, -half, half, 0.0, HEIGHT_M)
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
        for step in range(24):
            angle = 2.0 * math.pi * step / 24
            offset = side * (math.cos(angle) * radius) + binormal * (math.sin(angle) * radius)
            ring.append(bm.verts.new(center + offset))
        rings.append(ring)
    for step in range(24):
        nxt = (step + 1) % 24
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


def sector_bounds(index):
    mid = -math.pi / 2.0 + (index - 1) * (2.0 * math.pi / ROOF_SECTORS)
    half = math.pi / ROOF_SECTORS
    return mid, mid - half, mid + half


def circle_offset_point(angle, inward, radius):
    gap_half = ROOF_GAP_M * 0.5
    direction_x = math.cos(angle)
    direction_y = math.sin(angle)
    normal_x = -direction_y * inward
    normal_y = direction_x * inward
    reach = math.sqrt(radius * radius - gap_half * gap_half)
    return (
        normal_x * gap_half + direction_x * reach,
        normal_y * gap_half + direction_y * reach,
    )


def wrap_span(start, end):
    while end < start:
        end += 2.0 * math.pi
    return start, end


def make_sector(index, material):
    _mid, angle_0, angle_1 = sector_bounds(index)
    outer_0 = circle_offset_point(angle_0, 1.0, RADIUS_M)
    outer_1 = circle_offset_point(angle_1, -1.0, RADIUS_M)
    inner_0 = circle_offset_point(angle_0, 1.0, ROOF_HOLE_R)
    inner_1 = circle_offset_point(angle_1, -1.0, ROOF_HOLE_R)
    outer_span = wrap_span(math.atan2(outer_0[1], outer_0[0]), math.atan2(outer_1[1], outer_1[0]))
    inner_span = wrap_span(math.atan2(inner_0[1], inner_0[0]), math.atan2(inner_1[1], inner_1[0]))

    def arc(radius, span):
        points = []
        start, end = span
        for step in range(ROOF_ARC_STEPS + 1):
            angle = start + (end - start) * step / ROOF_ARC_STEPS
            points.append((radius * math.cos(angle), radius * math.sin(angle), HEIGHT_M))
        return points

    outer_points = arc(RADIUS_M, outer_span)
    inner_points = arc(ROOF_HOLE_R, inner_span)
    outer_points[0] = (outer_0[0], outer_0[1], HEIGHT_M)
    outer_points[-1] = (outer_1[0], outer_1[1], HEIGHT_M)
    inner_points[0] = (inner_0[0], inner_0[1], HEIGHT_M)
    inner_points[-1] = (inner_1[0], inner_1[1], HEIGHT_M)
    eave_0 = circle_offset_point(angle_0, 1.0, SKIRT_OUTER)
    eave_1 = circle_offset_point(angle_1, -1.0, SKIRT_OUTER)
    eave_span = wrap_span(math.atan2(eave_0[1], eave_0[0]), math.atan2(eave_1[1], eave_1[0]))
    eave_points = arc(SKIRT_OUTER, eave_span)
    eave_points[0] = (eave_0[0], eave_0[1], HEIGHT_M)
    eave_points[-1] = (eave_1[0], eave_1[1], HEIGHT_M)
    drop = HEIGHT_M - SKIRT_H
    eave_low = [(point[0], point[1], drop) for point in eave_points]

    name = f"SILO_ROOF_{index:02d}"
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    outer_vs = [bm.verts.new(point) for point in outer_points]
    inner_vs = [bm.verts.new(point) for point in inner_points]
    eave_vs = [bm.verts.new(point) for point in eave_points]
    low_vs = [bm.verts.new(point) for point in eave_low]
    for step in range(ROOF_ARC_STEPS):
        bm.faces.new(
            (
                outer_vs[step],
                outer_vs[step + 1],
                inner_vs[step + 1],
                inner_vs[step],
            )
        )
        bm.faces.new(
            (
                outer_vs[step],
                eave_vs[step],
                eave_vs[step + 1],
                outer_vs[step + 1],
            )
        )
        bm.faces.new(
            (
                low_vs[step],
                low_vs[step + 1],
                eave_vs[step + 1],
                eave_vs[step],
            )
        )
    finish_mesh(bm, mesh, smooth=False)
    mesh.materials.append(material)
    return obj


def make_ground(material):
    mesh = bpy.data.meshes.new("GROUND_MESH")
    obj = link(bpy.data.objects.new("GROUND", mesh))
    bm = bmesh.new()
    add_box(bm, -70.0, 70.0, -70.0, 70.0, -0.04, -0.02)
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
    curve.size = 0.6
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.space_line = 1.15
    curve.extrude = 0.012
    curve.resolution_u = 8
    curve.font = load_font()
    obj = link(bpy.data.objects.new("SILO_LABEL", curve))
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    obj.data.materials.append(material)
    return obj


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_camera(name, location, target, ortho=False, ortho_scale=30.0, lens=28.0):
    data = bpy.data.cameras.new(name + "_DATA")
    obj = link(bpy.data.objects.new(name, data))
    obj.location = Vector(location)
    look_at(obj, target)
    data.clip_start = 0.05
    data.clip_end = 400.0
    if ortho:
        data.type = "ORTHO"
        data.sensor_fit = "VERTICAL"
        data.ortho_scale = ortho_scale
    else:
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
    data.color = (1.0, 0.94, 0.86)
    data.shadow_soft_size = 0.6
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
    background.inputs[0].default_value = (0.16, 0.19, 0.23, 1.0)
    background.inputs[1].default_value = 1.0


def label_ndc(label, camera, scene):
    inverse = camera.matrix_world.inverted()
    if camera.data.type == "ORTHO":
        scale_y = camera.data.ortho_scale
        scale_x = scale_y * scene.render.resolution_x / scene.render.resolution_y
        xs = []
        ys = []
        for corner in label.bound_box:
            local = inverse @ (label.matrix_world @ Vector(corner))
            xs.append(local.x / (scale_x * 0.5))
            ys.append(local.y / (scale_y * 0.5))
        return min(xs), max(xs), min(ys), max(ys), scale_x * 0.5, scale_y * 0.5
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
    return min(xs), max(xs), min(ys), max(ys), tan_h, tan_v


def place_label(label, camera, scene):
    bpy.context.view_layer.update()
    rotation = camera.matrix_world.to_3x3()
    right = Vector(rotation.col[0])
    up = Vector(rotation.col[1])
    forward = -Vector(rotation.col[2])
    label.rotation_euler = camera.rotation_euler.copy()
    label.location = camera.location + forward * 30.0 + right * (-18.2) + up * (-6.4)
    bpy.context.view_layer.update()
    margin = 0.08
    for _ in range(16):
        minx, maxx, miny, maxy, tan_h, tan_v = label_ndc(label, camera, scene)
        shift_x = 0.0
        shift_y = 0.0
        if minx < -1.0 + margin:
            shift_x = (-1.0 + margin) - minx
        elif maxx > 1.0 - margin:
            shift_x = (1.0 - margin) - maxx
        if miny < -1.0 + margin:
            shift_y = (-1.0 + margin) - miny
        elif maxy > 1.0 - margin:
            shift_y = (1.0 - margin) - maxy
        if abs(shift_x) < 0.005 and abs(shift_y) < 0.005:
            break
        inverse = camera.matrix_world.inverted()
        depth = -(inverse @ label.matrix_world.translation).z
        if camera.data.type == "ORTHO":
            depth = 1.0
        label.location += right * (shift_x * tan_h * depth) + up * (shift_y * tan_v * depth)
        label.rotation_euler = camera.rotation_euler.copy()
        bpy.context.view_layer.update()
    minx, maxx, miny, maxy, _, _ = label_ndc(label, camera, scene)
    print("LABEL_NDC " + json.dumps([clean(minx), clean(maxx), clean(miny), clean(maxy)]))


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


def adjacent_gap(sectors):
    gaps = []
    for index in range(ROOF_SECTORS):
        first = world_coords(sectors[index])
        second = world_coords(sectors[(index + 1) % ROOF_SECTORS])
        best = None
        for origin in first:
            for other in second:
                distance = (origin - other).length
                if best is None or distance < best:
                    best = distance
        gaps.append(best)
    return min(gaps), max(gaps)


def write_report(failed=False):
    text = (
        "blender/silo_msvu_220_roof/measure.json\n"
        "\n"
        "Дах — 8 плоских секторів на висоті стіни, щілина 0.04 м, отвір у центрі 0.4 м. "
        "Ухилу немає. Карниз 0.9 м — показ, щоб шви читались з камери нижче даху, не товщина листа. "
        "Стіна як у стику: 14 поясів, фланець, 56 болтів, напуск 0.08 м. "
        "Усе це показ, не з паспорта. Хвилі гофри немає. "
        "blender/silo_msvu_220_seam/ не перезаписано.\n"
    )
    if failed:
        text += "SILO_FAIL.\n"
    else:
        text += "SILO_PASS.\n"
    (OUT / "build_report.md").write_text(text, encoding="utf-8")


def write_measure(measure):
    (OUT / "measure.json").write_text(json.dumps(measure, indent=2) + "\n", encoding="utf-8")


def main():
    if OUT.name != "silo_msvu_220_roof":
        raise RuntimeError("refusing to write outside silo_msvu_220_roof")
    OUT.mkdir(parents=True, exist_ok=True)
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    light_mat = make_material("RingLight", (0.86, 0.87, 0.89), 0.46)
    dark_mat = make_material("RingDark", (0.60, 0.64, 0.68), 0.5)
    hem_mat = make_material("RingHem", (0.22, 0.24, 0.27), 0.42)
    skirt_mat = make_material("RingSkirt", (0.42, 0.46, 0.50), 0.4)
    flange_mat = make_material("FlangeSteel", (0.20, 0.24, 0.30), 0.4, metallic=0.35)
    head_mat = make_material("BoltHead", (0.05, 0.05, 0.06), 0.28, metallic=0.85)
    shank_mat = make_material("BoltShank", (0.82, 0.78, 0.68), 0.22, metallic=0.9)
    roof_light = make_material("RoofLight", (0.74, 0.42, 0.20), 0.5, metallic=0.2)
    roof_dark = make_material("RoofDark", (0.16, 0.09, 0.06), 0.58, metallic=0.15)
    bounds = ring_bounds()
    rings = []
    for index, (z0, z1) in enumerate(bounds, start=1):
        wall_mat = light_mat if index % 2 else dark_mat
        rings.append(make_ring(index, z0, z1, wall_mat, hem_mat, skirt_mat))
    flange = make_flange(flange_mat)

    outer_x = RADIUS_M + FLANGE_PROTRUSION_M
    heads = []
    bodies = []
    bolt_number = 1
    bolt_spots = []
    for index, (z0, z1) in enumerate(bounds):
        body_low = z0 + (LAP_M if index else 0.2)
        body_high = z1 - HEM_H_M - 0.04
        span = body_high - body_low
        for y_value, tilt in ((-0.11, -0.70), (0.11, 0.70)):
            direction = Vector((math.cos(tilt), math.sin(tilt), 0.0))
            for fraction in (0.32, 0.68):
                z_value = body_low + fraction * span
                origin = Vector((outer_x, y_value, z_value))
                bolt_spots.append((bolt_number, y_value, z_value, origin, direction))
                bolt_number += 1
    for number, _y_value, _z_value, origin, direction in bolt_spots:
        bodies.append(
            make_cylinder_object(
                f"SILO_BOLT_{number:02d}_BODY",
                origin,
                direction,
                SHANK_H_M,
                SHANK_D_M * 0.5,
                shank_mat,
            )
        )
        heads.append(
            make_cylinder_object(
                f"SILO_BOLT_{number:02d}",
                origin + direction * SHANK_H_M,
                direction,
                HEAD_H_M,
                HEAD_D_M * 0.5,
                head_mat,
            )
        )

    floor = make_disk("SILO_FLOOR", 0.0, make_material("FloorSand", (0.78, 0.66, 0.42), 0.75))
    sectors = []
    for index in range(1, ROOF_SECTORS + 1):
        material = roof_light if index % 2 else roof_dark
        sectors.append(make_sector(index, material))
    make_ground(make_material("GroundConcrete", (0.76, 0.77, 0.74), 0.9))
    label = make_label(make_material("LabelBlack", (0.02, 0.02, 0.02), 0.4))

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    cam_ext = make_camera(
        "CAM_EXTERIOR",
        (40.0, -22.0, HEIGHT_M * 0.5),
        (2.0, 0.0, HEIGHT_M * 0.46),
        lens=26.0,
    )
    cam_open = make_camera(
        "CAM_OPEN",
        (0.0, -18.0, 40.0),
        (0.0, -1.0, 12.0),
        lens=18.0,
    )
    cam_inside = make_camera(
        "CAM_INSIDE",
        (0.0, -4.0, 2.0),
        (6.2, 1.0, 1.15),
        lens=20.0,
    )
    place_label(label, cam_ext, scene)
    sun_key = make_sun("SUN_KEY", (24.0, -14.0, 16.0), (0.0, 0.0, 10.0), 5.0)
    sun_fill = make_sun("SUN_FILL", (-12.0, -18.0, 12.0), (0.0, 0.0, 8.0), 1.8)
    sun_roof = make_sun("SUN_ROOF", (0.0, -8.0, 42.0), (0.0, -2.0, 0.0), 3.2)
    inside_key = make_point("LIGHT_INSIDE", (0.0, 0.0, 7.5), 9000.0)
    inside_fill = make_point("LIGHT_FLOOR", (0.0, -2.0, 3.2), 4500.0)
    setup_world(scene)

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError as exc:
        raise RuntimeError(f"BLENDER_EEVEE_NEXT unavailable: {exc}") from exc
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_motion_blur = False
    transforms = {
        item.identifier
        for item in scene.view_settings.bl_rna.properties["view_transform"].enum_items
    }
    if "Standard" in transforms:
        scene.view_settings.view_transform = "Standard"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 48
    try:
        scene.eevee.use_raytracing = False
    except Exception:
        pass

    bpy.context.view_layer.update()
    problems = []
    wall_coords = []
    all_ring_coords = []
    for ring in rings:
        coords = world_coords(ring)
        all_ring_coords.extend(coords)
        if len(ring.data.vertices) > SEGMENTS * 6:
            problems.append(f"{ring.name} too many vertices")
        wall_coords.extend(
            coord for coord in coords if math.hypot(coord.x, coord.y) < RADIUS_M + 0.02
        )
        for coord in coords:
            radius = math.hypot(coord.x, coord.y)
            if abs(radius - RADIUS_M) < 0.01 and abs(radius - RADIUS_M) > 0.001:
                problems.append(f"corrugation {ring.name}")
                break
    xs = [coord.x for coord in wall_coords]
    ys = [coord.y for coord in wall_coords]
    zs = [coord.z for coord in all_ring_coords]
    diameter_x = max(xs) - min(xs)
    diameter_y = max(ys) - min(ys)
    z_min = min(zs)
    z_max = max(zs)
    outer_diameter = max(diameter_x, diameter_y)

    if len(heads) != BOLT_COUNT or len(bodies) != BOLT_COUNT:
        problems.append(f"bolts {len(heads)}/{len(bodies)}")
    for head, body in zip(heads, bodies):
        if head.data is body.data:
            problems.append(f"{head.name} shares mesh with body")
    if flange.name != "SILO_FLANGE":
        problems.append("flange name")
    flange_coords = world_coords(flange)
    flange_y = max(coord.y for coord in flange_coords) - min(coord.y for coord in flange_coords)
    flange_x = max(coord.x for coord in flange_coords) - RADIUS_M
    if abs(flange_y - FLANGE_WIDTH_M) > 0.002:
        problems.append(f"flange width {flange_y:.4f}")
    if abs(flange_x - FLANGE_PROTRUSION_M) > 0.002:
        problems.append(f"flange protrusion {flange_x:.4f}")
    for index in range(1, RING_COUNT):
        lap = bounds[index - 1][1] - bounds[index][0]
        if abs(lap - LAP_M) > 0.0001:
            problems.append(f"lap {index} {lap:.5f}")
    expected_heads = [f"SILO_BOLT_{number:02d}" for number in range(1, BOLT_COUNT + 1)]
    if sorted(obj.name for obj in heads) != sorted(expected_heads):
        problems.append("bolt names")
    if len(rings) != RING_COUNT:
        problems.append("ring count")
    if label.type != "FONT" or "8 плоских секторів" not in label.data.body:
        problems.append("label")
    if "не з паспорта" not in label.data.body or "хвиля гофри" not in label.data.body:
        problems.append("label facts")
    if not near(diameter_x, DIAMETER_M) or not near(diameter_y, DIAMETER_M):
        problems.append(f"diameter {diameter_x:.6f} x {diameter_y:.6f}")
    if not near(z_min, 0.0) or not near(z_max, HEIGHT_M):
        problems.append(f"height {z_min:.6f}..{z_max:.6f}")
    if abs(z_max - 22.096) < 0.05:
        problems.append("rejected height used")
    if cam_ext.location.z > 16.0:
        problems.append(f"exterior camera z {cam_ext.location.z:.3f}")
    inside_delta = cam_inside.location - Vector((0.0, -4.0, 2.0))
    if inside_delta.length > 0.05:
        problems.append(f"inside camera {tuple(cam_inside.location)}")
    if scene.unit_settings.system != "METRIC" or scene.unit_settings.length_unit != "METERS":
        problems.append("units")
    if scene.unit_settings.scale_length != 1.0:
        problems.append("scale")
    if scene.render.engine != "BLENDER_EEVEE_NEXT":
        problems.append(scene.render.engine)
    if bpy.data.objects.get("SILO_ROOF") is not None:
        problems.append("single roof disk")
    names = [sector.name for sector in sectors]
    if names != [f"SILO_ROOF_{index:02d}" for index in range(1, ROOF_SECTORS + 1)]:
        problems.append(f"sector names {names}")

    roof_coords = []
    for sector in sectors:
        roof_coords.extend(world_coords(sector))
    roof_z = [coord.z for coord in roof_coords]
    roof_r = [math.hypot(coord.x, coord.y) for coord in roof_coords]
    roof_z_min = min(roof_z)
    roof_z_max = max(roof_z)
    roof_r_min = min(roof_r)
    roof_r_max = max(roof_r)
    cap_r = [radius for radius, z_value in zip(roof_r, roof_z) if abs(z_value - roof_z_max) <= TOLERANCE_M]
    z_levels = {round(z_value, 4) for z_value in roof_z}
    if len(z_levels) != 2:
        problems.append(f"roof z levels {sorted(z_levels)}")
    if roof_z_max - roof_z_min > SKIRT_H + 0.002 or roof_z_max - roof_z_min < SKIRT_H - 0.002:
        problems.append(f"skirt height {roof_z_min:.4f}..{roof_z_max:.4f}")
    if not near(roof_z_max, HEIGHT_M):
        problems.append(f"roof z {roof_z_max:.6f}")
    if roof_r_min < ROOF_HOLE_R - TOLERANCE_M:
        problems.append(f"hole filled {roof_r_min:.4f}")
    if abs(roof_r_min - ROOF_HOLE_R) > 0.002:
        problems.append(f"hole radius {roof_r_min:.4f}")
    if not any(abs(radius - RADIUS_M) <= 0.002 for radius in cap_r):
        problems.append("cap does not reach radius 11")
    if abs(roof_r_max - SKIRT_OUTER) > 0.002:
        problems.append(f"skirt radius {roof_r_max:.4f}")
    gap_min, gap_max = adjacent_gap(sectors)
    if abs(gap_min - ROOF_GAP_M) > 0.002 or abs(gap_max - ROOF_GAP_M) > 0.002:
        problems.append(f"gap {gap_min:.4f}..{gap_max:.4f}")
    floor_z = [coord.z for coord in world_coords(floor)]
    if max(floor_z) - min(floor_z) > TOLERANCE_M or not near(min(floor_z), 0.0):
        problems.append("floor not flat")

    open_hit = None
    direction = -cam_open.matrix_world.to_3x3().col[2]
    if abs(direction.z) > 1.0e-8:
        open_hit = cam_open.location + direction * ((HEIGHT_M - cam_open.location.z) / direction.z)
        hit_r = math.hypot(open_hit.x, open_hit.y)
        hit_a = math.atan2(open_hit.y, open_hit.x)
        _mid, angle_0, angle_1 = sector_bounds(1)
        while hit_a < angle_0:
            hit_a += 2.0 * math.pi
        while hit_a > angle_1 + 2.0 * math.pi:
            hit_a -= 2.0 * math.pi
        if not (angle_0 + 0.02 < hit_a < angle_1 - 0.02 and ROOF_HOLE_R + 0.3 < hit_r < RADIUS_M - 0.3):
            problems.append(
                f"open ray {clean(open_hit.x)} {clean(open_hit.y)} r {clean(hit_r)}"
            )
    else:
        problems.append("open ray parallel")

    measure = {
        "pass": not problems,
        "ring_count": RING_COUNT,
        "bolt_count": BOLT_COUNT,
        "flange": True,
        "roof_sectors": ROOF_SECTORS,
        "roof_slope_from_passport": False,
        "wall_z_min_m": clean(z_min),
        "wall_z_max_m": clean(z_max),
        "outer_diameter_m": clean(outer_diameter),
        "roof_z_m": clean(roof_z_max),
        "display_roof_gap_m": ROOF_GAP_M,
        "display_roof_hole_radius_m": ROOF_HOLE_R,
        "display_roof_skirt_height_m": SKIRT_H,
        "display_roof_skirt_radius_m": SKIRT_OUTER,
        "display_flange_width_m": FLANGE_WIDTH_M,
        "display_bolt_head_diameter_m": HEAD_D_M,
        "display_lap_m": LAP_M,
        "from_passport": False,
        "corrugation_wave": False,
        "rejected_height_m": 22.096,
    }
    print("SILO_MEASURE " + json.dumps(measure))
    print(
        "ROOF_FRAME "
        + json.dumps(
            [
                clean(roof_z_min),
                clean(roof_z_max),
                clean(roof_r_min),
                clean(roof_r_max),
                clean(gap_min),
                clean(gap_max),
                clean(cam_ext.location.z),
                clean(cam_inside.location.x),
                clean(cam_inside.location.y),
                clean(cam_inside.location.z),
            ]
        )
    )
    if problems:
        print("SILO_PROBLEMS " + " | ".join(problems))
        measure["pass"] = False
        write_measure(measure)
        success_blend = OUT / "silo_msvu_220_roof.blend"
        if success_blend.exists():
            success_blend.unlink()
        write_report(failed=True)
        print("SILO_FAIL")
        sys.exit(2)

    render_still(
        scene,
        OUT / "render_exterior.png",
        cam_ext,
        hidden=(inside_key, inside_fill),
    )
    inside_key.data.energy = 2200.0
    inside_fill.data.energy = 6500.0
    render_still(
        scene,
        OUT / "render_open.png",
        cam_open,
        hidden=(sectors[0], label, sun_roof),
    )
    inside_key.data.energy = 9000.0
    inside_fill.data.energy = 4500.0
    render_still(
        scene,
        OUT / "render_inside.png",
        cam_inside,
        hidden=(label, sun_key, sun_fill, sun_roof),
    )
    for obj in (sectors[0], label, inside_key, inside_fill, sun_key, sun_fill, sun_roof):
        obj.hide_render = False
        obj.hide_viewport = False
    scene.camera = cam_ext
    bpy.context.view_layer.update()
    for name in ("render_exterior.png", "render_open.png", "render_inside.png"):
        size = (OUT / name).stat().st_size
        print(f"RENDER_BYTES {name} {size}")
        if size < 20000:
            problems.append(f"{name} too small")
    if problems:
        measure["pass"] = False
        write_measure(measure)
        write_report(failed=True)
        print("SILO_FAIL")
        sys.exit(2)

    success_blend = OUT / "silo_msvu_220_roof.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(success_blend))
    backup = OUT / "silo_msvu_220_roof.blend1"
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
