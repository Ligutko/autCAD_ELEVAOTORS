"""COMPLEX-1: whole row of silos from a JSON config.

Silo and noria are linked from blender/noria_01/noria_01.blend, not redrawn.
Config X -> scene X, config vertical Y -> scene Z, millimetres -> metres.
The config is a front view. It has no plan depth, so NORIA_Y and the cross duct
are display only.
Run:
    blender --background --factory-startup --python blender/complex_01/build_complex.py -- config_7_silos.json
or, with the bpy module:
    python blender/complex_01/build_complex.py config_7_silos.json
"""

import json
import math
import sys
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh
import bmesh
from mathutils import Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
SRC = HERE.parent / "noria_01" / "noria_01.blend"
SRC_NORIA_X = 18.0
MM = 0.001
SILO_R = 11.0
NORIA_Y = -(SILO_R + 3.0)
CASING_H = 0.40
CASING_WALL = 0.006
CATALOG_CAPACITY_M3 = 6381


def config_path():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    name = args[0] if args else "config_7_silos.json"
    path = Path(name)
    return path if path.is_absolute() else ROOT / path


def out_dir(cfg_file):
    return HERE / cfg_file.stem


def link(obj, collection=None):
    (collection or bpy.context.scene.collection).objects.link(obj)
    return obj


def clean(value):
    value = round(float(value), 6)
    if abs(value) < 5e-7:
        return 0.0
    return value


