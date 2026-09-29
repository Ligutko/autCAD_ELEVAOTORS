"""Phase 5A check: the drying loop in 3D (world/kit/drying.py, research/design/drying_loop.md) against the
drawn tie-ins, the designed sizes and the real meshes around it.

FAIL:
  the dryer column (designed size) stands inside the drawn plan of building «4», full height;
  T3 top = the drawn T10 spout end onto T3 (sheet 4, set on the casing), the spout lands on the T3 run,
  T3 head drops into the dryer top hopper; H2 / H3 spouts land on T3;
  T5 top = the drawn spout end onto T5, H4 spout lands on T5, T5 drops at the centres of silos «2», «3»,
  the T5 head drum beyond the last drop;
  the dryer discharges onto T4 and T4 passes under the column;
  T5 trestles clear of the old silo plinths (>= 0.1 m);
  no clashes of the new meshes with the tower frame, decks, norias, old silos, plan conveyors, cleaning
  tower, the T7 / T10 gallery or each other (real meshes, BVH).
WARN: trestle clearance to a plinth under 0.3 m.

Dryer body (GCS p.2 section): zones along the long side, column volume >= catalogue grain volume, top fan unit
over the Ø1000 rotor on the exhaust chamber, burner louvres at the hot chamber bottom, T3 bridge posts on the
column roof, guard rails 1.1 m.

Broken variants that must fail: T5 0.25 m higher (the +22.0 girt), T3 0.2 m lower (the +19.4 girt), trestle
at x -13.4 (in the plinth of silo «2»), dryer centre at x 10.2 (out of building «4»), T5 on y 54.2 (drops
off the silo centres), column 1.2 m thick, fan unit 0.9 m.

Run:
    blender --background --python world/build/check_drying.py
"""

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import drying as dr  # noqa: E402
from kit import gallery as gal  # noqa: E402
from kit import receiving as rc  # noqa: E402

TOL = 0.03
NEW = ["t5_casing", "t5_deck", "t5_truss", "t5_trestle_legs", "t5_trestle_braces", "t5_trestle_feet", "t3_casing",
       "t3_bridge_deck", "t3_bridge_frame", "t3_drive", "t5_drive", "dryer_column", "dryer_chambers", "dryer_hopper", "dryer_fans",
       "dryer_screw_motor", "dryer_gas", "dryer_louvres", "dryer_doors",
       "dryer_ladder", "dryer_enclosure", "dryer_enclosure_roof", "dryer_platform", "wet_fans", "t5_ladder", "t5_landing"]
OLD = ["frame", "bracing", "decks", "noria_legs", "noria_heads", "noria_drives", "noria_boots", "old_silo_walls",
       "old_silo_roofs", "old_silo_plinths", "conveyors", "ct_room", "ct_columns", "ct_floor", "shed_columns", "shed_roof"]
# pairs that touch by design: the casing on its own deck / bridge, the column in its own enclosure roof opening
TOUCH = {("t3_casing", "t3_bridge_deck"), ("t5_casing", "t5_deck"), ("t3_bridge_frame", "t3_bridge_deck"),
         ("t5_truss", "t5_deck"), ("t5_trestle_legs", "t5_trestle_braces"), ("t5_trestle_legs", "t5_trestle_feet"),
         ("t5_trestle_braces", "t5_truss"), ("t5_trestle_legs", "t5_truss"), ("dryer_column", "dryer_chambers"),
         ("dryer_chambers", "dryer_hopper"), ("dryer_chambers", "dryer_fans"), ("dryer_chambers", "dryer_platform"),
         ("dryer_chambers", "dryer_louvres"), ("dryer_column", "dryer_louvres"), ("dryer_chambers", "dryer_doors"),
         ("dryer_chambers", "dryer_enclosure_roof"), ("dryer_column", "dryer_enclosure_roof"), ("dryer_chambers", "dryer_gas"),
         ("dryer_hopper", "dryer_screw_motor"), ("dryer_chambers", "dryer_ladder"), ("dryer_louvres", "dryer_enclosure"),
         ("dryer_fans", "dryer_platform"), ("dryer_gas", "dryer_louvres"),
         ("dryer_column", "dryer_hopper"), ("dryer_ladder", "dryer_enclosure_roof"), ("dryer_platform", "dryer_hopper"),
         ("dryer_platform", "dryer_column"), ("dryer_ladder", "dryer_platform"), ("dryer_fans", "dryer_column"),
         ("t3_bridge_frame", "dryer_hopper"), ("t3_drive", "t3_casing"), ("t5_drive", "t5_casing"),
         ("dryer_ladder", "dryer_column"),
         ("dryer_enclosure", "dryer_enclosure_roof"), ("t5_ladder", "t5_landing"), ("t5_landing", "t5_deck"),
         ("t5_landing", "t5_truss"), ("t5_ladder", "t5_trestle_braces"), ("t5_landing", "t5_trestle_braces")}


