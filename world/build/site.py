"""Whole site from SITE.json: silos (instanced), noria towers, silo-top galleries, tower bridge.

Run:
    python world/build/site.py [--quick]
    blender --python world/build/site.py -- --no-render     # opens the built scene in Blender to fly around
    (--no-render builds the scene, saves world/out/site/site.blend and skips the test frames)
"""

import json
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import gallery as gal  # noqa: E402
from kit import noria_tower as tower  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402
from kit import steel as st  # noqa: E402
from kit import tunnel as tun  # noqa: E402

OUT = ROOT / "out" / "site"


def materials():
    return {
        "galv": c.mat_galvanized("SITE_GALV", age=0.35, spangle_scale=60.0),
        "galv_old": c.mat_galvanized("SITE_GALV_OLD", age=0.6, spangle_scale=50.0),
        "grating": st.mat_grating("SITE_GRATING"),
        "yellow": c.mat_painted("SITE_RAIL_YELLOW", (0.80, 0.55, 0.03), 0.45),
        "dark": c.mat_painted("SITE_DRIVE_GREY", (0.20, 0.23, 0.24), 0.4),
        "motor": c.mat_painted("SITE_MOTOR_BLUE", (0.05, 0.16, 0.35), 0.35),
        "concrete": c.mat_concrete("SITE_CONCRETE"),
    }


def add_parts(prefix, parts, m, collection):
    mat_for = {
        "heavy": ("galv", False), "light": ("galv_old", False), "deck": ("grating", False),
        "rails": ("yellow", "quads"), "toes": ("yellow", False), "posts": ("galv", False),
        "spouts": ("galv", "quads"), "gates": ("dark", False), "conv_casing": ("galv", False),
        "conv_flanges": ("galv_old", False), "conv_drive": ("dark", False), "conv_motor": ("motor", "quads"),
    }
    for key, (v, f) in parts.items():
        mat, smooth = mat_for[key]
        c.mesh_from_arrays(f"{prefix}_{key.upper()}", v, f, m[mat], smooth=smooth, collection=collection)


def assemble(quick=False):
    """Build the whole site into a fresh scene. Returns (scene, site, build_seconds, silo_measure)."""
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    scene = c.reset_scene()
    c.setup_render(scene, samples=24 if quick else 128, res=(960, 540) if quick else (1920, 1080))
    c.setup_sky(scene, sun_elevation_deg=30.0, sun_rotation_deg=140.0)
    m = materials()
    t0 = time.time()

    # silo prototype in a hidden collection, instanced at every silo position
    proto = bpy.data.collections.new("KIT_SILO_MSVU220")
    _, silo_measure = silo.build(collection=proto)
    for s in site["silos"]:
        inst = bpy.data.objects.new(s["id"], None)
        inst.instance_type = "COLLECTION"
        inst.instance_collection = proto
        inst.location = (s["x"], s["y"], s["z"])
        scene.collection.objects.link(inst)

    tunnels = site.get("tunnels", [])
    for spec in site["noria_towers"]:
        col = bpy.data.collections.new(spec["id"])
        scene.collection.children.link(col)
        openings = [tun.pit_opening(site, t) for t in tunnels if t["tower"] == spec["id"]]
        dist = next((d for d in site.get("distribution", []) if d["tower"] == spec["id"]), None)
        objs, _ = tower.build(spec, collection=col, materials=m, openings=openings, distribution=dist)
        for o in objs.values():
            o.location = (spec["x"], spec["y"], 0.0)

    silo_xy = [(s["x"], s["y"]) for s in site["silos"]]
    for g in site["silo_top_conveyors"]:
        col = bpy.data.collections.new(g["id"])
        scene.collection.children.link(col)
        row = [p for p in silo_xy if abs(p[1] - g["from"][1]) < 0.1
               and min(g["from"][0], g["to"][0]) - 1 <= p[0] <= max(g["from"][0], g["to"][0]) + 1]
        start = (g["from"][0] + (2.2 if g["to"][0] > g["from"][0] else -2.2), g["from"][1])
        parts = gal.silo_row_gallery(start, g["to"], g["deck_z"], row)
        add_parts(g["id"], parts, m, col)

    for b in site["galleries"]:
        if b["id"] != "G_H5_H6":
            continue   # the bridge to the receiving tower comes with K6
        col = bpy.data.collections.new(b["id"])
        scene.collection.children.link(col)
        y_dir = 1 if b["to"][1] > b["from"][1] else -1
        p0 = (b["from"][0], b["from"][1] + y_dir * 2.2)
        p1 = (b["to"][0], b["to"][1] - y_dir * 2.2)
        add_parts(b["id"], gal.tower_bridge(p0, p1, b["z"], b["z"]), m, col)

    holes = []
    for t in tunnels:
        col = bpy.data.collections.new("TUNNEL_" + t["id"])
        scene.collection.children.link(col)
        tun.build(site, t, collection=col, materials=m)
        holes += tun.footprint(site, t)
    for spec in site["noria_towers"]:
        x0, y0, x1, y1 = tower.pit_inner(spec)
        w = spec["pit"]["wall_t"]
        holes.append((spec["x"] + x0 - w, spec["y"] + y0 - w, spec["x"] + x1 + w, spec["y"] + y1 + w))

    for col in bpy.data.collections:          # labels are for explainer shots only
        if col.name.startswith("LABELS_"):
            col.hide_render = True
    v, f = tun.ground_cells(2000, holes)
    c.mesh_from_arrays("GROUND", v, f, c.mat_ground())
    build_s = round(time.time() - t0, 1)

    return scene, site, build_s, silo_measure


def main():
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    scene, site, build_s, silo_measure = assemble(quick)

    cams = {
        "site_drone.png": c.camera("CAM_DRONE", (70, -70, 55), (-8, 12, 10), lens=28),
        "site_ground.png": c.camera("CAM_GROUND", (28, -16, 1.7), (-2, 8, 16), lens=20),
        "site_gallery_walk.png": c.camera("CAM_WALK", (-3.5, 0.4, 24.9), (-30, 0.2, 23.6), lens=20),
        "site_bridge.png": c.camera("CAM_BRIDGE", (9, 12.7, 17), (0, 12.7, 24.5), lens=24),
    }
    scene.camera = cams["site_drone.png"]
    if "--no-render" in sys.argv:
        path = OUT / "site.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
        print("saved", path, "build", build_s, "s", flush=True)
        return
    for name, cam in cams.items():
        t = time.time()
        c.render(scene, cam, OUT / name)
        print("rendered", name, round(time.time() - t, 1), "s", flush=True)
    measure = {"build_seconds": build_s, "silos": len(site["silos"]),
               "towers": [t["id"] for t in site["noria_towers"]],
               "galleries": [g["id"] for g in site["silo_top_conveyors"]] + ["G_H5_H6"],
               "silo_vertices": silo_measure["vertices_total"]}
    (OUT / "measure.json").write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
