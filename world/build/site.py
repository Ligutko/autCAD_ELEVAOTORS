"""Whole site from SITE.json: silos (instanced), noria towers, silo-top galleries, bridges, tunnels,
aspiration (dust bins, units, ducts).

Run:
    python world/build/site.py [--quick]
    blender --python world/build/site.py -- --no-render     # opens the built scene in Blender to fly around
    (--no-render builds the scene, saves world/out/site/site.blend and skips the test frames)
"""

import json
import math
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import aspiration as asp  # noqa: E402
from kit import common as c  # noqa: E402
from kit import foundation as fnd  # noqa: E402
from kit import gallery as gal  # noqa: E402
from kit import noria_tower as tower  # noqa: E402
from kit import receiving as rcv  # noqa: E402
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
        "road": c.mat_concrete_yard("SITE_ROAD", tint=(0.36, 0.35, 0.33)),   # concrete B25 drives (rec_6360894e), tyre-worn
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
    _, silo_measure = silo.build(collection=proto, with_foundation=False)
    fmat = {"ring": "concrete", "footing": "concrete", "floor_slab": "concrete",
            "anchor_rods": "galv_old", "anchor_plates": "dark", "marks": "galv"}
    for s in site["silos"]:
        inst = bpy.data.objects.new(s["id"], None)
        inst.instance_type = "COLLECTION"
        inst.instance_collection = proto
        inst.location = (s["x"], s["y"], s["z"])
        scene.collection.objects.link(inst)
        fcol = bpy.data.collections.new(f"{s['id']}_FOUNDATION")
        scene.collection.children.link(fcol)
        for k, (v, f) in fnd.build(fnd.tunnel_band(site, s)).items():
            o = c.mesh_from_arrays(f"{s['id']}_FOUNDATION_{k.upper()}", v, f, m[fmat[k]], collection=fcol)
            o.location = (s["x"], s["y"], s["z"])

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

    if "tower" in site.get("receiving", {}):                # existing receiving block, simplified (phase 4)
        col = bpy.data.collections.new("RECEIVING")
        scene.collection.children.link(col)
        for k, (mat, smooth, (v, f)) in rcv.build(site["receiving"], site).items():
            c.mesh_from_arrays(f"RECEIVING_{k.upper()}", v, f, m[mat], smooth=smooth, collection=col)
        r = site["receiving"]
        p, w = r["pit"], r["pit"]["wall_t"]
        tp = r["tower"]["pit"]
        holes += [(p["x"][0] - w, p["y"][0] - w, p["x"][1] + w, p["y"][1] + w),
                  (tp["inner_x"][0] - tp["wall_t"], tp["inner_y"][0] - tp["wall_t"], tp["inner_x"][1] + tp["wall_t"], tp["inner_y"][1] + tp["wall_t"])]

    if "site_plan" in site.get("designed", {}):             # phase 5B/5C: roads, scales, АПК, КПП, КТП, fire water
        from kit import site_plan as spl
        col = bpy.data.collections.new("SITE_PLAN")
        scene.collection.children.link(col)
        for k, (mat, smooth, (v, f)) in spl.build(site).items():
            c.mesh_from_arrays(f"SITE_PLAN_{k.upper()}", v, f, m[mat], smooth=smooth, collection=col)

    asp_measure = {}
    if "aspiration" in site:
        col = bpy.data.collections.new("ASPIRATION")
        scene.collection.children.link(col)
        _, asp_measure = asp.build(site, tower, tun, collection=col, materials=m)

    for col in bpy.data.collections:          # labels are for explainer shots only
        if col.name.startswith("LABELS_"):
            col.hide_render = True
    if "environment" in site.get("designed", {}):           # phase W1: yard + summer grass, road shoulders
        from kit import environment as env
        assert sorted(env.ground_holes(site)) == sorted(holes), "ground holes drifted from environment.ground_holes"
        col = bpy.data.collections.new("ENVIRONMENT")
        scene.collection.children.link(col)
        m.update({"yard": c.mat_concrete_yard("SITE_YARD"), "grass": c.mat_grass("SITE_GRASS"), "shoulder": c.mat_crushed_stone("SITE_SHOULDER"),
                  "fence": c.mat_painted("SITE_FENCE_RAL6005", (0.02, 0.09, 0.05), 0.45, grime=0.15)})   # polymer-coated mesh, judgment
        for k, (mat, smooth, (v, f)) in env.build(site).items():
            c.mesh_from_arrays(f"ENV_{k.upper()}", v, f, m[mat], smooth=smooth, collection=col)
        if "lighting" in site["designed"]["environment"]:     # W1c: floodlight masts and building-mounted floodlights
            from kit import lighting as lt
            col = bpy.data.collections.new("LIGHTING")
            scene.collection.children.link(col)
            m["lamp_glass"] = c.mat_painted("SITE_LAMP_GLASS", (0.55, 0.57, 0.6), 0.05, grime=0.0)
            for k, (mat, smooth, (v, f)) in lt.build(site).items():
                c.mesh_from_arrays(f"LIGHT_{k.upper()}", v, f, m[mat], smooth=smooth, collection=col)
    else:
        v, f = tun.ground_cells(2000, holes)
        c.mesh_from_arrays("GROUND", v, f, c.mat_ground())
    build_s = round(time.time() - t0, 1)

    return scene, site, build_s, silo_measure, asp_measure


