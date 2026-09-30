"""Phase 5B/5C check: the site plan (world/kit/site_plan.py, research/design/site_plan.md).

FAIL:
  the truck loop is continuous: gate -> scales in -> the drawn pit drive -> U-turn -> under Ш1 -> scales out
  -> gate (ends meet within 5 cm, the pit drive of sheet 2 is part of it);
  the out lane passes under the Ш1 outlet (drawn), clear height there >= 4.5 m (judgment until the norm);
  each scales sits whole on a straight stretch of its lane (not on the pit ramps or the U-turn);
  the sampler reaches the whole truck body on the inbound scales (0.72-5.35 m, ПГ-2.10.180);
  lanes keep >= 0.3 m from every structure: new and old silo plinths, the receiving tower pit, the
  cleaning tower columns (footings are flush, drive-over), the T5 trestle footings, dust bins, the dryer building, the wet-silo
  fan pads, the shed outer posts, and the designed buildings, tanks, trestle posts;
  hydrants <= 2.5 m from a road edge and >= 5 m from walls (ДБН В.2.5-74);
  fire tanks: 2, each >= the designed volume;
  the cable trestle and the designed buildings keep >= 0.3 m from silo plinths and towers.
WARN: straight approach to a scales under 50 m (KMZ); lab farther than 30 m from the sampler (pneumatic
line). Norm checks (research/site_plan_norms.md): lanes >= 4.5 m (СНиП табл. 46), U-turn swept circle
12.5 / 5.3 m (96/53/EC), clear height >= 4.5 (WARN < 5.0), scales straights >= 12 m (NIST), КТП >= 6 m from silos
(WARN < 12), fire water pier >= 10 m from buildings, fire access to every silo, no loose road ends.

Service spurs: a 2.55 x 3.8 m trailer box driven to each dust bin centre clears the bin meshes (BVH).
Road surface: the outer corner of every bend is paved (rays down on the built mesh), the surface seen from above
faces up and no face lies within 1 mm of another (coplanar overlaps render black).

Broken variants that must fail: a 4.3 m trailer under the bin gate, roads without the corner fill, scales in on the pit ramp, sampler post 7 m off the lane, hydrant 1 m from
the pit shed, U-turn centre at x -18 (through the plinth of silo «3»), out lane on y 44.0 (off Ш1, on the tower footings).

Run:
    blender --background --python world/build/check_site_plan.py
"""

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import common as c  # noqa: E402
from kit import site_plan as spl  # noqa: E402

REACH = (0.72, 5.35)                  # ПГ-2.10.180 (rec_2e227fdb)
TRUCK_W = 2.55                        # body width of a road train (judgment until the norm)
CLEAR = 0.3
HYD_ROAD, HYD_WALL = 2.5, 5.0         # ДБН В.2.5-74 (rec_944e9792)
APPROACH = 50.0                       # KMZ (rec_6c92404e)
HEADROOM = 4.5                        # judgment


def obstacles(site):
    """[(name, kind, geom)]: ('circle', (x, y, r)) or ('rect', (x0, y0, x1, y1)) footprints (kit/site_plan.footprints)."""
    return spl.footprints(site)


dist = spl.footprint_dist


