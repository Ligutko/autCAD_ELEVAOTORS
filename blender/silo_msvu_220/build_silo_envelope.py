"""SILO-ENVELOPE: one smooth silo shell, metric, headless.

Run:
    blender --background --factory-startup --python "d:\\autocad project\\blender\\silo_msvu_220\\build_silo_envelope.py"
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
SEGMENTS = 64
TOLERANCE_M = 0.0001
CATALOG_VOLUME_M3 = 6381
GROUND_OUTER_M = 45.0
LABEL_TEXT = (
    "МСВУ 220.13.В12\n"
    "Лубнимаш\n"
    "D = 22.000 м\n"
    "H = 21.422 м\n"
    "днище плоске\n"
    "немає факту: гофра, товщина листа, болти, ухил даху"
)
FONT_CANDIDATES = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\times.ttf",
)
OUT = Path(r"d:\autocad project\blender\silo_msvu_220")
MESH_NAMES = ("SILO_WALL", "SILO_FLOOR", "SILO_ROOF", "GROUND")


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
    for collection in (bpy.data.meshes, bpy.data.curves, bpy.data.cameras, bpy.data.lights, bpy.data.materials):
        for block in list(collection):
            if block.users == 0:
                collection.remove(block)


def make_material(name, color, roughness):
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
    return mat


def assign(obj, material):
    obj.data.materials.append(material)


def outward_or_up(bm, prefer_z=False):
    bm.faces.ensure_lookup_table()
    bm.normal_update()
    face = bm.faces[0]
    if prefer_z:
        inward = face.normal.z < 0.0
    else:
        inward = face.normal.dot(face.calc_center_median()) < 0.0
    if inward:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.normal_update()


def make_wall():
    mesh = bpy.data.meshes.new("SILO_WALL_MESH")
    obj = link(bpy.data.objects.new("SILO_WALL", mesh))
    bm = bmesh.new()
    bottom = []
    top = []
    for i in range(SEGMENTS):
        angle = 2.0 * math.pi * i / SEGMENTS
        x = RADIUS_M * math.cos(angle)
        y = RADIUS_M * math.sin(angle)
        bottom.append(bm.verts.new((x, y, 0.0)))
        top.append(bm.verts.new((x, y, HEIGHT_M)))
    for i in range(SEGMENTS):
        j = (i + 1) % SEGMENTS
        bm.faces.new((bottom[i], top[i], top[j], bottom[j]))
    outward_or_up(bm, prefer_z=False)
    for face in bm.faces:
        face.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    return obj


def make_disk(name, z_value):
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    verts = []
    for i in range(SEGMENTS):
        angle = 2.0 * math.pi * i / SEGMENTS
        verts.append(
            bm.verts.new((RADIUS_M * math.cos(angle), RADIUS_M * math.sin(angle), z_value))
        )
    bm.faces.new(verts)
    outward_or_up(bm, prefer_z=True)
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    return obj


def make_ground():
    mesh = bpy.data.meshes.new("GROUND_MESH")
    obj = link(bpy.data.objects.new("GROUND", mesh))
    bm = bmesh.new()
    inner = []
    outer = []
    for i in range(SEGMENTS):
        angle = 2.0 * math.pi * i / SEGMENTS
        inner.append(
            bm.verts.new((RADIUS_M * math.cos(angle), RADIUS_M * math.sin(angle), 0.0))
        )
        outer.append(
            bm.verts.new(
                (GROUND_OUTER_M * math.cos(angle), GROUND_OUTER_M * math.sin(angle), 0.0)
            )
        )
    for i in range(SEGMENTS):
        j = (i + 1) % SEGMENTS
        bm.faces.new((inner[i], outer[i], outer[j], inner[j]))
    outward_or_up(bm, prefer_z=True)
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    return obj


def load_font():
    for path in FONT_CANDIDATES:
        if Path(path).is_file():
            return bpy.data.fonts.load(path)
    raise RuntimeError("no Cyrillic font found under C:\\Windows\\Fonts")


def make_label():
    curve = bpy.data.curves.new("SILO_LABEL_CURVE", type="FONT")
    curve.body = LABEL_TEXT
    curve.size = 0.72
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.space_line = 1.25
    curve.extrude = 0.02
    curve.resolution_u = 8
    curve.font = load_font()
    obj = link(bpy.data.objects.new("SILO_LABEL", curve))
    obj.location = Vector((-18.0, -14.0, 9.0))
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    return obj


def look_at(obj, target, track="-Z", up="Y"):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat(track, up).to_euler()


def make_camera(name, location, target, ortho=False, ortho_scale=28.0, lens=24.0):
    data = bpy.data.cameras.new(name + "_DATA")
    obj = link(bpy.data.objects.new(name, data))
    obj.location = Vector(location)
    look_at(obj, target)
    data.clip_start = 0.1
    data.clip_end = 500.0
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
    if hasattr(data, "use_shadow"):
        data.use_shadow = False
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
    background.inputs[0].default_value = (0.10, 0.12, 0.15, 1.0)
    background.inputs[1].default_value = 1.0


def world_coords(obj):
    matrix = obj.matrix_world
    return [matrix @ vertex.co for vertex in obj.data.vertices]


def extents(coords):
    xs = [coord.x for coord in coords]
    ys = [coord.y for coord in coords]
    zs = [coord.z for coord in coords]
    return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)


def near(value, target):
    return abs(float(value) - float(target)) <= TOLERANCE_M


def label_ndc(label, camera, scene):
    inverse = camera.matrix_world.inverted()
    lens = camera.data.lens
    sensor = camera.data.sensor_width
    aspect = scene.render.resolution_x / scene.render.resolution_y
    tan_h = (sensor * 0.5) / lens
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
    """Keep the label parallel to the exterior frame and fully inside it."""
    bpy.context.view_layer.update()
    rotation = camera.matrix_world.to_3x3()
    right = Vector(rotation.col[0])
    up = Vector(rotation.col[1])
    forward = -Vector(rotation.col[2])
    label.rotation_euler = camera.rotation_euler.copy()
    label.location = camera.location + forward * 28.0 + right * (-7.2) + up * (-7.4)
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
        label.location += right * (shift_x * tan_h * depth) + up * (shift_y * tan_v * depth)
        label.rotation_euler = camera.rotation_euler.copy()
        bpy.context.view_layer.update()
    minx, maxx, miny, maxy, _, _ = label_ndc(label, camera, scene)
    print(
        "LABEL_AT "
        + json.dumps([clean(axis) for axis in label.location])
        + " NDC "
        + json.dumps([clean(minx), clean(maxx), clean(miny), clean(maxy)])
    )


def push_label_outside(label, min_radius):
    for _ in range(24):
        bpy.context.view_layer.update()
        corners = [label.matrix_world @ Vector(corner) for corner in label.bound_box]
        radial = min(math.hypot(corner.x, corner.y) for corner in corners)
        if radial >= min_radius:
            return radial
        horizontal = math.hypot(label.location.x, label.location.y)
        if horizontal < 1e-6:
            label.location.x = -min_radius
            continue
        label.location.x *= (horizontal + (min_radius - radial) + 0.4) / horizontal
        label.location.y *= (horizontal + (min_radius - radial) + 0.4) / horizontal
    bpy.context.view_layer.update()
    corners = [label.matrix_world @ Vector(corner) for corner in label.bound_box]
    return min(math.hypot(corner.x, corner.y) for corner in corners)


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


def write_report(measure, failed_blend=None):
    wall = measure["wall"]
    lines = [
        "blender/silo_msvu_220/measure.json",
        "",
        (
            f"Виміряно D = {wall['measured_diameter_m']:.6f} м, "
            f"H = {wall['measured_height_m']:.6f} м. "
            f"Вершин стіни: {wall['vertex_count']}."
        ),
        "Кришка SILO_ROOF — окремий об'єкт, не в одному меші зі стіною.",
        "Конуса немає. Днище плоске на Z = 0. Кришка плоска, без ухилу.",
        "Висоту 22.096 м з оголошення відкинуто.",
        "Статуси карток у inbox/records не змінювались. FACTS.json не створювався.",
        (
            f"Об'єм оболонки π×11²×21.422 = {measure['shell_cylinder_volume_m3']:.2f} м³. "
            "Паспортні 6381 м³ — місткість, геометрію під них не підганяли."
        ),
    ]
    if failed_blend is not None:
        lines.append(f"SILO_FAIL. Blend здачі не збережено. Поруч: {failed_blend.name}.")
    else:
        lines.append("SILO_PASS.")
    (OUT / "build_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if "proof" in OUT.parts:
        raise RuntimeError("refusing to write blender/proof")
    OUT.mkdir(parents=True, exist_ok=True)

    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"

    wall = make_wall()
    floor = make_disk("SILO_FLOOR", 0.0)
    roof = make_disk("SILO_ROOF", HEIGHT_M)
    ground = make_ground()
    label = make_label()

    assign(wall, make_material("WallSteel", (0.90, 0.91, 0.92), 0.36))
    assign(floor, make_material("FloorSand", (0.82, 0.68, 0.40), 0.7))
    assign(roof, make_material("RoofRust", (0.62, 0.26, 0.12), 0.45))
    assign(ground, make_material("GroundConcrete", (0.70, 0.71, 0.68), 0.9))
    assign(label, make_material("LabelBlack", (0.02, 0.02, 0.02), 0.45))

    cam_ext = make_camera(
        "CAM_EXTERIOR",
        (14.0, -15.0, 50.0),
        (0.0, 0.0, 10.0),
        lens=24.0,
    )
    cam_side = make_camera(
        "CAM_SIDE",
        (48.0, 0.0, HEIGHT_M / 2.0),
        (0.0, 0.0, HEIGHT_M / 2.0),
        ortho=True,
        ortho_scale=30.0,
    )
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    place_label(label, cam_ext, scene)
    make_sun("SUN_KEY", (12.0, -12.0, 40.0), (0.0, 0.0, 0.0), 4.2)
    make_sun("SUN_FILL", (-18.0, 14.0, 24.0), (0.0, 0.0, 10.0), 1.4)
    make_sun("SUN_DOWN", (0.0, 1.0, 40.0), (0.0, 0.0, 0.0), 1.6)
    setup_world(scene)

    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError as exc:
        raise RuntimeError(f"BLENDER_EEVEE_NEXT unavailable: {exc}") from exc
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_motion_blur = False
    view_transforms = {
        item.identifier
        for item in scene.view_settings.bl_rna.properties["view_transform"].enum_items
    }
    if "Standard" in view_transforms:
        scene.view_settings.view_transform = "Standard"
    if hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
        scene.eevee.taa_render_samples = 64

    bpy.context.view_layer.update()

    wall_co = world_coords(wall)
    floor_co = world_coords(floor)
    roof_co = world_coords(roof)
    wall_ext = extents(wall_co)
    floor_ext = extents(floor_co)
    roof_ext = extents(roof_co)
    wall_dx = wall_ext[1] - wall_ext[0]
    wall_dy = wall_ext[3] - wall_ext[2]
    floor_dx = floor_ext[1] - floor_ext[0]
    floor_dy = floor_ext[3] - floor_ext[2]
    roof_dx = roof_ext[1] - roof_ext[0]
    roof_dy = roof_ext[3] - roof_ext[2]
    wall_z0, wall_z1 = wall_ext[4], wall_ext[5]
    floor_z = (floor_ext[4] + floor_ext[5]) / 2.0
    roof_z = (roof_ext[4] + roof_ext[5]) / 2.0
    wall_height = wall_z1 - wall_z0
    wall_diameter = max(wall_dx, wall_dy)
    floor_diameter = max(floor_dx, floor_dy)
    roof_diameter = max(roof_dx, roof_dy)

    mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    mesh_names = tuple(sorted(obj.name for obj in mesh_objects))
    separate = (
        roof is not wall
        and roof.data is not wall.data
        and roof.parent is None
        and wall.parent is None
        and roof not in list(wall.children)
    )
    problems = []
    if len(wall_co) != 128:
        problems.append(f"wall vertices {len(wall_co)}")
    if len(mesh_objects) != 4 or mesh_names != tuple(sorted(MESH_NAMES)):
        problems.append(f"mesh objects {mesh_names}")
    if label.type != "FONT":
        problems.append(f"label type {label.type}")
    if any(obj.modifiers for obj in mesh_objects):
        problems.append("modifier present")
    if not separate:
        problems.append("roof is not a separate object")
    if not near(wall_dx, DIAMETER_M) or not near(wall_dy, DIAMETER_M):
        problems.append(f"wall diameter {wall_dx:.6f} x {wall_dy:.6f}")
    if not near(wall_height, HEIGHT_M) or not near(wall_z0, 0.0) or not near(wall_z1, HEIGHT_M):
        problems.append(f"wall z {wall_z0:.6f}..{wall_z1:.6f}")
    if not near(floor_dx, DIAMETER_M) or not near(floor_dy, DIAMETER_M) or not near(floor_z, 0.0):
        problems.append(f"floor {floor_diameter:.6f} z {floor_z:.6f}")
    if abs(floor_ext[5] - floor_ext[4]) > TOLERANCE_M:
        problems.append("floor not flat")
    if not near(roof_dx, DIAMETER_M) or not near(roof_dy, DIAMETER_M) or not near(roof_z, HEIGHT_M):
        problems.append(f"roof {roof_diameter:.6f} z {roof_z:.6f}")
    if abs(roof_ext[5] - roof_ext[4]) > TOLERANCE_M:
        problems.append("roof not flat")
    if scene.unit_settings.system != "METRIC" or scene.unit_settings.length_unit != "METERS":
        problems.append("units")
    if abs(scene.unit_settings.scale_length - 1.0) > 0.0:
        problems.append("scale_length")
    if scene.render.engine != "BLENDER_EEVEE_NEXT":
        problems.append(f"engine {scene.render.engine}")
    if math.hypot(cam_ext.location.x, cam_ext.location.y) <= RADIUS_M:
        problems.append("exterior camera inside the wall")
    if math.hypot(cam_side.location.x, cam_side.location.y) <= RADIUS_M:
        problems.append("side camera inside the wall")
    for obj in mesh_objects:
        if obj.name.startswith("SILO_") and any(abs(axis - 1.0) > 0.0 for axis in obj.scale):
            problems.append(f"scale on {obj.name}")

    shell_volume = round(math.pi * RADIUS_M * RADIUS_M * HEIGHT_M, 2)
    measure = {
        "pass": not problems,
        "unit_system": scene.unit_settings.system,
        "length_unit": scene.unit_settings.length_unit,
        "scale_length": scene.unit_settings.scale_length,
        "tolerance_m": TOLERANCE_M,
        "wall": {
            "name": "SILO_WALL",
            "vertex_count": len(wall_co),
            "target_diameter_m": DIAMETER_M,
            "target_height_m": HEIGHT_M,
            "measured_diameter_m": clean(wall_diameter),
            "measured_height_m": clean(wall_height),
            "z_min_m": clean(wall_z0),
            "z_max_m": clean(wall_z1),
        },
        "floor": {
            "name": "SILO_FLOOR",
            "measured_diameter_m": clean(floor_diameter),
            "z_m": clean(floor_z),
        },
        "roof": {
            "name": "SILO_ROOF",
            "measured_diameter_m": clean(roof_diameter),
            "z_m": clean(roof_z),
            "is_separate_object": separate,
        },
        "catalog_volume_m3": CATALOG_VOLUME_M3,
        "shell_cylinder_volume_m3": shell_volume,
        "volume_note": "6381 is rated capacity, not the volume of this shell",
        "not_modeled": [
            "corrugation_pitch",
            "sheet_thickness",
            "bolt_pattern",
            "roof_slope",
            "cone",
            "noria",
        ],
        "rejected_numbers": [
            {"value_m": 22.096, "why": "bizorg row height, disagrees with drawing 21.422 m"}
        ],
    }
    (OUT / "measure.json").write_text(
        json.dumps(measure, indent=2) + "\n", encoding="utf-8"
    )
    print("SILO_MEASURE " + json.dumps(measure))
    print("LABEL_AT " + json.dumps([clean(v) for v in label.location]))
    if problems:
        print("SILO_PROBLEMS " + " | ".join(problems))

    success_blend = OUT / "silo_msvu_220.blend"
    failed_blend = OUT / "silo_msvu_220.FAILED.blend"
    if problems:
        if success_blend.exists():
            success_blend.unlink()
        bpy.ops.wm.save_as_mainfile(filepath=str(failed_blend))
        write_report(measure, failed_blend=failed_blend)
        print("SILO_FAIL")
        sys.exit(2)

    render_still(scene, OUT / "render_exterior.png", cam_ext)
    render_still(scene, OUT / "render_open.png", cam_ext, hidden=(roof,))
    render_still(scene, OUT / "render_side.png", cam_side, hidden=(label,))
    roof.hide_render = False
    roof.hide_viewport = False
    label.hide_render = False
    label.hide_viewport = False
    scene.camera = cam_ext
    bpy.context.view_layer.update()
    if failed_blend.exists():
        failed_blend.unlink()
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
