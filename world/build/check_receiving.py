"""Phase 4 check: the receiving block of sheet 2 (existing, simplified) and its tie-ins with the new
stage, against the drawing numbers measured in research/receiving.md (kept here as independent
constants, not read back from SITE.json) and against the real meshes.

FAIL (drawing): tower grid centre and size, top and deck levels, noria axes, H3 legs along X, heads
clear of the decks, pit size / centre / floor / outlets, T1 on the pit and H1 axis at 8.5-9.5 deg
under both outlets, 20 anchors per old silo outside the wall, T7 pulleys and length, every T7 inlet fed
by a spout, T10 drive pulley, every T10 outlet reaching its receiver, gallery end at the tower,
cleaning tower floor meeting the tower, process edges with geometry, no clashes on the real meshes.
WARN (judgment): head-to-deck gap, drive ramp slope over 1:10.
FINDING: what the drawing does not give (heights marked judgment), ramp drawn longer than 1:10 needs.

Broken variants that must fail: tower on the old EST y 54.8, H2 head on +24.4, pit centred on the
drive axis, T1 on x 0.0, 21 anchors, T7 on the old SITE pulleys, T10 head at the axis end y 54.3,
gallery ending at y 51.0, no spout from T10 into the gravity pipe.

Run:
    blender --background --python world/build/check_receiving.py
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

from kit import common as c  # noqa: E402
from kit import gallery as gal  # noqa: E402
from kit import receiving as rc  # noqa: E402

# drawing numbers, research/receiving.md (inbox/extract_receiving_p2.py), cards in brackets
TOWER_C, TOWER_WH = (1.099, 54.403), (6.201, 6.004)                  # rec_21d41e0c
LEVELS = [30.0, 26.8, 24.4, 22.0, 19.4, 9.2]                         # rec_29580e76 (signed)
TOP = 33.0
NORIAS = {"H1": (1.101, 55.199), "H2": (2.698, 55.199), "H3": (2.549, 52.504), "H4": (-0.501, 55.199)}   # rec_7c736976
HEAD_ON = {"H4": 26.8, "H2": 22.0}                                   # heads standing on a deck (rec_a4d59747)
PIT_C, PIT_WH, PIT_FLOOR = (1.101, 63.653), (8.0, 6.0), -5.0         # rec_670d24cc
OUTLETS_Y = (62.656, 64.651)                                         # rec_c6dfdf20
DRIVE_Z = 0.100                                                      # rec_72b8152c (signed)
OLD_ANCHORS, OLD_ANCHOR_R = 20, 4.69                                 # rec_56e349e9, rec_fae114d4
T7_TAIL, T7_HEAD, T7_LEN = 55.36, 24.87, 30.5                        # rec_3543ac08, rec_66c16f74; spec 30.5 (p.8)
T7_INLETS = (52.37, 53.37, 54.01)                                    # rec_3543ac08 (chain signed)
T10_HEAD = 53.946                                                    # rec_ec92d4b3
T11_INLET = 24.47                                                    # T11 load point under the T7 head (research/tunnel_k4.md)
GALLERY_END = 51.406                                                 # rec_a4d59747
TOL = 0.05


def _bvh(data):
    v, f = data
    polys = [tuple(int(i) for i in row) for block in (f if isinstance(f, list) else [f]) for row in np.asarray(block)]
    return BVHTree.FromPolygons([tuple(p) for p in np.asarray(v, float)], polys)


def _bbox(data):
    v = np.asarray(data[0], float)
    return v.min(axis=0), v.max(axis=0)


def checks(site):
    r = site["receiving"]
    out = []
    parts = rc.build(r, site)
    t = r["tower"]

    lo, hi = _bbox(parts["frame"][2])
    cx, cy = (t["cols_x"][0] + t["cols_x"][1]) / 2, (t["cols_y"][0] + t["cols_y"][1]) / 2
    d = math.hypot(cx - TOWER_C[0], cy - TOWER_C[1])
    out.append(("receiving tower grid centre = drawing (p.2)", d <= 0.10,
                f"({cx:.3f}, {cy:.3f}) vs ({TOWER_C[0]}, {TOWER_C[1]}): {d:.3f} m" + (" — WARN > 0.03" if d > 0.03 else "")))
    wh = (t["cols_x"][1] - t["cols_x"][0], t["cols_y"][1] - t["cols_y"][0])
    out.append(("tower grid 6.2 x 6.0 (p.2)", all(abs(a - b) <= TOL for a, b in zip(wh, TOWER_WH)), f"{wh[0]:.3f} x {wh[1]:.3f}"))
    dz = sorted({round(float(z), 3) for z in np.asarray(parts["decks"][2][0])[:, 2]})
    deck_levels = sorted({lv["z"] for lv in t["decks"]}, reverse=True)
    ok = all(any(abs(a - b) <= TOL for b in deck_levels) for a in LEVELS) and abs(t["top_z"] - TOP) <= TOL and hi[2] >= TOP
    out.append(("tower top +33.0 and deck levels = section (p.4)", ok, f"decks {deck_levels}, frame top {hi[2]:.2f}"))

    heads, legs = {}, {}
    bad_axis = []
    for n in r["norias"]:
        bx = rc.noria_boxes(n, r)
        heads[n["id"]] = bx["head"]
        legs[n["id"]] = (bx["leg_a"], bx["leg_b"])
        ax = ((bx["leg_a"][0] + bx["leg_b"][3]) / 2, (bx["leg_a"][1] + bx["leg_b"][4]) / 2)
        if math.hypot(ax[0] - NORIAS[n["id"]][0], ax[1] - NORIAS[n["id"]][1]) > TOL:
            bad_axis.append(f"{n['id']} {ax[0]:.2f},{ax[1]:.2f}")
    p = t["pit"]
    inside = all(p["inner_x"][0] < b[0] and b[3] < p["inner_x"][1] and p["inner_y"][0] < b[1] and b[4] < p["inner_y"][1]
                 for n in r["norias"] for b in legs[n["id"]])
    h3 = legs["H3"]
    out.append(("noria axes = drawing, legs inside the pit, H3 legs along X (p.2)", not bad_axis and inside and abs(h3[0][1] - h3[1][1]) < 1e-6,
                f"off: {bad_axis}, legs inside {inside}"))
    gap_warn, off_deck = [], []
    for nid, z in HEAD_ON.items():
        hb = heads[nid]
        g = hb[2] - z
        mx, my = (hb[0] + hb[3]) / 2, (hb[1] + hb[4]) / 2
        on = any(x0 <= mx <= x1 and y0 <= my <= y1 for lv in t["decks"] if abs(lv["z"] - z) < 1e-6 for x0, y0, x1, y1 in lv["rects"])
        if not (on and 0.0 < g <= 1.5):
            off_deck.append(f"{nid} gap {g:.2f}, over the +{z} deck {on}")
        if not 0.2 <= g <= 0.5:                                       # H5 / H6 heads stand 0.26 / 0.36 over their decks
            gap_warn.append(f"{nid} {g:.2f}")
    out.append(("H4 and H2 heads stand on their decks +26.8 / +22.0 (p.3, p.4)", not off_deck, f"{off_deck}"))
    deck_bvh = _bvh(parts["decks"][2])
    hits = [nid for nid, hb in heads.items() if _bvh(c.box(hb[:3], hb[3:])).overlap(deck_bvh)]
    out.append(("noria heads clear of the decks (real meshes)", not hits, f"heads through a deck: {hits}"))
    out.append(("head base 0.2-0.5 over its deck like H5 / H6 (WARN)", True, ("WARN: " + ", ".join(gap_warn) + " (as drawn)") if gap_warn else "yes"))
    roof = [nid for nid in ("H1", "H3") if heads[nid][2] <= TOP]
    out.append(("H1 and H3 heads above the roof +33 (p.4)", not roof, f"below: {roof}"))

    pit = r["pit"]
    pc = ((pit["x"][0] + pit["x"][1]) / 2, (pit["y"][0] + pit["y"][1]) / 2)
    pw = (pit["x"][1] - pit["x"][0], pit["y"][1] - pit["y"][0])
    ok = (math.hypot(pc[0] - PIT_C[0], pc[1] - PIT_C[1]) <= TOL and all(abs(a - b) <= TOL for a, b in zip(pw, PIT_WH))
          and abs(pit["floor_z"] - PIT_FLOOR) <= 0.01 and all(any(abs(o[1] - y) <= TOL for o in pit["outlets"]) for y in OUTLETS_Y))
    out.append(("truck pit 8.0 x 6.0, centre, floor -5.0, two outlets (p.2, p.4)", ok, f"centre ({pc[0]:.3f}, {pc[1]:.3f}), {pw[0]:.2f} x {pw[1]:.2f}"))
    dr = pit["drive"]
    g = c.ground_z()
    rise = dr["deck_z"] - g
    slopes = [rise / (dr["flat_x"][0] - dr["x"][0]), rise / (dr["x"][1] - dr["flat_x"][1])]
    out.append(("drive deck +0.100, ramps not steeper than 1:8 (p.2)", abs(dr["deck_z"] - DRIVE_Z) <= 0.01 and max(slopes) <= 1 / 8,
                f"ramps 1:{1 / max(slopes):.1f}" + (" — WARN steeper than 1:10" if max(slopes) > 0.1 else "")))
    out.append(("drive ramps: FINDING", True, f"the drawing signs 1:10 but draws 8.0 m for {rise:.2f} m of rise (1:{8.0 / rise:.1f})"))

    t1 = next(cv for cv in r["conveyors"] if cv["id"] == "T1")
    ang = math.degrees(math.atan2(abs(t1["z_ends"][1] - t1["z_ends"][0]), abs(t1["y"][1] - t1["y"][0])))
    under = all(min(t1["y"]) <= y <= max(t1["y"]) for y in OUTLETS_Y)
    ok = abs(t1["x"] - PIT_C[0]) <= 0.01 + 0.005 and abs(t1["x"] - NORIAS["H1"][0]) <= 0.01 and 8.5 <= ang <= 9.5 and under
    out.append(("T1 on the pit and H1 axis, 8.5-9.5 deg, under both outlets (p.2, p.4)", ok, f"x {t1['x']}, {ang:.1f} deg, under outlets {under}"))

    bad = []
    for s in r["old_silos"]:
        if s["anchors"] != OLD_ANCHORS or abs(s["anchor_r"] - OLD_ANCHOR_R) > 0.01 or s["anchor_r"] <= s["wall_r"]:
            bad.append(s["id"])
    out.append(("old silos: 20 anchors on R 4.69 outside the wall (p.2)", not bad, f"off: {bad}"))
    out.append(("old silos, building 4: FINDING", True,
                f"no heights in the PDF: silo wall {r['old_silos'][0]['wall_h']} m and building eave {r['building_4']['eave_z']} m are judgment"))

    t7 = rc.bridge_conveyor("T7", site)
    t10 = rc.bridge_conveyor("T10", site)
    ok = abs(t7["tail"][0] - T7_TAIL) <= TOL and abs(t7["head"][0] - T7_HEAD) <= TOL
    length = abs(t7["tail"][0] - t7["head"][0])
    out.append(("T7 pulleys = drawing marks (p.4), length = spec 30.5 (p.8)", ok and abs(length - T7_LEN) <= 0.1,
                f"tail {t7['tail'][0]}, head {t7['head'][0]}, L {length:.2f}"))
    out.append(("T7 tail inside the receiving tower", t["cols_y"][0] < t7["tail"][0] < t["cols_y"][1], f"{t7['tail'][0]} in {t['cols_y']}"))
    t11 = rc.bridge_conveyor("T11", site)
    hy = t7["head"][0]
    span = sorted((t11["tail"][0], t11["head"][0]))
    gap = (t7["head"][1] - 0.25) - (rc.conveyor_z(t11, hy) + t11.get("casing_h", 0.5) / 2)
    inlet = abs(hy - T11_INLET)
    ok = span[0] < hy < span[1] and 0.05 <= gap <= 1.0 and inlet <= 0.5
    out.append(("T7 head discharges onto T11 in H5 (p.4: head over the T11 tail)", ok,
                f"T7 drum y {hy} over T11 {span}, casing gap {gap:.2f} m, nearest T11 inlet {inlet:.2f} m ahead"))
    sp = rc.spouts(r, site)
    fed = [y for y in T7_INLETS if any(abs(p1[1] - y) <= TOL and abs(p1[0] - t7["x"]) <= 0.02 for name, _, p1, _ in sp if "->T7" in name)]
    out.append(("every T7 inlet fed by a spout (p.4 chain 1000 / 642 / 1358)", len(fed) == len(T7_INLETS), f"fed {fed} of {T7_INLETS}"))
    out.append(("T10 drive pulley = drawing mark (p.4)", abs(t10["head"][0] - T10_HEAD) <= 0.02, f"{t10['head'][0]} vs {T10_HEAD}"))
    gp = r["cleaning_tower"]["gravity_pipe"]
    a, b = np.array([gp["x"], *gp["from"]]), np.array([gp["x"], *gp["to"]])

    def on_pipe(q):
        tt = np.clip((q - a) @ (b - a) / ((b - a) @ (b - a)), 0, 1)
        return np.linalg.norm(q - (a + (b - a) * tt))

    names = {n for n, *_ in sp}
    reach = [n for n, _, p1, _ in sp if n == "T10->gravity_pipe" and on_pipe(p1) <= 0.1]
    split = [n for n in ("splitter_7->T5", "splitter_7->T3") if n in names]
    out.append(("every T10 outlet reaches its receiver (gravity pipe, splitter -> T5 / T3)", len(reach) == 1 and len(split) == 2,
                f"into the pipe {reach}, splitter branches {split}"))
    out.append(("T3 / T5: FINDING", True, "the drawing shows only the spout ends (T5 at +22.0, T3 at +19.4); the conveyors themselves are not drawn"))
    gb = next(bb for bb in site["bridges"] if any(cv["id"] == "T7" for cv in bb["conveyors"]))
    out.append(("gallery ends at the tower south columns (p.3)", abs(gb["y"][1] - GALLERY_END) <= 0.02 and abs(gb["y"][1] - t["cols_y"][0]) <= 0.02,
                f"gallery end {gb['y'][1]}, tower {t['cols_y'][0]}"))
    ct = r["cleaning_tower"]
    out.append(("cleaning tower floor +9.2 meets the tower", abs(ct["floor_y"][1] - t["cols_y"][0]) <= 0.02 and ct["floor_z"] == 9.2,
                f"floor to y {ct['floor_y'][1]}"))

    # process edges with geometry (sheet 1 + 2 + 4)
    need = ["H3->T7@52.37", "H1->T7@53.37", "H4->T7@54.01", "T10->gravity_pipe", "T10->splitter_7",
            "splitter_7->T5", "splitter_7->T3", "node_1->gravity_pipe", "gravity_pipe->separator", "Sh1->tower_pit"]
    missing = [n for n in need if n not in names]
    starts = []
    for n, p0, p1, _ in sp:
        src = n.split("->")[0]
        if src in heads:
            hb = heads[src]
            if not (hb[0] - 0.3 <= p0[0] <= hb[3] + 0.3 and hb[1] - 0.3 <= p0[1] <= hb[4] + 0.3 and abs(p0[2] - hb[2]) <= 0.3):
                starts.append(n)
    out.append(("process edges have geometry with ends at their nodes (<= 0.3 m)", not missing and not starts,
                f"missing {missing}, starts off the head {starts}"))

    # real-mesh clashes: spouts, norias, T7 / T10 casings, gravity pipes, decks
    obs = {"decks": parts["decks"][2], "pit cover": parts["pit_cover"][2]}
    for nid in heads:
        obs[f"{nid} head"] = c.box(heads[nid][:3], heads[nid][3:])
        for k, lb in enumerate(legs[nid]):
            obs[f"{nid} leg {k}"] = c.box(lb[:3], lb[3:])
    br = gal.bridge(gb)
    conv = _bvh(br["conv_casing"])
    trees = {k: _bvh(v) for k, v in obs.items()}
    clashes = []
    for n, p0, p1, s in sp:
        src = n.split("->")[0]
        sb = _bvh(rc._spout_mesh(p0 + (p1 - p0) * 0.03, p1 - (p1 - p0) * 0.03, s))
        for k, tr in trees.items():
            if k.startswith(src + " ") or k in ("decks", "pit cover"):
                continue
            if sb.overlap(tr):
                clashes.append(f"{n} x {k}")
        if not n.startswith("T10") and "->T7" not in n and sb.overlap(conv):
            clashes.append(f"{n} x T7/T10 casing")
    for nid in heads:
        for k in ("head",) + tuple(f"leg {i}" for i in range(2)):
            if trees[f"{nid} {k}"].overlap(conv):
                clashes.append(f"{nid} {k} x T7/T10 casing")
    out.append(("no clashes: spouts, norias, T7 / T10 casings (real meshes)", not clashes, f"{clashes[:6]}"))
    return out


def main():
    run(json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8")))


def run(site):
    ok_all = True
    for name, ok, info in checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    def v_tower(s):
        s["receiving"]["tower"]["cols_y"] = [51.798, 57.802]
    def v_h2(s):
        n = next(n for n in s["receiving"]["norias"] if n["id"] == "H2")
        n["head_z"] = [24.3, 26.3]
    def v_pit(s):
        s["receiving"]["pit"]["y"] = [60.25, 66.25]
    def v_t1(s):
        next(cv for cv in s["receiving"]["conveyors"] if cv["id"] == "T1")["x"] = 0.0
    def v_anchor(s):
        s["receiving"]["old_silos"][0]["anchors"] = 21
    def v_t7(s):
        cv = rc.bridge_conveyor("T7", s)
        cv["tail"], cv["head"] = [54.97, 25.97], [24.47, 26.8]
    def v_t10(s):
        rc.bridge_conveyor("T10", s)["head"] = [54.3, 26.02]
    def v_gallery(s):
        next(b for b in s["bridges"] if b["id"] == "G_H14_H5")["y"][1] = 51.0
    def v_nospout(s):
        s["receiving"]["joints"]["T10"]["outlets"] = [o for o in s["receiving"]["joints"]["T10"]["outlets"] if o["to"] != "gravity_pipe"]

    def v_t7_long(s):
        cv = rc.bridge_conveyor("T7", s)
        cv["head"] = [26.3, 26.8]                     # head past the T11 tail: nothing to discharge onto

    variants = [("T7 head beyond the T11 tail", v_t7_long), ("tower on the old EST y 54.8", v_tower), ("H2 head on +24.4", v_h2), ("pit centred on the drive axis", v_pit),
                ("T1 on x 0.0", v_t1), ("21 anchors", v_anchor), ("T7 on the old SITE pulleys", v_t7),
                ("T10 head at the axis end y 54.3", v_t10), ("gallery ending at y 51.0", v_gallery),
                ("no spout from T10 into the gravity pipe", v_nospout)]
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
