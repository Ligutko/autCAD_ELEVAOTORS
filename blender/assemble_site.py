"""Збирач майданчика: SITE.json -> сцена лише з деталей кіта -> QA -> кадри.

SLICE-5/6 з PRD_3D_PIPELINE.md:
- світ ставить тільки деталі з `blender/kit` (REGISTRY); немає типу — FAIL з назвою;
- світ не змінює розміри деталі (поле `params` заборонене);
- після збірки QA міряє саму сцену (вершини екземплярів через depsgraph),
  а не константи зі SITE.json, і ловить: силос під землею, перетин силосів,
  норію всередині силоса, зсув позиції, зламану деталь кіта;
- лише при PASS рендерить кадри і зберігає blend.

Запуск:
    blender --background --factory-startup --python blender/assemble_site.py -- blender/site/SITE_tech_2024_06_06.json
    python blender/assemble_site.py blender/site/SITE_tech_2024_06_06.json      # модуль bpy 4.5
Ключі після шляху: --no-render, --out <тека>, --engine EEVEE|CYCLES|WORKBENCH, --samples N

Вихід (за замовчуванням blender/site/out/<site_id>/):
    qa.json, build_report.md, render_*.png, <site_id>.blend
Код виходу: 0 — SITE_PASS, 2 — SITE_FAIL.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

from kit import REGISTRY, common  # noqa: E402

TOL_POS_M = 0.001
TOL_DIM_M = 0.001
MIN_SILO_GAP_M = 0.5
GROUND_HALF_M = 90.0
ALLOWED_NODE_KEYS = {"id", "type", "x_m", "y_m", "z_m", "rot_deg", "cards", "note", "below_grade_m"}


# ---------------------------------------------------------------- аргументи


def parse_args(argv: list[str]) -> dict:
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = argv[1:]
    opts = {"site": None, "render": True, "out": None, "engine": "EEVEE", "samples": 16}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--no-render":
            opts["render"] = False
        elif arg == "--out":
            opts["out"] = Path(argv[i + 1])
            i += 1
        elif arg == "--engine":
            opts["engine"] = argv[i + 1].upper()
            i += 1
        elif arg == "--samples":
            opts["samples"] = int(argv[i + 1])
            i += 1
        elif opts["site"] is None:
            opts["site"] = Path(arg)
        i += 1
    if opts["site"] is None:
        raise SystemExit("usage: assemble_site.py SITE.json [--no-render] [--out DIR] [--engine E] [--samples N]")
    return opts


# ---------------------------------------------------------------- схема


def validate_schema(site: dict) -> list[str]:
    problems = []
    for key in ("site_id", "nodes"):
        if key not in site:
            problems.append(f"немає поля {key}")
    if problems:
        return problems
    if site.get("units") != "m":
        problems.append(f"units = {site.get('units')!r}, очікується 'm'")
    seen = set()
    for node in site["nodes"]:
        nid = node.get("id")
        if not nid:
            problems.append("вузол без id")
            continue
        if nid in seen:
            problems.append(f"id {nid} повторюється")
        seen.add(nid)
        extra = set(node) - ALLOWED_NODE_KEYS
        if "params" in extra:
            problems.append(f"{nid}: світ не змінює розміри деталі кіта (params={node['params']})")
            extra.discard("params")
        if extra:
            problems.append(f"{nid}: невідомі поля {sorted(extra)}")
        if node.get("type") not in REGISTRY:
            problems.append(f"{nid}: немає деталі кіта «{node.get('type')}». У кіті: {sorted(REGISTRY)}")
        for key in ("x_m", "y_m", "z_m", "rot_deg"):
            value = node.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(f"{nid}: {key} не число")
    return problems


# ---------------------------------------------------------------- збірка


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"
    return scene


def build_world(site: dict, scene) -> dict:
    kit_root = bpy.data.collections.new("KIT")
    scene.collection.children.link(kit_root)
    world = bpy.data.collections.new("WORLD")
    scene.collection.children.link(world)
    built = {}
    for node in site["nodes"]:
        module = REGISTRY[node["type"]]
        if module.COLLECTION not in built:
            module.build()
            kit_coll = bpy.data.collections[module.COLLECTION]
            if kit_coll.name not in kit_root.children:
                kit_root.children.link(kit_coll)
            built[module.COLLECTION] = kit_coll
        empty = bpy.data.objects.new(node["id"], None)
        empty.instance_type = "COLLECTION"
        empty.instance_collection = built[module.COLLECTION]
        empty.location = (node["x_m"], node["y_m"], node["z_m"])
        empty.rotation_euler = (0.0, 0.0, math.radians(node["rot_deg"]))
        empty["site_type"] = node["type"]
        empty["cards"] = ",".join(node.get("cards", []))
        world.objects.link(empty)
    # Деталі кіта існують у файлі, але в кадр потрапляють лише екземпляри.
    layer_coll = bpy.context.view_layer.layer_collection.children["KIT"]
    layer_coll.exclude = True

    ground_mat = common.Builder(world).material("GroundConcrete", (0.60, 0.61, 0.58), 0.9)
    common.Builder(world).new_mesh(
        "GROUND",
        lambda bm: common.add_box(bm, -GROUND_HALF_M + 38.0, GROUND_HALF_M + 38.0, -60.0, 85.0, -0.04, -0.02),
        ground_mat,
    )
    return built


# ---------------------------------------------------------------- вимірювання


def instance_points(depsgraph, parent_name: str, name_filter=None) -> np.ndarray:
    """Світові вершини всіх мешів, які depsgraph показує як екземпляри цього вузла."""
    chunks = []
    for inst in depsgraph.object_instances:
        if not inst.is_instance or inst.parent is None or inst.parent.original.name != parent_name:
            continue
        obj = inst.object
        if obj.type != "MESH":
            continue
        if name_filter and not name_filter(obj.original.name):
            continue
        mesh = obj.original.data
        n = len(mesh.vertices)
        if n == 0:
            continue
        co = np.empty(n * 3, dtype=np.float64)
        mesh.vertices.foreach_get("co", co)
        co = co.reshape(n, 3)
        mat = np.array(inst.matrix_world)
        chunks.append(co @ mat[:3, :3].T + mat[:3, 3])
    if not chunks:
        return np.empty((0, 3))
    return np.vstack(chunks)


def measure(site: dict, scene) -> dict:
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    nodes = {}
    for node in site["nodes"]:
        nid = node["id"]
        entry = {"type": node["type"]}
        if node["type"] == "silo_msvu_220":
            wall = instance_points(depsgraph, nid, lambda n: n.startswith("SILO_RING_"))
            roof = instance_points(depsgraph, nid, lambda n: n.startswith("SILO_ROOF_"))
            allp = instance_points(depsgraph, nid)
            if len(wall) == 0:
                entry["error"] = "немає стіни в екземплярі"
            else:
                cx = float((wall[:, 0].max() + wall[:, 0].min()) / 2.0)
                cy = float((wall[:, 1].max() + wall[:, 1].min()) / 2.0)
                radii = np.hypot(wall[:, 0] - cx, wall[:, 1] - cy)
                apex = roof[np.argmax(roof[:, 2])]
                rim = roof[np.argmax(np.hypot(roof[:, 0] - cx, roof[:, 1] - cy))]
                slope = math.degrees(
                    math.atan2(apex[2] - rim[2], math.hypot(rim[0] - apex[0], rim[1] - apex[1]))
                )
                entry.update(
                    {
                        "center_m": [common.clean(cx), common.clean(cy)],
                        "outer_diameter_m": common.clean(2.0 * radii.max()),
                        "wall_z_min_m": common.clean(wall[:, 2].min()),
                        "wall_z_max_m": common.clean(wall[:, 2].max()),
                        "roof_peak_z_m": common.clean(roof[:, 2].max()),
                        "roof_slope_deg": common.clean(slope),
                        "z_min_m": common.clean(allp[:, 2].min()),
                        "z_max_m": common.clean(allp[:, 2].max()),
                        "footprint_radius_m": common.clean(
                            np.hypot(allp[:, 0] - cx, allp[:, 1] - cy).max()
                        ),
                    }
                )
        elif node["type"] == "noria_n100":
            tube = instance_points(depsgraph, nid, lambda n: n.startswith("NORIA_SHEET_"))
            # Вісь — за барабанами: труба навмисно без передньої стінки (розріз).
            drums = instance_points(depsgraph, nid, lambda n: n.endswith("_DRUM"))
            allp = instance_points(depsgraph, nid)
            if len(tube) == 0 or len(drums) == 0:
                entry["error"] = "немає труби або барабанів в екземплярі"
            else:
                entry.update(
                    {
                        "center_m": [
                            common.clean((drums[:, 0].max() + drums[:, 0].min()) / 2.0),
                            common.clean((drums[:, 1].max() + drums[:, 1].min()) / 2.0),
                        ],
                        "tube_z_min_m": common.clean(tube[:, 2].min()),
                        "tube_z_max_m": common.clean(tube[:, 2].max()),
                        "tube_height_m": common.clean(tube[:, 2].max() - tube[:, 2].min()),
                        "z_min_m": common.clean(allp[:, 2].min()),
                        "z_max_m": common.clean(allp[:, 2].max()),
                        "bbox_xy_m": [
                            common.clean(allp[:, 0].min()),
                            common.clean(allp[:, 1].min()),
                            common.clean(allp[:, 0].max()),
                            common.clean(allp[:, 1].max()),
                        ],
                    }
                )
        nodes[nid] = entry
    return nodes


def kit_counts() -> dict:
    counts = {}
    for module in REGISTRY.values():
        coll = bpy.data.collections.get(module.COLLECTION)
        if coll is None:
            continue
        names = [o.name for o in coll.objects]
        counts[module.TYPE] = {
            "objects": len(names),
            "rings": sum(n.startswith("SILO_RING_") for n in names),
            "bolt_heads": sum(n.startswith("SILO_BOLT_") and not n.endswith("_BODY") for n in names),
            "roof_sectors": sum(n.startswith("SILO_ROOF_") for n in names),
            "tube_courses": sum(n.startswith("NORIA_SHEET_") for n in names),
        }
    return counts


def qa(site: dict, measured: dict, counts: dict) -> list[str]:
    problems = []
    by_id = {n["id"]: n for n in site["nodes"]}
    ground = float(site.get("ground_z_m", 0.0))
    # 1. Кожен вузол зібраний і лише з кіта.
    world = bpy.data.collections["WORLD"]
    for obj in world.objects:
        if obj.type == "MESH" and obj.name != "GROUND":
            problems.append(f"у світі меш поза кітом: {obj.name}")
        if obj.type == "EMPTY" and obj.name not in by_id:
            problems.append(f"у світі зайвий вузол {obj.name}")
    for nid in by_id:
        if nid not in world.objects:
            problems.append(f"{nid} не зібраний")
    # 2. Цілісність деталей кіта.
    silo_kit = counts.get("silo_msvu_220")
    if silo_kit and (silo_kit["rings"] != 13 or silo_kit["bolt_heads"] != 52 or silo_kit["roof_sectors"] != 8):
        problems.append(f"деталь silo_msvu_220 не та: {silo_kit}")
    noria_kit = counts.get("noria_n100")
    if noria_kit and noria_kit["tube_courses"] != 33:
        problems.append(f"деталь noria_n100 не та: {noria_kit}")
    silos = []
    for nid, m in measured.items():
        node = by_id[nid]
        if "error" in m:
            problems.append(f"{nid}: {m['error']}")
            continue
        # 3. Позиція в сцені = позиція в SITE.
        dx = m["center_m"][0] - node["x_m"]
        dy = m["center_m"][1] - node["y_m"]
        if math.hypot(dx, dy) > TOL_POS_M:
            problems.append(f"{nid}: центр {m['center_m']} замість ({node['x_m']}, {node['y_m']})")
        # 4. Нічого під землею без оголошеного приямку.
        below = float(node.get("below_grade_m", 0.0))
        if m["z_min_m"] < ground - below - TOL_DIM_M:
            problems.append(
                f"{nid}: низ на {m['z_min_m']:.3f} м, нижче землі {ground:.3f} м"
                + (f" і дозволеного приямку {below:.3f} м" if below else "")
            )
        if below and abs(m["z_min_m"] - (ground - below)) > TOL_DIM_M:
            problems.append(f"{nid}: приямок оголошено {below} м, низ деталі на {m['z_min_m']:.3f} м")
        if node["type"] == "silo_msvu_220":
            if abs(m["outer_diameter_m"] - 22.0) > TOL_DIM_M:
                problems.append(f"{nid}: діаметр {m['outer_diameter_m']}")
            if abs(m["wall_z_max_m"] - m["wall_z_min_m"] - 14.976) > TOL_DIM_M:
                problems.append(f"{nid}: висота стіни {m['wall_z_max_m'] - m['wall_z_min_m']:.4f}")
            if abs(m["roof_slope_deg"] - 30.0) > 0.25:
                problems.append(f"{nid}: ухил даху {m['roof_slope_deg']}")
            silos.append((nid, m))
        if node["type"] == "noria_n100" and abs(m["tube_height_m"] - 33.0) > 0.01:
            problems.append(f"{nid}: труба {m['tube_height_m']} м")
    # 5. Силоси не перетинаються.
    pairs = []
    for i in range(len(silos)):
        for j in range(i + 1, len(silos)):
            (a, ma), (b, mb) = silos[i], silos[j]
            dist = math.hypot(ma["center_m"][0] - mb["center_m"][0], ma["center_m"][1] - mb["center_m"][1])
            gap = dist - ma["footprint_radius_m"] - mb["footprint_radius_m"]
            pairs.append((gap, a, b))
            if gap < MIN_SILO_GAP_M:
                problems.append(f"{a} і {b}: зазор {gap:.3f} м < {MIN_SILO_GAP_M} м")
    # 6. Інші вузли не заходять у коло силоса.
    for nid, m in measured.items():
        if by_id[nid]["type"] == "silo_msvu_220" or "bbox_xy_m" not in m:
            continue
        x0, y0, x1, y1 = m["bbox_xy_m"]
        for sid, ms in silos:
            cx, cy = ms["center_m"]
            nx = min(max(cx, x0), x1)
            ny = min(max(cy, y0), y1)
            if math.hypot(nx - cx, ny - cy) < ms["footprint_radius_m"]:
                problems.append(f"{nid} заходить у силос {sid}")
    return problems


# ---------------------------------------------------------------- кадри


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_camera(scene, name, location, target, lens=None, ortho_scale=None):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = Vector(location)
    look_at(obj, target)
    data.clip_start = 0.1
    data.clip_end = 600.0
    if ortho_scale:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    else:
        data.lens = lens
    return obj


def add_sun(scene, name, location, target, energy):
    data = bpy.data.lights.new(name, type="SUN")
    data.energy = energy
    data.angle = math.radians(1.5)
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = Vector(location)
    look_at(obj, target)
    return obj


def add_label(scene, camera, text):
    """Напис у верхньому лівому куті кадру: текст на відстані 1 м перед камерою."""
    depth = 1.0
    half_w = depth * (camera.data.sensor_width * 0.5) / camera.data.lens
    half_h = half_w * 720.0 / 1280.0
    size = half_h * 2.0 / 30.0
    offset = (-half_w * 0.95, half_h * 0.92, -depth)

    curve = bpy.data.curves.new(camera.name + "_LABEL", type="FONT")
    curve.body = text
    curve.size = size
    curve.align_x = "LEFT"
    curve.align_y = "TOP"
    curve.space_line = 1.15
    curve.font = common.load_font()
    obj = bpy.data.objects.new(camera.name + "_LABEL", curve)
    scene.collection.objects.link(obj)
    mat = bpy.data.materials.new("LabelInk")
    mat.use_nodes = True
    emit = mat.node_tree.nodes.new("ShaderNodeEmission")
    emit.inputs[0].default_value = (0.02, 0.02, 0.03, 1.0)
    out = next(n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL")
    mat.node_tree.links.new(emit.outputs[0], out.inputs[0])
    curve.materials.append(mat)
    obj.parent = camera
    obj.location = offset
    obj.visible_shadow = False
    obj.hide_render = True
    return obj


def setup_render(scene, engine: str, samples: int):
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("SITE_WORLD")
    scene.world.use_nodes = True
    bg = next(n for n in scene.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.62, 0.70, 0.78, 1.0)
    bg.inputs[1].default_value = 0.9
    if engine == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = True
    elif engine == "WORKBENCH":
        scene.render.engine = "BLENDER_WORKBENCH"
        scene.display.shading.light = "STUDIO"
        scene.display.shading.color_type = "MATERIAL"
        scene.display.shading.show_cavity = True
        scene.display.shading.show_shadows = True
    else:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
        scene.eevee.taa_render_samples = samples
    if "Standard" in {i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items}:
        scene.view_settings.view_transform = "Standard"


def render_frames(site: dict, scene, out: Path, engine: str, samples: int) -> list[str]:
    setup_render(scene, engine, samples)
    add_sun(scene, "SUN_KEY", (70.0, -60.0, 90.0), (38.0, 12.0, 0.0), 3.6)
    add_sun(scene, "SUN_FILL", (-40.0, 60.0, 50.0), (38.0, 12.0, 0.0), 1.1)
    xs = [n["x_m"] for n in site["nodes"]]
    ys = [n["y_m"] for n in site["nodes"]]
    cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
    span = max(max(xs) - min(xs), max(ys) - min(ys)) + 30.0
    pending = len(site.get("pending", []))
    status = site.get("status", "unverified")
    text = (
        f"{site.get('title', site['site_id'])}\n"
        f"вузлів зібрано з кіта: {len(site['nodes'])}; ще без деталі кіта: {pending}\n"
        f"картки: {status} — чернетка до затвердження фактів\n"
        "розміри силоса і норії — з кіта (SILO-WAVE, NORIA-1), позиції — з плану арк. 2"
    )
    shots = [
        ("render_overview.png", add_camera(scene, "CAM_OVERVIEW", (cx - 38.0, cy - 95.0, 55.0), (cx, cy, 6.0), lens=30.0), True),
        ("render_ground.png", add_camera(scene, "CAM_GROUND", (cx + 58.0, cy - 60.0, 1.7), (cx - 5.0, cy + 5.0, 12.0), lens=22.0), True),
        ("render_plan.png", add_camera(scene, "CAM_PLAN", (cx, cy, 120.0), (cx, cy, 0.0), ortho_scale=span * 1.12), False),
    ]
    written = []
    for filename, camera, with_label in shots:
        label = None
        if with_label:
            label = add_label(scene, camera, text)
            label.hide_render = False
        scene.camera = camera
        scene.render.filepath = str(out / filename)
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"RENDER {filename} {time.time() - t0:.1f}s")
        if label:
            label.hide_render = True
        written.append(filename)
    return written


# ---------------------------------------------------------------- головне


def write_outputs(out: Path, report: dict):
    out.mkdir(parents=True, exist_ok=True)
    (out / "qa.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        f"blender/site/out/{report['site_id']}/qa.json",
        "",
        f"{'SITE_PASS' if report['pass'] else 'SITE_FAIL'}. SITE: `{report['site_file']}`.",
        f"Зібрано вузлів: {len(report.get('measured', {}))}. Без деталі кіта (pending): {report.get('pending_count', 0)}.",
    ]
    if report["problems"]:
        lines += ["", "Проблеми:"] + [f"- {p}" for p in report["problems"]]
    lines += ["", "Картки: усі unverified. FACTS.json не читався і не створювався."]
    (out / "build_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    opts = parse_args(sys.argv)
    site_path = opts["site"].resolve()
    site = json.loads(site_path.read_text(encoding="utf-8"))
    site_id = site.get("site_id", site_path.stem)
    out = (opts["out"] or HERE / "site" / "out" / site_id).resolve()
    try:
        site_file = str(site_path.relative_to(HERE.parent))
    except ValueError:
        site_file = str(site_path)
    report = {
        "site_id": site_id,
        "site_file": site_file,
        "pass": False,
        "stage": "schema",
        "problems": [],
        "pending_count": len(site.get("pending", [])),
    }
    problems = validate_schema(site)
    if problems:
        report["problems"] = problems
        write_outputs(out, report)
        print("SITE_PROBLEMS " + " | ".join(problems))
        print("SITE_FAIL")
        return 2
    scene = reset_scene()
    t0 = time.time()
    build_world(site, scene)
    report["build_s"] = round(time.time() - t0, 1)
    report["stage"] = "scene"
    measured = measure(site, scene)
    counts = kit_counts()
    problems = qa(site, measured, counts)
    report.update({"measured": measured, "kit": counts, "problems": problems, "pass": not problems})
    report["kit_provenance"] = {
        t: REGISTRY[t].SPEC["provenance"] for t in sorted({n["type"] for n in site["nodes"]})
    }
    if problems:
        write_outputs(out, report)
        print("SITE_PROBLEMS " + " | ".join(problems))
        print("SITE_FAIL")
        return 2
    if opts["render"]:
        out.mkdir(parents=True, exist_ok=True)
        report["renders"] = render_frames(site, scene, out, opts["engine"], opts["samples"])
        report["render_engine"] = scene.render.engine
        for name in report["renders"]:
            if (out / name).stat().st_size < 20000:
                report["problems"].append(f"кадр {name} порожній")
        report["pass"] = not report["problems"]
        if report["pass"]:
            blend = out / f"{site_id}.blend"
            bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
            backup = blend.with_suffix(".blend1")
            if backup.exists():
                backup.unlink()
            report["blend"] = blend.name
    write_outputs(out, report)
    print("SITE_MEASURE " + json.dumps({k: v for k, v in measured.items()}, ensure_ascii=False))
    print("SITE_PASS" if report["pass"] else "SITE_FAIL")
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    try:
        code = main()
    except SystemExit:
        raise
    except Exception as exc:  # збірка не мовчить
        import traceback

        traceback.print_exc()
        print("SITE_FAIL", repr(exc))
        code = 2
    sys.exit(code)
