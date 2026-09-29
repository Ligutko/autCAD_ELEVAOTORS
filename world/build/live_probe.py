"""Live scene probe (control center, stage 7 + phase 8): a server with a scenario, the live Blender window next to it,
viewport frame time per camera, the cost of one state update, the timer gap and the frame gap of the grain-packet
overlay (kit/live_motion.py), screenshots, and per camera a pair of screenshots a few tenths of a second apart with the
projected paths, for build/live_motion_shots.py (the shift of the pattern measured on the pixels).
Run: blender --python world/build/live_probe.py -- <out_dir> <scenario> <speed> [--xray] [--no-motion] [--at=1100,1500]
--at: instead of the four-camera run, wait for these simulated times (s) and take the CAM_DRYING view at each
(the trip proof: trip_h5_plug at speed 30 stops H5 at ~1200 s; the pattern must be gone from its path afterwards).
Opens a window, quits by itself; stale server.py processes on port 8799 must be stopped first."""
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.request

import bpy
import numpy as np

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT, SCEN, SPEED = os.path.abspath(ARGS[0]), ARGS[1], float(ARGS[2])   # screenshot_area ignores the cwd for relative paths
XRAY = "--xray" in ARGS
MOTION = "--no-motion" not in ARGS
AT = [float(x) for x in next((a.split("=", 1)[1] for a in ARGS if a.startswith("--at=")), "").split(",") if x]
WORLD = "D:/autocad project/world"
PORT = 8799
URL = f"http://127.0.0.1:{PORT}"
os.makedirs(OUT, exist_ok=True)
srv = subprocess.Popen(["python", f"{WORLD}/sim/server.py", "--port", str(PORT), "--scenario", SCEN],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
spec = importlib.util.spec_from_file_location("live_build", f"{WORLD}/build/live.py")
L = importlib.util.module_from_spec(spec)
sys.argv = [sys.argv[0], "--", f"--url={URL}"] + (["--xray"] if XRAY else [])
spec.loader.exec_module(L)
res = {"runs": [], "motion_pairs": [], "at": []}
T0 = time.perf_counter()
OV = None                                                           # the grain-packet overlay, when on


def log(*a):
    with open(os.path.join(OUT, "log.txt"), "a", encoding="utf-8") as f:
        f.write(f"{time.perf_counter() - T0:7.1f} " + " ".join(str(x) for x in a) + chr(10))


def post(path, body):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())


def raise_window():
    """Windows only, this process's own windows only: restore a minimized window and keep it on top without taking the focus,
    so that the screenshots are not black (a minimized window is not redrawn, a covered one can read back black).
    Returns (windows found, minimized before)."""
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        pid, found = os.getpid(), []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        def cb(h, _):
            p = wintypes.DWORD()
            u.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == pid and u.IsWindowVisible(h):
                found.append(h)
            return True
        u.EnumWindows(cb, 0)
        iconic = 0
        for h in found:
            if u.IsIconic(h):
                iconic += 1
                u.ShowWindow(h, 9)                                  # SW_RESTORE
            u.SetWindowPos(h, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)   # HWND_TOPMOST, NOSIZE | NOMOVE | NOACTIVATE
        return len(found), iconic
    except Exception:                                               # noqa: BLE001  not Windows, or no ctypes
        return 0, 0


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
    """Take the area as the last window redraw left it. Returns the overlay time of that frame: no redraw happens between
    the last draw of the timer loop and this call (one thread), so last_t is the time of the pixels; redraw_timer('DRAW')
    calls (draw()) move last_t without swapping, so a shot is never taken right after one (yield first)."""
    win, area, region = view3d()
    with bpy.context.temp_override(window=win, area=area, region=region):
        t = OV.last_t if OV else None
        bpy.ops.screen.screenshot_area(filepath=os.path.join(OUT, name))
    return t


def camera_frame(scene):
    """[x0, y0, x1, y1] of the camera frame in the pixels of the screenshot: outside it the viewport darkens the picture
    (passepartout), packets there do not have their own colour."""
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    win, area, region = view3d()
    rv3d = area.spaces.active.region_3d
    cam = scene.camera
    q = [location_3d_to_region_2d(region, rv3d, cam.matrix_world @ v) for v in cam.data.view_frame(scene=scene)]
    xs = [p.x + region.x - area.x for p in q]
    ys = [area.height - 1 - (p.y + region.y - area.y) for p in q]
    return [round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1)]


