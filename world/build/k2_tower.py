"""K2 test scene: noria tower H5 next to silo S2, positions from SITE.json.

Run:
    python world/build/k2_tower.py [--quick]
"""

import json
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import noria_n100 as nn  # noqa: E402
from kit import noria_tower as tower  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402

OUT = ROOT / "out" / "k2_tower"


def place(objs, offset):
    for o in objs.values():
        o.location = offset


def main():
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    spec = next(t for t in site["noria_towers"] if t["id"] == "H5")
    s2 = next(s for s in site["silos"] if s["id"] == "S2")
    scene = c.reset_scene()
    c.setup_render(scene, samples=24 if quick else 128, res=(960, 540) if quick else (1920, 1080))
    c.setup_sky(scene, sun_elevation_deg=34.0, sun_rotation_deg=130.0)

    t0 = time.time()
    dist = next(d for d in site["distribution"] if d["tower"] == spec["id"])
    t_objs, measure = tower.build(spec, distribution=dist)
    place(t_objs, (spec["x"], spec["y"], 0.0))
    s_objs, _ = silo.build()
    place(s_objs, (s2["x"], s2["y"], s2["z"]))
    measure["build_seconds"] = round(time.time() - t0, 1)

    for col in bpy.data.collections:          # labels are for explainer shots only
        if col.name.startswith("LABELS_"):
            col.hide_render = True
    v, f = c.box((-1500, -1500, -0.2), (1500, 1500, 0.0))
    c.mesh_from_arrays("GROUND", v, f, c.mat_ground())

    x, y = spec["x"], spec["y"]
    zh = measure["noria"]["head_pulley_z_m"]
    sx, sy, sz = dist["splitters"][0]["at"]              # site frame
    lx, ly = spec["access"]["x"], spec["access"]["y"]
    hx, hy = tower.noria_frame(spec)((nn.CX, nn.BELT_Y, zh))[:2] + (x, y)
    cams = {
        "k2_hero.png": c.camera("CAM_HERO", (x + 26, y - 30, 1.7), (x - 4, y, 14.0), lens=24),
        "k2_ladder.png": c.camera("CAM_LADDER", (lx - 1.2, ly + 4.6, 2.0), (lx, ly, 6.0), lens=20),   # the S2 wall is 1.2 m west of the tower
        "k2_head.png": c.camera("CAM_HEAD", (hx - 2.7, hy - 2.0, spec["top_z"] + 1.7), (hx, hy, zh - 0.1), lens=18),
        "k2_top_view.png": c.camera("CAM_DRONE", (x + 14, y - 16, 36.0), (x - 6, y, 22.0), lens=28),
        "k2_distribution.png": c.camera("CAM_DIST", (sx + 4.2, sy - 3.6, sz + 0.2), (sx - 0.2, sy - 0.2, sz - 0.9), lens=30),
    }
    (OUT / "measure.json").write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(measure, ensure_ascii=False))
    for name, cam in cams.items():
        t = time.time()
        c.render(scene, cam, OUT / name)
        print("rendered", name, round(time.time() - t, 1), "s", flush=True)


if __name__ == "__main__":
    main()
