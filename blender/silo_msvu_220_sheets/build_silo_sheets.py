"""SILO-SHEETS: 14 display courses and one bolted vertical joint.

Run:
    blender --background --factory-startup --python "d:\\autocad project\\blender\\silo_msvu_220_sheets\\build_silo_sheets.py"
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
SEGMENTS = 32
TOLERANCE_M = 0.0001
LIP_OUT_M = 0.04
LIP_H_M = 0.03
BOLT_DIAMETER_M = 0.08
BOLT_HEIGHT_M = 0.04
DISK_SEGMENTS = 64
LABEL_TEXT = (
    "МСВУ 220.13.В12\n"
    "D = 22.000 м\n"
    "H = 21.422 м\n"
    "днище плоске\n"
    "14 поясів — показ, крок не з паспорта\n"
    "болт — показ, діаметр не з паспорта\n"
    "немає факту: хвиля гофри, товщина листа, ухил даху"
)
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\times.ttf",
)
OUT = Path(r"d:\autocad project\blender\silo_msvu_220_sheets")


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


def ring_edges():
    edges = [0.0]
    for index in range(1, RING_COUNT):
        edges.append(HEIGHT_M * index / RING_COUNT)
    edges.append(HEIGHT_M)
    return edges


def outward_faces(bm):
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    face = bm.faces[0]
    if face.normal.dot(face.calc_center_median()) < 0.0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.normal_update()
    bm.faces.ensure_lookup_table()


def make_ring(index, z0, z1, wall_mat, lip_mat):
    name = f"SILO_RING_{index:02d}"
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    lip_z = z1 - LIP_H_M
    rows = []
    for radius, z_value in (
        (RADIUS_M, z0),
        (RADIUS_M, lip_z),
        (RADIUS_M + LIP_OUT_M, lip_z),
        (RADIUS_M + LIP_OUT_M, z1),
    ):
        row = []
        for step in range(SEGMENTS):
            angle = 2.0 * math.pi * step / SEGMENTS
            row.append(
                bm.verts.new((radius * math.cos(angle), radius * math.sin(angle), z_value))
            )
        rows.append(row)
    for row_index in range(3):
        lower = rows[row_index]
        upper = rows[row_index + 1]
        for step in range(SEGMENTS):
            nxt = (step + 1) % SEGMENTS
            bm.faces.new((lower[step], upper[step], upper[nxt], lower[nxt]))
    outward_faces(bm)
    for face in bm.faces:
        face.smooth = True
        radii = [math.hypot(vert.co.x, vert.co.y) for vert in face.verts]
        face.material_index = 1 if max(radii) > RADIUS_M + 0.02 else 0
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    mesh.materials.append(wall_mat)
    mesh.materials.append(lip_mat)
    return obj


def make_bolt(index, z_mid, material):
    name = f"SILO_BOLT_{index:02d}"
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    segments = 16
    radius = BOLT_DIAMETER_M * 0.5
    x_inner = RADIUS_M + 0.006
    x_outer = x_inner + BOLT_HEIGHT_M
    inner = []
    outer = []
    for step in range(segments):
        angle = 2.0 * math.pi * step / segments
        y_value = radius * math.cos(angle)
        z_value = z_mid + radius * math.sin(angle)
        inner.append(bm.verts.new((x_inner, y_value, z_value)))
        outer.append(bm.verts.new((x_outer, y_value, z_value)))
    for step in range(segments):
        nxt = (step + 1) % segments
        bm.faces.new((inner[step], outer[step], outer[nxt], inner[nxt]))
    bm.faces.new(list(reversed(inner)))
    bm.faces.new(outer)
    outward_faces(bm)
    for face in bm.faces:
        face.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    mesh.materials.append(material)
    return obj


def make_disk(name, z_value, material):
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    verts = []
    for step in range(DISK_SEGMENTS):
        angle = 2.0 * math.pi * step / DISK_SEGMENTS
        verts.append(
            bm.verts.new((RADIUS_M * math.cos(angle), RADIUS_M * math.sin(angle), z_value))
        )
    bm.faces.new(verts)
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    if bm.faces[0].normal.z < 0.0:
        bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    mesh.materials.append(material)
    return obj


def make_ground(material):
    mesh = bpy.data.meshes.new("GROUND_MESH")
    obj = link(bpy.data.objects.new("GROUND", mesh))
    bm = bmesh.new()
    size = 80.0
    z_value = -0.02
    coords = (
        (-size, -size, z_value),
        (size, -size, z_value),
        (size, size, z_value),
        (-size, size, z_value),
    )
    verts = [bm.verts.new(coord) for coord in coords]
    bm.faces.new(verts)
    bm.to_mesh(mesh)
    bm.free()
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
    curve.size = 0.92
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.space_line = 1.2
    curve.extrude = 0.015
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
    data.clip_start = 0.1
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


def setup_world(scene):
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("SILO_WORLD")
        scene.world = world
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs[0].default_value = (0.13, 0.16, 0.20, 1.0)
    background.inputs[1].default_value = 1.0


def label_ndc(label, camera, scene):
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
    return min(xs), max(xs), min(ys), max(ys), tan_h, tan_v


def place_label(label, camera, scene):
    bpy.context.view_layer.update()
    rotation = camera.matrix_world.to_3x3()
    right = Vector(rotation.col[0])
    up = Vector(rotation.col[1])
    forward = -Vector(rotation.col[2])
    label.rotation_euler = camera.rotation_euler.copy()
    label.location = camera.location + forward * 36.0 + right * (-15.5) + up * (-1.2)
    bpy.context.view_layer.update()
    margin = 0.1
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


def write_report(measure, failed=False):
    lines = [
        "blender/silo_msvu_220_sheets/measure.json",
        "",
        (
            "14 окремих поясів, крок "
            f"{measure['display_ring_height_m']:.6f} м не з паспорта. "
            "14 болтів на стику +X, діаметр 0.08 м екранний, не з паспорта. "
            "Хвилі гофри немає. "
            "blender/silo_msvu_220/ цим прогоном не перезаписувався."
        ),
    ]
    if failed:
        lines.append("SILO_FAIL.")
    else:
        lines.append("SILO_PASS.")
    (OUT / "build_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if OUT.name != "silo_msvu_220_sheets":
        raise RuntimeError("refusing to write outside silo_msvu_220_sheets")
    OUT.mkdir(parents=True, exist_ok=True)
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    lip_mat = make_material("LipSeam", (0.22, 0.24, 0.27), 0.55)
    bolt_mat = make_material("BoltHead", (0.08, 0.09, 0.10), 0.32, metallic=0.7)
    light_mat = make_material("RingLight", (0.84, 0.86, 0.88), 0.48)
    dark_mat = make_material("RingDark", (0.58, 0.62, 0.66), 0.52)
    edges = ring_edges()
    rings = []
    bolts = []
    for index in range(1, RING_COUNT + 1):
        z0 = edges[index - 1]
        z1 = edges[index]
        wall_mat = light_mat if index % 2 else dark_mat
        rings.append(make_ring(index, z0, z1, wall_mat, lip_mat))
        wall_mid = (z0 + (z1 - LIP_H_M)) * 0.5
        bolts.append(make_bolt(index, wall_mid, bolt_mat))

    floor = make_disk("SILO_FLOOR", 0.0, make_material("FloorSand", (0.78, 0.66, 0.42), 0.75))
    roof = make_disk("SILO_ROOF", HEIGHT_M, make_material("RoofRust", (0.62, 0.28, 0.14), 0.5))
    make_ground(make_material("GroundConcrete", (0.72, 0.73, 0.70), 0.9))
    label = make_label(make_material("LabelBlack", (0.02, 0.02, 0.02), 0.4))

    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    cam_ext = make_camera(
        "CAM_EXTERIOR",
        (30.0, -38.0, HEIGHT_M * 0.5),
        (0.0, 0.0, HEIGHT_M * 0.48),
        lens=24.0,
    )
    cam_seam = make_camera(
        "CAM_SEAM",
        (17.4, -2.4, HEIGHT_M * 0.5),
        (RADIUS_M + 0.03, 0.0, HEIGHT_M * 0.5),
        lens=16.0,
    )
    cam_side = make_camera(
        "CAM_SIDE",
        (52.0, 0.0, HEIGHT_M * 0.5),
        (0.0, 0.0, HEIGHT_M * 0.5),
        ortho=True,
        ortho_scale=30.0,
    )
    place_label(label, cam_ext, scene)
    make_sun("SUN_KEY", (18.0, -24.0, 18.0), (0.0, 0.0, 10.0), 4.5)
    make_sun("SUN_FILL", (-16.0, 12.0, 14.0), (0.0, 0.0, 10.0), 1.6)
    make_sun("SUN_SEAM", (18.0, -6.0, 12.0), (11.0, 0.0, 10.0), 2.4)
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

    bpy.context.view_layer.update()
    problems = []
    wall_coords = []
    all_ring_coords = []
    for ring in rings:
        coords = world_coords(ring)
        all_ring_coords.extend(coords)
        if len(coords) != SEGMENTS * 4:
            problems.append(f"{ring.name} vertices {len(coords)}")
        wall_coords.extend(coord for coord in coords if math.hypot(coord.x, coord.y) < RADIUS_M + 0.02)
    xs = [coord.x for coord in wall_coords]
    ys = [coord.y for coord in wall_coords]
    zs = [coord.z for coord in all_ring_coords]
    diameter_x = max(xs) - min(xs)
    diameter_y = max(ys) - min(ys)
    z_min = min(zs)
    z_max = max(zs)
    outer_diameter = max(diameter_x, diameter_y)
    for bolt in bolts:
        coords = world_coords(bolt)
        center_x = sum(coord.x for coord in coords) / len(coords)
        if center_x <= RADIUS_M:
            problems.append(f"{bolt.name} center inside the wall")
    mesh_names = sorted(obj.name for obj in bpy.data.objects if obj.type == "MESH")
    expected = [f"SILO_RING_{index:02d}" for index in range(1, RING_COUNT + 1)]
    expected += [f"SILO_BOLT_{index:02d}" for index in range(1, RING_COUNT + 1)]
    expected += ["SILO_FLOOR", "SILO_ROOF", "GROUND"]
    if mesh_names != sorted(expected):
        problems.append("mesh set " + ",".join(mesh_names))
    if label.type != "FONT" or "не з паспорта" not in label.data.body:
        problems.append("label text")
    if not near(diameter_x, DIAMETER_M) or not near(diameter_y, DIAMETER_M):
        problems.append(f"diameter {diameter_x:.6f} x {diameter_y:.6f}")
    if not near(z_min, 0.0) or not near(z_max, HEIGHT_M):
        problems.append(f"height {z_min:.6f}..{z_max:.6f}")
    if cam_ext.location.z > 16.0 or abs(cam_ext.location.z - 50.0) < 1.0:
        problems.append(f"exterior camera z {cam_ext.location.z:.3f}")
    if cam_seam.location.z > 16.0 or cam_side.location.z > 16.0:
        problems.append("camera above mid-wall")
    if roof.data is rings[-1].data or roof.parent is not None:
        problems.append("roof not separate")
    if scene.unit_settings.system != "METRIC" or scene.unit_settings.length_unit != "METERS":
        problems.append("units")
    if scene.unit_settings.scale_length != 1.0:
        problems.append("scale_length")
    if scene.render.engine != "BLENDER_EEVEE_NEXT":
        problems.append(scene.render.engine)

    pitch = round((z_max - z_min) / RING_COUNT, 6)
    measure = {
        "pass": not problems,
        "ring_count": RING_COUNT,
        "bolt_count": RING_COUNT,
        "wall_z_min_m": clean(z_min),
        "wall_z_max_m": clean(z_max),
        "outer_diameter_m": clean(outer_diameter),
        "display_ring_height_m": pitch,
        "display_bolt_diameter_m": BOLT_DIAMETER_M,
        "from_passport": False,
        "corrugation_wave": False,
        "rejected_height_m": 22.096,
        "not_modeled": [
            "corrugation_wave",
            "sheet_thickness",
            "roof_slope",
            "cone",
            "noria",
        ],
    }
    (OUT / "measure.json").write_text(json.dumps(measure, indent=2) + "\n", encoding="utf-8")
    print("SILO_MEASURE " + json.dumps(measure))
    print("CAM_Z " + json.dumps([clean(cam_ext.location.z), clean(cam_seam.location.z), clean(cam_side.location.z)]))
    if problems:
        print("SILO_PROBLEMS " + " | ".join(problems))

    success_blend = OUT / "silo_msvu_220_sheets.blend"
    if problems:
        if success_blend.exists():
            success_blend.unlink()
        write_report(measure, failed=True)
        print("SILO_FAIL")
        sys.exit(2)

    render_still(scene, OUT / "render_exterior.png", cam_ext)
    render_still(scene, OUT / "render_seam.png", cam_seam, hidden=(label,))
    render_still(scene, OUT / "render_side.png", cam_side, hidden=(label,))
    label.hide_render = False
    label.hide_viewport = False
    scene.camera = cam_ext
    bpy.context.view_layer.update()
    bpy.ops.wm.save_as_mainfile(filepath=str(success_blend))
    write_report(measure)
    print("SILO_PASS")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print("SILO_FAIL", repr(exc))
        sys.exit(2)