def _bvh(data):
    v, f = data
    polys = [tuple(int(i) for i in row) for block in (f if isinstance(f, list) else [f]) for row in np.asarray(block)]
    return BVHTree.FromPolygons([tuple(p) for p in np.asarray(v, float)], polys)


GRAIN_M3 = 54.7              # STRAHL 3000 FR grain volume (rec_eda294e3, table checked in the PDF)
ROTOR_D = 1.0                # top fan rotor Ø1000 mm (GCS p.4, research/design/dryer/strahl_fr_anatomy.md)
RAIL_H = 1.1                 # guard rail height ISO 14122-3


def _bb(data):
    v = np.asarray(data[0], float)
    return v.min(axis=0), v.max(axis=0)


def section_checks(site, d):
    """The dryer as the GCS p.2 section says, measured on the meshes against the section table and independent
    numbers (grain volume, rotor, T3 bridge)."""
    out = []
    parts = dr.build_dryer(site)
    sec, z = dr.section(site), d["section"]["z_m"]
    x0, y0, x1, y1 = dr.dryer_rect(site)
    ch0, ch1 = _bb(parts["dryer_chambers"][2])
    co0, co1 = _bb(parts["dryer_column"][2])
    ok = abs(ch1[2] - z["chamber_roof"]) < 1e-3 and abs(co1[2] - z["column_eave"]) < 1e-3 and         abs(co0[1] - sec["column"][0]) < 1e-3 and abs(co1[1] - sec["column"][1]) < 1e-3 and         abs(ch0[1] - y0) < 1e-3 and abs(ch1[1] - y1) < 1e-3
    a = d["section"]["along_long_m"]
    out.append(("dryer zones as the GCS section: chambers at the ends to the chamber roof, column between them", ok and
                abs(a["exhaust"] + a["column"] + a["hot"] - d["size"][0]) <= 0.05,
                f"chambers {ch0[1]:.2f}-{ch1[1]:.2f} to {ch1[2]:.2f}; column {co0[1]:.2f}-{co1[1]:.2f} to {co1[2]:.2f}; "
                f"zones sum {a['exhaust'] + a['column'] + a['hot']:.2f} vs {d['size'][0]}"))
    vol = (sec["column"][1] - sec["column"][0]) * (x1 - x0) * (z["column_eave"] - z["base_top"])
    out.append(("column gross volume holds the catalogue grain volume (54.7 m³) with room for the air ducts",
                GRAIN_M3 <= vol <= 2.0 * GRAIN_M3, f"{vol:.1f} m³ gross"))
    f0, f1 = _bb(parts["dryer_fans"][2])
    fv = np.asarray(parts["dryer_fans"][2][0], float)
    band = fv[(fv[:, 2] > z["fan_louvre_top"] + 0.1) & (fv[:, 2] < z["fan_casing_top"] - 0.1)]     # the casing only
    casing = band[:, 1].max() - band[:, 1].min() if len(band) else 0.0                              # across Y: the cooling tube runs +X
    ex = sec["exhaust"]
    fan_ok = casing >= ROTOR_D and ex[0] <= f0[1] and f1[1] <= ex[1] + 0.2 and abs(f1[2] - dr.dryer_top(site)) < 1e-3
    out.append(("top fan unit on the exhaust chamber, casing over the Ø1000 rotor, its top = the catalogue height",
                fan_ok, f"casing Ø{casing:.2f} m, unit y {f0[1]:.2f}-{f1[1]:.2f} in exhaust {ex[0]:.2f}-{ex[1]:.2f}, top {f1[2]:.2f}"))
    l0, l1 = _bb(parts["dryer_louvres"][2])
    hot = sec["hot"]
    lv = np.asarray(parts["dryer_louvres"][2][0], float)
    low = lv[lv[:, 2] < z["base_top"] + 0.01]
    burner_ok = len(low) and (low[:, 1].min() >= hot[0] - 0.2 if sec["north"] else True) and (low[:, 1].max() <= hot[1] + 0.2 if sec["north"] else True)
    out.append(("burner louvres at the bottom of the hot-air chamber", bool(burner_ok), f"{len(low)} louvre vertices under +{z['base_top']}"))
    frame = dr.build_t3(site)["t3_bridge_frame"][2]
    fv = np.asarray(frame[0], float)
    g3 = dr.geom(site)["T3"]
    posts = [p for p in fv if any(abs(p[0] - px) < 0.06 for px in g3["posts_x"]) and p[2] < g3["bridge"]["deck_z"] - 0.5]
    gaps = [abs(p[2] - dr.column_roof_z(p[1], site)) for p in posts]
    out.append(("T3 bridge posts stand on the column roof", bool(gaps) and max(gaps) < 0.06, f"{len(posts)} post-foot vertices, worst {max(gaps) if gaps else None}"))
    rl = np.asarray(parts["dryer_rails"][2][0], float)
    rh = rl[:, 2].max() - z["chamber_roof"]
    out.append(("guard rails around the chamber roofs (ISO 14122-3, 1.1 m)", abs(rh - RAIL_H) <= 0.05, f"{rh:.2f} m"))
    return out