def project_paths(live, owners, step=0.05):
    """Image pixel of every `step` m along the longest leg of each owner (the screenshot is the whole area)."""
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    from mathutils import Vector
    win, area, region = view3d()
    rv3d = area.spaces.active.region_3d
    out = {}
    for owner in owners:
        legs = [lg for lg in live.motion.legs if lg[0] == owner]
        if not legs:
            continue
        _, pts, s, length, v = max(legs, key=lambda lg: lg[3])
        arcs = np.arange(0.0, length, step)
        xyz = np.stack([np.interp(arcs, s, pts[:, i]) for i in range(3)], axis=1)
        px = []
        for p in xyz:
            q = location_3d_to_region_2d(region, rv3d, Vector(p))
            px.append(None if q is None else [round(q.x + region.x - area.x, 1), round(area.height - 1 - (q.y + region.y - area.y), 1)])
        out[owner] = {"v": v, "length_m": round(length, 3), "step_m": step, "px": px}
    return out


def motion_pair(live, cam):
    """Two screenshots ~0.3 s apart of a camera, with the packets of every owner that moves in both."""
    ta = shot(f"motion_{SCEN}_{cam}_a.png")
    act_a = set(live.motion.active)
    yield 0.3
    tb = shot(f"motion_{SCEN}_{cam}_b.png")
    both = sorted(act_a & set(live.motion.active))
    res["motion_pairs"].append({"cam": cam, "png_a": f"motion_{SCEN}_{cam}_a.png", "png_b": f"motion_{SCEN}_{cam}_b.png",
                                "t_a": ta, "t_b": tb, "active": both, "spacing_m": L.mo.SPACING_M, "dash_m": L.mo.DASH_M,
                                "core_rgb": [round(255 * c) for c in L.mo.LOOK["core"][:3]], "frame": camera_frame(bpy.context.scene),
                                "owners": project_paths(live, both)})
    log("pair", cam, "t_a", ta, "t_b", tb, "moving in both", both)


