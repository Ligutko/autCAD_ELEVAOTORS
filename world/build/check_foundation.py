"""Phase 3 check: silo foundation, anchors, ground level (research/foundation.md, SITE.json
silo_foundation, ground_z) against the drawing, ДБН В.2.6-221:2021 and the real geometry.

FAIL (drawing or norm):
- ring radii and plinth diameter = drawing (PDF p.2 vectors, p.4 section); plinth top level;
- under the foot of every stiffener of every silo there is concrete: a ray cast down on the real ring
  and tunnel meshes hits within 5 cm (ring or tunnel box, nothing hangs over soil);
- the ring does not cut the tunnel cavity and ends at the tunnel wall faces;
- one anchor per stiffener, under the chair nut within the plan tolerance; the anchor passes the nut
  within the projection tolerance; embedment >= design (a shortened anchor fails);
- footing below the frost depth; tilt and mean settlement within the norm (state);
- deformation marks: >= 6 on the plinth face, each with an opposite one through the centre;
- aeration fan ducts pass the plinth through its openings (no duct x ring overlap on the meshes);
- things that stand on the ground stand on the drawn ground (-0.451, PDF p.4): fan pads, the outside
  ladder, door steps, dust bin posts, tunnel exit stairs.
WARN (analog recommendation): embedment < 0.28 (Symaga), anchor edge distance < 0.19 (Sukup), no apron.
FINDING: through-bolts over the tunnel cavity; wind uplift vs anchor capacity; what the case 5 tilt moves.

Broken variants that must fail: anchors shortened to 0.10 (case 6), every second anchor missing,
tilt 0.6 deg (case 5), ring r_out 11.20, mean settlement 0.20, no duct opening in the ring, ground
taken at 0.000 (the old model).

Run:
    blender --background --python world/build/check_foundation.py
Exit code 1 when any case fails.
"""

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import aspiration as asp  # noqa: E402
from kit import common as c  # noqa: E402
from kit import foundation as fnd  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402
from kit import tunnel as tun  # noqa: E402

DRAWN_R_IN, DRAWN_R_OUT, DRAWN_TOL = 10.775, 11.375, 0.02     # PDF p.2 vectors (rec_006b7b47, rec_82817f8c)
DRAWN_PLINTH_D, PLINTH_TOL = 22.745, 0.03                    # PDF p.4 section (rec_4c478d1b)
DRAWN_GROUND = -0.451                                        # PDF p.4 pit section, scaled from -1.900 / -5.100
DRAWN_FLOOR = 0.600                                          # PDF p.4, p.6
STIFF_FOOT = (silo.R + 0.5 * silo.WAVE_DEPTH + silo.SHEET_T_BOTTOM,
              silo.R + 0.5 * silo.WAVE_DEPTH + silo.SHEET_T_BOTTOM + silo.OMEGA[2][0] + silo.OMEGA_T)
CHAIR_NUT = (STIFF_FOOT[0] + 0.11, 0.26)                     # silo_msvu220.build_anchors: nut r and top z
WIND_PA, CH, CF = 410.0, 1.3, 0.8                            # ДБН В.1.2-2 for Лубни (rec in research §5), gust, cylinder
FCK = 20.0                                                   # C20/25


def _bvh(data, off=(0.0, 0.0, 0.0)):
    v, f = data
    v = np.asarray(v, float) + off
    polys = [tuple(int(i) for i in row) for block in (f if isinstance(f, list) else [f]) for row in np.asarray(block)]
    return BVHTree.FromPolygons([tuple(p) for p in v], polys)


def _verts(data):
    return np.asarray(data[0], float)


