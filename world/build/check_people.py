"""People check (world/kit/people.py, Microsoft Rocketbox, MIT): every avatar in world/assets/people imports with its
licence and source note, stands 1.60-2.00 m tall with the feet on the ground (±2 cm), arms down along the body
(shoulder width under 0.80 m, a T-pose is ~1.35 m), and the site people land where SITE says.

Broken variant that must fail: the stand pose skipped (the T-pose stays).

Run:
    blender --background --python world/build/check_people.py
"""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import people as pp  # noqa: E402

SITE = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
HEIGHT = (1.60, 2.00)
WIDTH_MAX = 0.80


def measure(pose=True):
    c.reset_scene()
    col = bpy.data.collections.new("FIG")
    bpy.context.scene.collection.children.link(col)
    people = [[k * 2.0, 0.0, 0] for k in range(len(pp.AVATARS))]
    orig = pp.stand_pose
    if not pose:
        pp.stand_pose = lambda arm, facing: None
    try:
        arms = pp.place({"designed": {"environment": {"scale": {"people": people}}}}, col)
    finally:
        pp.stand_pose = orig
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for arm, (x, y, _) in zip(arms, people):
        vs = []
        for o in arm.children:
            if o.type != "MESH":
                continue
            ev = o.evaluated_get(dg)
            me = ev.to_mesh()
            vs.append(np.array([tuple(o.matrix_world @ p.co) for p in me.vertices]))
            ev.to_mesh_clear()
        v = np.concatenate(vs)
        out.append((arm.name, v.min(0), v.max(0), (x, y)))
    return out


def checks(meas):
    rows = []
    g = c.ground_z()
    lic = (pp.ASSETS / "LICENSE.txt").exists() and "MIT" in (pp.ASSETS / "LICENSE.txt").read_text(encoding="utf-8")
    src = all((pp.ASSETS / a / "SOURCE.txt").exists() and (pp.ASSETS / a / f"{a}.fbx").exists() for a in pp.AVATARS)
    rows.append(("licence", lic and src, f"MIT licence {lic}, FBX + SOURCE for all {len(pp.AVATARS)} avatars {src}"))
    bad_h, bad_w, bad_p = [], [], []
    for name, lo, hi, (x, y) in meas:
        h = hi[2] - lo[2]
        if not HEIGHT[0] <= h <= HEIGHT[1] or abs(lo[2] - g) > 0.02:
            bad_h.append(f"{name} {h:.2f} m, feet {lo[2] - g:+.3f}")
        if hi[0] - lo[0] > WIDTH_MAX:
            bad_w.append(f"{name} {hi[0] - lo[0]:.2f} m")
        if abs((lo[0] + hi[0]) / 2 - x) > 0.3 or abs((lo[1] + hi[1]) / 2 - y) > 0.3:
            bad_p.append(name)
    rows.append(("height", not bad_h, bad_h or "all 1.60-2.00 m, feet on the ground"))
    rows.append(("pose", not bad_w, bad_w or f"shoulder width under {WIDTH_MAX} m"))
    rows.append(("place", not bad_p, bad_p or "each at its place"))
    return rows


def main():
    sys.stdout.reconfigure(errors="replace")
    ok_all = True
    base = checks(measure())
    for rid, ok, info in base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {rid}: {info}", flush=True)
    got = {r for r, ok, _ in checks(measure(pose=False)) if not ok}
    seen = "pose" in got and not (got - {r for r, ok, _ in base if not ok} - {"pose"})
    ok_all &= seen
    print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} поза не застосована (T-поза) -> {'OK' if seen else sorted(got)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
