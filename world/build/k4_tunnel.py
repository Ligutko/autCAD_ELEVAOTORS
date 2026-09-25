"""K4 test scene: tunnels T13 and T16 under silo row 3-6 with tower H6, positions from SITE.json.

Run:
    blender --background --python world/build/k4_tunnel.py [-- --quick]
"""

import json
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import noria_tower as tower  # noqa: E402
from kit import tunnel as tun  # noqa: E402

OUT = ROOT / "out" / "k4_tunnel"


def point_light(name, loc, energy, size=0.2, color=(1.0, 0.93, 0.82)):
    data = bpy.data.lights.new(name, type="POINT")
    data.energy = energy
    data.shadow_soft_size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    return obj


def main():
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    spec = next(t for t in site["noria_towers"] if t["id"] == "H6")
    tunnels = [t for t in site["tunnels"] if t["tower"] == "H6"]
    scene = c.reset_scene()
    c.setup_render(scene, samples=24 if quick else 128, res=(960, 540) if quick else (1920, 1080))
    c.setup_sky(scene, sun_elevation_deg=34.0, sun_rotation_deg=130.0)
    t0 = time.time()
    openings = [tun.pit_opening(site, t) for t in tunnels]
    objs, _ = tower.build(spec, openings=openings)
    for o in objs.values():
        o.location = (spec["x"], spec["y"], 0.0)
    measures, holes = {}, []
    for t in tunnels:
        _, m, anchors = tun.build(site, t)
        measures[t["id"]] = m
        holes += tun.footprint(site, t)
        for k, p in enumerate(anchors["lamps"]):
            point_light(f"{t['id']}_LAMP_{k}", p, 120.0)
    x0, y0, x1, y1 = tower.pit_inner(spec)
    w = spec["pit"]["wall_t"]
    holes.append((spec["x"] + x0 - w, spec["y"] + y0 - w, spec["x"] + x1 + w, spec["y"] + y1 + w))
    v, f = tun.ground_cells(1500, holes)
    c.mesh_from_arrays("GROUND", v, f, c.mat_ground())
    for col in bpy.data.collections:
        if col.name.startswith("LABELS_"):
            col.hide_render = True
    point_light("PIT_WORK_LAMP", (spec["x"] + 1.3, spec["y"] + 1.2, -3.6), 150.0)
    build_s = round(time.time() - t0, 1)

    row = site["tunnels"][1]["row_y"]
    inlet = measures["T13"]["spout_end"]
    cams = {
        "k4_tunnel_walk.png": c.camera("CAM_WALK", (-27.0, row + 0.78, -0.2), (-45.0, row + 0.1, -1.2), lens=18),
        "k4_gate_stack.png": c.camera("CAM_GATE", (-13.3, row + 0.95, -0.35), (-14.5, row, -0.55), lens=16),
        "k4_boot_inlet.png": c.camera("CAM_BOOT", (1.55, row + 2.75, -2.75), tuple(inlet), lens=14),
    }
    (OUT / "measure.json").write_text(json.dumps({"build_seconds": build_s, "tunnels": measures},
                                                 ensure_ascii=False, indent=2), encoding="utf-8")
    for name, cam in cams.items():
        t = time.time()
        c.render(scene, cam, OUT / name)
        print("rendered", name, round(time.time() - t, 1), "s", flush=True)


if __name__ == "__main__":
    main()