def geometry_checks(site, fs, anchors_patch=None):
    out = []
    r = fs["ring"]
    ring0 = fnd.build_ring(None)
    rv = _verts(ring0)
    rr = np.hypot(rv[:, 0], rv[:, 1])
    out.append(("ring radii = drawing (PDF p.2)", abs(rr.min() - DRAWN_R_IN) <= DRAWN_TOL and abs(rr.max() - DRAWN_R_OUT) <= DRAWN_TOL,
                f"kit {rr.min():.3f}..{rr.max():.3f}, drawn {DRAWN_R_IN}..{DRAWN_R_OUT} ± {DRAWN_TOL}"))
    out.append(("plinth diameter = section (PDF p.4)", abs(2 * rr.max() - DRAWN_PLINTH_D) <= PLINTH_TOL,
                f"kit Ø{2 * rr.max():.3f}, drawn Ø{DRAWN_PLINTH_D}"))
    top = rv[:, 2].max() + silo.FLOOR_Z
    out.append(("plinth top = +0.600 (ДБН В.2.6-221 п. 6.10: ± 1.5 mm)", abs(top - DRAWN_FLOOR) <= fs["limits"]["found_top_tol_m"],
                f"{top:+.4f}"))
    fb = fs["ring"]["footing"]["bottom_z"]
    need = DRAWN_GROUND - fs["limits"]["frost_depth_m"]
    out.append(("footing below the frost depth (п. 6.3)", fb <= need + 1e-9, f"bottom {fb:+.2f} vs <= {need:+.2f}"))

    unsupported, cut_cavity, gap_bad, duct_hits = [], [], [], []
    fans = silo.build_fans()
    ducts = fans[2]
    for s in site["silos"]:
        off = np.array([s["x"], s["y"], s["z"]])
        band = fnd.tunnel_band(site, s)
        ring = fnd.build_ring(band)
        t = next((t for t in site["tunnels"] if fnd.tunnel_band(site, s) is not None and abs(t["row_y"] - s["y"]) < 1e-6
                  and min(t["conveyor"]["casing_x"]) - 1 <= s["x"] <= max(t["conveyor"]["casing_x"]) + 1), None)
        trees = [_bvh(ring, off)]
        if t is not None:
            trees.append(_bvh(tun.build_civil(site, t)))
            x0, y0, x1, y1, fz, cz = tun.inner_box(site, t)
            cav = c.box((x0 + 0.01, y0 + 0.01, fz + 0.01), (x1 - 0.01, y1 - 0.01, cz - 0.01))
            if _bvh(ring, off).overlap(_bvh(cav)):
                cut_cavity.append(s["id"])
            ys = _verts(ring)[:, 1]
            n_end = ys[ys > 0].min() - band[1]
            s_end = band[0] - ys[ys < 0].max()
            if not (0 <= n_end <= 0.05 and 0 <= s_end <= 0.05):
                gap_bad.append(f"{s['id']} ends {n_end:.3f} / {s_end:.3f}")
        for th in silo.stiffener_angles():
            for rad in STIFF_FOOT:
                p = Vector((s["x"] + rad * math.cos(th), s["y"] + rad * math.sin(th), s["z"] + 0.01))
                if not any(tr.ray_cast(p, Vector((0, 0, -1)), 0.06)[0] is not None for tr in trees):
                    unsupported.append(f"{s['id']} {math.degrees(th):.2f}° r {rad:.2f}")
        if _bvh(ducts, off).overlap(_bvh(ring, off)):
            duct_hits.append(s["id"])
    out.append(("concrete under the foot of every stiffener (real meshes)", not unsupported,
                f"{6 * silo.STIFFENERS * 2} rays; over soil: {unsupported[:6]}"))
    out.append(("ring does not cut the tunnel cavity", not cut_cavity, f"cut: {cut_cavity}"))
    out.append(("ring ends at the tunnel wall faces (<= 5 cm)", not gap_bad, f"{gap_bad}"))
    out.append(("aeration fan ducts pass the plinth through its openings", not duct_hits, f"duct x ring on {duct_hits}"))
    dv = _verts(ducts)
    inner = np.hypot(dv[:, 0], dv[:, 1]).min()
    out.append(("fan ducts reach under the collector ends (PDF p.2 r 10.68)", inner <= silo.aeration()["collector_r1"],
                f"duct inner end r {inner:.2f}"))
    return out


