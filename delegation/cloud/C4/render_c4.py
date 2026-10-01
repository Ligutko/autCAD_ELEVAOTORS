"""C4 frames: one tunnel gate (T13, under silo S4, gate S4.c, ТЗА-400) at pos 0 / 0.5 / 1, moved by the live scene.

    blender --background --python delegation/cloud/C4/render_c4.py [-- --cpu]

The whole site is built (quick), the live layer is added (kit/live.py Live) and Live.apply() gets a simulator state
in which only gate S4.c changes its "pos"; nothing else moves the blade. For the frames only (the model is not
changed): the near (-Y) half of this one gate's BODY object is cut away so the blade inside the casing can be seen,
the gate glow (live_on) is switched off so the blade reads against the body, and two work lamps light the tunnel.
Cycles, OptiX GPU when there is one. Frames: delegation/cloud/C4/gate_closed.png, gate_half.png, gate_open.png.
"""

import importlib.util
import json
import sys
import time
from pathlib import Path

import bmesh
import bpy

ROOT = Path(__file__).resolve().parents[3]
WORLD = ROOT / "world"
sys.path.insert(0, str(WORLD))

from kit import common as c  # noqa: E402
from kit import live as lv  # noqa: E402
from sim import core  # noqa: E402
from sim.control import Plant  # noqa: E402

OUT = Path(__file__).resolve().parent
GID, TUN, IDX = "S4.c", "T13", None      # the opening index is looked up from the gate's blade
CUT = 0.03                               # m: body faces with every vertex this far on the camera side of the row axis go


def gpu(scene):
    if "--cpu" in sys.argv:
        return "CPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "OPTIX"
    prefs.get_devices()
    on = [d for d in prefs.devices if d.type == "OPTIX"]
    for d in prefs.devices:
        d.use = d in on
    if on:
        scene.cycles.device = "GPU"
        return "GPU " + ", ".join(d.name for d in on)
    return "CPU"


def point(name, loc, energy, size=0.15):
    d = bpy.data.lights.new(name, type="POINT")
    d.energy, d.shadow_soft_size, d.color = energy, size, (1.0, 0.94, 0.85)
    o = bpy.data.objects.new(name, d)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    return o


def cut_near_half(o, y_cut):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.co.y < y_cut for v in f.verts)], context="FACES")
    bm.to_mesh(o.data)
    bm.free()


def main():
    spec = importlib.util.spec_from_file_location("site_scene", str(WORLD / "build" / "site.py"))
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    t0 = time.time()
    scene, site, _, _, _ = S.assemble(quick=True)
    live = lv.Live(scene, site, core.load_params()["grain"]["bulk_density_t_m3"]["value"])
    print("built", round(time.time() - t0), "s", flush=True)
    blades = live.blades[GID]
    blade = next(o for o, _, _ in blades if o.name.startswith(TUN + "_"))
    nn = blade.name.split("_")[2]
    t = next(x for x in site["tunnels"] if x["id"] == TUN)
    x, size = lv.tun._gate_positions(site, t)[int(nn)]
    y, z = t["row_y"], site["silo_gates"]["stack_z"]["tza"][0]
    body = scene.objects[f"{TUN}_GATE_{nn}_BODY"]
    cut_near_half(body, y - CUT)
    scene.render.resolution_x, scene.render.resolution_y = 1280, 720
    scene.cycles.samples = 96
    scene.view_settings.exposure = 0.0
    dev = gpu(scene)
    zb = z - 0.125                                           # blade plane: half the 250 mm ТЗА body under its top
    point("C4_LAMP_A", (x + 0.1, y - 0.7, zb + 0.3), 30.0)
    point("C4_LAMP_B", (x - 0.8, y - 0.6, zb + 0.1), 20.0)
    cam = c.camera("C4_CAM", (x + 0.3, y - 0.92, zb + 0.13), (x - 0.3, y + 0.05, zb - 0.04), lens=16)
    base = Plant().state()
    for pos, name in ((0.0, "gate_closed.png"), (0.5, "gate_half.png"), (1.0, "gate_open.png")):
        st = json.loads(json.dumps(base))
        st["gates"][GID] = {"state": "closed" if pos == 0 else ("open" if pos == 1 else "opening"), "pos": pos}
        k = live.apply(st)
        for o in live.gates[GID]:
            o[lv.ON] = 0.0                                   # frames only: no glow, the blade reads against the body
            o.update_tag()
        bpy.context.view_layer.update()
        print(f"pos {pos}: apply touched {k}, blade x {blade.location.x:+.3f} (opening x {x:.3f}, bore {size:.3f})", flush=True)
        t1 = time.time()
        c.render(scene, cam, OUT / name)
        print("rendered", name, round(time.time() - t1, 1), "s on", dev, flush=True)


main()
