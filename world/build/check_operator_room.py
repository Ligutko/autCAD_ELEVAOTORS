"""Operator room check (world/kit/operator_room.py) on the meshes against the sources in
world/kit/data/operator_room.json (Grok T7a):

FAIL:
- the room is the east 4.5 x 9 m of the АПК block (SITE designed.site_plan.apk rooms), inside the block;
- console top 750 mm, frame 1230 x 1050 (Knürr Dacobas) ±1 mm;
- seated eye to the screens >= 700 mm (ISO 11064-4, ДСанПіН 600-700), the screens stand on the console;
- the screen centre lies 0-40° under the eye horizontal (main zone, ISO 11064);
- the sight line from the seated eye to the middle of the inbound scales passes through a south window opening;
- chair seats 400-520 mm (RH Secure24 range, ДСанПіН 400-500 overlaps);
- no clash between the furniture, the walls and each other (BVH; things standing on the floor tested 2 mm up).

Broken variants that must fail their own rule: console frame 1500 mm, screens 0.5 m from the eye, windows moved to the
north wall.

Run:
    blender --background --python world/build/check_operator_room.py
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import operator_room as opr  # noqa: E402
from kit import site_plan as spl  # noqa: E402

SITE = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
D = json.loads((ROOT / "kit" / "data" / "operator_room.json").read_text(encoding="utf-8"))
EYE_MIN = D["ergonomics"]["дистанція_рекомендована_мм"]["v"] / 1000
DOWN_MAX = D["ergonomics"]["основна_зона_вертикаль_град"]["v"]
SEAT = [v / 1000 for v in D["chair"]["rh_secure24_висота_мм"]["v"]]


def _bb(p):
    v = np.asarray(p[0], float)
    return v.min(0), v.max(0)


def _bvh(data, dz=0.0):
    v, f = data
    polys = [tuple(int(i) for i in row) for b in (f if isinstance(f, list) else [f]) for row in np.asarray(b)]
    return BVHTree.FromPolygons([tuple(p) for p in np.asarray(v, float) + (0, 0, dz)], polys)


def checks(site, parts=None, L=None):
    out = []
    L = L or opr.layout(site)
    parts = parts or opr.build(site)
    ap = site["designed"]["site_plan"]["apk"]
    x0, y0, x1, y1, h = L["room"]
    ok = abs((x1 - x0) - 4.5) < 1e-6 and abs((y1 - y0) - 9.0) < 1e-6 and ap["x"][0] <= x0 and x1 <= ap["x"][1] + 1e-9
    out.append(("room", ok, f"room {x1 - x0:.2f} x {y1 - y0:.2f} at x {x0:.2f}-{x1:.2f} in АПК {ap['x']}"))
    c0, c1 = _bb(parts["op_console"][2])
    top = c1[2] - L["g"]
    ok = abs(top - 0.75) < 1e-3 and abs((c1[0] - c0[0]) - 1.33) < 1e-3 and abs((c1[1] - c0[1]) - 1.05) < 1e-3
    out.append(("console", ok, f"top {top * 1000:.0f} mm, {(c1[0] - c0[0]) * 1000:.0f} x {(c1[1] - c0[1]) * 1000:.0f} mm (frame 1230 + 2 x 50 top overhang)"))
    s0, s1 = _bb(parts["op_screens"][2])
    eye = L["eye"]
    dist = eye[1] - s1[1]
    on = c0[0] <= s0[0] and s1[0] <= c1[0] and c0[1] <= s0[1] <= c1[1]
    out.append(("eye", dist >= EYE_MIN - 1e-6 and on, f"eye to screen {dist * 1000:.0f} mm (>= {EYE_MIN * 1000:.0f}), on the console {on}"))
    sc = (s0 + s1) / 2
    down = math.degrees(math.atan2(eye[2] - sc[2], eye[1] - sc[1]))
    out.append(("gaze", 0.0 <= down <= DOWN_MAX, f"screen centre {down:.1f}° under the eye horizontal (0-{DOWN_MAX})"))
    sp = site["designed"]["site_plan"]
    sx0, sy0, sx1, sy1 = spl.scales_box(sp, "scales_in")
    target = np.array([(sx0 + sx1) / 2, (sy0 + sy1) / 2, L["g"] + 0.35])
    t = (y0 - eye[1]) / (target[1] - eye[1])
    hit = eye + t * (target - eye)
    ww, wh, sill = opr.WIN
    through = any(abs(hit[0] - wx) <= ww / 2 and L["g"] + sill <= hit[2] <= L["g"] + sill + wh and abs(wy - y0) < 1e-6
                  for wx, wy in L["windows"])
    out.append(("view", through, f"sight line to the scales crosses the south wall at x {hit[0]:.2f}, z {hit[2] - L['g']:.2f}: window {through}"))
    ch = np.asarray(parts["op_chairs"][2][0], float)
    ch = ch[np.hypot(ch[:, 0] - eye[0], ch[:, 1] - eye[1]) < 0.45]      # the operator's chair only
    seat = None                                   # the seat: the highest level whose vertices span >= 0.4 m in X and Y
    for z in sorted(set(np.round(ch[:, 2], 4)), reverse=True):
        lv = ch[np.abs(ch[:, 2] - z) < 1e-4]
        if np.ptp(lv[:, 0]) >= 0.4 and np.ptp(lv[:, 1]) >= 0.4 and z - L["g"] < 0.9:
            seat = z - L["g"]
            break
    seat = seat or 0.0
    out.append(("seat", SEAT[0] <= seat <= SEAT[1], f"seat {seat * 1000:.0f} mm ({SEAT})"))
    hits = []
    touch = {("op_console", "op_monitors"), ("op_monitors", "op_screens")}          # a monitor stands on the console
    names = [n for n in parts if n not in ("op_floor", "op_ceiling", "op_walls")]
    for i, a in enumerate(names):
        ta = _bvh(parts[a][2], 0.002)
        for b in names[i + 1:] + ["op_walls"]:
            if (a == "op_window_frames" and b == "op_walls") or (a, b) in touch or (b, a) in touch:
                continue
            if ta.overlap(_bvh(parts[b][2])):
                hits.append(f"{a} x {b}")
    out.append(("clash", not hits, hits[:6] or "clean"))
    return out


def main():
    sys.stdout.reconfigure(errors="replace")
    ok_all = True
    base = checks(SITE)
    for rid, ok, info in base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {rid}: {info}", flush=True)
    base_fail = {r for r, ok, _ in base if not ok}

    def high_console():
        d = opr._d()
        d["console_dacobas"]["ширина_рами_мм"]["v"] = 1500
        orig = opr._d
        opr._d = lambda: d
        try:
            return checks(SITE)
        finally:
            opr._d = orig

    def near_screen():
        L = opr.layout(SITE)
        parts = opr.build(SITE)
        v, f = parts["op_screens"][2]
        v = np.asarray(v, float) + (0, (L["eye"][1] - 0.5) - np.asarray(v)[:, 1].max(), 0)
        parts["op_screens"] = (parts["op_screens"][0], parts["op_screens"][1], (v, f))
        return checks(SITE, parts, L)

    def north_windows():
        L = opr.layout(SITE)
        L["windows"] = [(x, L["room"][3]) for x, _ in L["windows"]]
        return checks(SITE, None, L)

    for rid, title, fn in (("console", "рама консолі 1500 мм", high_console), ("eye", "екран за 0,5 м", near_screen),
                           ("view", "вікна на північній стіні", north_windows)):
        got = {r for r, ok, _ in fn() if not ok}
        seen = rid in got and not (got - base_fail - {rid})
        ok_all &= seen
        print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} {title} -> {'OK' if seen else sorted(got)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