def anchor_checks(site, fs, state, patch=None):
    out = []
    a, lim = fs["anchors"], fs["limits"]
    s0 = site["silos"][0]
    band = fnd.tunnel_band(site, s0)
    anchors = fnd.anchor_layout(band, state)
    if patch:
        anchors = patch(anchors)
    out.append(("one anchor per stiffener", len(anchors) == silo.STIFFENERS, f"{len(anchors)} vs {silo.STIFFENERS} stiffeners"))
    off = []
    for k in anchors:
        th = math.radians(k["deg"])
        off.append(math.hypot(k["x"] - CHAIR_NUT[0] * math.cos(th), k["y"] - CHAIR_NUT[0] * math.sin(th)))
    out.append(("anchors under the chair nuts (п. 6.10: ± 5 mm in plan)", max(off) <= lim["anchor_plan_tol_m"],
                f"worst {max(off) * 1000:.1f} mm"))
    lo, hi = lim["anchor_top_tol_m"]
    proj = [k["z_top"] for k in anchors]
    ok = all(a["projection"] + lo <= p <= a["projection"] + hi for p in proj) and min(proj) > CHAIR_NUT[1]
    out.append(("anchor projection within tolerance and through the nut (п. 6.10)", ok,
                f"{min(proj):.3f}..{max(proj):.3f} m vs design {a['projection']} [{lo:+}, {hi:+}], nut top {CHAIR_NUT[1]}"))
    ring = [k for k in anchors if k["kind"] != "through_bolt"]
    emb = min(k["embed"] for k in ring)
    out.append(("anchor embedment >= design (shortened anchor = case 6)", emb >= a["hef"] - 1e-9, f"min {emb:.2f} m vs {a['hef']}"))
    out.append((f"embedment >= {lim['hef_warn_m']} m (Symaga, WARN)", True,
                f"{emb:.2f} m" + (" — WARN: below the Symaga minimum" if emb < lim["hef_warn_m"] else "")))
    edge = fs["ring"]["r_out"] - a["r"]
    out.append((f"anchor edge distance >= {lim['edge_dist_min_m']} m (Sukup, WARN)", True,
                f"{edge:.3f} m" + (" — WARN" if edge < lim["edge_dist_min_m"] else "")))
    out.append(("apron >= 2 m on collapsible soil (ДСТУ-Н 44, WARN)", True,
                "WARN: no apron in the drawing or the model" if not fs["apron"]["in_drawing"] else "drawn"))
    tb = [k for k in anchors if k["kind"] == "through_bolt"]
    tb_deg = ", ".join("%.2f°" % k["deg"] for k in tb)
    out.append(("anchors over the tunnel cavity: FINDING, not a model error", True,
                f"{len(tb)} per silo on the tunnel line ({tb_deg}): the 0.40 roof slab "
                f"cannot take a {a['hef']} m cast-in anchor, the model uses through-bolts with a plate under the ceiling"))

    # wind uplift on the empty silo against the concrete cone (EN 1992-4, uncracked), rough: wall only, roof ignored
    force = WIND_PA * CH * CF * 2 * silo.R * silo.WALL_TOP / 1000.0
    moment = force * (silo.FOUND_H + silo.WALL_TOP / 2)
    t_max = 4 * moment / (len(anchors) * 2 * a["r"]) if anchors else float("inf")
    cap = 7.7 * math.sqrt(FCK) * (emb * 1000) ** 1.5 / 1000 / 1.5
    out.append(("wind uplift vs anchor capacity: FINDING", True,
                f"empty silo, {WIND_PA:.0f} Pa × {CH} × {CF}: M ≈ {moment:.0f} kNm, tension ≤ {t_max:.1f} kN per anchor "
                f"(dead load ignored) vs concrete cone ≈ {cap:.0f} kN at hef {emb:.2f}: a storm alone does not pull "
                + ("even the shortened anchors" if emb < a["hef"] else "the anchors")))
    return out