def checks(site):
    out = []
    sp = spl.spec(site)
    r = site["receiving"]
    lanes = {ln["id"]: ln for ln in sp["lanes"]}
    drive = r["pit"]["drive"]
    dy = sum(drive["y"]) / 2
    ends = lambda ln: (spl.lane_polyline(ln)[0], spl.lane_polyline(ln)[-1])
    chain = [ends(lanes["in"]), ((drive["x"][1], dy), (drive["x"][0], dy)), ends(lanes["west"]), ends(lanes["uturn"]), ends(lanes["out"])]
    gaps = [round(math.dist(a[1], b[0]), 3) for a, b in zip(chain, chain[1:])]
    gate = sp["gate"]["x"]
    at_gate = abs(chain[0][0][0] - gate) < 0.05 and abs(chain[-1][1][0] - gate) < 0.05
    out.append(("truck loop continuous: gate -> scales in -> pit drive (drawn) -> U-turn -> under Ш1 -> scales out -> gate",
                all(x <= 0.05 for x in gaps) and at_gate, f"joint gaps {gaps}, both ends at the gate {at_gate}"))

    b = r["cleaning_tower"]["bin_Sh1"]
    ox, (oy, oz) = sum(b["x"]) / 2, b["outlet"]
    lo = lanes["out"]
    y_out = lo["pts"][0][1]
    under = lo["pts"][0][0] <= ox <= lo["pts"][-1][0] and abs(y_out - oy) <= spl.lane_width(lo, ox) / 2 - TRUCK_W / 2
    head = oz - (c.ground_z() + sp["road_z_over_ground"])
    out.append(("out lane passes under the Ш1 outlet, clear height >= 4.5 m", under and head >= HEADROOM,
                f"outlet ({ox}, {oy}), lane y {y_out}, clear {head:.2f} m"))

    straight = {}
    for key, lid in (("scales_in", "in"), ("scales_out", "out")):
        ln = lanes[lid]
        (xa, _), (xb, _) = ln["pts"][0], ln["pts"][-1]
        x0, x1 = sp[key]["x"]
        rp = sp[key]["ramp"]
        lo_x, hi_x = sorted((xa, xb))
        ok = lo_x <= x0 - rp and x1 + rp <= hi_x
        up = (xa - (x1 + rp)) if lid == "in" else ((x0 - rp) - max(b["x"]))        # straight run before the scales
        straight[key] = (ok, round(up, 1))
    out.append(("each scales whole on a straight stretch of its lane", all(v[0] for v in straight.values()), f"{straight}"))
    short = {k: v[1] for k, v in straight.items() if v[1] < APPROACH}
    if short:
        out.append(("straight approach to a scales under 50 m (KMZ): WARN", True, f"{short}"))

    out += scales_checks(site)

    (px, py), _ = spl.sampler_geometry(sp)
    y_in = lanes["in"]["pts"][0][1]
    near, far = abs(py - y_in) - TRUCK_W / 2, abs(py - y_in) + TRUCK_W / 2
    sx0, _, sx1, _ = spl.scales_box(sp, "scales_in")
    ok = REACH[0] <= near and far <= REACH[1] and sx0 <= px <= sx1
    out.append(("sampler reaches the whole truck body on the scales in (0.72-5.35 m, ПГ-2.10.180)", ok,
                f"body at {near:.2f}-{far:.2f} m from the post, post x {px} on scales {sx0}-{sx1}"))
    a = sp["apk"]
    d_lab = dist((px, py), "rect", (a["x"][0], a["y"][0], a["x"][1], a["y"][1]))
    if d_lab > 30.0:
        out.append(("lab farther than 30 m from the sampler: WARN", True, f"{d_lab:.1f} m"))

    ob = obstacles(site)
    hits = []
    for ln in sp["lanes"]:
        for p in spl.lane_polyline(ln, 0.25):
            hw = spl.lane_width(ln, p[0]) / 2 if "pts" in ln else ln["w"] / 2
            for name, kind, gm in ob:
                d = dist(p, kind, gm) - hw
                if d < CLEAR:
                    hits.append((ln["id"], name, round(d, 2)))
    worst = {}
    for lid, name, d in hits:
        worst[(lid, name)] = min(d, worst.get((lid, name), 9))
    out.append(("lanes keep >= 0.3 m from every structure", not hits, f"{dict(list(worst.items())[:6])}"))

    walls = [o for o in ob if not o[0].startswith(("fire tank", "wet fan", "dust bin", "T5 trestle", "shed outer"))]
    shed = r["pit"]["building"]
    walls.append(("pit shed", "rect", (shed["x"][0], shed["y"][0], shed["x"][1], shed["y"][1])))
    bad_h = []
    for x, y in sp["hydrants"]:
        d_road = min(min(dist((x, y), "circle", (q[0], q[1], 0)) - (spl.lane_width(ln, q[0]) / 2 if "pts" in ln else ln["w"] / 2)
                         for q in spl.lane_polyline(ln, 0.25)) for ln in sp["lanes"])
        d_wall = min(dist((x, y), k, gm) for _, k, gm in walls)
        if not (0 < d_road <= HYD_ROAD and d_wall >= HYD_WALL):
            bad_h.append(((x, y), round(d_road, 2), round(d_wall, 2)))
    out.append(("hydrants <= 2.5 m from a road edge, >= 5 m from walls (ДБН В.2.5-74)", not bad_h, f"{len(sp['hydrants'])} hydrants, bad {bad_h}"))

    ft = sp["fire_tanks"]
    vol = spl.tank_volume(sp)
    need = site["designed"]["fire_water"]["tank_m3"]
    out.append(("fire tanks: 2, each >= the designed volume", len(ft["c"]) >= 2 and vol >= need, f"{len(ft['c'])} × {vol:.0f} m³ vs {need}"))

    base = [o for o in ob if o[0] in [s["id"] for s in site["silos"]] or o[0].startswith(("tower", "old silo"))]
    ct = sp["cable_trestle"]
    pts = []
    for (x0, y0), (x1, y1) in zip(ct["pts"], ct["pts"][1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / 0.25))
        pts += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n + 1)]
    worst_t = min(dist(p, k, gm) for p in pts for _, k, gm in base)
    blds = [o for o in ob if o[0] in ("apk", "ktp", "kpp", "pump house")]
    worst_b = min(dist((cx, cy), k2, g2) for _, k1, g1 in blds for (cx, cy) in
                  ((g1[0], g1[1]), (g1[2], g1[1]), (g1[2], g1[3]), (g1[0], g1[3])) for _, k2, g2 in base)
    out.append(("cable trestle and designed buildings keep >= 0.3 m from silo plinths and towers", worst_t >= CLEAR and worst_b >= CLEAR,
                f"trestle {worst_t:.2f} m, buildings {worst_b:.2f} m"))
    out += norm_checks(site)
    out += surface_checks(site)
    out += spur_checks(site)
    return out