def make_material(name, color, roughness, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(node for node in mat.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return mat


def new_mesh(name, builder, material, smooth=False):
    mesh = bpy.data.meshes.new(name + "_MESH")
    obj = link(bpy.data.objects.new(name, mesh))
    bm = bmesh.new()
    builder(bm)
    bm.normal_update()
    for face in bm.faces:
        face.smooth = smooth
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(material)
    return obj


def add_box(bm, p0, p1):
    x0, y0, z0 = p0
    x1, y1, z1 = p1
    v = [bm.verts.new((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]
    for face in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
        bm.faces.new([v[i] for i in face])


def add_cylinder(bm, bottom, top, radius, steps=24):
    rings = []
    for z_value in (bottom, top):
        rings.append([
            bm.verts.new((z_value[0] + radius * math.cos(2 * math.pi * i / steps),
                          z_value[1] + radius * math.sin(2 * math.pi * i / steps),
                          z_value[2]))
            for i in range(steps)
        ])
    for i in range(steps):
        j = (i + 1) % steps
        bm.faces.new((rings[0][i], rings[0][j], rings[1][j], rings[1][i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[1])


def load_prototypes():
    """Link silo and noria meshes from the accepted NORIA-1 scene into two collections."""
    with bpy.data.libraries.load(str(SRC), link=True, relative=True) as (data_from, data_to):
        data_to.objects = [
            name for name in data_from.objects
            if name.startswith(("SILO_", "NORIA_")) and not name.endswith("_LABEL")
        ]
    silo = bpy.data.collections.new("PROTO_SILO")
    noria = bpy.data.collections.new("PROTO_NORIA")
    for obj in data_to.objects:
        (silo if obj.name.startswith("SILO_") else noria).objects.link(obj)
    noria.instance_offset = (SRC_NORIA_X, 0.0, 0.0)
    return silo, noria


def instance(name, collection, location):
    obj = link(bpy.data.objects.new(name, None))
    obj.instance_type = "COLLECTION"
    obj.instance_collection = collection
    obj.location = location
    return obj


def build_conveyor(conv, mat):
    x0 = min(conv["start_x"], conv["end_x"]) * MM
    x1 = max(conv["start_x"], conv["end_x"]) * MM
    z0 = conv["start_y"] * MM
    half = conv["width"] * MM * 0.5

    def build(bm):
        add_box(bm, (x0, -half, z0), (x1, half, z0 + CASING_H))

    return new_mesh("CONV_" + conv["tag"], build, mat)


def build_pipe(pipe, mat):
    x = pipe["from_x"] * MM
    z0 = pipe["from_y"] * MM
    z1 = pipe["to_y"] * MM

    def build(bm):
        add_cylinder(bm, (x, 0.0, z0), (x, 0.0, z1), pipe["diameter"] * MM * 0.5)

    return new_mesh("PIPE_" + pipe["tag"], build, mat, smooth=True)


def build_cross_duct(elev, conv_width, mat):
    x = elev["x"] * MM
    z0 = elev["lift_height"] * MM
    half = conv_width * MM * 0.5

    def build(bm):
        add_box(bm, (x - half, NORIA_Y, z0), (x + half, 0.0, z0 + CASING_H))

    return new_mesh("DUCT_" + elev["tag"], build, mat)


def make_tag(text, location, mat, size=1.6):
    data = bpy.data.curves.new("TAG_" + text, type="FONT")
    data.body = text
    data.size = size
    data.align_x = "CENTER"
    data.extrude = 0.02
    obj = link(bpy.data.objects.new("TAG_" + text, data))
    obj.location = location
    obj.rotation_euler = (math.radians(90), 0.0, 0.0)
    obj.data.materials.append(mat)
    return obj


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def make_camera(name, location, target, lens=35.0, ortho=None):
    data = bpy.data.cameras.new(name + "_DATA")
    obj = link(bpy.data.objects.new(name, data))
    obj.location = Vector(location)
    look_at(obj, target)
    data.clip_start = 0.1
    data.clip_end = 2000.0
    if ortho:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    return obj


def make_sun(name, rotation, energy):
    data = bpy.data.lights.new(name + "_DATA", type="SUN")
    data.energy = energy
    data.angle = math.radians(2.0)
    obj = link(bpy.data.objects.new(name, data))
    obj.rotation_euler = [math.radians(a) for a in rotation]
    return obj


def setup_scene(scene):
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.view_settings.view_transform = "AgX"
    world = scene.world or bpy.data.worlds.new("COMPLEX_WORLD")
    scene.world = world
    world.use_nodes = True
    background = next(node for node in world.node_tree.nodes if node.type == "BACKGROUND")
    background.inputs["Color"].default_value = (0.62, 0.68, 0.75, 1.0)
    background.inputs["Strength"].default_value = 0.8


def render_still(scene, camera, path):
    scene.camera = camera
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def world_bounds(obj):
    """Bounds of a collection instance, from the linked prototype meshes."""
    offset = Vector(obj.location) - Vector(obj.instance_collection.instance_offset)
    pts = [o.matrix_world @ Vector(c) + offset
           for o in obj.instance_collection.objects if o.type == "MESH" for c in o.bound_box]
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def main():
    cfg_file = config_path()
    cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
    eq = cfg["equipment"]
    out = out_dir(cfg_file)
    out.mkdir(parents=True, exist_ok=True)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    setup_scene(scene)

    silo_proto, noria_proto = load_prototypes()
    steel = make_material("COMPLEX_CASING", (0.72, 0.74, 0.76), 0.35, 0.8)
    pipe_mat = make_material("COMPLEX_PIPE", (0.60, 0.62, 0.64), 0.4, 0.7)
    duct_mat = make_material("COMPLEX_DUCT_SHOW", (0.85, 0.55, 0.25), 0.5, 0.2)
    ground_mat = make_material("COMPLEX_GROUND", (0.42, 0.42, 0.40), 0.9)
    tag_mat = make_material("COMPLEX_TAG", (0.08, 0.10, 0.14), 0.6)

    silos = [instance(s["tag"], silo_proto, (s["x"] * MM, s["y"] * MM, 0.0)) for s in eq["silos"]]
    norias = [instance(e["tag"], noria_proto, (e["x"] * MM, NORIA_Y, 0.0)) for e in eq["elevators"]]
    conveyors = [build_conveyor(c, steel) for c in eq["conveyors"]]
    pipes = [build_pipe(p, pipe_mat) for p in eq["pipes"]]
    width = eq["conveyors"][0]["width"] if eq["conveyors"] else 320
    ducts = [build_cross_duct(e, width, duct_mat) for e in eq["elevators"]]

    xs = [s["x"] * MM for s in eq["silos"]] + [e["x"] * MM for e in eq["elevators"]]
    x_min, x_max = min(xs) - SILO_R, max(xs) + SILO_R
    x_mid = (x_min + x_max) * 0.5
    span = x_max - x_min

    def ground(bm):
        add_box(bm, (x_min - 60, -80, -0.2), (x_max + 60, 60, 0.0))

    new_mesh("GROUND", ground, ground_mat)
    for s in eq["silos"]:
        make_tag(s["tag"], (s["x"] * MM, -SILO_R - 0.6, 0.3), tag_mat, size=2.2)
    for e in eq["elevators"]:
        make_tag(e["tag"], (e["x"] * MM, NORIA_Y - 1.2, 0.3), tag_mat, size=1.6)

    make_sun("SUN_KEY", (50, 0, -35), 3.5)
    make_sun("SUN_FILL", (70, 0, 140), 0.8)

    cam_over = make_camera("CAM_OVERVIEW", (x_min - 25, -span * 0.75, 70), (x_mid, 0, 14), lens=30)
    cam_front = make_camera("CAM_FRONT", (x_mid, -600, 17), (x_mid, 0, 17), ortho=span * 1.08)
    e0 = eq["elevators"][0]
    head = Vector((e0["x"] * MM, NORIA_Y * 0.5, e0["lift_height"] * MM))
    cam_head = make_camera("CAM_HEAD", head + Vector((-22, -30, 10)), head, lens=50)
    cam_plan = make_camera("CAM_PLAN", (x_mid, -10, 400), (x_mid, -10, 0), ortho=span * 1.08)

    renders = {
        "render_overview.png": cam_over,
        "render_front.png": cam_front,
        "render_head.png": cam_head,
        "render_plan.png": cam_plan,
    }

    bpy.context.view_layer.update()
    silo_bounds = [world_bounds(o) for o in silos]
    noria_bounds = [world_bounds(o) for o in norias]
    pitches = [round(b["x"] - a["x"], 3) for a, b in zip(eq["silos"], eq["silos"][1:])]
    gaps = [clean((p * MM) - 2 * SILO_R) for p in pitches]
    capacity = sum(s["capacity"] for s in eq["silos"])

    checks = {
        "silo_count_matches": len(silos) == cfg.get("silos_count", len(silos)),
        "silo_centres_match_config": all(
            abs(o.location.x - s["x"] * MM) < 1e-6 for o, s in zip(silos, eq["silos"])),
        "silo_diameter_22m": all(abs((b[1][0] - b[0][0]) - 2 * SILO_R) < 0.5 for b in silo_bounds),
        "silos_do_not_touch": all(g > 0 for g in gaps),
        "noria_tube_top_matches_config": all(
            abs(b[1][2] - e["lift_height"] * MM) < 0.5 for b, e in zip(noria_bounds, eq["elevators"])),
        "capacity_matches_totals": capacity == cfg["totals"]["total_storage_capacity_m3"],
        "capacity_per_silo_is_catalog": all(s["capacity"] == CATALOG_CAPACITY_M3 for s in eq["silos"]),
    }
    measure = {
        "pass": all(checks.values()),
        "config": cfg_file.name,
        "source_blend": "blender/noria_01/noria_01.blend",
        "linked_not_redrawn": True,
        "silo_count": len(silos),
        "silo_centres_x_m": [clean(o.location.x) for o in silos],
        "silo_pitch_mm": pitches,
        "silo_clear_gap_m": gaps,
        "noria_count": len(norias),
        "noria_axes_m": [[clean(o.location.x), clean(o.location.y)] for o in norias],
        "noria_z_max_m_with_head": [clean(b[1][2]) for b in noria_bounds],
        "noria_y_from_config": False,
        "conveyor_lengths_m": [clean(abs(c["end_x"] - c["start_x"]) * MM) for c in eq["conveyors"]],
        "conveyor_z_m": [clean(c["start_y"] * MM) for c in eq["conveyors"]],
        "conveyor_casing_height_from_catalog": False,
        "pipe_count": len(pipes),
        "pipe_z_m": [[clean(p["from_y"] * MM), clean(p["to_y"] * MM)] for p in eq["pipes"]],
        "cross_duct_from_config": False,
        "supports_modelled": False,
        "total_capacity_m3": capacity,
        "checks": checks,
    }
    (out / "measure.json").write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")

    for name, cam in renders.items():
        render_still(scene, cam, out / name)

    bpy.ops.wm.save_as_mainfile(filepath=str(out / (cfg_file.stem + ".blend")), relative_remap=True)
    print("COMPLEX_PASS" if measure["pass"] else "COMPLEX_FAIL", out / "measure.json")
    return measure["pass"]


if __name__ == "__main__":
    ok = main()
    if not ok:
        sys.exit(1)
