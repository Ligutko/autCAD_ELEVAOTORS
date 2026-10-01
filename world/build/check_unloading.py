"""Unloading check (world/kit/unloading.py): a DAF + Schmitz tipper unloads into the receiving pit under the drawn shed.

FAIL rules:
  stop       every axle's tyres on the level drive (flat_x, the grating between), none on a ramp; the truck within
             the drive width
  roof       at the top of the tip the body, bows and cylinder clear the shed eave by ROOF_CLEAR and cut no shed part
  empties    the top tip reaches FLOW_END (wheat 30 deg, Opanasyuk 2021): the body empties by gravity
  lands      the grain stream lands on the pit grating, 0.3 m inside its edges
  volume     grain is conserved: body polygon x width and the pit level give back the state's volumes (2 %)
  inside     grain in the body stays inside the tipped body, grain in the pit inside the hoppers under the grating
FINDINGS printed with the rules: the angle the shed allows vs the sheet's 44.5 deg and where the truck would have to
stand for it; the pit holds the whole load or not (choke flow).
Broken variants that must fail: truck 2 m further east (empties), full 44.5 deg forced at the stop (roof), front axle
2.2 m onto the west ramp (stop), pit level doubled (volume), stream moved 5 m west (lands), body grain lifted out of the
body (inside).

Run:
    blender --background --python world/build/check_unloading.py
"""

import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import receiving as rc  # noqa: E402
from kit import trucks as tr  # noqa: E402
from kit import unloading as u  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

SITE = u._site()
TIMES = (60.0, 75.0, 90.0, 105.0, 120.0)


def _bvh(data):
    v, f = data
    polys = [tuple(int(i) for i in row) for b in (f if isinstance(f, list) else [f]) for row in np.asarray(b)]
    return BVHTree.FromPolygons([tuple(p) for p in np.asarray(v, float)], polys)


def run(x_front=None, tip_top=None, tamper=None):
    """{t: (parts, state)} over the flow, plus the top-of-tip frame."""
    xf = u.stop_x(SITE) if x_front is None else x_front
    top = u.max_tip(SITE, xf) if tip_top is None else tip_top
    out = {}
    for t in TIMES + (top / u.TIP_RATE + 1.0,):
        parts, s = u.build(SITE, t, x_front=xf, tip_top=tip_top)
        if tamper:
            parts, s = tamper(parts, s)
        out[t] = (parts, s)
    return out