def night(scene, site):
    """Night preset: a flat late-twilight sky, the sun off, every floodlight lit from its IES file
    (the same photometry as check_lighting), glowing glass, exposure opened for ~10-200 lx scenes."""
    from kit import lighting as lt
    nt = scene.world.node_tree
    bg = next(n for n in nt.nodes if n.type == "BACKGROUND")
    for ln in list(bg.inputs["Color"].links):                           # the physical sky is black under the horizon:
        nt.links.remove(ln)                                               # a flat late-twilight blue instead (judgment)
    bg.inputs["Color"].default_value = (0.004, 0.008, 0.02, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    for ob in scene.objects:
        if ob.type == "LIGHT" and ob.data.type == "SUN":
            ob.hide_render = True
    col = bpy.data.collections.new("LAMPS")
    scene.collection.children.link(col)
    lt.add_lamps(site, collection=col)
    glass = bpy.data.materials.get("SITE_LAMP_GLASS")
    if glass:
        b = next(n for n in glass.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Emission Color"].default_value = (1.0, 0.93, 0.85, 1.0)
        b.inputs["Emission Strength"].default_value = 40.0
    scene.view_settings.exposure = 3.8


def main():
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    scene, site, build_s, silo_measure, asp_measure = assemble(quick)
    if "--night" in sys.argv:
        night(scene, site)
        g = c.ground_z()
        cams = {"night_drone.png": c.camera("CAM_N_DRONE", (70, -70, 55), (-8, 12, 10), lens=28),
                "night_scales.png": c.camera("CAM_N_SCALES", (58.0, 80.0, 9.0), (36.0, 63.0, 1.5), lens=24),
                "night_gate.png": c.camera("CAM_N_GATE", (124, 36, 6), (104, 56, 1.0), lens=26),
                "night_pit.png": c.camera("CAM_N_PIT", (19.0, 62.2, g + 1.7), (0.0, 63.4, 4.0), lens=22),
                "night_ring.png": c.camera("CAM_N_RING", (-70, -32, 14), (-30, 0, 2), lens=24)}
        only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")]
        for name, cam in cams.items():
            if only and name not in only:
                continue
            t = time.time()
            c.render(scene, cam, OUT / name)
            print("rendered", name, round(time.time() - t, 1), "s", flush=True)
        return

    cams = {
        "site_drone.png": c.camera("CAM_DRONE", (70, -70, 55), (-8, 12, 10), lens=28),
        "site_ground.png": c.camera("CAM_GROUND", (28, -16, c.ground_z() + 1.7), (-2, 8, 16), lens=20),
        "site_receiving.png": c.camera("CAM_RECV", (38.0, 22.0, 42.0), (-6.0, 57.0, 6.0), lens=24),
        "site_drying.png": c.camera("CAM_DRYING", (26.0, 30.0, 30.0), (-8.0, 54.0, 12.0), lens=24),
        "site_wet_silos.png": c.camera("CAM_WET", (-38.0, 78.0, 32.0), (-6.0, 53.0, 13.0), lens=24),
        "site_plan_top.png": c.camera("CAM_PLAN", (40.0, -40.0, 120.0), (25.0, 40.0, 0.0), lens=24),
        "site_scales.png": c.camera("CAM_SCALES", (58.0, 80.0, 9.0), (36.0, 63.0, 1.5), lens=24),
        "site_truck_pit.png": c.camera("CAM_TRUCK", (19.0, 62.2, c.ground_z() + 1.7), (0.0, 63.4, 4.0), lens=22),
        "site_tunnel_exit.png": c.camera("CAM_EXIT", (-56.5, 9.5, c.ground_z() + 1.7), (-51.1, 2.8, -1.2), lens=24),
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
    only = [a.split("=", 1)[1] for a in sys.argv if a.startswith("--only=")]
    for name, cam in cams.items():
        if only and name not in only:
            continue
        t = time.time()
        c.render(scene, cam, OUT / name)
        print("rendered", name, round(time.time() - t, 1), "s", flush=True)
    if only:
        return
    measure = {"build_seconds": build_s, "silos": len(site["silos"]),
               "towers": [t["id"] for t in site["noria_towers"]],
               "galleries": [ln["id"] for ln in site["silo_top_galleries"]["lines"]] + [b["id"] for b in site["bridges"]],
               "silo_vertices": silo_measure["vertices_total"], "aspiration": asp_measure}
    (OUT / "measure.json").write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
