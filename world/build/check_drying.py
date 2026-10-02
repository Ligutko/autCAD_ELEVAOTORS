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

C5 (discharge A24, fans A12 / A13, measured on the meshes; FAIL):
  the flaps stay inside the base contour (base side walls, column faces) and the trays between the frame end walls;
  the cylinder and the guides do not touch the flaps or the dry-grain screw (BVH);
  every closed flap is under its neck and reaches past both neck edges by gap / tan(25°) (wheat repose, physical);
  the A12 rotor is inside the roof casing (radius and height band), the A13 rotor inside the exhaust chamber.
C5 broken variants (through `faults`, each must fail its own rule only): trays 60 mm longer into the drive bay,
guides 80 mm higher through the flap pivots, trays 30 mm narrower, roof fan lifted 1.5 m out of its casing.

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
       "dryer_ladder", "dryer_enclosure", "dryer_enclosure_roof", "dryer_platform", "wet_fans", "t5_ladder", "t5_landing",
       "dryer_fan_top_shroud", "dryer_fan_top_rotor", "dryer_fan_top_motor", "dryer_fan_top_cooling",
       "dryer_fan_low_shroud", "dryer_fan_low_rotor", "dryer_fan_low_motor", "dryer_fan_low_cooling",
       "dryer_discharge_frame", "dryer_flaps", "dryer_flap_rods", "dryer_cylinder", "dryer_hopper_dry", "dryer_screw",
       "dryer_screw_gear", "dryer_screw_gearmotor"]
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
         ("t5_landing", "t5_truss"), ("t5_ladder", "t5_trestle_braces"), ("t5_landing", "t5_trestle_braces"),
         # C5: the motor shaft sits in the rotor hub; the cooling tubes go out through the louvre-box / chamber wall;
         # the gearmotor flange is bolted to its case; the torque-arm pad bolts go through the trough end plate
         ("dryer_fan_top_rotor", "dryer_fan_top_motor"), ("dryer_fan_low_rotor", "dryer_fan_low_motor"),
         ("dryer_fans", "dryer_fan_top_cooling"), ("dryer_chambers", "dryer_fan_low_cooling"),
         ("dryer_screw_gear", "dryer_screw_gearmotor"), ("dryer_hopper_dry", "dryer_screw_gear")}


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


C5_FLAPS_IN = "discharge flaps inside the base contour (base side walls, column faces) and the trays between the frame end walls"
C5_CLEAR = "discharge cylinder and guides clear of the flaps and the dry-grain screw (BVH)"
C5_COVER = "closed flap covers its channel: tray past both neck edges by gap / tan(repose 25°), under the neck"
C5_ROTOR = "fan rotors inside their casings: A12 in the roof casing, A13 in the exhaust chamber"


def _hit(a, b):
    return bool(_bvh(a).overlap(_bvh(b)))