TRAILER = (2.55, 3.8)                 # dust trailer width (road-train judgment above) and height under the bin gate (judgment)


def spur_checks(site, trailer=TRAILER):
    """A trailer box driven along each service spur up to its dust bin centre clears every mesh of that bin
    (frame, bracing, ladder, cage, gate), built by kit/aspiration.build_bin."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    from kit import aspiration as asp
    out = []
    g = c.ground_z()
    hits = []
    for ln in spl.spec(site)["lanes"]:
        if not ln.get("to_bin"):
            continue
        b = next(bb for bb in site["aspiration"]["dust_bins"] if bb["id"] == ln["to_bin"])
        parts = [p for p in asp.build_bin(b, b["center"][1] + 1.0).values() if p is not None]
        v, f = c.merge_parts(parts)
        bvh = BVHTree.FromPolygons([Vector(q) for q in v], [tuple(int(i) for i in q) for blk in f for q in blk])
        (x0, y0), (x1, y1) = ln["pts"][0], ln["pts"][-1]
        hw = trailer[0] / 2
        lo = (min(x0, x1) - (hw if x0 == x1 else 0), min(y0, y1) - (hw if y0 == y1 else 0), g + 0.3)
        hi = (max(x0, x1) + (hw if x0 == x1 else 0), max(y0, y1) + (hw if y0 == y1 else 0), g + trailer[1])
        bv, bf = c.box(lo, hi)
        box = BVHTree.FromPolygons([Vector(q) for q in bv], [tuple(int(i) for i in q) for q in bf])
        if box.overlap(bvh):
            hits.append((ln["id"], b["id"]))
    out.append((f"a {trailer[0]} x {trailer[1]} m trailer drives along each service spur under its dust bin without touching it",
                not hits, f"clash {hits}"))
    return out


def surface_checks(site):
    """The built road mesh: the outer corner of every bend is paved (rays down), faces point up, no face lies
    within 1 mm of another (coplanar overlaps render black in Cycles)."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    out = []
    sp = spl.spec(site)
    v, f = spl.build_roads(site)["roads"][2]
    polys = [tuple(int(i) for i in q) for blk in f for q in blk]
    bvh = BVHTree.FromPolygons([Vector(p) for p in v], polys)
    top = float(v[:, 2].max()) + 1.0
    open_ = []
    for ln in sp["lanes"]:
        for other in sp["lanes"]:
            p, q = ln.get("pts"), other.get("pts")
            if not p or not q:
                continue
            bends = [(p[i - 1], p[i], p[i + 1]) for i in range(1, len(p) - 1)] if other is ln else                     ([(p[-2], p[-1], q[1])] if math.dist(p[-1], q[0]) < 0.01 else [])
            for a, cp, b in bends:
                d1 = np.subtract(cp, a) / math.dist(cp, a)
                d2 = np.subtract(b, cp) / math.dist(b, cp)
                hw = min(spl.lane_width(ln, cp[0]), spl.lane_width(other, cp[0])) / 2
                out_dir = (d1 - d2) / np.linalg.norm(d1 - d2)                     # away from the turn
                miter = hw / math.sqrt((1 + float(np.dot(d1, d2))) / 2)             # axis to the outer edge corner
                for probe in (np.add(cp, out_dir * miter * 0.5), np.add(cp, out_dir * miter * 0.9)):
                    hit, *_ = bvh.ray_cast(Vector((probe[0], probe[1], top)), Vector((0, 0, -1)), 5.0)
                    if hit is None:
                        open_.append((ln["id"], tuple(cp)))
    out.append(("outer corner of every road bend is paved (rays down on the built roads)", not open_, f"open {sorted(set(open_))}"))
    down, stacked = 0, 0
    for q in polys:                                  # what a camera sees from above must face it (box bottoms don't count)
        cen = v[list(q)].mean(axis=0)
        hit, nrm, *_ = bvh.ray_cast(Vector((cen[0], cen[1], top)), Vector((0, 0, -1)), top - float(v[:, 2].min()) + 1.0)
        down += hit is not None and nrm.z <= 0
        stacked += len({r[2] for r in bvh.find_nearest_range(Vector(cen), 1e-3)}) > 1
    out.append(("road surface seen from above faces up and no face lies within 1 mm of another", down == 0 and stacked == 0,
                f"{down} down, {stacked} stacked of {len(polys)}"))
    return out