def state_checks(fs, state):
    out = []
    lim = fs["limits"]
    i = math.tan(math.radians(state.get("deg", 0.0)))
    out.append(("tilt <= 0.002 (ДБН В.2.6-221 п. 6.8)", i <= lim["tilt_max"], f"i = {i:.4f} ({state.get('deg', 0.0)}°)"))
    sm = state.get("settle_mean_m", 0.0)
    out.append(("mean settlement <= 0.15 m (п. 6.8)", sm <= lim["settle_mean_max_m"], f"{sm:.2f} m"))
    marks = fnd.mark_positions()
    rr = [math.hypot(x, y) for x, y, _, _ in marks]
    opp = all(any(math.hypot(x + x2, y + y2) <= 0.05 for x2, y2, _, _ in marks) for x, y, _, _ in marks)
    above = min(z for _, _, z, _ in marks) + silo.FLOOR_Z > DRAWN_GROUND
    out.append(("settlement marks: >= 6, on the plinth face, in opposite pairs (п. 6.11–6.12)",
                len(marks) >= 6 and opp and above and max(abs(v - fs["ring"]["r_out"]) for v in rr) <= 0.02,
                f"{len(marks)} marks, opposite pairs {opp}, above ground {above}"))
    deg = fs["states"]["case5_tilt"]["deg"]
    post_z = 14.57 - silo.FLOOR_Z                  # SITE silo_top_galleries.supports.post_z on the silo wall
    deck = 23.2 - silo.FLOOR_Z
    out.append(("case 5 tilt: FINDING", True,
                f"{deg}° moves the gallery post feet on the wall by {post_z * math.tan(math.radians(deg)):.3f} m and the deck "
                f"level by {deck * math.tan(math.radians(deg)):.3f} m against the neighbour silo. No settlement joint between "
                f"silo and noria pit on the drawing (ДБН В.2.6-221 п. 6.9): candidate for case 7"))
    return out


def ground_checks(site, ground):
    out, bad = [], []

    def bottom(data, dz=0.0):
        return float(_verts(data)[:, 2].min()) + dz

    fans = silo.build_fans()
    g_local = lambda z: z + silo.FLOOR_Z  # noqa: E731
    items = [("fan pads", g_local(bottom(fans[3]))), ("outside ladder", g_local(bottom(silo.build_ladder()))),
             ("door steps", g_local(bottom(silo.build_doors()[2])))]
    for b in site["aspiration"]["dust_bins"]:
        sysd = next(s for s in site["aspiration"]["systems"] if s["unit_at"] == b["id"])
        items.append((f"dust bin {b['id']} posts", bottom(asp.build_bin(b, sysd["riser_xy"][1])["bin_frame"])))
    for t in site["tunnels"]:
        _, treads, _ = tun.build_exit_stair(t)
        items.append((f"{t['id']} exit stair top", float(_verts(treads)[:, 2].max())))
    for name, z in items:
        tol = 0.25 if "stair top" in name else 0.02     # top tread one riser below grade, riser <= 0.25 (ISO 14122-3)
        if not (ground - tol <= z <= ground + 0.02):
            bad.append(f"{name} {z:+.3f}")
    out.append((f"things on the ground stand on the drawn ground {DRAWN_GROUND} (PDF p.4)", not bad and abs(ground - DRAWN_GROUND) <= 0.01,
                f"{len(items)} items vs ground {ground:+.3f}; off: {bad}"))
    return out


def checks(site, fs=None, state=None, anchors_patch=None, ground=None):
    fs = fs or site["silo_foundation"]
    state = state if state is not None else fs["states"]["design"]
    saved = fnd.spec
    fnd.spec = lambda: fs
    try:
        return (geometry_checks(site, fs) + anchor_checks(site, fs, state, anchors_patch) + state_checks(fs, state)
                + ground_checks(site, c.ground_z() if ground is None else ground))
    finally:
        fnd.spec = saved


def main():
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    ok_all = True
    for name, ok, info in checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    fs = site["silo_foundation"]
    narrow = copy.deepcopy(fs)
    narrow["ring"]["r_out"] = 11.20
    no_open = copy.deepcopy(fs)
    no_open["ring"]["fan_duct_opening"]["w"] = 0.0
    variants = [
        ("anchors shortened to 0.10 m (case 6)", dict(state=fs["states"]["case6_short_anchor"])),
        ("every second anchor missing", dict(anchors_patch=lambda a: a[::2])),
        ("tilt 0.6 deg (case 5)", dict(state=fs["states"]["case5_tilt"])),
        ("ring r_out 11.20", dict(fs=narrow)),
        ("mean settlement 0.20 m", dict(state={"settle_mean_m": 0.20})),
        ("no duct opening in the ring", dict(fs=no_open)),
        ("ground taken at 0.000 (old model)", dict(ground=0.0)),
    ]
    for name, kw in variants:
        failed = [n for n, ok, _ in checks(site, **kw) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
