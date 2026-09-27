"""Phase W1 check: the environment (world/kit/environment.py, research/design/environment.md).

FAIL:
  shoulders: every road edge carries a hardened shoulder of the design width 1.0 m (СНиП 2.05.07-91 табл. 46,
  п. 5.22) wherever no structure stands closer; measured by casting rays down on the built strip at points
  sampled independently of the kit (other step, own free-width march on site_plan.footprint_dist);
  no shoulder vertex lies inside a structure footprint (> 1 cm);
  shoulders lie over the ground and under every road ribbon (no z-fighting, roads stay on top);
  ground: yard + grass cover exactly the ground of tunnel.ground_cells with the same holes (no gaps, no overlap).
FINDING: stretches where a structure leaves less than 1.0 m of shoulder, with the least width.
WARN: a silo plinth, tower or dust bin not wholly inside the hard-surface yard (judgment).

  every shoulder face points up (a face turned down renders black at the road corners);
  no shoulder face lies within 1 mm over another (coplanar overlaps at corners and junctions render black).
Broken variants that must fail: shoulder 0.5 m, shoulders that ignore structures, shoulders 5 cm over the ground
(over the roads), shoulder faces turned down, all strips on one level.

Run:
    blender --background --python world/build/check_environment.py
"""

import copy
import json
import sys
from pathlib import Path

import bpy  # noqa: F401,I001  bpy first: the pip module registers mathutils
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import environment as env  # noqa: E402
from kit import site_plan as spl  # noqa: E402
from kit import tunnel as tun  # noqa: E402

STEP = 0.37                   # sampling step along the lanes, not the kit's 0.25
MARCH = 0.01                  # own free-width march
SHOULDER = 1.0                # СНиП 2.05.07-91 табл. 46, IV-в (rec_3710fc66): the norm, not the data value
INSIDE_TOL = 0.01


def free_width(p, n, ob, w):
    """Distance from road-edge point p along n until a footprint (own scalar march), capped at w."""
    near = [o for o in ob if spl.footprint_dist(p, o[1], o[2]) < w + 0.5]
    d = 0.0
    while d < w - 1e-9:
        q = (p[0] + n[0] * (d + MARCH), p[1] + n[1] * (d + MARCH))
        if any(spl.footprint_dist(q, k, g) < 0 for _, k, g in near):
            return d, next(nm for nm, k, g in near if spl.footprint_dist(q, k, g) < 0)
        d += MARCH
    return w, None


def shoulder_checks(site, ob_kit=None):
    out = []
    w = SHOULDER
    ob = env.obstacles(site)
    (v, f), _ = env.build_shoulders(site, ob_kit)
    bvh = BVHTree.FromPolygons([Vector(p) for p in v], [tuple(int(i) for i in q) for blk in f for q in blk])
    z_sh = float(v[:, 2].max()) if len(v) else c.ground_z()

    missing, short = [], {}
    for ln in spl.spec(site)["lanes"]:
        pts, nrm, hw = env.lane_frame(ln, STEP)
        corners = [tuple(p) for p in ln.get("pts", [])[1:-1]]
        for i in range(1, len(pts) - 1):                                  # ends sit in a junction or at the gate
            if any(abs(pts[i][0] - x) < 1e-6 and abs(pts[i][1] - y) < 1e-6 for x, y in corners):
                continue                                                  # a corner point has no single normal
            for side in (1.0, -1.0):
                n = nrm[i] * side
                edge = pts[i] + n * hw[i]
                fw, by = free_width(edge, n, ob, w)
                if fw < w - 1e-6:
                    s = short.setdefault((ln["id"], by), [9.0, 0.0])
                    s[0], s[1] = min(s[0], fw), s[1] + STEP
                if fw < 0.1:
                    continue
                probe = edge + n * (fw - 0.06)
                hit, *_ = bvh.ray_cast(Vector((probe[0], probe[1], z_sh + 1.0)), Vector((0, 0, -1)), 2.0)
                if hit is None:
                    missing.append((ln["id"], round(float(probe[0]), 2), round(float(probe[1]), 2), round(fw, 2)))
    out.append((f"every road edge has a {w} m shoulder where free (СНиП табл. 46, п. 5.22), rays on the built strip",
                not missing, f"{len(missing)} probes miss, first {missing[:4]}"))
    if short:
        worst = {f"{k[0]} by {k[1]}": (round(a, 2), round(b, 1)) for k, (a, b) in short.items()}
        out.append(("shoulder under 1.0 m where a structure stands at the road: FINDING", True,
                    f"(least width m, length m) {dict(sorted(worst.items(), key=lambda kv: kv[1][0])[:8])}"))

    inside = []
    for p in v:
        for name, k, g in ob:
            d = spl.footprint_dist((p[0], p[1]), k, g)
            if d < -INSIDE_TOL:
                inside.append((name, round(float(p[0]), 2), round(float(p[1]), 2), round(d, 3)))
                break
    out.append(("no shoulder vertex inside a structure footprint", not inside, f"{len(inside)} vertices, first {inside[:3]}"))

    down = 0
    for blk in f:
        p = v[np.asarray(blk)]
        down += int(np.sum(np.cross(p[:, 1] - p[:, 0], p[:, -1] - p[:, 0])[:, 2] <= 0))
    out.append(("every shoulder face points up (a face turned down renders black)", down == 0, f"{down} of {sum(len(b) for b in f)} faces down"))

    stacked = []
    for blk in f:
        for q in np.asarray(blk)[::3]:
            cen = v[q].mean(axis=0)
            near = {r[2] for r in bvh.find_nearest_range(Vector(cen), 1e-3)}  # polygon indices (a quad is 2 triangles)
            if len(near) > 1:                                                 # itself plus a face in (or within 1 mm of) its plane
                stacked.append((round(float(cen[0]), 2), round(float(cen[1]), 2)))
    out.append(("no shoulder face lies within 1 mm over another (coplanar overlaps render black in Cycles)", not stacked,
                f"{len(stacked)} stacked, first {stacked[:4]}"))

    g = c.ground_z()
    road_z = g + spl.spec(site)["road_z_over_ground"]
    zmin = float(v[:, 2].min()) if len(v) else g
    out.append(("shoulders over the ground and under every road ribbon", g < zmin and z_sh < road_z - 1e-4,
                f"shoulder z {zmin:.3f}..{z_sh:.3f}, ground {g:.3f}, lowest road {road_z:.3f}"))
    return out