def checks(frames):
    rows = []
    p = SITE["receiving"]["pit"]
    d = p["drive"]
    t_top = max(frames)
    parts0, s0 = frames[t_top]
    xf, y = s0["x_front"], s0["y"]
    # stop: wheel footprints on the level drive
    bad = []
    for name, lx in [("front", tr.TRACTOR_FRONT_X), ("drive", tr.TRACTOR_REAR_X)] + [(f"trailer {i + 1}", a) for i, a in enumerate(tr.TRAILER_AXLES)]:
        x = u.to_world(np.array([[lx, 0.0, 0.0]]), xf, y, 0.0)[0, 0]
        r = (tr.T_TYRE_D if name in ("front", "drive") else tr.X_TYRE_D) / 2
        if not (d["flat_x"][0] <= x - r and x + r <= d["flat_x"][1]):
            bad.append(f"{name} axle at x {x:.2f}")
    if not (d["y"][0] <= y - tr.TR_W / 2 and y + tr.TR_W / 2 <= d["y"][1]):
        bad.append("off the drive width")
    rows.append(("stop", not bad, bad or f"all axles on the level drive {d['flat_x']}, bumper at x {xf:.2f}"))
    # roof
    top = s0["tip_top"]
    zt = u.top_under_shed(SITE, xf, top)
    eave = p["building"]["eave_z"]
    shed = rc.build_pit_and_shed()
    hits = []
    for k in ("trailer_body", "trailer_body_trim", "trailer_tarp", "trailer_cylinder", "trailer_door"):
        hb = _bvh(parts0[k])
        for sk in ("shed_roof", "shed_columns", "shed_walls"):
            if hb.overlap(_bvh(shed[sk][2])):
                hits.append(f"{k} x {sk}")
    full = u.full_tip_stop(SITE)
    rows.append(("roof", zt <= eave - u.ROOF_CLEAR + 1e-6 and not hits,
                 f"top {zt:.2f} m at {top:.1f} deg under the eave {eave} (clear {eave - zt:.2f}), {hits or 'no clash'}; "
                 f"FINDING: the sheet's {tr.TIP_MAX} deg needs the bumper at x {full:.2f}, the front axle "
                 f"{d['flat_x'][0] - u.to_world(np.array([[tr.TRACTOR_FRONT_X, 0, 0]]), full, y, 0)[0, 0]:.2f} m down the west ramp"))
    rows.append(("empties", top >= u.FLOW_END - 1e-9,
                 f"top tip {top:.1f} deg >= wheat flow end {u.FLOW_END} (Opanasyuk: maize 27, barley 29, sunflower 33"
                 f"{' - FINDING: not reached' if top < 33 else ''})"))
    # lands
    bad = []
    for t, (parts, s) in frames.items():
        if "grain_stream" not in parts:
            continue
        v = np.asarray(parts["grain_stream"][0], float)
        low = v[v[:, 2] < v[:, 2].min() + 0.15]
        if not (p["x"][0] + 0.3 <= low[:, 0].min() and low[:, 0].max() <= p["x"][1] - 0.3
                and p["y"][0] + 0.3 <= low[:, 1].min() and low[:, 1].max() <= p["y"][1] - 0.3):
            bad.append(f"t {t:.0f}: x {low[:, 0].min():.2f}..{low[:, 0].max():.2f}")
    rows.append(("lands", not bad, bad or f"stream lands on the grating {p['x']} x {p['y']}"))
    # volume and inside
    vbad, ibad = [], []
    for t, (parts, s) in frames.items():
        poly = u.body_grain(s["tip"], s["body_volume"])
        vb = u._area(poly) * u.BODY_W if len(poly) else 0.0
        if abs(vb - s["body_volume"]) > 0.02 * s["load_volume"]:
            vbad.append(f"t {t:.0f} body {vb:.1f} vs {s['body_volume']:.1f}")
        if s["pit_volume"] > 0:
            vp = u.pit_volume_below(SITE, s["pit_level"])
            if abs(vp - s["pit_volume"]) > 0.02 * s["load_volume"]:
                vbad.append(f"t {t:.0f} pit {vp:.1f} vs {s['pit_volume']:.1f}")
        if "grain_body" in parts:
            loc = np.asarray(parts["grain_body"][0], float)
            ib = u._rot(u._interior(), s["tip"])
            lx = -(loc[:, 0] - xf) + u.FRONT_X                     # back to the rig frame (facing -X)
            lz = loc[:, 2] - s["deck_z"]
            ly = y - loc[:, 1]
            out_ = 0
            for px, pz in zip(lx, lz):
                for a, b in zip(ib, np.roll(ib, -1, axis=0)):
                    if (b[0] - a[0]) * (pz - a[1]) - (b[1] - a[1]) * (px - a[0]) < -0.01 * math.hypot(*(b - a)):
                        out_ += 1
                        break
            if out_ or np.abs(ly).max() > u.BODY_W / 2 + 0.01:
                ibad.append(f"t {t:.0f}: {out_} body grain points outside")
        if "grain_pit" in parts:
            v = np.asarray(parts["grain_pit"][0], float)
            hs = u.hoppers(SITE)
            if v[:, 2].max() > p["deck_z"] - 0.3 + 1e-6 or v[:, 2].min() < min(h[3] for h in hs) - 0.05:
                ibad.append(f"t {t:.0f}: pit grain z {v[:, 2].min():.2f}..{v[:, 2].max():.2f}")
    rows.append(("volume", not vbad, vbad[:4] or f"body + pit = load {s0['load_volume']:.1f} m3 at every frame"))
    cap = u.pit_capacity(SITE)
    rows.append(("inside", not ibad, (str(ibad[:4]) if ibad else "grain inside the body and the hoppers") +
                 (f"; FINDING: the pit holds {cap:.1f} m3 >= the load {s0['load_volume']:.1f}: free fall, no choke"
                  if cap >= s0["load_volume"] else f"; FINDING: the pit holds {cap:.1f} m3 < the load: choke flow")))
    return rows


def main():
    sys.stdout.reconfigure(errors="replace")
    ok_all = True
    base = checks(run())
    for rid, ok, info in base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {rid}: {info}", flush=True)
    base_fail = {r for r, ok, _ in base if not ok}
    xf = u.stop_x(SITE)

    def double_pit(parts, s):
        return parts, dict(s, pit_level=s["pit_level"] + 1.0 if s["pit_level"] is not None else None)

    def stream_west(parts, s):
        if "grain_stream" in parts:
            v, f = parts["grain_stream"]
            parts = dict(parts, grain_stream=(np.asarray(v, float) - (5.0, 0, 0), f))
        return parts, s

    def lift_grain(parts, s):
        if "grain_body" in parts:
            v, f = parts["grain_body"]
            parts = dict(parts, grain_body=(np.asarray(v, float) + (0, 0, 2.5), f))
        return parts, s

    for want, title, kw in (("empties", "фура на 2 м далі на схід", {"x_front": xf + 2.0}),
                            ("roof", "повні 44.5 градуса на цій зупинці", {"tip_top": tr.TIP_MAX}),
                            ("stop", "передня вісь на 2.2 м на західному з'їзді", {"x_front": xf - 2.2}),
                            ("volume", "рівень у ямі на 1 м вищий", {"tamper": double_pit}),
                            ("lands", "струмінь на 5 м західніше", {"tamper": stream_west}),
                            ("inside", "зерно піднято з кузова на 2.5 м", {"tamper": lift_grain})):
        got = {r for r, ok, _ in checks(run(**kw)) if not ok}
        seen = want in got and not (got - base_fail - {want})
        ok_all &= seen
        print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} {title} -> {'OK' if seen else sorted(got)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
