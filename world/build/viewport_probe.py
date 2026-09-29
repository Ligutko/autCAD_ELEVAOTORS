"""Stage 0, third pass: what makes the live viewport heavy. Collections with object / face counts,
then RENDERED frame time with groups hidden one after another and with lighter EEVEE settings.

Run:  blender world/out/site/site.blend --python world/build/viewport_probe.py -- <out_dir>
(opens a GUI window, quits by itself; results: <out_dir>/probe3.json and p3_*.png screenshots)
"""
import json
import os
import sys
import time
from collections import defaultdict

import bpy

OUT = sys.argv[sys.argv.index("--") + 1]
res = {"collections": {}, "prefix": {}, "runs": []}
T0 = time.perf_counter()


def view3d():
    win = bpy.context.window_manager.windows[0]
    area = max((a for a in win.screen.areas if a.type == "VIEW_3D"), key=lambda a: a.width * a.height)
    return win, area, next(r for r in area.regions if r.type == "WINDOW")


def draw(n):
    win, area, region = view3d()
    with bpy.context.temp_override(window=win, area=area, region=region):
        t = time.perf_counter()
        bpy.ops.wm.redraw_timer(type="DRAW", iterations=n)
        return (time.perf_counter() - t) / n


def shot(name):
    win, area, region = view3d()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.screen.screenshot_area(filepath=os.path.join(OUT, name))


def faces(o):
    if o.type == "MESH":
        return len(o.data.polygons)
    if o.instance_type == "COLLECTION" and o.instance_collection:
        return sum(faces(x) for x in o.instance_collection.all_objects)
    return 0


def census():
    fc = {}
    for c in bpy.data.collections:
        objs = list(c.objects)
        res["collections"][c.name] = {"objects": len(objs), "faces": sum(faces(o) for o in objs)}
    pre = defaultdict(lambda: [0, 0])
    for o in bpy.context.scene.objects:
        p = o.name.split("_")[0].split(".")[0]
        pre[p][0] += 1
        pre[p][1] += faces(o)
    res["prefix"] = {k: {"objects": v[0], "faces": v[1]} for k, v in sorted(pre.items(), key=lambda kv: -kv[1][1])}
    return fc


def settle():
    """Draw until two consecutive 5-frame means agree within 10 % and at least 6 s passed."""
    t = time.perf_counter()
    last = draw(5)
    while True:
        yield 0.05
        cur = draw(5)
        if time.perf_counter() - t > 6 and abs(cur - last) < 0.1 * last:
            return
        last = cur
        if time.perf_counter() - t > 90:
            return


def measure(tag, cams=("CAM_DRONE", "CAM_WALK")):
    win, area, region = view3d()
    sp = area.spaces.active
    for cam in cams:
        bpy.context.scene.camera = bpy.data.objects[cam]
        sp.region_3d.view_perspective = "CAMERA"
        yield from settle()
        per = draw(15)
        res["runs"].append({"variant": tag, "view": cam, "frame_ms": round(per * 1000, 1), "fps": round(1 / per, 1)})
        print("PROBE", res["runs"][-1], flush=True)
        shot(f"p3_{tag}_{cam}.png")


def hide(pred):
    n = 0
    for o in bpy.context.scene.objects:
        if pred(o) and not o.hide_viewport:
            o.hide_viewport = True
            n += 1
    return n


def steps():
    census()
    win, area, region = view3d()
    with bpy.context.temp_override(window=win, area=area):
        bpy.ops.screen.screen_full_area()
    win, area, region = view3d()
    sp = area.spaces.active
    sp.overlay.show_overlays = False
    sp.shading.type = "RENDERED"
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    res["region_px"] = [region.width, region.height]
    ee = scene.eevee
    res["eevee"] = {k: getattr(ee, k) for k in ("taa_samples", "use_shadows", "use_raytracing", "shadow_ray_count",
                                                  "shadow_step_count", "use_volumetric_shadows") if hasattr(ee, k)}
    yield from measure("full")
    res["hidden_trees"] = hide(lambda o: o.name.startswith("TREE"))
    yield from measure("no_trees")
    res["hidden_interior"] = hide(lambda o: any(k in o.name for k in ("INTERIOR", "GRAIN", "THERMO", "RAFTER", "AERATION")))
    yield from measure("no_trees_interior")
    if hasattr(ee, "use_shadows"):
        ee.use_shadows = False
    if hasattr(ee, "use_raytracing"):
        ee.use_raytracing = False
    yield from measure("no_trees_interior_noshadow")
    res["total_s"] = round(time.perf_counter() - T0, 1)


GEN = steps()


def tick():
    try:
        return next(GEN)
    except StopIteration:
        pass
    except Exception:                                  # noqa: BLE001
        import traceback
        res["error"] = traceback.format_exc()
        print("PROBE ERROR", res["error"], flush=True)
    with open(os.path.join(OUT, "probe3.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(tick, first_interval=3.0)