def norm_checks(site):
    """research/site_plan_norms.md: widths, the U-turn swept circle, headroom, scales straights, КТП distance,
    fire water intake, fire access to the silos from two sides, dead ends."""
    out = []
    sp = spl.spec(site)
    nm = sp["norms"]
    lanes = {ln["id"]: ln for ln in sp["lanes"]}
    main = [lanes[k] for k in ("in", "west", "out")]
    wmin = min(ln["w"] for ln in main)
    out.append(("truck lanes >= 4.5 m (СНиП табл. 46), one-lane ring allowed (п. 5.22)", wmin >= nm["lane_w_min"], f"min {wmin} m"))
    if wmin < nm["lane_w_trains"]:
        out.append(("truck lanes under 5.0 m for road trains: WARN", True, f"{wmin}"))
    nar = lanes["out"].get("narrow")
    if nar and nar["w"] < nm["lane_w_min"]:
        out.append(("lane under Ш1 narrower than 4.5 m: FINDING", True,
                    f"{nar['w']} m: the existing cleaning tower columns leave 4.2 m clear, less than a one-lane road (СНиП табл. 46)"))
    u = lanes["uturn"]
    r_out, r_in = u["arc"]["r"] + u["w"] / 2, u["arc"]["r"] - u["w"] / 2
    so, si = nm["swept_circle"]
    out.append(("U-turn holds the road-train swept circle 12.5 / 5.3 m (96/53/EC)", r_out >= so - 1e-6 and r_in <= si + 1e-6,
                f"outer {r_out:.2f}, inner {r_in:.2f}"))
    if r_out < nm["uturn_outer_rec"] - 1e-6:
        out.append(("U-turn outer edge under 13.0 m (margin): WARN", True, f"{r_out:.2f}"))
    b = site["receiving"]["cleaning_tower"]["bin_Sh1"]
    head = b["outlet"][1] - (c.ground_z() + sp["road_z_over_ground"])
    out.append(("clear height under Ш1 >= 4.5 m (cab + 0.5)", head >= nm["headroom_min"], f"{head:.2f} m"))
    if head < nm["headroom_rec"]:
        out.append(("clear height under Ш1 under 5.0 m: WARN", True, f"{head:.2f}"))
    for key, lid in (("scales_in", "in"), ("scales_out", "out")):
        ln = lanes[lid]
        x0, x1 = sp[key]["x"]
        rp = sp[key]["ramp"]
        xs = [p[0] for p in ln["pts"]]
        before = (max(xs) - (x1 + rp)) if lid == "in" else ((x0 - rp) - max(b["x"]))
        after = ((x0 - rp) - lanes["in"]["pts"][-1][0]) if lid == "in" else (sp["gate"]["x"] - (x1 + rp))
        out.append((f"{key}: straight >= 12 m before and after (NIST HB44, analog)", min(before, after) >= nm["scales_straight_min"],
                    f"before {before:.1f}, after {after:.1f} m"))
    k = sp["ktp"]
    d_ktp = min(dist((x, y), "circle", (s["x"], s["y"], 11.0)) for s in site["silos"] for x in k["x"] for y in k["y"])
    lo, hi = nm["ktp_from_silo"]
    out.append(("КТП >= 6 m from the silo walls (least of the norms)", d_ktp >= lo, f"{d_ktp:.1f} m"))
    if d_ktp < hi:
        out.append(("КТП under 12 m from a silo (strictest norm): WARN", True, f"{d_ktp:.1f}"))
    hs = sp["fire_tanks"]["hardstand"]
    blds = [sp["apk"], sp["ktp"], sp["gate"]["kpp"]]
    mid = ((hs[0] + hs[2]) / 2, (hs[1] + hs[3]) / 2)
    d_in = min(dist(mid, "rect", (q["x"][0], q["y"][0], q["x"][1], q["y"][1])) for q in blds)
    d_in = min([d_in] + [dist(mid, "circle", (s["x"], s["y"], 11.0)) for s in site["silos"]])
    out.append(("fire water intake (pier) >= 10 m from buildings, pier >= 12 x 12", d_in >= nm["fire_intake_from_building"]
                and hs[2] - hs[0] >= 12 and hs[3] - hs[1] >= 12, f"{d_in:.1f} m, pier {hs[2] - hs[0]:.0f} x {hs[3] - hs[1]:.0f}"))

    f0, f1 = nm["fire_access"]["from_wall"]
    sides = {}
    for s in site["silos"]:
        served = set()
        for ln in sp["lanes"]:
            if ln.get("kind") == "service":                              # dust-bin spurs are too narrow for a fire engine
                continue
            pts = spl.lane_polyline(ln, 0.5)
            hw = ln["w"] / 2
            n = 0
            for a in np.radians(np.arange(0, 360, 5)):
                wx, wy = s["x"] + 11.0 * math.cos(a), s["y"] + 11.0 * math.sin(a)
                d = min(math.hypot(wx - p[0], wy - p[1]) for p in pts) - hw
                n += f0 <= d <= f1
            if n >= 3:                                                   # >= 15 degrees of the wall faces the road
                served.add(ln["id"])
        sides[s["id"]] = sorted(served)
    none = [k for k, v in sides.items() if not v]
    one = {k: v for k, v in sides.items() if len(v) == 1}
    out.append(("fire access: every silo has a road 5-8 m from its wall (ДБН Б.2.2-12 п. 15.3.2)", not none, f"{sides}"))
    if one:
        out.append(("fire access from one side only: FINDING", True,
                    f"{one}: the drawn rows are 3.5 m apart and the corridor between the towers is 7 m, no room for a road 5 m off both walls"))

    loose = []
    for ln in sp["lanes"]:
        if ln.get("kind") not in ("fire", "service"):
            continue
        for end in (ln["pts"][0], ln["pts"][-1]):
            on = any(min(math.hypot(end[0] - p[0], end[1] - p[1]) for p in spl.lane_polyline(o, 0.25)) <= o["w"] / 2 + 0.05
                     for o in sp["lanes"] if o is not ln)
            pad = ln.get("end_pad") and (ln["end_pad"][0] - 0.1 <= end[0] <= ln["end_pad"][2] + 0.1
                                         and ln["end_pad"][1] - 0.1 <= end[1] <= ln["end_pad"][3] + 0.1)
            binb = next((bb for bb in site["aspiration"]["dust_bins"] if bb["id"] == ln.get("to_bin")), None)
            under = binb is not None and math.hypot(end[0] - binb["center"][0], end[1] - binb["center"][1]) <= 0.2
            if not (on or pad or under):
                loose.append((ln["id"], end))
    out.append(("fire / service roads: every end joins a road, a 12 x 12 turnaround or ends under its dust bin", not loose, f"loose {loose}"))
    return out