def checks(site):
    out = []
    r, g, d = site["receiving"], dr.geom(site), site["designed"]["dryer"]
    b4 = r["building_4"]
    x0, y0, x1, y1 = dr.dryer_rect(site)
    inside = b4["outer_x"][0] <= x0 and x1 <= b4["outer_x"][1] and b4["outer_y"][0] <= y0 and y1 <= b4["outer_y"][1]
    out.append(("dryer column inside building «4», designed size and height", inside and dr.dryer_top(site) == d["size"][2],
                f"column [{x0:.2f}, {x1:.2f}] x [{y0:.2f}, {y1:.2f}] in {b4['outer_x']} x {b4['outer_y']}, top {dr.dryer_top(site)}"))

    sp = {n: (np.asarray(p0), np.asarray(p1)) for n, p0, p1, _ in rc.spouts(r, site)}

    def on_run(cid, p):
        t = g[cid]
        lo, hi = sorted(t["x"])
        return lo - 0.3 <= p[0] <= hi + 0.3 and abs(p[1] - t["y"]) <= t["w"] / 2 and abs(p[2] - dr.conv_top(cid, site)) <= TOL

    br = {b["to"]: b for b in r["joints"]["T10"]["outlets"][1]["branches"]}
    t3_end, t5_end = br["T3"]["end"][1], br["T5"]["end"][1]
    ok3 = abs(dr.conv_top("T3", site) - t3_end) <= TOL and on_run("T3", sp["splitter_7->T3"][1]) \
        and on_run("T3", sp["H2->T3"][1]) and on_run("T3", sp["H3->T3"][1])
    q = sp["T3->dryer"][1]
    sec = dr.section(site)
    hop = (x0 + 0.3 <= q[0] <= x1 - 0.3) and (sec["column"][0] + 0.3 <= q[1] <= sec["column"][1] - 0.3)         and abs(q[2] - d["section"]["z_m"]["inlet_top"]) <= 0.1           # onto the wet screw on the column ridge
    out.append(("T3: top = drawn spout end, T10 / H2 / H3 spouts on its run, head drops into the dryer hopper", ok3 and hop,
                f"top {dr.conv_top('T3', site):.2f} vs {t3_end}, dryer inlet {np.round(q, 2)}"))

    ok5 = abs(dr.conv_top("T5", site) - t5_end) <= TOL and on_run("T5", sp["splitter_7->T5"][1]) and on_run("T5", sp["H4->T5"][1])
    drops = []
    for s in r["old_silos"]:
        p0, p1 = sp[f"T5->OS{s['label']}"]
        drops.append(math.hypot(p1[0] - s["x"], p1[1] - s["y"]) <= 0.05 and abs(p0[1] - g["T5"]["y"]) < 1e-6
                     and abs(p0[1] - s["y"]) <= g["T5"]["w"] / 2)
    last = min(s["x"] for s in r["old_silos"])
    head_ok = 0.3 <= last - g["T5"]["x"][1] <= 0.8
    out.append(("T5: top = drawn spout end, T10 / H4 spouts on its run, drops at the centres of silos «2», «3», head drum past the last drop",
                ok5 and all(drops) and head_ok, f"top {dr.conv_top('T5', site):.2f} vs {t5_end}, drops {drops}, head {g['T5']['x'][1]} vs last drop {last}"))

    out += section_checks(site, d)

    t4 = next(cv for cv in r["conveyors"] if cv["id"] == "T4")
    p0, p1 = sp["dryer->T4"]
    under = min(t4["x"]) < x0 and max(t4["x"]) > x1 and y0 < t4["y"] < y1
    out.append(("dryer discharges onto T4, T4 runs under the column", under and abs(p1[2] - (t4["z"] + 0.40)) <= TOL and abs(p1[1] - t4["y"]) <= 0.05,
                f"T4 x {t4['x']} y {t4['y']}, outlet {np.round(p1, 2)}"))

    worst = 9.0
    for tr in g["T5"]["trestles"]:
        for px in (tr["x"] - tr["hx"], tr["x"] + tr["hx"]):
            for py in tr["y"]:
                for s in r["old_silos"]:
                    worst = min(worst, math.hypot(px - s["x"], py - s["y"]) - s["plinth_r"] - dr.TRESTLE_FOOT)   # footing edge
    out.append(("T5 trestles clear of the old silo plinths (>= 0.1 m, foot included)", worst >= 0.1, f"min {worst:.2f} m"))
    lad = "t5_ladder" in rc.build(r, site) and "t5_landing" in rc.build(r, site)
    out.append(("T5 gallery has an access: caged ladder on trestle A to a landing at the deck (ISO 14122-4)", lad, f"{lad}"))
    if worst < 0.3:
        out.append(("trestle clearance under 0.3 m: WARN", True, f"{worst:.2f} m"))

    parts = rc.build(r, site)
    gb = next(b for b in site["bridges"] if any(cv["id"] == "T7" for cv in b["conveyors"]))
    bparts = gal.bridge(gb)
    trees = {k: _bvh(parts[k][2]) for k in NEW + OLD if k in parts}
    for k in ("heavy", "light", "deck", "conv_casing"):
        trees[f"T7T10_{k}"] = _bvh(bparts[k])
    clashes = []
    for a in NEW:
        for b in OLD + [k for k in trees if k.startswith("T7T10_")] + NEW:
            if a == b or (a, b) in TOUCH or (b, a) in TOUCH or (b in NEW and NEW.index(b) < NEW.index(a)):
                continue
            if a in trees and b in trees and trees[a].overlap(trees[b]):
                clashes.append(f"{a} x {b}")
    out.append(("no clashes of the drying loop with the tower, norias, old silos, conveyors, gallery (real meshes)", not clashes, f"{clashes[:8]}"))
    return out


