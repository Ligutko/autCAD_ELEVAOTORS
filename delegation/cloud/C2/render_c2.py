"""C2 frames (Cycles, 960x540, 32 samples): the KA gearmotor close-up and the drive on a gallery with its E-stop.

    blender --background --python delegation/cloud/C2/render_c2.py -- unit|drive|gallery|tunnel OUT.png [gpu]

unit    - the component alone (local frame), for a look at the shape;
drive   - the T12 drive on the gallery, close (casing, gearmotor, torque arm and clevis, deck);
gallery - the T12 head end of the gallery with the walkway, rail and the E-stop station next to the drive;
tunnel  - the T13 tunnel drive.
"""
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "world"))

from kit import common as c  # noqa: E402
from kit import components as comp  # noqa: E402
from kit import gallery as gal  # noqa: E402

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

paint = c.mat_painted("GM_PAINT", (0.36, 0.40, 0.42), 0.38, grime=0.25)
dark = c.mat_painted("GM_DARK", (0.16, 0.17, 0.18), 0.45)
blue = c.mat_painted("GM_MOTOR", (0.05, 0.16, 0.35), 0.35)
galv = c.mat_galvanized("GM_GALV", age=0.4, spangle_scale=60.0)
rubber = c.mat_rubber()
site = json.loads((ROOT / "world/site/SITE.json").read_text(encoding="utf-8"))


def ground(z):
    g = bpy.data.objects.new("G", bpy.data.meshes.new("G"))
    scene.collection.objects.link(g)
    g.data.from_pydata([(-80, -80, z), (80, -80, z), (80, 80, z), (-80, 80, z)], [], [(0, 1, 2, 3)])
    g.data.materials.append(c.mat_concrete())


if what in ("unit", "unit2"):
    ground(-0.45)
    r = comp.shaft_gearmotor(15.0)
    look = {"case": paint, "ribs": paint, "covers": paint, "hollow_shaft": dark, "torque_arm": dark, "support": galv,
            "bearing": dark, "bolts": dark, "motor": blue}
    for k, (v, f) in r["parts"].items():
        c.mesh_from_arrays("GM_" + k, v, f, look[k], smooth="quads" if k == "motor" else False)
    if what == "unit":
        cam = c.camera("CAM", (-1.0, 1.9, 0.55), (0.32, -0.02, -0.08), lens=40)
    else:
        cam = c.camera("CAM", (0.9, -1.6, -0.2), (0.1, -0.1, -0.2), lens=35)
elif what in ("drive", "gallery"):
    from kit import controls as ctl  # noqa: F401,E402
    g = site["silo_top_galleries"]
    line = next(l for l in g["lines"] if l["id"] == "T12")
    parts = gal.silo_row_gallery(g, line)
    look = {"heavy": (dark, False), "light": (dark, False), "deck": (galv, False), "rails": (c.mat_painted("YEL", (0.8, 0.55, 0.03), 0.45), "quads"),
            "toes": (dark, False), "posts": (dark, False), "spouts": (galv, False), "gates": (galv, False),
            "conv_casing": (galv, False), "conv_flanges": (galv, False), "conv_drive": (paint, False), "conv_motor": (blue, "quads")}
    for k, data in parts.items():
        mat, sm = look[k]
        c.mesh_from_arrays("GAL_" + k, *data, mat, smooth=sm)
    hands, info = gal.build_controls(site, "T12")
    hl = {"estop": dark, "estop_red": c.mat_painted("RED", (0.7, 0.03, 0.02), 0.4), "estop_blue": blue,
          "estop_tag": c.mat_painted("TAG", (0.9, 0.9, 0.85), 0.5), "cord_switch": c.mat_painted("YELB", (0.85, 0.65, 0.05), 0.4)}
    for k, data in hands.items():
        c.mesh_from_arrays("H_" + k, *data, hl.get(k, dark))
    ground(14.5)
    hx, y, z = line["head_x"], line["row_y"], sum(g["conveyor"]["casing_z"]) / 2
    if what == "drive":
        cam = c.camera("CAM", (hx - 1.7, y + 1.55, z + 0.55), (hx - 0.35, y + 0.42, z - 0.12), lens=32)
    else:
        px, py, pz = info["post"]
        cam = c.camera("CAM", (hx - 4.6, y + 0.75, z + 1.05), (hx - 0.6, y + 0.3, z - 0.15), lens=24)
else:
    from kit import tunnel as tun  # noqa: E402
    t = next(t for t in site["tunnels"] if t["id"] == "T13")
    conv, _ = tun.build_conveyor(site, t, tun.boot_inlet(site, t))
    look = {"drive": paint, "motor": blue}
    for k, data in conv.items():
        c.mesh_from_arrays("TUN_" + k, *data, look.get(k, galv), smooth="quads" if k == "motor" else False)
    ground(t["floor_z"])
    cv = t["conveyor"]
    dx, y = cv["drive_x"], t["row_y"]
    cam = c.camera("CAM", (dx - 2.2, y + 1.15, -0.9), (dx - 0.3, y + 0.45, -1.45), lens=26)
    sun = bpy.data.lights.new("L", "POINT")
    sun.energy = 300
    lo = bpy.data.objects.new("L", sun)
    lo.location = (dx - 1.0, y + 0.9, -0.4)
    scene.collection.objects.link(lo)
c.render(scene, cam, out)
