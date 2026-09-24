"""K2b: detailed noria Н-100 in tower H5. Head and boot cutaways with Ukrainian labels.

Run:
    python world/build/k2b_noria.py [--quick]
"""

import json
import math
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import noria_tower as tower  # noqa: E402

OUT = ROOT / "out" / "k2b_noria"


def point_light(name, loc, energy, size=0.3):
    data = bpy.data.lights.new(name, type="POINT")
    data.energy = energy
    data.shadow_soft_size = size
    data.color = (1.0, 0.93, 0.82)
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    return obj


def main():
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    spec = dict(next(t for t in site["noria_towers"] if t["id"] == "H5"))
    spec.update(x=0.0, y=0.0)
    scene = c.reset_scene()
    c.setup_render(scene, samples=32 if quick else 160, res=(810, 1080) if quick else (1080, 1440))
    c.setup_sky(scene, sun_elevation_deg=38.0, sun_rotation_deg=150.0)
    t0 = time.time()
    objs, measure = tower.build(spec)
    measure["build_seconds"] = round(time.time() - t0, 1)
    v, f = c.box((-800, -800, -0.2), (800, 800, 0.0))
    c.mesh_from_arrays("GROUND", v, f, c.mat_ground())
    labels = [o for o in bpy.data.objects if o.name.startswith("LBL_")]

    zt = spec["top_z"]
    zh = measure["noria"]["head_pulley_z_m"]
    zb = measure["noria"]["boot_pulley_z_m"]
    cover = [o for o in bpy.data.objects if o.name.endswith(("NORIA_HEAD_COVER", "NORIA_BOOT_COVER"))]
    shots = [
        ("noria_head_cutaway.png", c.camera("CAM_HEAD_CUT", (1.2, 2.05, zh + 0.25), (1.0, 0.3, zh - 0.15), lens=17), True, None),
        ("noria_head_closed.png", c.camera("CAM_HEAD", (2.05, -1.7, zt + 1.75), (0.8, 0.1, zh - 0.15), lens=18), False, None),
        ("noria_boot_cutaway.png", c.camera("CAM_BOOT", (1.1, 2.0, zb + 0.9), (0.95, 0.3, zb + 0.05), lens=16), True,
         (1.3, 1.6, zb + 1.6)),
    ]
    (OUT / "measure.json").write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(measure["noria"], ensure_ascii=False))
    for name, cam, cut, lamp in shots:
        for o in cover:
            o.hide_render = cut
        lamp_obj = point_light("WORK_LAMP", lamp, 250.0) if lamp else None
        bpy.context.view_layer.update()
        c.face_labels(labels, cam)
        t = time.time()
        c.render_with_labels(scene, cam, OUT / name, labels)
        print("rendered", name, round(time.time() - t, 1), "s", flush=True)
        if lamp_obj:
            bpy.data.objects.remove(lamp_obj)


if __name__ == "__main__":
    main()
