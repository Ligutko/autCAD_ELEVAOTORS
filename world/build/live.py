"""Control center, module L: the live Blender scene next to the web panel (CONTROL_CENTER_SPEC.md §6).

Run (first the server, then Blender with a window):
    python world/sim/server.py --scenario receive_s1
    blender --python world/build/live.py -- [--url http://127.0.0.1:8765] [--xray] [--full-trees] [--no-motion]   (--full-trees keeps the 55 k tree objects: slow)
The scene is built fresh from the kits (the saved site.blend can be older than the kits), the live layer is
added (kit/live.py), the viewport switches to EEVEE in the drone camera, and a timer reads /state 5 times a second
and applies only what changed. --xray hides the silo walls so the grain heaps are seen. The grain packets running
along the flow lines are a viewport overlay (kit/live_motion.py) redrawn ~30 times a second while something moves;
--no-motion leaves them out.
"""

import importlib.util
import json
import sys
import time
import urllib.request
from pathlib import Path

import bpy  # noqa: I001

WORLD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORLD))

from kit import live as lv  # noqa: E402
from kit import live_motion as mo  # noqa: E402
from sim import core  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
URL = next((a.split("=", 1)[1] for a in ARGS if a.startswith("--url=")), "http://127.0.0.1:8765")
POLL_S = 0.2


def load_site_scene():
    spec = importlib.util.spec_from_file_location("site_scene", str(WORLD / "build" / "site.py"))
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    return S


def build(xray=False, full_trees=False):
    S = load_site_scene()
    scene, site, build_s, _, _ = S.assemble(quick=True)
    rho = core.load_params()["grain"]["bulk_density_t_m3"]["value"]
    t = time.time()
    live = lv.Live(scene, site, rho)
    if not full_trees:
        live.trees = lv.trees_merge(scene)
    if xray:
        for o in scene.objects:
            if o.name in {s["id"] for s in site["silos"]}:
                o.hide_viewport = True                    # the instanced silo shell; the heaps stay
    for o in scene.objects:
        if o.name.startswith("LBL_"):                     # drawing labels: hidden only in renders by site.py, black lines in the viewport
            o.hide_viewport = True
    cams = cameras()
    scene.camera = cams["CAM_DRONE"]
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    print(f"live: scene {build_s} s, live layer {time.time() - t:.1f} s; nodes without objects "
          f"{[n for n, v in live.nodes.items() if not v and n not in lv.NO_BODY]}; gates {len(live.gates)}; "
          f"loose gate parts {len(live.gate_loose)}; flow owners {len(live.flows)}, failed routes {len(live.flow_fails)}", flush=True)
    return scene, site, live


def cameras():
    """The views for the recording, the same positions as the site.py frames (site_drone, truck_pit, gallery_walk,
    drying); site.py makes its cameras in main(), not in assemble()."""
    from kit import common as c
    return {
        "CAM_DRONE": c.camera("CAM_DRONE", (70, -70, 55), (-8, 12, 10), lens=28),
        "CAM_TRUCK": c.camera("CAM_TRUCK", (19.0, 62.2, c.ground_z() + 1.7), (0.0, 63.4, 4.0), lens=22),
        "CAM_WALK": c.camera("CAM_WALK", (-3.5, 0.4, 24.9), (-30, 0.2, 23.6), lens=20),
        "CAM_DRYING": c.camera("CAM_DRYING", (26.0, 30.0, 30.0), (-8.0, 54.0, 12.0), lens=24),
    }


def view_camera(scene, cam="CAM_DRONE"):
    scene.camera = bpy.data.objects.get(cam) or scene.camera
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == "VIEW_3D":
                sp = area.spaces.active
                sp.shading.type = "RENDERED"
                sp.overlay.show_overlays = False
                sp.region_3d.view_perspective = "CAMERA"


def main():
    scene, site, live = build("--xray" in ARGS, "--full-trees" in ARGS)
    state = {"errors": 0}
    if "--no-motion" not in ARGS:                     # grain packets along the flow lines (kit/live_motion.py)
        try:
            live.overlay = mo.Overlay(live.motion)
            live.overlay.install()
        except Exception as e:                        # noqa: BLE001  a GPU without the polyline shader: the scene works without
            print("live: no grain packets:", e, flush=True)

    def poll():
        try:
            with urllib.request.urlopen(URL + "/state", timeout=0.15) as r:
                live.apply(json.loads(r.read()))
            state["errors"] = 0
        except Exception as e:                            # noqa: BLE001  the server may not be up yet
            state["errors"] += 1
            if state["errors"] in (1, 50):
                print("live: no state from", URL, "-", e, flush=True)
        return POLL_S

    def first():
        view_camera(scene)
        bpy.app.timers.register(poll, first_interval=POLL_S, persistent=True)
        return None

    bpy.app.timers.register(first, first_interval=1.0)


if __name__ == "__main__" and not bpy.app.background:
    main()