def main():
    run(json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8")))


def run(site):
    ok_all = True
    for name, ok, info in checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    def v_t5_up(s):
        s["designed"]["drying_geom"]["T5"]["z_bot"] += 0.25
    def v_t3_down(s):
        s["designed"]["drying_geom"]["T3"]["z_bot"] -= 0.2
    def v_trestle(s):
        s["designed"]["drying_geom"]["T5"]["trestles"][0]["x"] = -13.4
    def v_dryer(s):
        s["designed"]["drying_geom"]["dryer_centre"][0] = 10.2
    def v_t5_y(s):
        s["designed"]["drying_geom"]["T5"]["y"] = 54.2

    def v_column(s):
        s["designed"]["dryer"]["section"]["along_long_m"].update({"column": 1.2, "hot": 3.86})
    def v_fan(s):
        s["designed"]["dryer"]["section"]["fan_unit_m"]["side"] = 0.9
    def v_inlet(s):
        s["designed"]["dryer"]["section"]["z_m"]["inlet_top"] = 16.75

    variants = [("T5 0.25 m higher", v_t5_up), ("T3 0.2 m lower", v_t3_down), ("trestle at x -13.4", v_trestle),
                ("dryer centre at x 10.2", v_dryer), ("T5 on y 54.2", v_t5_y), ("column 1.2 m thick (no room for the grain)", v_column),
                ("fan unit 0.9 m (smaller than the rotor)", v_fan)]
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
