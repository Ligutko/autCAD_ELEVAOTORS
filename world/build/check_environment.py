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
W1b FAIL: the fence encloses every structure, hydrant and road; >= 1.5 m from every road and shoulder edge
(ДБН Б.2.2-12 табл. 7.1) except where a road passes a gate; every road through the fence has a gate >= 4.5 m
(п. 7.2.15) holding the lane and both shoulders; fence 1.6-2.0 m, mesh on a plinth (СН 441-72); posts at run ends and
<= 2.5 m apart; sliding leaves roll back along solid fence; over 5 ha -> 2 entries (п. 15.3.5); hard apron >= 1.5 m
round every structure of the stage and the designed buildings, rays down (ДСТУ-Н Б В.1.1-44 п. 12.8.3), WARN under 2.0
(ДБН В.1.1-5, loess).

Broken variants that must fail: fence on the fire road shoulder, gate 4.0 m, fence 2.4 m, a leaf rolling over the
wicket, apron 1.0 m, shoulder 0.5 m, shoulders that ignore structures, shoulders 5 cm over the ground
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


FENCE_ROAD = 1.5              # ДБН Б.2.2-12 табл. 7.1 (rec_5d6eae7a): road / shoulder edge to the site fence
FENCE_H = (1.6, 2.0)          # СН 441-72 табл. рядки 2, 6*; п. 2 not over 2 m (rec_969c0665)
GATE_MIN = 4.5                # ДБН Б.2.2-12 п. 7.2.15 (rec_575442a8)
PANEL = 2.5                   # section length (rec_02af4fc5)
APRON = (1.5, 2.0)            # ДСТУ-Н Б В.1.1-44 (rec_833d7e46) / ДБН В.1.1-5 (rec_985b02a1): FAIL under 1.5, WARN under 2.0
AREA_TWO_ENTRIES = 5.0e4      # ДБН Б.2.2-12 п. 15.3.5 (rec_639fe089): over 5 ha -> 2 entries >= 200 m apart


def _box_centres(v):
    b = v.reshape(-1, 8, 3)
    return b.mean(axis=1), b.min(axis=1), b.max(axis=1)


