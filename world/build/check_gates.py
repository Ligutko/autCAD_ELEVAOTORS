"""Tunnel slide gates check (kit world/kit/gates.py): ТЗА-350/400 electric, ТЗР-350/400 manual.

Everything is measured on the meshes and compared with numbers the kit does not own:
- body height = Lubnymash site table (world/kit/data/gates_tza_tzr.json) AND the stack split in SITE.json
  silo_gates.stack_z (ТЗА 250 mm, ТЗР 90 mm), ±1 mm;
- bolt heads sit on the catalogue bolt square («рейсмус» 402 / 450), ±1 mm;
- nothing but the blade (and the rack riding on it) enters the bore prism;
- closed: the blade covers the bore with overlap; open: the bore is clear of the blade;
- the ТЗА motor is the shared IEC component for 0.18 kW (frame 63) and touches its gearbox;
- the drive (motor, gearbox, screw, switches) and the handwheel are on the chosen side, outside the body;
- handwheel rim diameter as the data row (EST 275 / 250 mm), the rim clear of the sled rails ≥ 0.1 m (a hand);
- a ТЗА over a ТЗР as in the tunnel stack: no clash (Blender BVH on the real meshes);
- face budget ТЗА ≤ 6000, ТЗР ≤ 4000; no NaN, indices in range, no degenerate faces.

Broken variants, each must fail exactly its own rule: blade 90 % open called open, body 200 mm, bolt square
+10 mm, motor pulled 50 mm off the gearbox, drive built on the wrong side, handwheel 5 cm from the rail,
ТЗР raised 50 mm into the ТЗА. (handwheel variant: rim 5 cm from the rail)

Run:
    blender --background --python world/build/check_gates.py
Exit code 1 when any case fails.
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
from kit import gates as g  # noqa: E402

SITE = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
STACK = SITE["silo_gates"]["stack_z"]
SITE_H = {"ТЗА": STACK["tza"][0] - STACK["tza"][1], "ТЗР": STACK["tzr"][0] - STACK["tzr"][1]}
BOLT_SQUARE = {350: 0.402, 400: 0.450}          # Lubnymash table (rec_bd555bb6, rec_c314da5d)
MOTOR_FRAME = "63"                              # 0.18 kW 4-pole: IEC table (iec_motor_frames.json)
HAND = 0.10                                     # judgment: room for a hand around the rim
BUDGET = {"ТЗА": 6000, "ТЗР": 4000}
DRIVE = ("motor", "gearbox", "screw", "switches")


def _arr(part):
    v, f = part
    return np.asarray(v, float), [np.asarray(b) for b in (f if isinstance(f, list) else [f])]


def _nf(part):
    return sum(len(b) for b in _arr(part)[1])


def _bbox(part):
    v = _arr(part)[0]
    return v.min(axis=0), v.max(axis=0)


def _bvh(part, dz=0.0):
    v, fs = _arr(part)
    v = v + (0.0, 0.0, dz)
    polys = [tuple(int(i) for i in row) for b in fs for row in b]
    return BVHTree.FromPolygons([tuple(p) for p in v], polys)


def _box_gap(a, b):
    (a0, a1), (b0, b1) = a, b
    d = np.maximum(0.0, np.maximum(a0 - b1, b0 - a1))
    return float(np.linalg.norm(d))


def build(tamper=None):
    """{(kind, size, state): kit result} for both kinds, both sizes, closed / open, side +1 and one side -1."""
    out = {}
    for size in (350, 400):
        for kind, fn in (("ТЗА", g.gate_tza), ("ТЗР", g.gate_tzr)):
            out[(kind, size, "closed")] = fn(size, 0.0)
            out[(kind, size, "open")] = fn(size, 1.0)
        out[("ТЗА", size, "mirror")] = g.gate_tza(size, 0.0, side=-1)
        out[("ТЗР", size, "mirror")] = g.gate_tzr(size, 0.0, side=-1)
    if tamper:
        tamper(out)
    return out


def checks(res, stack_dz=0.0):
    rows = []
    # 1. body height: data table and the SITE stack split
    bad = []
    for (kind, size, state), r in res.items():
        top = max(_bbox(r["parts"][p])[1][2] for p in ("flanges",))
        low = min(_bbox(r["parts"][p])[0][2] for p in ("flanges",))
        h = top - low
        if abs(h - SITE_H[kind]) > 1e-3 or abs(h - r["dims"]["body_h"]) > 1e-3:
            bad.append(f"{kind}-{size} {state}: {h * 1000:.1f} mm vs SITE {SITE_H[kind] * 1000:.0f}")
    rows.append(("height", not bad, "висота корпусу = таблиця Лубнимаш = SITE stack_z", bad or "250 / 90 мм"))

    # 2. bolt square
    bad = []
    for (kind, size, state), r in res.items():
        v, fs = _arr(r["parts"]["bolts"])
        top = v[v[:, 2] >= -g.FLANGE_T - 0.0085]
        half = BOLT_SQUARE[size] / 2
        ex = np.abs(np.abs(top[:, :2]).max(axis=0).max() - half - g.BOLT_HEAD / math.sqrt(3.0))
        if ex > 1e-3:
            bad.append(f"{kind}-{size}: {ex * 1000:.1f} мм від кола {BOLT_SQUARE[size]}")
    rows.append(("bolts", not bad, "болти на рейсмусі 402 / 450", bad or "±1 мм"))

    # 3. nothing but the blade and the rack inside the bore prism (between the flanges)
    bad = []
    for (kind, size, state), r in res.items():
        s = r["dims"]["bore"]
        for name, part in r["parts"].items():
            if name in ("blade", "rack"):
                continue
            v = _arr(part)[0]
            inside = (np.abs(v[:, 0]) < s / 2 - 1e-4) & (np.abs(v[:, 1]) < s / 2 - 1e-4) & (v[:, 2] < -1e-4) & (v[:, 2] > -r["dims"]["body_h"] + 1e-4)
            if inside.any():
                bad.append(f"{kind}-{size} {state}: {name}")
    rows.append(("bore", not bad, "у прохідному отворі лише полотно (і рейка на ньому)", sorted(set(bad)) or "чисто"))

    # 4. blade: closed covers the bore with overlap, open leaves it clear
    bad = []
    for (kind, size, state), r in res.items():
        s = r["dims"]["bore"]
        b0, b1 = _bbox(r["parts"]["blade"])
        if state in ("closed", "mirror") and not (b0[0] <= -s / 2 and b1[0] >= s / 2 and b0[1] <= -s / 2 and b1[1] >= s / 2):
            bad.append(f"{kind}-{size} {state}: не перекриває")
        if state == "open" and b1[0] > -s / 2 + 1e-6:
            bad.append(f"{kind}-{size} open: полотно в отворі на {(b1[0] + s / 2) * 1000:.0f} мм")
    rows.append(("blade", not bad, "закрита перекриває отвір, відкрита звільняє", bad or "так"))

    # 5. ТЗА motor = shared IEC component 0.18 kW, touching the gearbox
    bad = []
    for (kind, size, state), r in res.items():
        if kind != "ТЗА":
            continue
        if r["dims"]["motor_frame"] != MOTOR_FRAME:
            bad.append(f"{size}: типорозмір {r['dims']['motor_frame']}")
        gap = _box_gap(_bbox(r["parts"]["motor"]), _bbox(r["parts"]["gearbox"]))
        if gap > 0.002:
            bad.append(f"{size} {state}: мотор відірвано від редуктора на {gap * 1000:.0f} мм")
    rows.append(("motor", not bad, "мотор 0,18 кВт (IEC 63) на редукторі", bad or "так"))

    # 6. drive and handwheel on the chosen side, outside the body
    bad = []
    for (kind, size, state), r in res.items():
        sgn = -1 if state == "mirror" else 1
        fo = r["dims"]["flange"] / 2
        names = DRIVE if kind == "ТЗА" else ("handwheel",)
        for n in names:
            b0, b1 = _bbox(r["parts"][n])
            near = b0[1] if sgn > 0 else -b1[1]
            if near < fo - 1e-3:
                bad.append(f"{kind}-{size} {state}: {n} на {near:.3f} < {fo:.3f}")
    rows.append(("side", not bad, "привід і штурвал з обраного боку, поза корпусом", bad or "так"))

    # 7. handwheel: rim diameter as the data, clear of the sled rails by a hand
    bad = []
    for (kind, size, state), r in res.items():
        if kind != "ТЗР":
            continue
        b0, b1 = _bbox(r["parts"]["handwheel"])
        dia = b1[2] - b0[2]
        if abs(dia - r["dims"]["wheel_d"]) > 0.002:
            bad.append(f"{size}: обід {dia:.3f} ≠ {r['dims']['wheel_d']}")
        rail = _bbox(r["parts"]["frame"])
        sgn = -1 if state == "mirror" else 1
        gap = (b0[1] - rail[1][1]) if sgn > 0 else (rail[0][1] - b1[1])
        if gap < HAND:
            bad.append(f"{size} {state}: до рами {gap:.3f} м")
    rows.append(("wheel", not bad, "штурвал: діаметр з даних, рука проходить", bad or "так"))

    # 8. stack: ТЗА on top of ТЗР as in the tunnel, no clash
    bad = []
    for size in (350, 400):
        a = res[("ТЗА", size, "closed")]
        b = res[("ТЗР", size, "closed")]
        za = 0.0
        zb = -a["dims"]["body_h"] + stack_dz
        for na, pa in a["parts"].items():
            ta = _bvh(pa, za)
            for nb, pb in b["parts"].items():
                if ta.overlap(_bvh(pb, zb)):
                    bad.append(f"{size}: ТЗА.{na} × ТЗР.{nb}")
    rows.append(("stack", not bad, "ТЗА над ТЗР без перетинів (BVH)", sorted(set(bad))[:6] or "чисто"))

    # 9. faces and geometry sanity
    bad = []
    for (kind, size, state), r in res.items():
        n = sum(_nf(p) for p in r["parts"].values())
        if n > BUDGET[kind]:
            bad.append(f"{kind}-{size}: {n} граней")
        for name, p in r["parts"].items():
            v, fs = _arr(p)
            if not np.isfinite(v).all():
                bad.append(f"{kind}-{size}.{name}: NaN")
            for blk in fs:
                if len(blk) and (blk.min() < 0 or blk.max() >= len(v)):
                    bad.append(f"{kind}-{size}.{name}: індекси")
                elif len(blk):
                    p0, p1, p2 = v[blk[:, 0]], v[blk[:, 1]], v[blk[:, 2]]
                    area = np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
                    if len(blk[0]) == 4:
                        p3 = v[blk[:, 3]]
                        area = area + np.linalg.norm(np.cross(p2 - p0, p3 - p0), axis=1)
                    if (area < 1e-12).any():
                        bad.append(f"{kind}-{size}.{name}: вироджені грані {(area < 1e-12).sum()}")
    peak = {k: max(sum(_nf(p) for p in r["parts"].values()) for (kk, _, _), r in res.items() if kk == k) for k in BUDGET}
    rows.append(("mesh", not bad, "бюджет граней і ціла геометрія", bad[:6] or f"пік {peak}"))
    return rows


def _failed(rows):
    return {rid for rid, ok, _l, _i in rows if not ok}


def main():
    sys.stdout.reconfigure(errors="replace")
    ok_all = True
    base = checks(build())
    for rid, ok, label, info in base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: {info}", flush=True)
    base_fail = _failed(base)

    def t_open(o):
        o[("ТЗА", 400, "open")] = g.gate_tza(400, 0.9)

    def t_height(o):
        for k, r in o.items():
            if k[0] == "ТЗА":
                v, f = r["parts"]["flanges"]
                v = np.array(v, float)
                v[v[:, 2] < -0.1, 2] += 0.05
                r["parts"]["flanges"] = (v, f)

    def t_bolts(o):
        v, f = o[("ТЗР", 350, "closed")]["parts"]["bolts"]
        v = np.array(v, float)
        v[:, :2] *= (0.412 / 0.402)
        o[("ТЗР", 350, "closed")]["parts"]["bolts"] = (v, f)

    def t_motor(o):
        v, f = o[("ТЗА", 350, "closed")]["parts"]["motor"]
        o[("ТЗА", 350, "closed")]["parts"]["motor"] = (np.array(v, float) - (0.05, 0.0, 0.0), f)

    def t_side(o):
        o[("ТЗА", 400, "mirror")] = g.gate_tza(400, 0.0, side=1)

    def t_wheel(o):
        r = o[("ТЗР", 400, "closed")]
        v, f = r["parts"]["handwheel"]
        v = np.array(v, float)
        rail = _bbox(r["parts"]["frame"])[1][1]
        v[:, 1] -= v[:, 1].min() - (rail + 0.05)
        r["parts"]["handwheel"] = (v, f)

    variants = (("blade", "полотно відкрите на 90 % назване відкритим", t_open, 0.0),
                ("height", "корпус ТЗА 200 мм", t_height, 0.0),
                ("bolts", "рейсмус +10 мм", t_bolts, 0.0),
                ("motor", "мотор відтягнуто на 50 мм від редуктора", t_motor, 0.0),
                ("side", "привід не з того боку", t_side, 0.0),
                ("wheel", "штурвал притиснуто до рами (5 см)", t_wheel, 0.0),
                ("stack", "ТЗР піднято на 50 мм у ТЗА", None, 0.05))
    for rid, title, tamper, dz in variants:
        got = _failed(checks(build(tamper), stack_dz=dz))
        extra = got - base_fail - {rid}
        seen = rid in got and not extra
        ok_all &= seen
        print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} {title} -> {'OK' if seen else f'failed {sorted(got)}'}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
