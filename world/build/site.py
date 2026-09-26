"""Whole site from SITE.json: silos (instanced), noria towers, silo-top galleries, bridges, tunnels,
aspiration (dust bins, units, ducts).

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

from kit import aspiration as asp  # noqa: E402
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
        "red": c.mat_painted("SITE_GATE_RED", (0.55, 0.06, 0.04), 0.45, grime=0.3),
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
    roof_holes, cover_holes = asp.riser_holes(site, tun)     # aspiration risers through the tunnel roof / pit cover
    for spec in site["noria_towers"]:
        col = bpy.data.collections.new(spec["id"])
        scene.collection.children.link(col)
        openings = [tun.pit_opening(site, t) for t in tunnels if t["tower"] == spec["id"]]
        dist = next((d for d in site.get("distribution", []) if d["tower"] == spec["id"]), None)
        holes = [(x0 - spec["x"], y0 - spec["y"], x1 - spec["x"], y1 - spec["y"]) for x0, y0, x1, y1 in cover_holes.get(spec["id"], ())]
        objs, _ = tower.build(spec, collection=col, materials=m, openings=openings, distribution=dist, cover_holes=holes)
        for o in objs.values():
            o.location = (spec["x"], spec["y"], 0.0)

    g = site["silo_top_galleries"]
    for line in g["lines"]:
        col = bpy.data.collections.new("GALLERY_" + line["id"])
        scene.collection.children.link(col)
        add_parts(line["id"], gal.silo_row_gallery(g, line), m, col)

    for b in site["bridges"]:
        col = bpy.data.collections.new(b["id"])
        scene.collection.children.link(col)
        add_parts(b["id"], gal.bridge(b), m, col)

    holes = []
    for t in tunnels:
        col = bpy.data.collections.new("TUNNEL_" + t["id"])
        scene.collection.children.link(col)
        tun.build(site, t, collection=col, materials=m, roof_holes=roof_holes.get(t["id"], ()))
        holes += tun.footprint(site, t)
    for spec in site["noria_towers"]:
        x0, y0, x1, y1 = tower.pit_inner(spec)
        w = spec["pit"]["wall_t"]
        holes.append((spec["x"] + x0 - w, spec["y"] + y0 - w, spec["x"] + x1 + w, spec["y"] + y1 + w))

    asp_measure = {}
    if "aspiration" in site:
        col = bpy.data.collections.new("ASPIRATION")
        scene.collection.children.link(col)
        _, asp_measure = asp.build(site, tower, tun, collection=col, materials=m)

    for col in bpy.data.collections:          # labels are for explainer shots only
        if col.name.startswith("LABELS_"):
            col.hide_render = True
    v, f = tun.ground_cells(2000, holes)
    c.mesh_from_arrays("GROUND", v, f, c.mat_ground())
    build_s = round(time.time() - t0, 1)

    return scene, site, build_s, silo_measure, asp_measure


def main():
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    scene, site, build_s, silo_measure, asp_measure = assemble(quick)

    cams = {
        "site_drone.png": c.camera("CAM_DRONE", (70, -70, 55), (-8, 12, 10), lens=28),
        "site_ground.png": c.camera("CAM_GROUND", (28, -16, 1.7), (-2, 8, 16), lens=20),
        "site_gallery_walk.png": c.camera("CAM_WALK", (-3.5, 0.4, 24.9), (-30, 0.2, 23.6), lens=20),
        "site_bridge.png": c.camera("CAM_BRIDGE", (9, 12.7, 17), (0, 12.7, 24.5), lens=24),
        "site_aspiration_81.png": c.camera("CAM_ASP_81", (-15.5, 50.5, 4.5), (-26.5, 36.8, 7.5), lens=22),
        "site_aspiration_82.png": c.camera("CAM_ASP_82", (8.5, -21.0, 3.5), (-0.3, -6.0, 7.0), lens=22),
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
               "galleries": [ln["id"] for ln in site["silo_top_galleries"]["lines"]] + [b["id"] for b in site["bridges"]],
               "silo_vertices": silo_measure["vertices_total"], "aspiration": asp_measure}
    (OUT / "measure.json").write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
