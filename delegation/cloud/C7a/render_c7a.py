"""C7a frames (Cycles, 960x540): silo roof fan in section, sweep centre drive in section, sweep tractor.

    blender --background --python delegation/cloud/C7a/render_c7a.py -- roof_fan|roof_fan_close|sweep_drive|tractor OUT.png [gpu]

roof_fan    - silo exterior (kit.silo_msvu220.build, detail full), cut by a vertical plane through the axis of a roof fan:
              casing, impeller, finger guard, motor and foot plate under the roof;
sweep_drive - interior (kit.silo_interior.build, detail full) cut through the centre: housing frame, lids, panels, motor,
              couplings, reducer, bevel box on the slewing ring;
tractor     - the same interior from behind the parked arm: wheel, cheek plates, worm reducer, motor, counterweights.
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "world"))

from kit import common as c  # noqa: E402
from kit import silo_interior as si  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[-2:]
what, out = args[0], args[1]
gpu = len(args) > 2 and args[2] == "gpu"
c.reset_scene()
scene = bpy.context.scene
c.setup_render(scene, samples=64, res=(960, 540))
c.setup_sky(scene, 40, 215, 0.8)
if gpu:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "OPTIX"
    scene.cycles.device = "GPU"


def light(name, loc, energy, size=0.3, kind="POINT"):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    if kind == "POINT":
        ld.shadow_soft_size = size
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    scene.collection.objects.link(lo)


def ground(z, half=60.0):
    g = bpy.data.objects.new("G", bpy.data.meshes.new("G"))
    scene.collection.objects.link(g)
    g.data.from_pydata([(-half, -half, z), (half, -half, z), (half, half, z), (-half, half, z)], [], [(0, 1, 2, 3)])
    g.data.materials.append(c.mat_ground())


if what in ("roof_fan", "roof_fan_close"):
    _orig = silo.build_roof_vents
    silo.build_roof_vents = lambda ops, **kw: _orig(ops, detail="full", **kw)       # full detail for the frame
    fan = next(o for o in silo.roof_openings() if o["kind"] == "fan_vent")
    th = math.radians(fan["deg"])
    radial = np.array([math.cos(th), math.sin(th)])
    nrm = np.array([-math.sin(th), math.cos(th)])
    silo.build(cut=tuple(nrm), with_foundation=False)
    ground(-0.5)
    zc = silo.roof_z(fan["r"])
    tgt = np.array([fan["x"], fan["y"], zc - 0.05])
    if what == "roof_fan":
        cam = c.camera("CAM", tuple(tgt + np.array([*(nrm * 3.2 - radial * 0.8), 0.9])), tuple(tgt + [0, 0, 0.12]), lens=38)
    else:                                                                            # impeller, throat and motor close up
        cam = c.camera("CAM", tuple(tgt + np.array([*(nrm * 1.0 - radial * 0.25), 0.55])), tuple(tgt + [0, 0, -0.1]), lens=45)
    light("L1", tuple(tgt + np.array([*(nrm * 0.9), -0.2])), 40, 0.15)
elif what == "sweep_drive":
    si.build(fill=0.0, cut=(0.0, 1.0), detail="full")
    cam = c.camera("CAM", (-1.2, 3.1, 1.55), (0.0, 0.0, 0.85), lens=30)
    light("L1", (0.0, 1.2, 1.2), 90, 0.15)
else:
    d = np.array([math.cos(math.radians(si.SWEEP_ANGLE)), math.sin(math.radians(si.SWEEP_ANGLE))])
    n = np.array([-d[1], d[0]])
    p = d * (si.SWEEP["tractor"]["at_frac"] * si.SWEEP_LEN)
    si.build(fill=0.0, detail="full")
    tgt = np.array([*(p + n * -0.42), 0.26])
    cam = c.camera("CAM", tuple(tgt + np.array([*(-n * 1.0 - d * 1.7), 0.5])), tuple(tgt), lens=28)
    light("L1", tuple(tgt + np.array([*(-n * 1.0), 0.9])), 80, 0.2)

bpy.context.view_layer.update()
c.render(scene, cam, out)
print("rendered", out)
