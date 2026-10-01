"""C0 probe: two rigs from world/kit/trucks.py (laden, and tipped 44.5 deg), 8 m apart, Cycles CPU, 32 spl, 960x540.

Run: python delegation/cloud/probe/render_truck.py      (pip bpy)
  or blender --background --python delegation/cloud/probe/render_truck.py
"""
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers mathutils
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "world"))

from kit import common as c  # noqa: E402
from kit import trucks as tr  # noqa: E402

OUT = Path(__file__).resolve().parent / "truck.png"
PAINT = {"red": (0.55, 0.05, 0.04), "white": (0.80, 0.80, 0.78), "blue": (0.05, 0.12, 0.45)}
DARK = (0.03, 0.03, 0.03)
STEEL = (0.35, 0.36, 0.38)


def colour_for(name, cab):
    if name in ("tractor_cab",):
        return PAINT[cab], 0.35
    if name.endswith(("tyres", "glass", "lamps", "grille")):
        return DARK, 0.6
    if name == "trailer_grain":
        return (0.62, 0.48, 0.16), 0.9
    if name in ("trailer_body", "trailer_door", "trailer_tarp"):
        return (0.70, 0.70, 0.68), 0.45
    return STEEL, 0.5


def place(rig, offset_y, cab):
    mats = {}
    for name, (verts, faces) in rig["parts"].items():
        col, rough = colour_for(name, cab)
        key = (col, rough)
        if key not in mats:
            mats[key] = c.mat_painted(f"M{len(mats)}", col, roughness=rough)
        obj = c.mesh_from_arrays(f"{cab}_{name}", verts, faces, material=mats[key], smooth="quads")
        obj.location = Vector((0.0, offset_y, c.ground_z() * 0))


def main():
    t0 = time.time()
    scene = c.reset_scene()
    c.setup_render(scene, samples=32, res=(960, 540))
    c.setup_sky(scene, sun_elevation_deg=35.0, sun_rotation_deg=150.0)
    a = tr.rig(0.0, load=0.9)
    b = tr.rig(44.5, variant=1)
    place(a, 0.0, a["dims"]["cab_colour"])
    place(b, 8.0, b["dims"]["cab_colour"])
    plane = c.mesh_from_arrays("GROUND", [(-60, -40, 0), (60, -40, 0), (60, 40, 0), (-60, 40, 0)], np.array([[0, 1, 2, 3]]),
                               material=c.mat_asphalt())
    cam = c.camera("CAM", (-20.0, -22.0, 7.5), (-3.0, 4.0, 2.2), lens=32.0)
    t1 = time.time()
    c.render(scene, cam, OUT)
    print(f"BUILD {t1 - t0:.1f} s  RENDER {time.time() - t1:.1f} s  -> {OUT}")


if __name__ == "__main__":
    main()
