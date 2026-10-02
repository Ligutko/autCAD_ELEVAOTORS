"""K5-b check: equipment inside the silo against the sources (research/silo_equipment.md,
SITE.json silo_equipment) and against the rest of the model.

Thermometry: cable count and sensor step as the sources; plan coverage of the floor not worse than
the reference layout (OPI table for a 72 ft bin, computed here from that table); cable bottoms above
the sweep envelope (the sweep turns round the whole floor); cables away from the outlet line (WARN,
judgment). Level sensor: one upper sensor (Lubnymash standard), outside the gallery band, clear of
the cables. Sweep: length, screw axis height, tractor position, drive housing clear of the side
outlets. Aeration: specific air flow >= the norm, longest / shortest air path <= 1.5 at full fill.

Sweep drive and tractor on real parts (si.build_sweep_parts, parked, silo frame): the housing holds the 18.5 kW motor stack
(plan and height); 18.5 kW = IEC 180M and 1.1 kW = IEC 90S; the motor shaft stands on the rotation axis; every tractor vertex
is under sweep_height_at; wheel Ø and counterweight count = SITE; BVH: the new parts cut neither the auger nor each other.
The original intermediate wheel crossing the flight is a FINDING.

Broken variants that must fail: housing 1.4 m, motor 22 kW, shaft 8 mm off the axis, tractor motor +0.6 m, wheel 10 % small,
three counterweights, wheel on the auger; 7 probes (Neuero economy set), sweep 11.0 m long, three level sensors,
cables tied to the floor at 0.4 m (the old layout).

Run:
    blender --background --python world/build/check_silo_interior.py
Exit code 1 when any case fails.
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
from kit import silo_interior as si  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402

OPI_72FT = [{"n": 4, "r": 2.80, "a0_deg": 45}, {"n": 9, "r": 8.80, "a0_deg": 10}]   # OPI Rev1.2 p.5 (rec_17065a5b)
OPI_COUNT = 13
LUB_SENSOR_STEP = 2.0            # rec_11f1e058
LUB_UPPER_SENSORS = 1            # rec_c8b8b530
SWEEP_LEN_RANGE = (si.R_IN - 0.6, si.R_IN - 0.2)   # research/silo_equipment.md §3
OUTLET_CLEAR = 1.0               # judgment: no cable over the draw-down zone of the outlet line
CABLE_CLEAR = 0.1


def coverage(xy, detect=2.7):
    g = np.linspace(-si.R_IN, si.R_IN, 241)
    xx, yy = np.meshgrid(g, g)
    pts = np.c_[xx.ravel(), yy.ravel()]
    pts = pts[np.hypot(pts[:, 0], pts[:, 1]) < si.R_IN]
    d = np.min(np.linalg.norm(pts[:, None, :] - np.asarray(xy)[None, :, :2], axis=2), axis=1)
    return float(d.max()), float((d <= detect).mean())


# ---- sweep drive and tractor on real parts (C7a): geometry from build_sweep_parts, parked at SWEEP_ANGLE, silo frame.
DRIVE_KW = 18.5               # PDF p.8 / SITE register S*.sweep: 18.5 kW
DRIVE_FRAME = "180M"          # 18.5 kW -> IEC 180M (iec_motor_frames.json, WEG W22 p.46), literal
TRACTOR_KW = 1.1              # sourced text + render (rec_979d8f61), research §3
TRACTOR_FRAME = "90S"         # 1.1 kW -> IEC 90S, literal
FIT_MARGIN = 0.0              # contents inside the housing: no margin beyond the sheet (shortfall is a FINDING for the designer)
WHEEL_TOL = 0.002             # tractor wheel Ø within 2 mm of SITE
AXIS_TOL = 0.002              # drive motor shaft on the rotation axis
_BVH_CACHE = {}


def _bvh(part):
    from mathutils.bvhtree import BVHTree
    v = np.asarray(part[0], float).reshape(-1, 3)
    polys = [tuple(int(i) for i in row) for b in (part[1] if isinstance(part[1], list) else [part[1]]) for row in np.asarray(b)]
    return BVHTree.FromPolygons([tuple(p) for p in v], polys) if polys else None


def _overlap(a, b):
    ta, tb = _bvh(a), _bvh(b)
    return ta is not None and tb is not None and bool(ta.overlap(tb))


def sweep_geom_checks(eq, faults=None):
    """Centre drive housing, motor chain, tractor against SITE `sweep` (patched dict `eq` is already in si.SWEEP)."""
    out = []
    sw = eq["sweep"]
    p = si.build_sweep_parts(detail="lod", faults=faults)
    hw, hh = sw["drive"]["w_m"] / 2, sw["drive"]["h_m"]
    t = si.DRIVE_PANEL_T
    # 1. the housing holds the drive stack: everything inside the sheet in plan, under the lids in height
    inner = [p[k] for k in ("drive_motor", "drive_gear", "drive_hub", "drive_bracket")]
    allv = np.concatenate([np.asarray(q[0], float).reshape(-1, 3) for q in inner])
    over_xy = float(np.abs(allv[:, :2]).max()) - (hw - t)
    over_z = float(allv[:, 2].max()) - (hh - 0.06)
    out.append(("sweep drive housing holds the motor, reducer, bevel box and bracket (plan and height)",
                over_xy <= FIT_MARGIN and over_z <= FIT_MARGIN,
                f"stack {np.abs(allv[:, :2]).max() * 1000:.0f} mm from the axis of {(hw - t) * 1000:.0f}, top {allv[:, 2].max():.2f} m of {hh - 0.06:.2f} m under the lids"))
    # 2. power and frame: SITE kW = registry, IEC frame = table literal
    dm = p["dims"]
    out.append((f"sweep drive {DRIVE_KW} kW = IEC {DRIVE_FRAME}, tractor {TRACTOR_KW} kW = IEC {TRACTOR_FRAME}",
                abs(sw["drive"]["kw"] - DRIVE_KW) < 1e-9 and dm["drive_frame"] == DRIVE_FRAME and abs(sw["tractor"]["kw"] - TRACTOR_KW) < 1e-9
                and dm["tractor_frame"] == TRACTOR_FRAME,
                f"SITE {sw['drive']['kw']} kW -> {dm['drive_frame']}, tractor {sw['tractor']['kw']} kW -> {dm['tractor_frame']}"))
    # 3. drive motor shaft on the rotation axis, vertical
    sh = np.asarray(p["drive_motor_parts"]["shaft"][0], float).reshape(-1, 3)
    # the keyway cuts the shaft on the crown side (-e), so the axis is the feet-side extreme minus D/2, D from the width across e
    ex, ey = si._wall_axis(si._sw_axes()[0])
    e2 = np.array([ex, ey], float)
    s2 = np.array([-ey, ex], float)
    dia = float(np.ptp(sh[:, :2] @ s2))
    a_e = float((sh[:, :2] @ e2).max()) - dia / 2.0
    a_s = 0.5 * float((sh[:, :2] @ s2).max() + (sh[:, :2] @ s2).min())
    vertical = float(np.ptp(sh[:, 2])) > 2.0 * dia
    off = math.hypot(a_e, a_s)
    out.append(("sweep drive motor shaft on the rotation axis (above the reducer and bevel box), vertical",
                off <= AXIS_TOL and vertical, f"offset {off * 1000:.2f} mm (tolerance {AXIS_TOL * 1000:.0f}), vertical {vertical}"))
    # 4. tractor under the sweep envelope: every vertex below sweep_height_at(its radius)
    low = []
    top = 0.0
    for k in ("tractor_frame", "tractor_motor", "tractor_shelf", "tractor_weights", "tractor_wheel"):
        if p.get(k) is None:
            continue
        v = np.asarray(p[k][0], float).reshape(-1, 3)
        r = np.hypot(v[:, 0], v[:, 1])
        env = np.array([si.sweep_height_at(float(x)) for x in r])
        top = max(top, float(v[:, 2].max()))
        bad = v[v[:, 2] > env + 1e-9]
        if len(bad):
            low.append(f"{k} {float(bad[:, 2].max()):.2f} m over the envelope")
    out.append(("tractor parts stay under sweep_height_at (thermometry cables are hung to that envelope)", not low,
                f"top {top:.2f} m of {si.sweep_height_at(si.SWEEP['tractor']['at_frac'] * si.SWEEP_LEN):.2f} m at the tractor; {low or 'ok'}"))
    # 5. wheel Ø from the tyre vertices (distance from the axle line), counterweights = SITE
    d, n = si._sw_axes()
    v = np.asarray(p["tractor_wheel"][0], float).reshape(-1, 3)
    c0 = v.mean(axis=0)
    rel = v - c0
    perp = rel - (rel @ d)[:, None] * d[None, :]
    d_w = 2.0 * float(np.linalg.norm(perp, axis=1).max())
    out.append(("tractor wheel Ø = SITE (tyre with tread lugs, from vertices)", abs(d_w - sw["tractor"]["wheel_d_m"]) <= WHEEL_TOL,
                f"Ø{d_w * 1000:.1f} mm vs {sw['tractor']['wheel_d_m'] * 1000:.0f}, tolerance {WHEEL_TOL * 1000:.0f} mm"))
    n_w = 0 if p.get("tractor_weights") is None else len(np.asarray(p["tractor_weights"][0])) // 8      # one 8-vertex plate each
    out.append(("tractor counterweights = SITE", n_w == sw["tractor"]["counterweights"], f"{n_w} plates vs {sw['tractor']['counterweights']}"))
    # 6. nothing of the new parts cuts the parked auger, nor each other (BVH); joined parts are listed apart
    mb = lambda key: c.merge_parts([q for k, q in p[key + "_parts"].items() if k != "shaft"])      # noqa: E731
    P = {"arm": p["arm"], "flight": p["flight"], "drive frame": p["drive_frame"], "drive cover": p["drive_cover"],
         "drive gear": p["drive_gear"], "drive hub": p["drive_hub"], "drive bracket": p["drive_bracket"], "drive motor": mb("drive_motor"),
         "wheel": p["tractor_wheel"], "tractor frame": p["tractor_frame"], "tractor motor": mb("tractor_motor"), "shelf": p["tractor_shelf"]}
    if p.get("tractor_weights") is not None:
        P["weights"] = p["tractor_weights"]
    joined = {frozenset(x) for x in (("drive gear", "drive hub"), ("drive gear", "drive frame"), ("drive hub", "drive frame"), ("drive bracket", "drive frame"),
                                     ("arm", "drive hub"), ("flight", "drive hub"), ("wheel", "tractor frame"), ("shelf", "tractor frame"),
                                     ("arm", "flight"), ("drive frame", "drive cover"), ("drive bracket", "drive cover"), ("drive motor", "drive cover"),
                                     ("drive gear", "drive cover"), ("drive hub", "drive cover"), ("drive frame", "arm"), ("drive frame", "flight"))}
    names = list(P)
    hits = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if frozenset((a, b)) in joined:
                continue
            if _overlap(P[a], P[b]):
                hits.append(f"{a} x {b}")
    out.append(("parked sweep: new drive and tractor parts cut neither the auger nor each other (BVH)", not hits,
                f"{len(names)} parts, {len(names) * (len(names) - 1) // 2 - len(joined)} pairs; clashes {hits or 'none'}"))
    mid = _overlap(p["mid_wheel"], p["flight"])
    out.append(("sweep intermediate wheel: FINDING, not a model error", True,
                "the original intermediate support wheel (left as it was, brief C7a) " + ("crosses the auger flight and its axle lies across the arm, so it would roll radially"
                                                                                          if mid else "clears the flight") ))
    return out


def checks(eq, faults=None):
    out = []
    saved = (si.EQ, si.SWEEP, si.SWEEP_LEN, si.SENSOR_STEP)
    si.EQ, si.SWEEP, si.SWEEP_LEN, si.SENSOR_STEP = eq, eq["sweep"], eq["sweep"]["length_m"], eq["thermo"]["sensor_step_m"]
    try:
        th = eq["thermo"]
        pos = si.cable_positions(th["rings"])
        out.append(("thermo cable count = reference (OPI 72 ft)", len(pos) == OPI_COUNT, f"{len(pos)} vs {OPI_COUNT}"))
        out.append(("sensor step = Lubnymash", abs(th["sensor_step_m"] - LUB_SENSOR_STEP) < 1e-6, f"{th['sensor_step_m']} m"))
        dmax, share = coverage(pos, th["detect_radius_marketing_m"])
        rmax, rshare = coverage(si.cable_positions(OPI_72FT), th["detect_radius_marketing_m"])
        out.append(("floor coverage not worse than the reference layout", dmax <= rmax + 0.05 and share >= rshare - 0.02,
                    f"farthest point {dmax:.2f} m (reference {rmax:.2f}), within {th['detect_radius_marketing_m']} m {share:.0%} (reference {rshare:.0%})"))
        _, share09 = coverage(pos, 0.9)
        out.append(("thermometry: FINDING, not a model error", True,
                    f"only {share09:.0%} of the floor lies within 0.9 m of a cable, the distance at which a hot spot shows "
                    f"in 4-5 weeks (Maier, rec_0443b316); the 2.7 m 'control radius' is marketing"))
        low = []
        for x, y, r in pos:
            bottom, top = si.cable_ends(r)
            env = si.sweep_height_at(r)
            if bottom < env + CABLE_CLEAR:
                low.append(f"r {r} bottom {bottom:.2f} < sweep {env:.2f}")
        out.append(("cable bottoms clear the sweep envelope", not low, f"too low: {low[:3]}"))
        near = [f"({x:.1f}, {y:.1f})" for x, y, _ in pos if abs(y) < OUTLET_CLEAR]
        out.append((f"cables >= {OUTLET_CLEAR} m from the outlet line (WARN, judgment)", True,
                    "WARN: " + ", ".join(near) if near else "none closer"))
        hw = eq["sweep"]["drive"]["w_m"] / 2
        dh = min(max(abs(x) - hw, abs(y) - hw) for x, y, _ in pos)
        out.append(("cables clear of the sweep drive housing", dh >= 0.3, f"closest {dh:.2f} m"))

        ls = si.level_sensor_positions()
        out.append(("one upper level sensor (Lubnymash standard)", len(ls) == LUB_UPPER_SENSORS, f"{len(ls)} in the model"))
        site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
        band = site["silo_top_galleries"]["y_rel_row"]
        bad = [f"({x:.1f}, {y:.1f})" for x, y, _ in ls if band[0] - 0.3 <= y <= band[1] + 0.3]
        out.append(("level sensor outside the gallery band on the roof", not bad, f"in the band: {bad}"))
        dc = min(math.hypot(x - cx, y - cy) for x, y, _ in ls for cx, cy, _ in pos)
        out.append(("level sensor clear of the cables", dc >= 0.5, f"closest cable {dc:.2f} m"))

        sw = eq["sweep"]
        out.append(("sweep length in range", SWEEP_LEN_RANGE[0] <= sw["length_m"] <= SWEEP_LEN_RANGE[1],
                    f"{sw['length_m']} m vs {SWEEP_LEN_RANGE[0]:.2f}..{SWEEP_LEN_RANGE[1]:.2f}"))
        axis = sw["screw_d_m"] / 2 + sw["floor_gap_m"]
        out.append(("screw axis = D/2 + floor gap", abs(si.SWEEP_R + sw["floor_gap_m"] - axis) < 1e-6 and sw["floor_gap_m"] <= 0.01,
                    f"{axis:.3f} m"))
        out.append(("tractor at 0.6-0.7 of the length (Lubnymash render)", 0.6 <= sw["tractor"]["at_frac"] <= 0.7, f"{sw['tractor']['at_frac']}"))
        side = [x for x in si.GATE_OFFSETS if x != 0.0]
        gap = min(abs(x) - si.GATE_SIZES[si.GATE_OFFSETS.index(x)] / 2 for x in side) - hw
        out.append(("sweep drive housing clear of the side outlets", gap > 0.2, f"{gap:.2f} m"))

        out += sweep_geom_checks(eq, faults)

        a = eq["aeration"]
        mass = 6381 * a["bulk_density_t_m3"]                     # PDF p.8: V = 6381 m3
        spec = len(silo.FAN_ANGLES) * a["fan_flow_m3h"] / mass
        out.append(("specific air flow >= norm", spec >= a["specific_min_m3h_t"],
                    f"{len(silo.FAN_ANGLES)} × {a['fan_flow_m3h']} / {mass:.0f} t = {spec:.1f} m3/(h·t) vs >= {a['specific_min_m3h_t']}"))
        peak = si.R_IN * math.tan(si.REPOSE)
        ratio = (silo.WALL_TOP + peak) / silo.WALL_TOP
        out.append(("air path ratio at full fill <= norm", ratio <= a["air_path_ratio_max"],
                    f"longest / shortest {ratio:.2f} vs <= {a['air_path_ratio_max']} (peaked at {math.degrees(si.REPOSE):.0f} deg)"))
        h_min = peak / (a["air_path_ratio_max"] - 1.0)
        out.append(("air path: FINDING, not a model error", True,
                    f"with a peaked top the ratio exceeds {a['air_path_ratio_max']} below {h_min:.1f} m of grain at the wall "
                    f"({h_min / silo.WALL_TOP:.0%} fill): level the peak before aerating a part-filled silo"))
    finally:
        si.EQ, si.SWEEP, si.SWEEP_LEN, si.SENSOR_STEP = saved
    return out


def main():
    eq = copy.deepcopy(silo.equipment())
    ok_all = True
    for name, ok, info in checks(eq):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    def neuero(e):
        e["thermo"]["rings"] = e["thermo"]["case2_wrong"]["rings"]
        e["thermo"]["sensor_step_m"] = e["thermo"]["case2_wrong"]["sensor_step_m"]

    def floor_tie(e):
        e["thermo"]["rings"] = [{"n": 1, "r": 0.0, "a0_deg": 0}, {"n": 4, "r": 4.5, "a0_deg": 45}, {"n": 8, "r": 8.5, "a0_deg": 0}]
        e["thermo"]["bottom_above_sweep_m"] = 0.4 - 0.55      # old kit: bottom tied at 0.4 m

    def drive_low(e):
        e["sweep"]["drive"]["h_m"] = 1.4                       # housing lower than the motor stack

    variants = (("Neuero economy set: 7 probes, sensors every 4 m", neuero),
                ("sweep 11.0 m long", lambda e: e["sweep"].update(length_m=11.0)),
                ("three level sensors", lambda e: e["level_sensors"].extend([dict(e["level_sensors"][0], angle_deg=150.0),
                                                                             dict(e["level_sensors"][0], angle_deg=270.0, r=5.0)])),
                ("cables tied to the floor at 0.4 m (old layout)", floor_tie),
                ("sweep drive housing 1.4 m high, lower than the motor stack", drive_low),
                ("sweep drive motor 22 kW (IEC 180L) instead of 18.5 kW", lambda e: e["sweep"]["drive"].update(kw=22.0)),
                ("sweep drive motor shaft 8 mm off the rotation axis", lambda e: None, {"drive_motor_dx": 0.008}),
                ("tractor motor raised 0.6 m above its shelf, over the envelope", lambda e: None, {"tractor_motor_dz": 0.6}),
                ("tractor wheel 10 % smaller than SITE", lambda e: None, {"wheel_scale": 0.9}),
                ("three counterweights instead of two", lambda e: None, {"counterweights": 3}),
                ("tractor wheel moved onto the auger (n = -0.15 m)", lambda e: None, {"tractor_n": -0.15}))
    for name, patch, *fl in variants:
        bad = copy.deepcopy(silo.equipment())
        patch(bad)
        failed = [n for n, ok, _ in checks(bad, fl[0] if fl else None) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
