"""K5 test scene: inside silo МСВУ 220. Four shots from BUILD_SPEC 1.4.

Run:
    python world/build/k5_interior.py [--quick]
"""

import json
import math
import sys
import time
from pathlib import Path

import bpy  # noqa: I001  bpy first: the pip module registers bmesh and mathutils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import silo_interior as si  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402

OUT = ROOT / "out" / "k5_interior"


def volume_fog(density=0.03):
    mat = bpy.data.materials.new("SILO_DUST")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    for n in list(nodes):
        if n.type == "BSDF_PRINCIPLED":
            nodes.remove(n)
    vol = nodes.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = density
    vol.inputs["Color"].default_value = (0.95, 0.88, 0.75, 1.0)
    out = next(n for n in nodes if n.type == "OUTPUT_MATERIAL")
    links.new(vol.outputs[0], out.inputs["Volume"])
    v, f = c.cylinder(si.R_IN - 0.05, 0.02, silo.WALL_TOP + 5.5, steps=64)
    return c.mesh_from_arrays("SILO_DUST_VOLUME", v, f, mat)


def spot(name, loc, target, energy, size_deg, blend=0.15, color=(1.0, 0.95, 0.85)):
    data = bpy.data.lights.new(name, type="SPOT")
    data.energy = energy
    data.spot_size = math.radians(size_deg)
    data.spot_blend = blend
    data.shadow_soft_size = 0.05
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = loc
    from mathutils import Vector
    obj.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return obj


def main():
    quick = "--quick" in sys.argv
    OUT.mkdir(parents=True, exist_ok=True)
    scene = c.reset_scene()
    c.setup_render(scene, samples=32 if quick else 160, res=(960, 540) if quick else (1920, 1080))
    scene.cycles.volume_bounces = 1
    c.setup_sky(scene, sun_elevation_deg=35.0, sun_rotation_deg=150.0)
    t0 = time.time()
    full = bpy.data.collections.new("FULL")
    cutc = bpy.data.collections.new("CUTAWAY")
    scene.collection.children.link(full)
    scene.collection.children.link(cutc)
    silo.build(collection=full)
    objs, labels_def, measure, hatch = si.build(collection=full, fill=0.0)
    grain = c.mesh_from_arrays("SILO_IN_GRAIN_30", *si.build_grain(0.3), si.mat_grain("WHEAT_30"), smooth=True,
                               collection=full)
    # cutaway set: the half facing the camera removed, section faces for the foundation and the grain
    cut_n = (34.0, -24.0)
    silo.build(collection=cutc, cut=cut_n)
    si.build(collection=cutc, fill=0.0, cut=cut_n)
    gv, gf = si.build_grain(0.3)
    c.mesh_from_arrays("CUT_GRAIN", *c.cut_mesh(gv, gf, cut_n), si.mat_grain("WHEAT_CUT"), smooth=True, collection=cutc)
    n = math.hypot(*cut_n)
    nx, ny = cut_n[0] / n, cut_n[1] / n
    c.mesh_from_arrays("CUT_GRAIN_SECTION", *si.grain_section(0.3, (nx, ny)), bpy.data.materials["WHEAT_CUT"],
                       collection=cutc)
    t = (-ny, nx)
    fr = silo.FOUND_R
    fv = [(-t[0] * fr, -t[1] * fr, -silo.FOUND_H), (t[0] * fr, t[1] * fr, -silo.FOUND_H),
          (t[0] * fr, t[1] * fr, 0.0), (-t[0] * fr, -t[1] * fr, 0.0)]
    import numpy as np
    c.mesh_from_arrays("CUT_FOUNDATION_SECTION", np.array(fv), np.array([(0, 1, 2, 3)]),
                       bpy.data.materials["SILO_FOUNDATION"], collection=cutc)
    label_objs = c.labels(labels_def, "SILO_IN")
    v, f = c.box((-800, -800, -0.8), (800, 800, -0.6))
    c.mesh_from_arrays("GROUND", v, f, c.mat_ground())
    fog = volume_fog()
    measure["build_seconds"] = round(time.time() - t0, 1)

    # light through the roof hatch and a dim bounce light
    beam = spot("HATCH_SUN", tuple(hatch - [0, 0, 0.35]), (hatch[0] * 0.25, hatch[1] * 0.25, 0.0), 450000, 9, blend=0.05)
    bounce = bpy.data.lights.new("BOUNCE", type="AREA")
    bounce.energy = 250
    bounce.size = 8.0
    bounce_obj = bpy.data.objects.new("BOUNCE", bounce)
    scene.collection.objects.link(bounce_obj)
    bounce_obj.location = (0, 0, 13.5)

    door = math.radians(silo.DOOR_ANGLE)
    gz = 0.3 * silo.WALL_TOP
    shots = [
        ("k5_floor_from_door.png", c.camera("CAM_DOOR", (9.6 * math.cos(door), 9.6 * math.sin(door), 1.7),
                                            (0.0, 0.0, 0.4), lens=16), 0.0, True),
        ("k5_on_grain.png", c.camera("CAM_GRAIN", (6.5 * math.cos(door + 0.5), 6.5 * math.sin(door + 0.5),
                                                   gz + (si.R_IN - 6.5) * math.tan(si.REPOSE) + 1.7),
                                     (0.0, 0.0, gz + si.R_IN * math.tan(si.REPOSE) + 1.2), lens=18), 0.3, True),
        ("k5_light_shaft.png", c.camera("CAM_SHAFT", (6.0, -6.0, gz + 3.8), (hatch[0] * 0.6, hatch[1] * 0.6, 8.0),
                                        lens=18), 0.3, False),
        ("k5_cutaway.png", c.camera("CAM_CUT", (34.0, -24.0, 13.0), (0.0, 0.0, 5.0), lens=28), 0.3, True),
    ]
    (OUT / "measure.json").write_text(json.dumps(measure, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(measure, ensure_ascii=False))
    for name, cam, fill, with_labels in shots:
        grain.hide_render = fill == 0.0
        cutaway = name == "k5_cutaway.png"
        full.hide_render = cutaway
        cutc.hide_render = not cutaway
        fog.hide_render = cutaway
        beam.hide_render = cutaway
        for lo in label_objs:
            lo.hide_render = not with_labels
        bpy.context.view_layer.update()
        if with_labels:
            c.face_labels(label_objs, cam, max_dist=60.0 if cutaway else 14.0)
        t = time.time()
        if with_labels:
            c.render_with_labels(scene, cam, OUT / name, label_objs)
        else:
            c.render(scene, cam, OUT / name)
        print("rendered", name, round(time.time() - t, 1), "s", flush=True)


if __name__ == "__main__":
    main()