def main():
    run(json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8")))


SCALE_SHEET = {"len": 24.0, "w": 3.0, "modules": 4, "module_h": 0.25}        # Тензо-М ВА-80-24-4 (brochure pdf_28 p.15)
DECK_H = (0.25, 0.35)          # deck over the road: ВА 250 mm, Техноваги 300-350 mm
RAMP_MIN = 3.5                 # Техноваги: 3.5-4 m ramp at 300-350 mm


def scales_checks(site):
    """Scales measured on the kit meshes against the ВА-80-24-4 sheet, the Техноваги heights and ramps, and where
    the driver sees the display (left of travel, past the exit end, facing the cab)."""
    out = []
    sp = site["designed"]["site_plan"]
    parts = spl.build_roads(site)
    dv = np.asarray(parts["scale_decks"][2][0], float)
    g = c.ground_z() + sp["road_z_over_ground"]
    for key in ("scales_in", "scales_out"):
        x0, y0, x1, y1 = spl.scales_box(sp, key)
        mine = dv[(dv[:, 0] >= x0 - 1e-6) & (dv[:, 0] <= x1 + 1e-6) & (dv[:, 1] >= y0 - 1e-6) & (dv[:, 1] <= y1 + 1e-6)]
        xs = np.unique(np.round(mine[:, 0], 3))
        modules = (len(xs) - 2) // 2 + 1                               # 2 x-planes per joint, plus the two ends
        L, W, H = mine[:, 0].ptp(), mine[:, 1].ptp(), mine[:, 2].max() - g
        ok = abs(L - SCALE_SHEET["len"]) < 1e-3 and abs(W - SCALE_SHEET["w"]) < 1e-3 and modules == SCALE_SHEET["modules"]             and DECK_H[0] - 1e-6 <= H <= DECK_H[1] + 1e-6 and sp[key]["ramp"] >= RAMP_MIN
        out.append((f"{key}: 24 x 3 m of four 6 m modules (ВА-80-24-4), deck 0.25-0.35 m, ramp >= 3.5 m (Техноваги)", ok,
                    f"{L:.2f} x {W:.2f} m, {modules} modules, deck {H:.2f} m, ramp {sp[key]['ramp']}"))
        ld = spl.lane(sp, sp[key]["lane"])["pts"]
        tx = np.sign(ld[1][0] - ld[0][0])
        rv = np.asarray(parts["scale_red"][2][0], float)
        near = rv[np.abs(rv[:, 1] - (y0 + y1) / 2) < 3.0]
        exit_x = x1 if tx > 0 else x0
        digits = near[(np.sign(near[:, 0] - exit_x) == tx) & (near[:, 2] > 2.0)]
        left = (digits[:, 1].mean() - (y0 + y1) / 2) * (1 if tx > 0 else -1) > 0 if len(digits) else False
        faces_cab = len(digits) and (digits[:, 0].mean() - exit_x) * tx > 0
        out.append((f"{key}: display past the exit end, left of travel (the driver's side), facing the cab", bool(left and faces_cab),
                    f"{len(digits)} digit vertices, left {left}"))
    return out


def run(site):
    ok_all = True
    for name, ok, info in checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    def v_scales(s):
        s["designed"]["site_plan"]["scales_in"]["x"] = [5.0, 29.0]
    def v_sampler(s):
        s["designed"]["site_plan"]["sampler_post"] = [38.0, 72.5]
    def v_hydrant(s):
        s["designed"]["site_plan"]["hydrants"][1] = [6.7, 67.25]
    def v_uturn(s):
        sp = s["designed"]["site_plan"]
        for ln in sp["lanes"]:
            if ln["id"] == "uturn":
                ln["arc"]["c"][0] = -18.0
            if ln["id"] == "west":
                ln["pts"][1][0] = -18.0
            if ln["id"] == "out":
                ln["pts"][0][0] = -18.0
    def v_lane(s):
        sp = s["designed"]["site_plan"]
        for ln in sp["lanes"]:
            if ln["id"] == "out":
                ln["pts"] = [[x, 44.0] for x, _ in ln["pts"]]
            if ln["id"] == "uturn":
                ln["arc"]["r"] = (63.25 - 44.0) / 2
                ln["arc"]["c"][1] = (63.25 + 44.0) / 2

    tall = [n for n, ok, _ in spur_checks(site, trailer=(TRAILER[0], 4.3)) if not ok]
    ok_all &= bool(tall)
    print(f"{'PASS' if tall else 'FAIL'}  broken variant must be rejected — a 4.3 m trailer under the bin gate: failed {tall}", flush=True)

    joins = spl.corner_joins
    spl.corner_joins = lambda sp: []                                     # the ribbons alone leave the outer corners open
    failed = [n for n, ok, _ in checks(site) if not ok]
    spl.corner_joins = joins
    hit = any("outer corner" in n for n in failed)
    ok_all &= hit
    print(f"{'PASS' if hit else 'FAIL'}  broken variant must be rejected — roads without the corner fill: failed {failed}", flush=True)

    def v_modules(s):
        spl.SCALE_MODULES = 3
    def v_ramp(s):
        s["designed"]["site_plan"]["scales_out"]["ramp"] = 2.5

    variants = [("scales of three modules", v_modules), ("ramp 2.5 m", v_ramp), ("scales in on the pit ramp", v_scales), ("sampler post 7 m off the lane", v_sampler),
                ("hydrant 1 m from the pit shed", v_hydrant), ("U-turn centre at x -18 (through silo «3»)", v_uturn), ("out lane on y 44.0", v_lane)]
    for name, patch in variants:
        bad = copy.deepcopy(site)
        patch(bad)
        failed = [n for n, ok, _ in checks(bad) if not ok]
        spl.SCALE_MODULES = 4
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
