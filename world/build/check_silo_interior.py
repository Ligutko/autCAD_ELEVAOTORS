"""K5-b check: equipment inside the silo against the sources (research/silo_equipment.md,
SITE.json silo_equipment) and against the rest of the model.

Thermometry: cable count and sensor step as the sources; plan coverage of the floor not worse than
the reference layout (OPI table for a 72 ft bin, computed here from that table); cable bottoms above
the sweep envelope (the sweep turns round the whole floor); cables away from the outlet line (WARN,
judgment). Level sensor: one upper sensor (Lubnymash standard), outside the gallery band, clear of
the cables. Sweep: length, screw axis height, tractor position, drive housing clear of the side
outlets. Aeration: specific air flow >= the norm, longest / shortest air path <= 1.5 at full fill.

Broken variants that must fail: 7 probes (Neuero economy set), sweep 11.0 m long, three level sensors,
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


def checks(eq):
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

    variants = (("Neuero economy set: 7 probes, sensors every 4 m", neuero),
                ("sweep 11.0 m long", lambda e: e["sweep"].update(length_m=11.0)),
                ("three level sensors", lambda e: e["level_sensors"].extend([dict(e["level_sensors"][0], angle_deg=150.0),
                                                                             dict(e["level_sensors"][0], angle_deg=270.0, r=5.0)])),
                ("cables tied to the floor at 0.4 m (old layout)", floor_tie))
    for name, patch in variants:
        bad = copy.deepcopy(silo.equipment())
        patch(bad)
        failed = [n for n, ok, _ in checks(bad) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
