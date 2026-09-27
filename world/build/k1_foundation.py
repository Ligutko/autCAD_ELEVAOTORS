"""Phase 3 frames: silo S3 foundation in section (ring beam, footing, floor slab, anchor, tunnel T13,
soil layers) and outside (fan duct through the plinth, settlement mark, anchor chairs).

Run:
    blender --background --python world/build/k1_foundation.py -- [--quick] [--only=name.png]
"""

import json
import math
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import foundation as fnd  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402
from kit import tunnel as tun  # noqa: E402

OUT = ROOT / "out" / "k1_foundation"
CUT_DEG = 92.25                                   # a stiffener angle: the plane passes through its anchor
SOIL = [("SOIL_TOP", (0.20, 0.15, 0.10)), ("SOIL_LOESS", (0.62, 0.50, 0.33)), ("SOIL_LOAM", (0.45, 0.38, 0.28))]


def main():
    quick = "--quick" in sys.argv
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")]
    OUT.mkdir(parents=True, exist_ok=True)
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    scene = c.reset_scene()
    c.setup_render(scene, samples=32 if quick else 160, res=(960, 540) if quick else (1920, 1080))
    c.setup_sky(scene, sun_elevation_deg=30.0, sun_rotation_deg=160.0)
    t0 = time.time()

    s = next(x for x in site["silos"] if x["id"] == "S3")
    t = next(x for x in site["tunnels"] if x["id"] == "T13")
    band = fnd.tunnel_band(site, s)
    a = math.radians(CUT_DEG)
    normal = (math.sin(a), -math.cos(a))              # t = (-ny, nx) points along CUT_DEG
    shift = np.array([s["x"], s["y"], silo.FLOOR_Z])

    objs, _ = silo.build(cut=normal, band=band)
    concrete = bpy.data.materials["SILO_FOUNDATION"]

    # tunnel T13 around this silo, in the silo frame, cut like the silo
    tmat = c.mat_concrete("TUNNEL_CONCRETE")
    v, f = tun.build_civil(site, t)
    v, f = c.cut_mesh(np.asarray(v) - shift, f, normal)
    c.mesh_from_arrays("T13_CIVIL", v, f, tmat)
    galv = c.mat_galvanized("TUNNEL_GALV", age=0.5, spangle_scale=60.0)
    for k, data in tun.build_gate_stacks(site, t).items():
        v, f = c.cut_mesh(np.asarray(data[0]) - shift, data[1], normal)
        if f:
            c.mesh_from_arrays(f"T13_{k.upper()}", v, f, galv)

    # section faces
    x0, y0, x1, y1, fz, cz = tun.inner_box(site, t)
    tun_d = {"y0": y0 - s["y"], "y1": y1 - s["y"], "wall_t": t["wall_t"], "floor_z": fz, "floor_slab_t": t["floor_slab_t"],
             "roof_top_z": t["roof_top_z"], "ceiling_z": cz, "roof_hole": (-0.21, 0.21)}
    rects = fnd.section_rects(normal, band, tun_d, soil_depth=8.0)
    mats = {"ring": concrete, "footing": concrete, "floor_slab": concrete, "tunnel": tmat,
            "fill": c.mat_painted("SOIL_FILL", (0.42, 0.41, 0.37), 0.95, grime=0.0),
            "anchor": c.mat_painted("ANCHOR_STEEL", (0.08, 0.08, 0.09), 0.4, grime=0.0)}
    for i, (name, col) in enumerate(SOIL):
        mats[f"soil_{i}"] = c.mat_painted(name, col, 0.95, grime=0.0)
    for k, rs in rects.items():
        lift = {"anchor": 0.008, "ring": 0.004, "footing": 0.004, "floor_slab": 0.004, "tunnel": 0.004}.get(k, 0.0)
        data = fnd.section_mesh(rs, normal, lift)
        if data is not None:
            c.mesh_from_arrays(f"SECTION_{k.upper()}", *data, mats[k])

    # ground behind the plane only, with the tunnel and its stair well left open
    holes = []
    for x0_, y0_, x1_, y1_ in tun.footprint(site, t):
        holes.append((x0_ - s["x"], y0_ - s["y"], x1_ - s["x"], y1_ - s["y"]))
    v, f = tun.ground_cells(400, holes)
    v, f = c.cut_mesh(np.asarray(v) - [0, 0, silo.FLOOR_Z], f, normal)
    c.mesh_from_arrays("GROUND", v, f, c.mat_ground())
    build_s = round(time.time() - t0, 1)

    u = np.array([math.cos(a), math.sin(a)])
    rc = (fnd.spec()["ring"]["r_in"] + fnd.spec()["ring"]["r_out"]) / 2
    g = fnd.to_local(c.ground_z())
    anc = fnd.spec()["anchors"]

    def on_plane(sv, z):
        return (u[0] * sv + normal[0] * 0.05, u[1] * sv + normal[1] * 0.05, z)

    labels = [
        ("Кільцевий фундамент 0.6 м під стіною, R 10.775–11.375 (арк. 2)", on_plane(rc, -0.45)),
        ("Підошва 1.6 × 0.5, низ −1.70: нижче промерзання (judgment)", on_plane(rc, fnd.to_local(-1.45))),
        (f"Анкер M24, закладення {anc['hef']:.2f} м (аналог Sukup / Symaga)", on_plane(anc["r"], -0.2)),
        ("Земля −0.45 (арк. 4); цоколь 1.05 м над землею", on_plane(-13.0, g + 0.15)),
        ("Тунель T13: плита 0.40 тут несе стіну силоса, кільця немає", on_plane(0.0, fnd.to_local(0.4))),
        ("Лесоподібний суглинок, просідний, до ≈10 м (аналог: Лубенський р-н)", on_plane(-8.0, fnd.to_local(-2.8))),
        ("Засипка під підлогою силоса", on_plane(-6.0, (g - 0.25) / 2)),
    ]
    label_objs = c.labels(labels, "FOUND")

    fan_a = math.radians(132.5)
    duct_p = (silo.FOUND_R * math.cos(math.radians(141.0)), silo.FOUND_R * math.sin(math.radians(141.0)), -0.5)
    cam_p = (17.5 * math.cos(math.radians(144.0)), 17.5 * math.sin(math.radians(144.0)), g + 1.6)
    n3 = np.array([normal[0], normal[1], 0.0])
    shots = [
        ("found_section.png", c.camera("CAM_SECTION", tuple(n3 * 17 + [0, 0, 1.4]), (0.0, 0.0, -0.4), lens=24), True),
        ("found_ring_anchor.png", c.camera("CAM_RING", tuple(n3 * 3.2 + [*(u * (rc + 0.4)), 0.1]),
                                           (*(u * (rc - 0.05)), -0.55), lens=24), True),
        ("found_duct_plinth.png", c.camera("CAM_DUCT", cam_p, duct_p, lens=24), False),
    ]
    for name, cam, with_labels in shots:
        if only and name not in only:
            continue
        for lo in label_objs:
            lo.hide_render = not with_labels
        bpy.context.view_layer.update()
        t1 = time.time()
        if with_labels:
            c.face_labels(label_objs, cam, max_dist=40.0)
            c.render_with_labels(scene, cam, OUT / name, label_objs)
        else:
            c.render(scene, cam, OUT / name)
        print("rendered", name, round(time.time() - t1, 1), "s", flush=True)
    if not only:
        measure = {"build_seconds": build_s, "cut_deg": CUT_DEG, "section_rects": {k: len(v) for k, v in rects.items()},
                   "anchors_per_silo": len(fnd.anchor_layout(band)),
                   "through_bolts": sum(k["kind"] == "through_bolt" for k in fnd.anchor_layout(band))}
        (OUT / "measure.json").write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
