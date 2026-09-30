"""Truck check (world/kit/trucks.py): the DAF XF FT 4x2 + Schmitz S.KI 24 SG 9.6 AK rig measured on its meshes.

FAIL rules (sheet numbers from kit/data/truck_grain.json, re-read in the PDFs 2026-09-30; tolerance 10 mm):
  envelope       96/53/EC: length <= 16.50 m, width without mirrors <= 2.55 m, height <= 4.00 m
  tractor_sheet  WB 3800, VA 1530, AE 990, AC 830 (cab rear wall), KA 770 (kingpin ahead of the drive axle),
                 roof 3980 over the road, rear tyres TB 2480, fifth wheel top = S 1140
  trailer_sheet  kingpin -> middle axle R 6600, axles 1310 apart, middle axle -> rear N 2920, body top HA 3490 (3600
                 with the roller tarp),
                 width 2550, wheel centres 2040, body volume within 5 % of 49.7 m3
  ground         every tyre touches the road (lowest point 0 +- 5 mm)
  underrun       rear underrun bar bottom <= 400 mm over the road
  clash          tractor and trailer do not cut each other (the kingpin in the fifth wheel slot excepted)
  tip            tipping 0 .. 44.5 deg: the body and cylinder never touch the tractor, the body stays over the road;
                 at 44.5 deg the top front edge within 0.5 m of the sheet HK 9455 (the hinge is not dimensioned:
                 the difference is printed as a FINDING)
Broken variants that must fail: trailer axles 0.3 m forward (trailer_sheet), tractor tyres 5 cm up (ground),
trailer 1.6 m forward on the tractor (clash), hinge in the middle of the body (tip), trailer 2.7 m longer (envelope +
trailer_sheet).

Run:
    blender --background --python world/build/check_trucks.py
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import trucks as tr  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

TOL = 0.010


def _v(parts, *keys):
    return np.concatenate([np.asarray(parts[k][0], float) for k in keys if k in parts])


def _bvh(data, lift=0.0):
    v, f = data
    polys = [tuple(int(i) for i in row) for b in (f if isinstance(f, list) else [f]) for row in np.asarray(b)]
    return BVHTree.FromPolygons([tuple(p) for p in np.asarray(v, float) + (0, 0, lift)], polys)


def _axles(v):
    """x centres of the wheel stations in a tyre cloud (clusters over 0.15 m apart)."""
    xs = np.sort(np.round(v[:, 0], 2))
    groups, cur = [], [xs[0]]
    for x in xs[1:]:
        if x - cur[-1] > 0.15:
            groups.append(cur)
            cur = []
        cur.append(x)
    groups.append(cur)
    return [(min(g) + max(g)) / 2 for g in groups]


def checks(parts, parts_tipped=None):
    rows = []
    allv = np.concatenate([np.asarray(v, float) for v, _ in parts.values()])
    no_mirror = np.concatenate([np.asarray(v, float) for k, (v, _) in parts.items() if k not in ("tractor_trim", "tractor_glass")])
    L = allv[:, 0].max() - allv[:, 0].min()
    W = no_mirror[:, 1].max() - no_mirror[:, 1].min()
    H = allv[:, 2].max()
    rows.append(("envelope", L <= 16.5 + 1e-6 and W <= 2.55 + 1e-6 and H <= 4.0 + 1e-6,
                 f"length {L:.2f} <= 16.50, width {W:.3f} <= 2.55 (mirrors out), height {H:.2f} <= 4.00"))
    # tractor
    tt = _v(parts, "tractor_tyres")
    ax = _axles(tt)
    rear, front = min(ax), max(ax)
    bumper = allv[:, 0].max()
    frame_end = _v(parts, "tractor_chassis")[:, 0].min()
    cab_rear = _v(parts, "tractor_cab")[:, 0].min()
    roof = _v(parts, "tractor_cab")[:, 2].max()
    rt = tt[np.abs(tt[:, 0] - rear) < 0.6]
    fw_top = _v(parts, "tractor_fifth_wheel")[:, 2].max()
    got = {"WB": front - rear, "VA": bumper - front, "AE": rear - frame_end, "AC": front - cab_rear, "KA": -rear,
           "roof": roof, "TB": rt[:, 1].max() - rt[:, 1].min(), "S": fw_top}
    want = {"WB": tr.WB, "VA": tr.VA, "AE": tr.AE, "AC": tr.AC, "KA": tr.KA, "roof": tr.ROOF_Z, "TB": tr.TB, "S": tr.S_KP}
    bad = {k: round(got[k], 3) for k in want if abs(got[k] - want[k]) > TOL}
    rows.append(("tractor_sheet", not bad, bad or "WB 3.80, VA 1.53, AE 0.99, AC 0.83, KA 0.77, roof 3.98, TB 2.48, fifth wheel 1.14"))
    # trailer
    xt = _v(parts, "trailer_tyres")
    ax = sorted(_axles(xt))
    mid = ax[1]
    rear_end = _v(parts, "trailer_frame")[:, 0].min()
    body = _v(parts, "trailer_body", "trailer_body_trim")         # the 2550 is over the chords
    left = xt[xt[:, 1] > 0][:, 1]
    right = xt[xt[:, 1] < 0][:, 1]
    track = (left.max() + left.min()) / 2 - (right.max() + right.min()) / 2
    hw_in = tr.TR_W / 2 - tr.WALL
    zf, zt = tr.FLOOR_Z, tr.HA_TR
    x_front = lambda z: tr.BODY_FRONT_BOTTOM - tr.WALL * 1.1 + (tr.BODY_FRONT_TOP - tr.BODY_FRONT_BOTTOM) * (z - tr.BODY_SIDE_Z0) / (zt - tr.BODY_SIDE_Z0)  # noqa: E731
    vol = 2 * hw_in * (zt - zf) * ((x_front(zf) + x_front(zt)) / 2 - tr.BODY_REAR_X)
    with_tarp = _v(parts, "trailer_body", "trailer_body_trim", "trailer_tarp")[:, 2].max()
    fr = _v(parts, "trailer_frame")
    pin = fr[(fr[:, 2] < tr.S_KP - 0.01) & (fr[:, 2] > tr.S_KP - 0.1) & (np.abs(fr[:, 1]) < 0.06)]   # the kingpin under the plate
    kp = (pin[:, 0].min() + pin[:, 0].max()) / 2
    got = {"R": kp - mid, "gap": (ax[2] - ax[0]) / 2, "N": mid - rear_end, "HA": body[:, 2].max(), "HA_tarp": with_tarp,
           "width": body[:, 1].max() - body[:, 1].min(), "track": track}
    want = {"R": tr.R_KP, "gap": tr.AX_GAP, "N": tr.N_REAR, "HA": tr.HA_TR, "HA_tarp": tr.HA_TR + tr.TARP_UP, "width": tr.TR_W,
            "track": tr.TR_TRACK}
    bad = {k: round(got[k], 3) for k in want if abs(got[k] - want[k]) > TOL}
    if abs(vol / tr.VOLUME - 1) > 0.05:
        bad["volume"] = round(vol, 1)
    rows.append(("trailer_sheet", not bad, bad or f"R 6.60, axles 1.31, N 2.92, top 3.49 (3.60 with the tarp), width 2.55, track 2.04, body {vol:.1f} m3 (sheet 49.7)"))
    lows = {k: round(float(_v(parts, k)[:, 2].min()), 4) for k in ("tractor_tyres", "trailer_tyres")}
    rows.append(("ground", all(abs(z) <= 0.005 for z in lows.values()), f"lowest tyre points {lows}"))
    ub = parts["trailer_trim"][0]
    ub = np.asarray(ub, float)
    ub = ub[ub[:, 0] < rear_end + 0.2]
    rows.append(("underrun", ub[:, 2].min() <= tr.UNDERRUN_MAX + 1e-6, f"underrun bar bottom {ub[:, 2].min():.3f} m <= {tr.UNDERRUN_MAX}"))
    hits = []
    tractor_b = {k: _bvh(v) for k, v in parts.items() if k.startswith("tractor_")}
    for k, v in parts.items():
        if not k.startswith("trailer_"):
            continue
        hb = _bvh(v, lift=0.002)                                   # the kingpin plate rests on the fifth wheel
        for k2, b2 in tractor_b.items():
            if (k, k2) == ("trailer_frame", "tractor_fifth_wheel"):
                continue                                           # the kingpin sits in the slot
            if hb.overlap(b2):
                hits.append(f"{k} x {k2}")
    rows.append(("clash", not hits, hits[:5] or "clean"))
    bad, info = [], ""
    for deg, tp in (parts_tipped or {}).items():
        moving = {k: v for k, v in tp.items() if k in ("trailer_body", "trailer_body_trim", "trailer_tarp", "trailer_cylinder", "trailer_door")}
        mv = np.concatenate([np.asarray(v, float) for v, _ in moving.values()])
        if mv[:, 2].min() < 0.05:
            bad.append(f"{deg} deg: body down to {mv[:, 2].min():.2f} m")
        for k, v in moving.items():
            hb = _bvh(v)
            for k2, b2 in tractor_b.items():
                if hb.overlap(b2):
                    bad.append(f"{deg} deg: {k} x {k2}")
        if deg == tr.TIP_MAX:
            top = tr.body_corner_top_front(deg)[2]
            info = f"top front edge {top:.2f} m at {deg} deg, sheet HK {tr.HK:.3f} (FINDING: {top - tr.HK:+.2f} m, hinge not on the sheet)"
            if abs(top - tr.HK) > 0.5:
                bad.append(f"top {top:.2f} vs HK {tr.HK}")
    rows.append(("tip", not bad, bad[:5] or info))
    return rows


def build(tamper=None):
    parts = tr.rig(0.0, load=0.9)["parts"]
    tipped = {d: tr.rig(d)["parts"] for d in (15.0, 30.0, tr.TIP_MAX)}
    if tamper:
        parts, tipped = tamper(parts, tipped)
    return parts, tipped


def main():
    sys.stdout.reconfigure(errors="replace")
    ok_all = True
    base = checks(*build())
    for rid, ok, info in base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {rid}: {info}", flush=True)
    base_fail = {r for r, ok, _ in base if not ok}

    def shift(parts, keys, d):
        return {k: ((np.asarray(v, float) + d, f) if k in keys else (v, f)) for k, (v, f) in parts.items()}

    def axles_fwd(parts, tipped):
        return shift(parts, ("trailer_tyres", "trailer_rims"), (0.3, 0, 0)), tipped

    def tyres_up(parts, tipped):
        return shift(parts, ("tractor_tyres",), (0, 0, 0.05)), tipped

    def trailer_fwd(parts, tipped):
        return shift(parts, [k for k in parts if k.startswith("trailer_")], (1.6, 0, 0)), tipped

    def hinge_mid(parts, tipped):
        h = tr.HINGE
        tr.HINGE = (-4.0, 1.28)
        try:
            return parts, {d: tr.rig(d)["parts"] for d in (15.0, 30.0, tr.TIP_MAX)}
        finally:
            tr.HINGE = h

    def longer(parts, tipped):
        keys = [k for k in parts if k.startswith("trailer_")]
        out = {}
        for k, (v, f) in parts.items():
            v = np.asarray(v, float).copy()
            if k in keys:
                v[v[:, 0] < -2.7, 0] -= 2.7
            out[k] = (v, f)
        return out, tipped

    for want, title, tamper in (({"trailer_sheet"}, "осі причепа на 0.3 м вперед", axles_fwd),
                                ({"ground"}, "колеса тягача на 5 см над дорогою", tyres_up),
                                ({"clash"}, "причіп на 1.6 м вперед на тягачі", trailer_fwd),
                                ({"tip"}, "шарнір підйому посередині кузова", hinge_mid),
                                ({"envelope", "trailer_sheet"}, "причіп на 2.7 м довший (16.9 м)", longer)):
        got = {r for r, ok, _ in checks(*build(tamper)) if not ok}
        seen = want <= got and not (got - base_fail - want)
        ok_all &= seen
        print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} {title} -> {'OK' if seen else sorted(got)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
