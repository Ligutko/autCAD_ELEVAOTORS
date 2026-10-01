"""C1 frames: fan close-up and the whole aspiration unit (Cycles CPU, 960x540, 32 samples).

    $CLOUD_PY delegation/cloud/C1/render_c1.py fan|unit OUT.png
"""
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "world"))

from kit import aspiration as asp  # noqa: E402
from kit import common as c  # noqa: E402
from kit import components as comp  # noqa: E402

what, out = sys.argv[-2], sys.argv[-1]
c.reset_scene()
scene = bpy.context.scene
c.setup_render(scene, samples=32, res=(960, 540))
c.setup_sky(scene, 35, 215, 0.6)

grey = c.mat_painted("FAN_PAINT", (0.42, 0.45, 0.46), 0.35, grime=0.3)
dark = c.mat_painted("FAN_DARK", (0.20, 0.23, 0.24), 0.4)
blue = c.mat_painted("FAN_MOTOR", (0.05, 0.16, 0.35), 0.35)
galv = c.mat_galvanized("FAN_GALV", age=0.4, spangle_scale=60.0)
ground = bpy.data.objects.new("G", bpy.data.meshes.new("G"))
scene.collection.objects.link(ground)
ground.data.from_pydata([(-60, -60, 0), (60, -60, 0), (60, 60, 0), (-60, 60, 0)], [], [(0, 1, 2, 3)])
ground.data.materials.append(c.mat_concrete())

if what == "fan":
    r = comp.radial_fan(7.5)
    look = {"motor": blue, "frame": dark, "bolts": dark}
    for k, (v, f) in r["parts"].items():
        c.mesh_from_arrays("FAN_" + k, v, f, look.get(k, grey), smooth="quads" if k == "motor" else False)
    cam = c.camera("CAM", (-1.85, -2.3, 1.5), (0.22, -0.1, 0.5), lens=38)
else:
    site = json.loads((ROOT / "world/site/SITE.json").read_text(encoding="utf-8"))
    sysd = site["aspiration"]["systems"][0]
    b = next(x for x in site["aspiration"]["dust_bins"] if x["id"] == sysd["unit_at"])
    ry = sysd["riser_xy"][1]
    filt = c.mat_painted("ASP_FILTER", (0.80, 0.81, 0.80), 0.4, grime=0.35)
    look = {"bin_frame": (galv, False), "bin_shell": (galv, False), "bin_gate": (dark, False), "ladder": (galv, False),
            "ladder_rungs": (galv, "quads"), "bin_rest": (dark, False), "bin_rails": (c.mat_painted("YEL", (0.8, 0.55, 0.03), 0.45), "quads"),
            "bin_toes": (dark, False), "filter": (filt, "quads"), "fan": (grey, False), "fan_frame": (dark, False),
            "fan_motor": (blue, "quads")}
    parts = {**asp.build_bin(b, ry), **asp.build_unit(b, ry)}
    for k, data in parts.items():
        if data is not None:
            mat, smooth = look[k]
            c.mesh_from_arrays("U_" + k, *data, mat, smooth=smooth)
    cx, cy = b["center"]
    zt = asp.bin_top_z()
    cam = c.camera("CAM", (cx + 7.5, cy + 5.8, zt + 4.2), (cx + 0.1, cy - 0.3, zt + 2.3), lens=30)
c.render(scene, cam, out)
