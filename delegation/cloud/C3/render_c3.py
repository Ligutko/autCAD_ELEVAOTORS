"""C3 frames (Cycles, 960x540, 32 samples): the noria drive (Dodge TA6307H + belt drive + 22 kW motor) close up,
and the H6 tower top from a person's eye height.

    blender --background --python delegation/cloud/C3/render_c3.py -- unit|reducer|tower_top|back OUT.png [gpu]

unit      - the component alone (local frame), for a look at the shape;
reducer   - the H6 drive close up on the top platform (reducer, motor plate, guard, torque arm and its stand);
tower_top - the H6 top platform from 1.6 m above the deck: head, drive, E-stop station, rails;
back      - the H6 drive from the other side (torque arm, stand, shaft between the bearing and the hub).
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "world"))

from kit import common as c  # noqa: E402
from kit import components as comp  # noqa: E402
from kit import noria_tower as tower  # noqa: E402
from kit import noria_n100 as nn  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[-2:]
what, out = args[0], args[1]
gpu = len(args) > 2 and args[2] == "gpu"
c.reset_scene()
scene = bpy.context.scene
c.setup_render(scene, samples=32, res=(960, 540))
c.setup_sky(scene, 35, 215, 0.6)
if gpu:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "OPTIX"
    scene.cycles.device = "GPU"

site = json.loads((ROOT / "world/site/SITE.json").read_text(encoding="utf-8"))


def ground(z):
    g = bpy.data.objects.new("G", bpy.data.meshes.new("G"))
    scene.collection.objects.link(g)
    g.data.from_pydata([(-80, -80, z), (80, -80, z), (80, 80, z), (-80, 80, z)], [], [(0, 1, 2, 3)])
    g.data.materials.append(c.mat_concrete())


if what in ("unit", "unit_back", "unit_side"):
    paint = c.mat_painted("R_PAINT", (0.20, 0.23, 0.24), 0.4)
    blue = c.mat_painted("R_MOTOR", (0.05, 0.16, 0.35), 0.35)
    yellow = c.mat_painted("R_GUARD", (0.80, 0.55, 0.03), 0.45)
    galv = c.mat_galvanized("R_GALV", age=0.4, spangle_scale=60.0)
    r = comp.shaft_mount_reducer(22.0, output_rpm=61.1, floor_z=-1.385)
    for k, (v, f) in r["parts"].items():
        mat = {"motor": blue, "guard": yellow, "stand": galv}.get(k, paint)
        c.mesh_from_arrays("R_" + k, v, f, mat, smooth="quads" if k == "motor" else False)
    ground(-1.385)
    if what == "unit":
        cam = c.camera("CAM", (1.6, -2.4, 0.5), (-0.1, 0.2, -0.2), lens=30)
    elif what == "unit_back":
        cam = c.camera("CAM", (-1.5, 2.3, 0.4), (-0.1, 0.0, -0.25), lens=30)
    else:
        cam = c.camera("CAM", (-0.1, -3.2, 0.0), (-0.1, 0.0, -0.25), lens=35)
else:
    spec = next(t for t in site["noria_towers"] if t["id"] == "H6")
    objs, measure = tower.build(spec)
    for o in list(bpy.data.objects):
        if o.name.startswith("LBL_"):
            bpy.data.objects.remove(o, do_unlink=True)
    zt = spec["top_z"]
    ground(zt - 6.0)
    fr = tower.noria_frame(spec)
    parts, _, _, _ = tower.build_noria(spec)
    mv = fr(np.asarray(parts["motor"][0], float))
    mc = (mv.min(0) + mv.max(0)) / 2
    for nm, loc, e in (("L1", (mc[0] - 1.2, mc[1] - 1.0, zt + 2.6), 260), ("L2", (mc[0] + 1.5, mc[1] + 1.5, zt + 2.4), 160)):
        ld = bpy.data.lights.new(nm, "POINT")
        ld.energy = e
        ld.shadow_soft_size = 0.4
        lo = bpy.data.objects.new(nm, ld)
        lo.location = loc
        scene.collection.objects.link(lo)
    if what == "reducer":
        cam = c.camera("CAM", (mc[0] - 2.0, mc[1] - 1.9, zt + 1.75), (mc[0] + 0.1, mc[1] - 0.3, zt + 1.18), lens=24)
    elif what == "reducer2":
        cam = c.camera("CAM", (mc[0] - 1.6, mc[1] + 1.3, zt + 1.6), (mc[0] + 0.1, mc[1] - 0.25, zt + 1.0), lens=26)
    elif what == "back":
        cam = c.camera("CAM", (mc[0] - 1.3, mc[1] + 1.8, zt + 1.3), (mc[0] + 0.1, mc[1] - 0.2, zt + 0.8), lens=28)
    else:
        hx, hy = spec["size"][0] / 2, spec["size"][1] / 2
        cam = c.camera("CAM", (-hx + 0.35, -hy + 0.35, zt + 1.6), (mc[0] + 0.4, mc[1] + 0.6, zt + 0.9), lens=22)
c.render(scene, cam, out)
