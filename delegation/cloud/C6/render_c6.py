"""C6 frames (Cycles GPU OptiX, 960x540): the MCC room in the КТП block.

    blender --background --python delegation/cloud/C6/render_c6.py -- [aisle,plan,outside] [samples]

aisle   - mcc_aisle.png: along the aisle from 1.6 m eye height just inside the door (the scene camera site_mcc.png);
plan    - mcc_plan.png: from above with the КТП roof and the MCC ceiling hidden (roof cut);
outside - ktp_outside.png: the block from the south-west at a person's eye: walls, three doors, trestle, roof.
"""
import importlib.util
import sys
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
which = args[0].split(",") if args else ["aisle", "plan", "outside"]
samples = int(args[1]) if len(args) > 1 else 96

spec = importlib.util.spec_from_file_location("site_scene", str(ROOT / "world" / "build" / "site.py"))
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
c = S.c
scene, site, *_ = S.assemble(quick=True)
scene.render.resolution_x, scene.render.resolution_y = 960, 540
scene.cycles.samples = samples
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type == "OPTIX"
scene.cycles.device = "GPU"
scene.cycles.denoiser = "OPTIX"
g = c.ground_z()
base_exp = scene.view_settings.exposure


def hide(names, state=True):
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob:
            ob.hide_render = state


if "aisle" in which:
    cam = c.camera("CAM_C6_AISLE", (22.25, 26.75, g + 1.6), (22.0, 31.6, g + 1.1), lens=16)
    scene.view_settings.exposure = base_exp + 2.0          # a camera indoors opens up (EST, judgment)
    c.render(scene, cam, OUT / "mcc_aisle.png")
    print("rendered mcc_aisle.png", flush=True)
if "plan" in which:
    hide(["SITE_PLAN_KTP_ROOF", "SITE_PLAN_MCC_CEILING", "SITE_PLAN_MCC_LAMPS"])
    cam = c.camera("CAM_C6_PLAN", (22.25, 28.4, g + 16.0), (22.25, 29.0, g), lens=35)
    scene.view_settings.exposure = base_exp
    c.render(scene, cam, OUT / "mcc_plan.png")
    hide(["SITE_PLAN_KTP_ROOF", "SITE_PLAN_MCC_CEILING", "SITE_PLAN_MCC_LAMPS"], False)
    print("rendered mcc_plan.png", flush=True)
if "outside" in which:
    cam = c.camera("CAM_C6_OUT", (14.0, 19.5, g + 1.7), (25.0, 29.0, g + 1.6), lens=24)
    scene.view_settings.exposure = base_exp
    c.render(scene, cam, OUT / "ktp_outside.png")
    print("rendered ktp_outside.png", flush=True)