def c5_checks(site, faults=None):
    """C5 (discharge A24, fans A12 / A13), measured on the meshes build_dryer gives; `faults` reach the builders."""
    out = []
    parts = dr.build_dryer(site, faults)
    dis = dr.discharge(site, faults)
    sub = dis["sub"]
    bx0, bx1, ca, cb = sub["base_inner"]
    xa, xb = sub["x_frame"]
    fv = np.asarray(parts["dryer_flaps"][2][0], float)
    tv = np.concatenate([np.asarray(t[0], float) for t in sub["trays"]])
    in_base = bx0 <= fv[:, 0].min() and fv[:, 0].max() <= bx1 and ca <= fv[:, 1].min() and fv[:, 1].max() <= cb
    in_frame = xa <= tv[:, 0].min() and tv[:, 0].max() <= xb
    out.append((C5_FLAPS_IN, in_base and in_frame,
                f"flaps x {fv[:, 0].min():.3f}-{fv[:, 0].max():.3f} in {bx0:.3f}-{bx1:.3f}, y {fv[:, 1].min():.3f}-{fv[:, 1].max():.3f} "
                f"in {ca:.3f}-{cb:.3f}; trays x {tv[:, 0].min():.3f}-{tv[:, 0].max():.3f} in the frame {xa:.3f}-{xb:.3f}"))
    cyl, rods = parts["dryer_cylinder"][2], parts["dryer_flap_rods"][2]
    flaps, screw = parts["dryer_flaps"][2], parts["dryer_screw"][2]
    hits = [f"{a} x {b}" for a, pa in (("cylinder", cyl), ("guides", rods)) for b, pb in (("flaps", flaps), ("screw", screw)) if _hit(pa, pb)]
    out.append((C5_CLEAR, not hits, f"{hits or 'no contact'}"))
    tan_r = math.tan(math.radians(dr.REPOSE_DEG))
    bad, worst = [], 9.0
    if len(sub["trays"]) != len(sub["necks"]):
        bad.append(f"{len(sub['trays'])} trays for {len(sub['necks'])} channels")
    for i, (tray, (n0, n1, nz)) in enumerate(zip(sub["trays"], sub["necks"])):
        t = np.asarray(tray[0], float)
        under = float(t[:, 2].max()) < nz                                  # lips included
        gap = nz - float(np.sort(np.unique(np.round(t[:, 2], 6)))[1])     # neck bottom -> tray floor top (lips stand higher)
        over = min(n0 - float(t[:, 1].min()), float(t[:, 1].max()) - n1) - gap / tan_r
        worst = min(worst, over)
        if not under or over < 0.0:
            bad.append(f"channel {i + 1}: overlap margin {over * 1000:.1f} mm, under the neck {under}")
    out.append((C5_COVER, not bad, f"{len(sub['necks'])} channels, worst margin {worst * 1000:.1f} mm over gap/tan25°; {bad[:3] or 'ok'}"))
    s = dr.section(site)
    z = s["z"]
    side = site["designed"]["dryer"]["section"]["fan_unit_m"]["side"]
    cx, cy = dr.fan_top_centre(site)
    rt = np.asarray(parts["dryer_fan_top_rotor"][2][0], float)
    r_out = float(np.hypot(rt[:, 0] - cx, rt[:, 1] - cy).max())
    top_ok = r_out < side / 2 and z["fan_louvre_top"] <= rt[:, 2].min() and rt[:, 2].max() <= z["fan_casing_top"]
    x0, y0, x1, y1 = dr.dryer_rect(site)
    ea, eb = s["exhaust"]
    rl = np.asarray(parts["dryer_fan_low_rotor"][2][0], float)
    low_ok = x0 < rl[:, 0].min() and rl[:, 0].max() < x1 and ea < rl[:, 1].min() and rl[:, 1].max() < eb and \
        0.0 < rl[:, 2].min() and rl[:, 2].max() < z["chamber_roof"]
    out.append((C5_ROTOR, top_ok and low_ok,
                f"A12 tip circle {2 * r_out:.3f} m in the Ø{side:.2f} casing, z {rt[:, 2].min():.2f}-{rt[:, 2].max():.2f} in "
                f"{z['fan_louvre_top']}-{z['fan_casing_top']}; A13 in the exhaust chamber {low_ok}"))
    return out


C5_VARIANTS = (
    (C5_FLAPS_IN, "flap trays 60 mm longer at -X, out of the frame into the drive bay", {"tray_dx0": -0.06}),
    (C5_CLEAR, "guides and their pins 80 mm higher, through the flap pivots", {"rods_dz": 0.08}),
    (C5_COVER, "trays 30 mm narrower on the pivot side", {"tray_w": -0.03}),
    (C5_ROTOR, "roof fan lifted 1.5 m out of its casing", {"top_fan_dz": 1.5}),
)


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
    out += c5_checks(site)

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
    # C5 broken variants go in through `faults` of the dryer builders and must fail their own rule and nothing else
    base_c5 = {n for n, ok, _ in c5_checks(site) if not ok}
    for rule, name, faults in C5_VARIANTS:
        failed = {n for n, ok, _ in c5_checks(site, faults) if not ok}
        good = rule in failed and not (failed - base_c5 - {rule})
        ok_all &= good
        print(f"{'PASS' if good else 'FAIL'}  broken variant must be rejected — {name}: failed {sorted(failed)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
