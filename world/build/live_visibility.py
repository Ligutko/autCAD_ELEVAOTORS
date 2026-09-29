"""Which grain paths of the live scene can a camera see (control center, phase 8): the experiment behind kit/live_motion.py.

    blender --background --python world/build/live_visibility.py [-- <out.json>]

Builds the site with the live layer, then for each of the four recording cameras (build/live.py cameras()) walks every flow
path of the model (kit/live.py flow_paths: conveyor casing centrelines, noria loaded legs, spouts, falls, truck lanes) in
steps of 20 cm and casts a ray from the camera to each point against the rendered meshes of the scene (route_fx.scene_bvh,
without thin members): the point is seen when nothing is hit closer than TOL to it. Run twice: as built, and with the head /
boot covers of H5 and H6 removed. Result per camera and owner: metres of path, metres in the frame, metres seen, pixels of
seen path at 1920 x 1080. Default output: world/out/control_center/motion/recon_visibility.json.
"""
import importlib.util
import json
import sys
from pathlib import Path

import bpy
import numpy as np
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD))
OUT = Path(sys.argv[sys.argv.index("--") + 1]) if "--" in sys.argv else WORLD / "out" / "control_center" / "motion" / "recon_visibility.json"
TOL = 0.03          # m: a path point is hidden when a surface is hit more than this far before it (the casing wall is 0.13 m or more)
STEP = 0.2          # m along a path

from kit import live as lv  # noqa: E402
from kit import route_fx as fx  # noqa: E402
from sim import core  # noqa: E402

spec = importlib.util.spec_from_file_location("live_build", str(WORLD / "build" / "live.py"))
L = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], "--"]
spec.loader.exec_module(L)


def analyse(scene, cams, paths, tree):
    res = {}
    for cname, cam in cams.items():
        eye = cam.matrix_world.translation
        rows = {}
        for owner, plist in paths.items():
            tot = inf = vis = px_vis = 0.0
            for pts in plist:
                if len(pts) < 2:
                    continue
                pts = np.asarray(pts, float)
                s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
                arcs = np.arange(0.0, s[-1] + 1e-9, STEP)
                xyz = np.stack([np.interp(arcs, s, pts[:, i]) for i in range(3)], axis=1)
                prev = None
                for p in xyz:
                    v = Vector(p)
                    co = world_to_camera_view(scene, cam, v)
                    tot += STEP
                    in_frame = co.z > 0.05 and 0 <= co.x <= 1 and 0 <= co.y <= 1
                    seen = False
                    if in_frame:
                        inf += STEP
                        d = v - eye
                        hit, *_ = tree.ray_cast(eye, d.normalized(), max(d.length - TOL, 0.01))
                        seen = hit is None
                        vis += STEP if seen else 0.0
                    px = (co.x * 1920, (1 - co.y) * 1080)
                    if prev is not None and prev[1] and seen:
                        px_vis += float(np.hypot(px[0] - prev[0][0], px[1] - prev[0][1]))
                    prev = (px, seen and in_frame)
            rows[owner] = {"len_m": round(tot, 1), "in_frame_m": round(inf, 1), "seen_m": round(vis, 1), "seen_px": round(px_vis)}
        res[cname] = rows
    return res


def summary(res):
    out = {}
    for cam, rows in res.items():
        seen = {k: v for k, v in rows.items() if v["seen_m"] > 0.5}
        out[cam] = {"in_frame_m": round(sum(v["in_frame_m"] for v in rows.values())),
                    "seen_m": round(sum(v["seen_m"] for v in rows.values())),
                    "owners_seen_over_0.5m": {k: v["seen_m"] for k, v in sorted(seen.items(), key=lambda kv: -kv[1]["seen_m"])}}
    return out


def main():
    S = L.load_site_scene()
    scene, site, _, _, _ = S.assemble(quick=True)
    live = lv.Live(scene, site, core.load_params()["grain"]["bulk_density_t_m3"]["value"])
    cams = L.cameras()
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 1920, 1080, 100
    bpy.context.view_layer.update()
    paths, fails = lv.flow_paths(site)
    out = {"about": "metres of grain path seen from each recording camera; TOL / STEP in the script", "tol_m": TOL, "step_m": STEP,
           "no_path": sorted(fails)}
    out["as_built"] = analyse(scene, cams, paths, fx.scene_bvh(scene, all_parts=False)[0])
    covers = [o for o in scene.objects if o.name.endswith(("NORIA_HEAD_COVER", "NORIA_BOOT_COVER"))]
    for o in covers:
        o.hide_render = True
    bpy.context.view_layer.update()
    out["covers_off"] = analyse(scene, cams, paths, fx.scene_bvh(scene, all_parts=False)[0])
    out["covers_removed"] = [o.name for o in covers]
    out["summary_as_built"] = summary(out["as_built"])
    out["summary_covers_off"] = summary(out["covers_off"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for key in ("summary_as_built", "summary_covers_off"):
        print(key)
        for cam, v in out[key].items():
            print(f"  {cam:<11} paths in frame {v['in_frame_m']:>4} m, seen {v['seen_m']:>3} m: {v['owners_seen_over_0.5m']}")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