def fence_checks(site):
    out = []
    e = env.spec(site)
    fe = e["fence"]
    x0, y0, x1, y1 = fe["rect"]
    sp = spl.spec(site)
    ops = env.openings(site)
    sides = env.fence_sides(fe)
    g = c.ground_z()
    w_sh = SHOULDER

    def on_line(side, t):
        fixed, _, _, ax, _ = sides[side]
        return (t, fixed) if ax == 0 else (fixed, t)

    def in_opening(p, margin=0.0):
        for side, a, b, *_ in ops:
            fixed, _, _, ax, _ = sides[side]
            if abs(p[1 - ax] - fixed) < 0.6 and a - margin <= p[ax] <= b + margin:
                return True
        return False

    outside = []
    for name, k, gm in env.obstacles(site):
        ext = (gm[0] - gm[2], gm[1] - gm[2], gm[0] + gm[2], gm[1] + gm[2]) if k == "circle" else gm
        if not (x0 + 0.5 <= ext[0] and ext[2] <= x1 - 0.5 and y0 + 0.5 <= ext[1] and ext[3] <= y1 - 0.5):
            outside.append(name)
    for x, y in sp["hydrants"]:
        if not (x0 + 0.5 <= x <= x1 - 0.5 and y0 + 0.5 <= y <= y1 - 0.5):
            outside.append(f"hydrant {x},{y}")
    for ln in sp["lanes"]:
        for p in spl.lane_polyline(ln, 0.5):
            if not (x0 < p[0] < x1 and y0 < p[1] < y1) and not in_opening(p):
                outside.append(f"lane {ln['id']}")
                break
    out.append(("the fence encloses every structure, hydrant and road (roads leave only through the gates)", not outside, f"outside {outside[:6]}"))

    close = []
    frames = [(ln["id"], *env.lane_frame(ln, 0.25)) for ln in sp["lanes"]]
    for side, t0, t1 in env.fence_runs(site):
        for t in np.arange(t0, t1 + 1e-9, 0.25):
            p = on_line(side, t)
            if in_opening(p, margin=FENCE_ROAD):              # where a road passes the gate it meets the fence by design
                continue
            for lid, pts, _, hw in frames:
                d = np.min(np.hypot(pts[:, 0] - p[0], pts[:, 1] - p[1]) - hw) - w_sh
                if d < FENCE_ROAD - 1e-6:
                    close.append((lid, side, round(float(t), 1), round(float(d), 2)))
    out.append(("fence >= 1.5 m from every road and shoulder edge (ДБН Б.2.2-12 табл. 7.1)", not close, f"{len(close)} points, first {close[:4]}"))

    bad_g = []
    for ln in sp["lanes"]:
        if "pts" not in ln:
            continue
        for end in (ln["pts"][0], ln["pts"][-1]):
            on_fence = [s for s, (fixed, _, _, ax, _) in sides.items() if abs(end[1 - ax] - fixed) < 0.5]
            if not on_fence:
                continue
            side = on_fence[0]
            ax = sides[side][3]
            hw = spl.lane_width(ln, end[0]) / 2
            gate = next((op for op in ops if op[0] == side and op[3] == "gate" and op[1] <= end[ax] <= op[2]), None)
            if gate is None:
                bad_g.append((ln["id"], "no gate"))
                continue
            clear = gate[2] - gate[1]
            if clear < max(GATE_MIN, 2 * hw) or not (gate[1] <= end[ax] - hw - w_sh + 1e-6 and end[ax] + hw + w_sh <= gate[2] + 1e-6):
                bad_g.append((ln["id"], round(clear, 2), "lane + shoulders", round(end[ax] - hw - w_sh, 2), round(end[ax] + hw + w_sh, 2)))
    n_gates = sum(op[3] == "gate" for op in ops)
    out.append(("every road through the fence has a gate >= 4.5 m holding the lane and its shoulders (ДБН Б.2.2-12 п. 7.2.15)",
                not bad_g and n_gates > 0, f"{n_gates} gates, bad {bad_g}"))

    fp = env.build_fence(site)
    top = float(fp["mesh"][0][:, 2].max()) - g
    plinth = float(fp["plinth"][0][:, 2].max()) - g
    out.append(("fence 1.6-2.0 m, steel mesh on a plinth (СН 441-72 табл. рядки 2, 6*; п. 2 not over 2 m)",
                FENCE_H[0] - 1e-6 <= top <= FENCE_H[1] + 1e-6 and plinth > 0.05, f"mesh top {top:.2f} m, plinth {plinth:.2f} m"))

    cen, lo, hi = _box_centres(fp["posts"][0])
    gaps = []
    for side, t0, t1 in env.fence_runs(site):
        fixed, _, _, ax, _ = sides[side]
        on = cen[(np.abs(cen[:, 1 - ax] - fixed) < 0.05) & (cen[:, ax] >= t0 - 0.06) & (cen[:, ax] <= t1 + 0.06)
                 & (hi[:, 2] - lo[:, 2] > 1.0)]
        ts = np.sort(on[:, ax])
        if len(ts) < 2 or ts[0] > t0 + 0.06 or ts[-1] < t1 - 0.06:
            gaps.append((side, "run end without a post"))
        elif np.max(np.diff(ts)) > PANEL + 1e-6:
            gaps.append((side, round(float(np.max(np.diff(ts))), 2)))
    out.append(("posts at every run end and <= 2.5 m apart (panel length)", not gaps, f"{gaps[:4]}"))

    clash = []
    for op in ops:
        if op[3] != "gate":
            continue
        side = op[0]
        _, t0s, t1s, ax, _ = sides[side]
        l0, l1 = env.gate_leaf(fe, op)
        if l0 < t0s or l1 > t1s:
            clash.append((op[4]["lane"], "leaf runs past the corner"))
        for other in ops:
            if other is not op and other[0] == side and other[1] < l1 and l0 < other[2]:
                clash.append((op[4]["lane"], "leaf over the", other[3], round(other[1], 2)))
    out.append(("sliding gate leaves roll back along solid fence (no opening or corner in the way)", not clash, f"{clash}"))

    area = (x1 - x0) * (y1 - y0)
    far = [abs(a[1] - b[1]) for a in ops for b in ops if a[3] == b[3] == "gate"]
    two = n_gates >= 2 and max(far) >= 200.0
    out.append(("site over 5 ha needs 2 entries >= 200 m apart (ДБН Б.2.2-12 п. 15.3.5)", area <= AREA_TWO_ENTRIES or two,
                f"fenced {area / 1e4:.2f} ha, {n_gates} gates"))
    return out


