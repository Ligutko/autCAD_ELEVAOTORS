"""C5 frames (Cycles, 960x540): the STRAHL FR axial fan alone, the roof fan A12 in its casing, the discharge A24
under the column (flaps, guides, cylinder, dry-grain screw A20).

    blender --background --python delegation/cloud/C5/render_c5.py -- unit|fan_top|discharge|low_fan OUT.png [gpu]

unit      - axial_fan(1.0, 22) in its local frame, shroud cut on the camera side (rotor, vanes, motor, bracket, tube);
fan_top   - the roof fan unit on the exhaust chamber, casing and louvre box cut on the camera side;
discharge - the dryer base from the west with the base wall, the hopper and the chamber walls cut away;
low_fan   - the recirculation fan A13 in the exhaust chamber, chamber cut away.
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

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[-2:]
what, out = args[0], args[1]
gpu = len(args) > 2 and args[2] == "gpu"
c.reset_scene()
scene = bpy.context.scene
c.setup_render(scene, samples=48, res=(960, 540))
c.setup_sky(scene, 35, 215, 0.6)
if gpu:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "OPTIX"
    scene.cycles.device = "GPU"

site = json.loads((ROOT / "world/site/SITE.json").read_text(encoding="utf-8"))
M = {
    "galv": c.mat_galvanized("C5_GALV", age=0.35, spangle_scale=60.0),
    "galv_old": c.mat_galvanized("C5_GALV_OLD", age=0.6, spangle_scale=50.0),
    "dark": c.mat_painted("C5_DARK", (0.20, 0.23, 0.24), 0.4),
    "motor": c.mat_painted("C5_MOTOR", (0.05, 0.16, 0.35), 0.35),
    "yellow": c.mat_painted("C5_YELLOW", (0.80, 0.55, 0.03), 0.45),
    "red": c.mat_painted("C5_RED", (0.55, 0.06, 0.04), 0.45),
    "concrete": c.mat_concrete("C5_CONCRETE"),
    "grating": c.mat_galvanized("C5_GRATING", age=0.5),
}


def light(name, loc, energy, size=0.4):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy
    ld.shadow_soft_size = size
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    scene.collection.objects.link(lo)


def ground(z, half=60.0):
    g = bpy.data.objects.new("G", bpy.data.meshes.new("G"))
    scene.collection.objects.link(g)
    g.data.from_pydata([(-half, -half, z), (half, -half, z), (half, half, z), (-half, half, z)], [], [(0, 1, 2, 3)])
    g.data.materials.append(M["concrete"])


def cut(piece, normal, origin):
    """Cut away the half on the `normal` side of a vertical plane through `origin` (plan)."""
    v = np.asarray(piece[0], float) - [origin[0], origin[1], 0.0]
    v, f = c.cut_mesh(v, piece[1], normal)
    return np.asarray(v) + [origin[0], origin[1], 0.0], f


def add(name, piece, mat, smooth=False):
    v, f = piece
    if len(np.asarray(v)) == 0:
        return
    c.mesh_from_arrays(name, v, f, M[mat], smooth=smooth)


if what == "unit":
    fan = comp.axial_fan(1.0, 22.0)
    mats = {"shroud": "galv", "rotor": "dark", "vanes": "galv", "bracket": "galv_old", "cooling": "galv_old"}
    for k, p in fan["parts"].items():
        if k == "motor":
            continue
        if k == "shroud":
            p = cut(p, (0.6, -1.0), (0.0, 0.0))
        add("F_" + k, p, mats[k])
    for k, p in fan["motor_parts"].items():
        add("M_" + k, p, "motor", smooth="quads")
    ground(-0.75)
    light("L1", (1.4, -1.8, 1.4), 220)
    light("L2", (-1.2, -1.0, -0.2), 90)
    cam = c.camera("CAM", (1.55, -2.35, 0.75), (0.0, 0.0, -0.05), lens=34)
else:
    from kit import drying as dr
    parts = dr.build_dryer(site)
    s = dr.section(site)
    z = s["z"]
    x0, y0, x1, y1 = dr.dryer_rect(site)
    cxm = (x0 + x1) / 2
    if what == "fan_top":
        fy = dr.fan_top_centre(site)
        keep = ("dryer_fans", "dryer_fan_top_shroud", "dryer_fan_top_rotor", "dryer_fan_top_motor", "dryer_fan_top_cooling",
                "dryer_chambers", "dryer_platform", "dryer_rails", "dryer_toes", "dryer_column", "dryer_hopper")
        for k in keep:
            mat, smooth, p = parts[k]
            if k in ("dryer_fans", "dryer_fan_top_shroud"):
                p = cut(p, (0.55, -1.0), (cxm, fy))
            add(k, p, mat, smooth="quads" if smooth else False)
        zc = z["chamber_roof"]
        light("L1", (cxm + 1.6, fy - 2.2, zc + 2.6), 300)
        light("L2", (cxm - 0.3, fy - 0.6, zc + 0.9), 60, 0.2)
        cam = c.camera("CAM", (cxm + 1.75, fy - 2.6, zc + 2.05), (cxm, fy, zc + 1.0), lens=30)
    elif what == "low_fan":
        ya, yb = s["exhaust"]
        for k, (mat, smooth, p) in parts.items():
            if not k.startswith(("dryer_fan_low", "dryer_column", "dryer_discharge", "dryer_flap", "dryer_hopper_dry",
                                 "dryer_pad", "dryer_doors", "dryer_screw")):
                continue
            if k == "dryer_column":
                p = cut(p, (-1.0, 0.0), (x0 + 0.06, 0.0))
            add(k, p, mat, smooth="quads" if smooth else False)
        light("L1", (x0 - 0.3, (ya + yb) / 2, 2.2), 250)
        light("L2", (x0 + 0.4, ya + 0.4, 1.6), 120)
        cam = c.camera("CAM", (x0 - 2.2, yb + 0.6, 2.3), (cxm, ya + 0.9, 0.85), lens=26)
    else:   # discharge
        ca, cb = s["column"]
        for k, (mat, smooth, p) in parts.items():
            if not k.startswith(("dryer_column", "dryer_discharge", "dryer_flap", "dryer_cylinder", "dryer_hopper_dry",
                                 "dryer_screw", "dryer_pad")):
                continue
            if k in ("dryer_column", "dryer_hopper_dry"):
                p = cut(p, (-1.0, 0.0), (x0 + 0.08, 0.0))
            add(k, p, mat, smooth="quads" if smooth else False)
        ym = (ca + cb) / 2
        light("L1", (x0 - 0.6, ca + 0.3, 2.6), 260)
        light("L2", (x0 + 1.2, cb - 0.2, 1.2), 140)
        light("L3", (x1 - 0.2, ca + 0.2, 1.4), 120)
        cam = c.camera("CAM", (x0 - 1.15, ca - 0.25, 2.55), (cxm + 0.35, ym, 1.45), lens=24)
c.render(scene, cam, out)
