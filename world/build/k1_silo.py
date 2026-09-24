"""K1 test scene: one silo МСВУ 220 on gravel under a physical sky.

Run:
    python world/build/k1_silo.py [--quick]
    blender --background --factory-startup --python world/build/k1_silo.py -- [--quick]
"""

import json
import sys
import time
from pathlib import Path

import bpy  # noqa: F401,I001  bpy first: the pip module registers bmesh and mathutils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402

OUT = ROOT / "out" / "k1_silo"


def main():
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    scene = c.reset_scene()
    c.setup_render(scene, samples=24 if quick else 128, res=(960, 540) if quick else (1920, 1080))
    c.setup_sky(scene, sun_elevation_deg=32.0, sun_rotation_deg=120.0)

    t0 = time.time()
    objs, measure = silo.build()
    measure["build_seconds"] = round(time.time() - t0, 1)

    v, f = c.box((-1500, -1500, -0.8), (1500, 1500, -0.6))
    c.mesh_from_arrays("GROUND", v, f, c.mat_ground())

    base = (0, 0, 0)
    cams = {
        "k1_hero.png": c.camera("CAM_HERO", (-30.0, -34.0, 1.7), (0.0, 0.0, 9.0), lens=24),
        "k1_wall_close.png": c.camera("CAM_WALL", (-13.2, -4.2, 1.9), (-11.0, -1.2, 3.2), lens=35),
        "k1_base.png": c.camera("CAM_BASE", (-3.5, -17.5, 1.6), (-6.8, -9.0, 0.6), lens=28),
        "k1_roof.png": c.camera("CAM_ROOF", (-24.0, 16.0, 27.0), (0.0, 0.0, 16.0), lens=35),
    }
    del base
    (OUT / "measure.json").write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(measure, ensure_ascii=False))
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")]
    for name, cam in cams.items():
        if only and name not in only:
            continue
        t = time.time()
        c.render(scene, cam, OUT / name)
        print("rendered", name, round(time.time() - t, 1), "s")
    if not quick and not only:
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "k1_silo.blend"), compress=True)


if __name__ == "__main__":
    main()
