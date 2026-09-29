"""Live scene probe (control center, stage 7): a server with a scenario, the live Blender window next to it,
viewport frame time per camera, the cost of one state update and the timer gap, screenshots.
Run: blender --python world/build/live_probe.py -- <out_dir> <scenario> <speed> [--xray]
Opens a window, quits by itself; stale server.py processes on port 8799 must be stopped first."""
import importlib.util
import json
import os
import subprocess
import sys
import time
import urllib.request

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT, SCEN, SPEED = os.path.abspath(ARGS[0]), ARGS[1], float(ARGS[2])   # screenshot_area ignores the cwd for relative paths
XRAY = "--xray" in ARGS
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
res = {"runs": []}
T0 = time.perf_counter()


def log(*a):
    with open(os.path.join(OUT, "log.txt"), "a", encoding="utf-8") as f:
        f.write(f"{time.perf_counter() - T0:7.1f} " + " ".join(str(x) for x in a) + chr(10))


def post(path, body):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=5).read())


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


def steps():
    t0 = time.perf_counter()
    log("build start")
    scene, site, live = L.build(xray=XRAY)
    log("build done", round(time.perf_counter() - t0, 1), "trees", getattr(live, "trees", None))
    res["build_s"] = round(time.perf_counter() - t0, 1)
    win, area, region = view3d()
    with bpy.context.temp_override(window=win, area=area):
        bpy.ops.screen.screen_full_area()
    L.view_camera(scene)
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
    while time.perf_counter() - t < 40:                               # grain on its way, shaders compiled
        d = draw(1)
        log("warm draw", round(d * 1000), "ms")
        yield 0.3
    for cam in ("CAM_DRONE", "CAM_DRYING", "CAM_TRUCK", "CAM_WALK"):
        scene.camera = bpy.data.objects[cam]
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
        res["runs"].append({"view": cam, "frame_ms": round(per * 1000, 1), "fps": round(1 / per, 1), "sim_t": st["t_s"]})
        print("GUIPROBE", res["runs"][-1], flush=True)
        log("run", res["runs"][-1])
        shot(f"live_{SCEN}_{cam}.png")
        yield 0.1


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
