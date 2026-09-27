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
line); U-turn centreline radius under 9 m or width under 6 m (judgment until research/site_plan_norms.md).

Broken variants that must fail: scales in on the pit ramp, sampler post 7 m off the lane, hydrant 1 m from
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
from kit import drying as dr  # noqa: E402
from kit import site_plan as spl  # noqa: E402

REACH = (0.72, 5.35)                  # ПГ-2.10.180 (rec_2e227fdb)
TRUCK_W = 2.55                        # body width of a road train (judgment until the norm)
CLEAR = 0.3
HYD_ROAD, HYD_WALL = 2.5, 5.0         # ДБН В.2.5-74 (rec_944e9792)
APPROACH = 50.0                       # KMZ (rec_6c92404e)
UTURN_R, UTURN_W = 9.0, 6.0           # judgment
HEADROOM = 4.5                        # judgment


def obstacles(site):
    """[(name, kind, geom)]: ('circle', (x, y, r)) or ('rect', (x0, y0, x1, y1)) footprints."""
    ob = []
    rf = site["silo_foundation"]["ring"]["r_out"]
    ob += [(s["id"], "circle", (s["x"], s["y"], rf)) for s in site["silos"]]
    r = site["receiving"]
    ob += [(f"old silo {s['label']}", "circle", (s["x"], s["y"], s["plinth_r"])) for s in r["old_silos"]]
    tp = r["tower"]["pit"]
    ob.append(("receiving tower pit", "rect", (tp["inner_x"][0] - tp["wall_t"], tp["inner_y"][0] - tp["wall_t"],
                                              tp["inner_x"][1] + tp["wall_t"], tp["inner_y"][1] + tp["wall_t"])))
    ct = r["cleaning_tower"]
    h = ct["col"] / 2
    ob += [("cleaning tower column", "rect", (x - h, y - h, x + h, y + h)) for x in ct["cols_x"] for y in ct["cols_y"]]
    # the cleaning tower footings are flush with the ground (±0.05): wheels roll over them, not an obstacle
    ob += [("shed outer post", "rect", (x - 0.6, y - 0.6, x + 0.6, y + 0.6)) for x, y in r["pit"]["outer_posts"]]
    b4 = r["building_4"]
    ob.append(("building 4 / dryer", "rect", (b4["outer_x"][0], b4["outer_y"][0], b4["outer_x"][1], b4["outer_y"][1])))
    g = dr.geom(site)
    f = dr.TRESTLE_FOOT
    for tr in g["T5"]["trestles"]:
        for px in (tr["x"] - tr["hx"], tr["x"] + tr["hx"]):
            for py in tr["y"]:
                ob.append(("T5 trestle footing", "rect", (px - f, py - f, px + f, py + f)))
    for s in r["old_silos"]:
        y = s["y"] + s["plinth_r"] + dr.WET_FAN_OFFSET
        ob.append((f"wet fan pad {s['label']}", "rect", (s["x"] - 0.7, y - 0.6, s["x"] + 0.7, y + 0.6)))
    for b in site["aspiration"]["dust_bins"]:
        (cx, cy), (fx, fy) = b["center"], b["frame"]
        ob.append((f"dust bin {b['id']}", "rect", (cx - fx / 2, cy - fy / 2, cx + fx / 2, cy + fy / 2)))
    for t in site["noria_towers"]:
        hx, hy = t["size"][0] / 2, t["size"][1] / 2
        ob.append((f"tower {t['id']}", "rect", (t["x"] - hx, t["y"] - hy, t["x"] + hx, t["y"] + hy)))
    sp = spl.spec(site)
    for key in ("apk", "ktp"):
        ob.append((key, "rect", (sp[key]["x"][0], sp[key]["y"][0], sp[key]["x"][1], sp[key]["y"][1])))
    k = sp["gate"]["kpp"]
    ob.append(("kpp", "rect", (k["x"][0], k["y"][0], k["x"][1], k["y"][1])))
    ph = sp["fire_tanks"]["pump_house"]
    ob.append(("pump house", "rect", (ph["x"][0], ph["y"][0], ph["x"][1], ph["y"][1])))
    ob += [("fire tank", "circle", (x, y, sp["fire_tanks"]["d"] / 2)) for x, y in sp["fire_tanks"]["c"]]
    return ob


def dist(p, kind, gm):
    if kind == "circle":
        return math.hypot(p[0] - gm[0], p[1] - gm[1]) - gm[2]
    x0, y0, x1, y1 = gm
    dx, dy = max(x0 - p[0], 0, p[0] - x1), max(y0 - p[1], 0, p[1] - y1)
    return math.hypot(dx, dy) if dx or dy else -min(p[0] - x0, x1 - p[0], p[1] - y0, y1 - p[1])


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
    u = lanes["uturn"]
    if u["arc"]["r"] < UTURN_R or u["w"] < UTURN_W:
        out.append(("U-turn under the judgment radius / width: WARN", True, f"r {u['arc']['r']}, w {u['w']}"))
    else:
        out.append(("U-turn radius / width (judgment until the norm)", True, f"r {u['arc']['r']}, w {u['w']}"))

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
    return out


def main():
    run(json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8")))


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

    variants = [("scales in on the pit ramp", v_scales), ("sampler post 7 m off the lane", v_sampler),
                ("hydrant 1 m from the pit shed", v_hydrant), ("U-turn centre at x -18 (through silo «3»)", v_uturn), ("out lane on y 44.0", v_lane)]
    for name, patch in variants:
        bad = copy.deepcopy(site)
        patch(bad)
        failed = [n for n, ok, _ in checks(bad) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