def apron_checks(site):
    """Hard surface all round each structure of our stage and the designed buildings: rays down 1.5 and 2.0 m
    out from the walls must hit an apron, the concrete yard, a shoulder or a road (probed 2 cm inside each limit)."""
    out = []
    parts = [env.build_aprons(site), env.ground(site, env.ground_holes(site))["yard"], env.build_shoulders(site)[0],
             spl.build_roads(site)["roads"][2]]
    v, f = c.merge_parts(parts)
    bvh = BVHTree.FromPolygons([Vector(p) for p in v], [tuple(int(i) for i in q) for blk in f for q in blk])
    ob = env.obstacles(site)
    holes = env.ground_holes(site)
    sp = spl.spec(site)
    rf = site["silo_foundation"]["ring"]["r_out"]
    items = [(s["id"], "circle", (s["x"], s["y"], rf)) for s in site["silos"]]
    items += [(t["id"], "rect", (t["x"] - t["size"][0] / 2, t["y"] - t["size"][1] / 2, t["x"] + t["size"][0] / 2, t["y"] + t["size"][1] / 2))
              for t in site["noria_towers"]]
    for key in ("apk", "ktp"):
        items.append((key, "rect", (sp[key]["x"][0], sp[key]["y"][0], sp[key]["x"][1], sp[key]["y"][1])))
    k, ph = sp["gate"]["kpp"], sp["fire_tanks"]["pump_house"]
    items += [("kpp", "rect", (k["x"][0], k["y"][0], k["x"][1], k["y"][1])), ("pump house", "rect", (ph["x"][0], ph["y"][0], ph["x"][1], ph["y"][1]))]
    items += [("fire tank", "circle", (x, y, sp["fire_tanks"]["d"] / 2)) for x, y in sp["fire_tanks"]["c"]]
    x0, y0, x1, y1 = env.spec(site)["fence"]["rect"]
    top = float(v[:, 2].max()) + 1.0
    res = {APRON[0]: [], APRON[1]: []}
    for name, kind, gm in items:
        if kind == "circle":
            ang = np.radians(np.arange(0, 360, 4))
            base = [((gm[0] + np.cos(a) * gm[2], gm[1] + np.sin(a) * gm[2]), (np.cos(a), np.sin(a))) for a in ang]
        else:
            ax0, ay0, ax1, ay1 = gm
            base = []
            for t in np.linspace(0, 1, 25):
                base += [((ax0 + (ax1 - ax0) * t, ay0), (0, -1)), ((ax0 + (ax1 - ax0) * t, ay1), (0, 1)),
                         ((ax0, ay0 + (ay1 - ay0) * t), (-1, 0)), ((ax1, ay0 + (ay1 - ay0) * t), (1, 0))]
        for d in APRON:
            for (px, py), (nx, ny) in base:
                q = (px + nx * (d - 0.02), py + ny * (d - 0.02))              # 2 cm inside the limit: an edge ray misses on float
                if not (x0 < q[0] < x1 and y0 < q[1] < y1):
                    continue                                          # beyond the fence (the КПП wall stands 2 m off it)
                if any(spl.footprint_dist(q, kk, gg) < 0 for nm, kk, gg in ob if nm != name) or \
                        any(h[0] <= q[0] <= h[2] and h[1] <= q[1] <= h[3] for h in holes):
                    continue                                          # another structure or a pit there
                hit, *_ = bvh.ray_cast(Vector((q[0], q[1], top)), Vector((0, 0, -1)), 10.0)
                if hit is None:
                    res[d].append((name, round(q[0], 1), round(q[1], 1)))
    out.append(("hard apron >= 1.5 m round every structure of the stage and the designed buildings (ДСТУ-Н Б В.1.1-44 п. 12.8.3)",
                not res[APRON[0]], f"{len(res[APRON[0]])} bare points, first {res[APRON[0]][:4]}"))
    if res[APRON[1]]:
        names = sorted({r[0] for r in res[APRON[1]]})
        out.append(("apron under 2.0 m (loess may settle under its own weight, ДБН В.1.1-5): WARN", True, f"{names}"))
    return out


def checks(site, ob_kit=None):
    out = shoulder_checks(site, ob_kit) + ground_checks(site)
    e = env.spec(site)
    if "fence" in e:
        out += fence_checks(site)
    if "aprons" in e:
        out += apron_checks(site)
    return out


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

    def v_fence_w(s):
        s["designed"]["environment"]["fence"]["rect"][0] = -61.5
        return None
    def v_gate(s):
        s["designed"]["environment"]["fence"]["gates"][0]["clear"] = 4.0
        return None
    def v_tall(s):
        s["designed"]["environment"]["fence"]["panel_h"] = 2.2
        return None
    def v_roll(s):
        s["designed"]["environment"]["fence"]["gates"][0]["roll"] = -1
        return None
    def v_apron(s):
        s["designed"]["environment"]["aprons"]["w"] = 1.0
        return None

    variants = [("fence west side at x -61.5 (on the fire road shoulder)", v_fence_w, "1.5 m from every road"),
                ("gate 4.0 m", v_gate, "gate >= 4.5"), ("fence 2.4 m high", v_tall, "1.6-2.0"),
                ("in gate rolls south over the wicket", v_roll, "roll back"), ("apron 1.0 m", v_apron, "hard apron"),
                ("shoulder 0.5 m", v_narrow, "shoulder where free"), ("shoulders ignore structures", v_through, "inside a structure"),
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