def ground_checks(site):
    out = []
    holes = env.ground_holes(site)
    parts = env.ground(site, holes)
    z = c.ground_z()
    a_yard, a_grass = (env.top_area(*parts[k], z) for k in ("yard", "grass"))
    a_ref = env.top_area(*tun.ground_cells(2000, holes), z)
    out.append(("yard + grass cover exactly the ground of tunnel.ground_cells (same holes)",
                abs(a_yard + a_grass - a_ref) < 0.5, f"yard {a_yard:.0f} + grass {a_grass:.0f} vs {a_ref:.0f} m²"))
    rects = env.spec(site)["yard"]["rects"]
    in_yard = lambda x0, y0, x1, y1: any(r[0] <= x0 and x1 <= r[2] and r[1] <= y0 and y1 <= r[3] for r in rects)
    out_ = []
    rf = site["silo_foundation"]["ring"]["r_out"]
    for s in site["silos"]:
        if not in_yard(s["x"] - rf, s["y"] - rf, s["x"] + rf, s["y"] + rf):
            out_.append(s["id"])
    for t in site["noria_towers"]:
        hx, hy = t["size"][0] / 2, t["size"][1] / 2
        if not in_yard(t["x"] - hx, t["y"] - hy, t["x"] + hx, t["y"] + hy):
            out_.append(t["id"])
    for b in site["aspiration"]["dust_bins"]:
        (cx, cy), (fx, fy) = b["center"], b["frame"]
        if not in_yard(cx - fx / 2, cy - fy / 2, cx + fx / 2, cy + fy / 2):
            out_.append(f"bin {b['id']}")
    if out_:
        out.append(("structures outside the hard-surface yard: WARN", True, f"{out_}"))
    return out


def checks(site, ob_kit=None):
    return shoulder_checks(site, ob_kit) + ground_checks(site)


def main():
    run(json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8")))


def run(site):
    ok_all = True
    for name, ok, info in checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    def v_narrow(s):
        s["designed"]["environment"]["shoulder"]["w"] = 0.5
        return None
    def v_through(s):
        return []
    def v_high(s):
        s["designed"]["environment"]["shoulder"]["z_over_ground"] = 0.05
        return None

    def v_down(s):
        env._faces_up = lambda v, f: np.asarray(f)[:, ::-1] if np.asarray(f).ndim == 2 else f
        return None
    def v_flat(s):
        s["designed"]["environment"]["shoulder"]["z_step"] = 0.0
        return None

    variants = [("shoulder 0.5 m", v_narrow, "shoulder where free"), ("shoulders ignore structures", v_through, "inside a structure"),
                ("shoulders 5 cm over the ground", v_high, "under every road"), ("shoulder faces turned down", v_down, "points up"),
                ("all shoulder strips on one level", v_flat, "within 1 mm")]
    faces_up = env._faces_up
    for name, patch, expect in variants:
        bad = copy.deepcopy(site)
        ob = patch(bad)
        try:
            failed = [n for n, ok, _ in checks(bad, ob) if not ok]
        finally:
            env._faces_up = faces_up
        hit = any(expect in n for n in failed)
        ok_all &= hit
        print(f"{'PASS' if hit else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
