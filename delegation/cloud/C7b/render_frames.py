"""C7b frames (960 x 540, Cycles): wet_fan.png, ktp_open.png, ktp_outside.png into delegation/cloud/C7b/.

    blender --background --python delegation/cloud/C7b/render_frames.py -- [--only=wet_fan.png] [--samples=48]

The scene is the full site (world/build/site.py assemble); for ktp_open the roof and the chamber ceilings are hidden (a section
from above) and the closed door leaves are hidden, so the open doorways show the transformer.
"""
import importlib.util
import sys
import time
from pathlib import Path

import bpy  # noqa: F401

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "world"))
spec = importlib.util.spec_from_file_location("site_scene", ROOT / "world" / "build" / "site.py")
site_scene = importlib.util.module_from_spec(spec)
spec.loader.exec_module(site_scene)
from kit import common as c  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
only = [a.split("=", 1)[1] for a in args if a.startswith("--only=")]
samples = next((int(a.split("=", 1)[1]) for a in args if a.startswith("--samples=")), 48)

scene, site, *_ = site_scene.assemble(quick=True)
scene.cycles.samples = samples
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for dev in prefs.devices:
    dev.use = dev.type == "OPTIX"
scene.cycles.device = "GPU"
g = c.ground_z()
FRAMES = {
    "wet_fan.png": dict(cam=((-4.0, 58.2, g + 1.6), (-8.4, 59.0, g + 0.6), 30), hide=(), ev=1.2),
    "ktp_open.png": dict(cam=((27.4, 20.2, 4.6), (27.2, 30.3, g + 0.8), 30), hide=("KTP_ROOF", "KTP_CEILING", "BUILDING_DOORS", "KTP_LOUVRES"), cut=True, ev=0.8),
    "ktp_outside.png": dict(cam=((38.0, 18.0, g + 3.5), (26.0, 29.0, g + 1.6), 28), hide=()),
}
base_ev = scene.view_settings.exposure


def cut_south_wall():
    """Section: a second copy of the chamber walls without the south wall (mcc_room.chamber_shell faults {"section"}); the full walls are hidden."""
    from kit import mcc_room as mcc
    L = mcc.layout(site)
    mat, smooth, (v, f) = mcc.chamber_shell(L, {"section": True})["ktp_trafo"]
    full = next(o for o in scene.objects if o.name.upper().endswith("KTP_TRAFO"))
    sec = c.mesh_from_arrays("KTP_TRAFO_SECTION", v, f, full.active_material or full.data.materials[0], smooth=smooth)
    full.hide_render = True
    return full, sec


for name, fr in FRAMES.items():
    if only and name not in only:
        continue
    hidden = [o for o in scene.objects if any(k in o.name.upper() for k in fr["hide"])]
    cut = cut_south_wall() if fr.get("cut") else None
    for o in hidden:
        o.hide_render = True
    scene.view_settings.exposure = base_ev + fr.get("ev", 0.0)
    cam = c.camera("CAM_" + name[:-4].upper(), fr["cam"][0], fr["cam"][1], lens=fr["cam"][2])
    t = time.time()
    c.render(scene, cam, OUT / name)
    print("rendered", OUT / name, round(time.time() - t, 1), "s", flush=True)
    for o in hidden:
        o.hide_render = False
    if cut:
        cut[0].hide_render = False
        bpy.data.objects.remove(cut[1])