def steps():
    global OV
    t0 = time.perf_counter()
    log("build start")
    scene, site, live = L.build(xray=XRAY)
    log("build done", round(time.perf_counter() - t0, 1), "trees", getattr(live, "trees", None))
    res["build_s"] = round(time.perf_counter() - t0, 1)
    if MOTION:
        OV = L.mo.Overlay(live.motion)
        OV.install()
    win, area, region = view3d()
    with bpy.context.temp_override(window=win, area=area):
        bpy.ops.screen.screen_full_area()
    L.view_camera(scene)
    log("view after view_camera:", view3d()[1].spaces.active.region_3d.view_perspective, "; own windows raised (found, minimized):", raise_window())
    for _ in range(50):
        try:
            post("/cmd", {"op": "speed", "value": SPEED})
            break
        except Exception:                                           # noqa: BLE001
            yield 0.2

    stats = res.setdefault("poll", {"n": 0, "apply_ms": 0.0, "apply_max_ms": 0.0, "gaps": []})
    last = [time.perf_counter()]

    def poll():
        now = time.perf_counter()
        stats["gaps"].append(round((now - last[0]) * 1000))
        last[0] = now
        try:
            with urllib.request.urlopen(URL + "/state", timeout=0.15) as r:
                st = json.loads(r.read())
            t = time.perf_counter()
            live.apply(st)
            bpy.context.view_layer.update()                          # the depsgraph cost of the change, measured here
            d = (time.perf_counter() - t) * 1000
            stats["n"] += 1
            stats["apply_ms"] += d
            stats["apply_max_ms"] = max(stats["apply_max_ms"], d)
        except Exception:                                           # noqa: BLE001
            pass
        return 0.2
    bpy.app.timers.register(poll, first_interval=0.2, persistent=True)
    log("polling; first draw", round(draw(1) * 1000), "ms")
    t = time.perf_counter()
    warm = 12 if AT else 40
    while time.perf_counter() - t < warm:                            # grain on its way, shaders compiled
        d = draw(1)
        log("warm draw", round(d * 1000), "ms")
        yield 0.3
    if AT:
        L.view_camera(scene, "CAM_DRYING")
        log("windows (found, minimized):", raise_window())
        for _ in range(8):
            draw(2)
            yield 0.2
        for target in AT:
            while json.loads(urllib.request.urlopen(URL + "/state").read())["t_s"] < target:
                yield 0.25
            st = json.loads(urllib.request.urlopen(URL + "/state").read())
            live.apply(st)
            yield 0.6                                               # the pattern is drawn from the applied state
            log("windows (found, minimized):", raise_window())
            yield 0.4
            name = f"at_{int(target)}_{SCEN}_CAM_DRYING"
            tt = shot(name + ".png")
            row = {"sim_t": st["t_s"], "png": name + ".png", "overlay_t": tt, "moving": sorted(live.motion.active),
                   "alarms": [a["id"] + ":" + a["level"] for a in st["alarms"]],
                   "H5": st["motors"]["H5"]["state"], "H5_load_t_h": st["motors"]["H5"]["load_t_h"],
                   "frame": camera_frame(scene), "paths": project_paths(live, ["H5"])}
            res["at"].append(row)
            log("at", target, {k: v for k, v in row.items() if k != "paths"})
        return
    for cam in ("CAM_DRONE", "CAM_DRYING", "CAM_TRUCK", "CAM_WALK"):
        log(cam, "view before:", view3d()[1].spaces.active.region_3d.view_perspective, "; windows (found, minimized):", raise_window())
        L.view_camera(scene, cam)                                   # the camera and the camera view of the viewport
        log(cam, "view after:", view3d()[1].spaces.active.region_3d.view_perspective)
        t = time.perf_counter()
        prev = draw(5)                                              # not `last`: poll() closes over it
        while True:
            yield 0.05
            cur = draw(5)
            if time.perf_counter() - t > 6 and abs(cur - prev) < 0.15 * prev:
                break
            prev = cur
            if time.perf_counter() - t > 60:
                break
        per = draw(20)
        st = json.loads(urllib.request.urlopen(URL + "/state").read())
        run = {"view": cam, "frame_ms": round(per * 1000, 1), "fps": round(1 / per, 1), "sim_t": st["t_s"]}
        yield 0.3
        mark = len(stats["gaps"])
        if OV:
            OV.draw_gap_ms.clear()
            OV.tick_gap_ms.clear()
        yield 4.0                                                   # nothing but the timers runs: the real cadence of the live scene
        pg = sorted(stats["gaps"][mark:]) or [0]
        run["poll_gap_ms"] = {"median": pg[len(pg) // 2], "p95": pg[int(len(pg) * 0.95)], "n": len(pg)}
        if OV:
            g, tg, d = sorted(OV.draw_gap_ms) or [0], sorted(OV.tick_gap_ms) or [0], sorted(OV.draw_ms) or [0]
            run["overlay"] = {"moving": len(live.motion.active), "draw_py_ms": round(sum(d) / len(d), 2),
                              "frame_gap_median_ms": round(g[len(g) // 2], 1), "frame_gap_p95_ms": round(g[int(len(g) * 0.95)], 1),
                              "frames": len(g), "tick_gap_median_ms": round(tg[len(tg) // 2], 1)}
        res["runs"].append(run)
        print("GUIPROBE", run, flush=True)
        log("run", run)
        shot(f"live_{SCEN}_{cam}.png")
        yield 0.1
        if OV:
            yield from motion_pair(live, cam)
            yield 0.1
    if OV:
        res["overlay_timer"] = {"ticks": OV.ticks, "draws": OV.draws, "redraw_s": OV.redraw_s}


GEN = steps()


def tick():
    try:
        return next(GEN)
    except StopIteration:
        pass
    except Exception:                                               # noqa: BLE001
        import traceback
        res["error"] = traceback.format_exc()
        print("GUIPROBE ERROR", res["error"], flush=True)
    p = res.get("poll")
    if p and p["n"]:
        g = sorted(p["gaps"][5:]) or [0]
        res["poll_summary"] = {"updates": p["n"], "apply_avg_ms": round(p["apply_ms"] / p["n"], 1), "apply_max_ms": round(p["apply_max_ms"]),
                               "gap_median_ms": g[len(g) // 2], "gap_p95_ms": g[int(len(g) * 0.95)]}
        p["gaps"] = p["gaps"][-5:]                                   # kept short; poll() still appends until Blender quits
    with open(os.path.join(OUT, "gui_probe.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    srv.terminate()
    bpy.ops.wm.quit_blender()
    return None


bpy.app.timers.register(tick, first_interval=2.0, persistent=True)
