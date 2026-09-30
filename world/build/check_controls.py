"""Hands kit check (world/kit/controls.py): what is measured on the meshes against the vendor sheets and norms in
world/kit/data/control_posts.json (Grok T8a, sheets in research/design/control_posts/sources/).

FAIL:
- E-stop station box = R.STAHL 8150 sheet (116.5 x 176.5 x 91 mm) ±1 mm; the red mushroom stands out of the
  front face towards the operator side; its centre inside the reach band 0.6-1.7 m (EN 620 via a secondary source,
  analog) and not under 0.6 m (EN 60204-1);
- the station turns to the side asked for (the mushroom is on that side);
- rope-pull switch: rope supports not farther apart than 3 m (ZQ 900 manual), a run over 75 m is refused;
- cabinet = Rittal VX25 800 x 2000 x 600 on the plinth ±1 mm, HMI face 330 x 241 mm (Siemens TP1200) ±1 mm;
- stack light: base Ø60, tier 50 mm, red on top (EN 60204-1 order);
- no NaN, indices in range.

Placement in the tunnels (tunnel.build_controls): the station within 3.5 m of the conveyor drive, on the walkway,
mushroom 0.6-1.7 m over the tunnel floor; rope <= 75 m with supports <= 3 m, reaching the ends of the run; no
clash with the tunnel concrete, conveyor, gate stacks, lamps and tray (BVH on the real meshes).

Broken variants, each must fail its own rule: station centre at 0.4 m, station turned to the wrong side,
supports every 4 m, an 80 m rope, a 900 mm cabinet, green on top of the stack light, the T13 station 6 m from
its drive, the T9 rope inside the casing.

Run:
    blender --background --python world/build/check_controls.py
"""

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import controls as k  # noqa: E402
from kit import tunnel as tun  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

DATA = json.loads((ROOT / "kit" / "data" / "control_posts.json").read_text(encoding="utf-8"))
REACH = [v / 1000 for v in DATA["en620_вторинний_переказ"]["висота_пристрою_мм"]["v"]]      # 0.6-1.7 m
MIN_Z = DATA["висота_органів_мм"]["мінімум_над_рівнем_обслуговування"]["v"] / 1000             # 0.6 m
STAHL = [DATA["зона_22_пост"][n]["v"] / 1000 for n in ("ширина_мм", "висота_мм", "глибина_мм")]
RITTAL = [DATA["шафа"]["rittal_vx25_8807"][n]["v"] / 1000 for n in ("ширина_мм", "висота_мм", "глибина_мм")]
HMI = [v / 1000 for v in DATA["шафа"]["hmi_tp1200_comfort"]["фасад_мм"]["v"]]
SUPPORT = DATA["трос_zq900"]["опора_не_рідше_мм"]["v"] / 1000
XVU_D = DATA["колона_xvu"]["база_xvuc21b_діаметр_мм"]["v"] / 1000
XVU_T = DATA["колона_xvu"]["світло_xvuc29_довжина_мм"]["v"] / 1000


def _bb(p):
    v = np.asarray(p[0], float)
    return v.min(axis=0), v.max(axis=0)


def build(t=None):
    t = t or {}
    return {"post": k.ex_estop_post(-1), "post_plus": t.get("post_plus", lambda: k.ex_estop_post(+1))(),
            "cord": t.get("cord", lambda: k.pull_cord((0, 0, 0), (20, 0, 0)))(),
            "cabinet": t.get("cabinet", lambda: k.cabinet(2, hmi=True))(),
            "column": t.get("column", lambda: k.signal_column())()}


def checks(r):
    out = []
    p = r["post"]["parts"]
    b0, b1 = _bb(p["box"])
    size = b1 - b0
    dims_ok = all(abs(a - b) <= 0.0011 for a, b in zip((size[0], size[2]), (STAHL[0], STAHL[1]))) and \
        abs(size[1] - STAHL[2]) <= 0.0011 + 0.004                                  # + the 4 mm lid lip
    m0, m1 = _bb(p["mushroom"])
    zc = (m0[2] + m1[2]) / 2
    out.append(("stahl", dims_ok, f"E-stop box {np.round(size * 1000, 1)} mm vs {np.round(np.array(STAHL) * 1000, 1)}"))
    out.append(("reach", REACH[0] <= zc <= REACH[1] and zc >= MIN_Z and m0[1] < b0[1],
                f"mushroom centre {zc:.2f} m (band {REACH}, min {MIN_Z}), front {m0[1]:.3f} < box {b0[1]:.3f}"))
    q0, q1 = _bb(r["post_plus"]["parts"]["mushroom"])
    c0, c1 = _bb(r["post_plus"]["parts"]["box"])
    out.append(("side", q1[1] > c1[1], f"side +1: mushroom y {q1[1]:.3f} beyond box {c1[1]:.3f}"))
    d = r["cord"]["dims"]
    gap = d["run"] / (d["supports"] + 1)
    out.append(("rope", gap <= SUPPORT + 1e-9, f"{d['supports']} supports on {d['run']:.1f} m, gap {gap:.2f} m (max {SUPPORT})"))
    try:
        k.pull_cord((0, 0, 0), (80, 0, 0))
        refused = False
    except ValueError:
        refused = True
    out.append(("rope_max", refused, "an 80 m rope is refused (75 m per switch)"))
    cb = r["cabinet"]
    body0, body1 = _bb(cb["parts"]["body"])
    n = cb["dims"]["n"]
    csize = body1 - body0
    cab_ok = abs(csize[0] - n * RITTAL[0]) <= 0.001 and abs(csize[1] - RITTAL[2]) <= 0.001 and \
        abs(csize[2] - (RITTAL[1] + cb["dims"]["plinth"])) <= 0.001
    h0, h1 = _bb(cb["parts"]["hmi"])
    hmi_ok = abs((h1[0] - h0[0]) - HMI[0]) <= 0.001 and abs((h1[2] - h0[2]) - HMI[1]) <= 0.001
    out.append(("cabinet", cab_ok and hmi_ok, f"row {np.round(csize, 3)} for {n}, HMI {h1[0] - h0[0]:.3f} x {h1[2] - h0[2]:.3f}"))
    col = r["column"]["parts"]
    tiers = sorted((k2 for k2 in col if k2.startswith("tier_")), key=lambda t: _bb(col[t])[1][2])
    base = _bb(col["base"])
    t0, t1 = _bb(col[tiers[0]])
    col_ok = tiers[-1] == "tier_red" and abs((base[1][2] - base[0][2]) - DATA["колона_xvu"]["база_довжина_мм"]["v"] / 1000) <= 0.001 \
        and abs((t1[2] - t0[2]) - XVU_T) <= 0.001 and abs(abs(t1[0] - t0[0]) / 0.97 - XVU_D) <= 0.003
    out.append(("column", col_ok, f"bottom-up {tiers}, tier {t1[2] - t0[2]:.3f} m"))
    bad = []
    for name, res in r.items():
        for pn, (v, f) in res["parts"].items():
            v = np.asarray(v, float)
            if not np.isfinite(v).all():
                bad.append(f"{name}.{pn} NaN")
            for blk in (f if isinstance(f, list) else [f]):
                blk = np.asarray(blk)
                if len(blk) and (blk.min() < 0 or blk.max() >= len(v)):
                    bad.append(f"{name}.{pn} indices")
    out.append(("mesh", not bad, bad or "ok"))
    return out


SITE = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
NEAR_DRIVE = 3.5          # judgment: the E-stop station within sight and reach of the drive (m in plan)
END_SLACK = 1.5           # the rope reaches within 1.5 m of each end of the conveyor run in the tunnel


def _bvh(data):
    v, f = data
    polys = [tuple(int(i) for i in row) for b in (f if isinstance(f, list) else [f]) for row in np.asarray(b)]
    return BVHTree.FromPolygons([tuple(p) for p in np.asarray(v, float)], polys)


def placement(site, tamper=None):
    """Tunnel hands on the real tunnel meshes: station by the drive on the walkway, mushroom in reach over the tunnel
    floor, rope along the run (<= 75 m, supports <= 3 m), nothing cuts concrete, conveyor, gate stacks or services."""
    out = []
    for t in site["tunnels"]:
        conv, _ = tun.build_conveyor(site, t, tun.boot_inlet(site, t))
        hands, info = tun.build_controls(site, t, conv)
        if tamper:
            hands, info = tamper(t, hands, info)
        x0, y0, x1, y1, fz, cz = tun.inner_box(site, t)
        cas = np.asarray(conv["casing"][0], float)
        px, py = info["post_xy"]
        d = abs(px - info["drive_x"])
        on_walk = (y0 < py < cas[:, 1].min()) or (cas[:, 1].max() < py < y1)
        zm = info["mushroom_z"] - fz
        out.append((f"post_{t['id']}", d <= NEAR_DRIVE and on_walk and REACH[0] <= zm <= REACH[1],
                    f"{t['id']}: station {d:.2f} m from the drive, on the walkway {on_walk}, mushroom {zm:.2f} m over the floor"))
        ra, rb = info["rope"]
        lo, hi = sorted((ra[0], rb[0]))
        run_lo, run_hi = max(cas[:, 0].min(), x0), min(cas[:, 0].max(), x1)
        gap = info["rope_run"] / (info["rope_supports"] + 1)
        out.append((f"rope_{t['id']}", info["rope_run"] <= 75.0 and gap <= SUPPORT + 1e-9 and lo - run_lo <= END_SLACK + 1e-6
                    and run_hi - hi <= END_SLACK + 1.2 + 1e-6,
                    f"{t['id']}: rope {info['rope_run']:.1f} m, supports every {gap:.2f} m, covers {lo:.1f}..{hi:.1f} of {run_lo:.1f}..{run_hi:.1f}"))
        obs = {"civil": tun.build_civil(site, t)}
        obs.update({f"conv_{k2}": v for k2, v in conv.items()})
        obs.update({f"stack_{k2}": v for k2, v in tun.build_gate_stacks(site, t).items()})
        lamps, tray, _ = tun.build_services(site, t)
        obs.update({"lamps": lamps, "tray": tray})
        hits = []
        for hk, hv in hands.items():
            v, f = hv                                  # the stand plate rests on the floor: test it 2 mm up, deeper
            hb = _bvh((np.asarray(v, float) + (0, 0, 0.002), f))   # penetration still shows
            for ok_, ov in obs.items():
                if len(np.asarray(ov[0])) and hb.overlap(_bvh(ov)):
                    hits.append(f"{hk} x {ok_}")
        out.append((f"clash_{t['id']}", not hits, f"{t['id']}: {hits[:5] or 'clean'}"))
    return out


def main():
    sys.stdout.reconfigure(errors="replace")
    ok_all = True
    base = checks(build()) + placement(SITE)
    for rid, ok, info in base:
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {rid}: {info}", flush=True)
    base_fail = {rid for rid, ok, _ in base if not ok}

    def low_post():
        z = k.POST_CENTRE_Z
        k.POST_CENTRE_Z = 0.4
        try:
            return {"post": k.ex_estop_post(-1)}
        finally:
            k.POST_CENTRE_Z = z

    def sparse():
        s = k.ROPE_SUPPORT_MAX
        k.ROPE_SUPPORT_MAX = 4.0
        try:
            return k.pull_cord((0, 0, 0), (20, 0, 0))
        finally:
            k.ROPE_SUPPORT_MAX = s

    def wide():
        res = k.cabinet(2, hmi=True)
        v, f = res["parts"]["body"]
        v = np.asarray(v, float).copy()
        v[:, 0] *= 0.9 / 0.8
        res["parts"]["body"] = (v, f)
        return res

    def green_top():
        return k.signal_column(tiers=("green", "yellow", "red"))

    lp = low_post()
    variants = (("reach", "пост на висоті 0.4 м", lambda: dict(build(), post=lp["post"])),
                ("side", "пост розвернуто не в той бік", lambda: build({"post_plus": lambda: k.ex_estop_post(-1)})),
                ("rope", "опори троса через 4 м", lambda: build({"cord": sparse})),
                ("cabinet", "шафа 900 мм", lambda: build({"cabinet": wide})),
                ("column", "зелений нагорі колони", lambda: build({"column": green_top})))
    for rid, title, make in variants:
        got = {r for r, ok, _ in checks(make()) + placement(SITE) if not ok}
        seen = rid in got and not (got - base_fail - {rid})
        ok_all &= seen
        print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} {title} -> {'OK' if seen else sorted(got)}", flush=True)
    rmax = k.ROPE_MAX
    k.ROPE_MAX = 100.0
    got = {r for r, ok, _ in checks(build()) + placement(SITE) if not ok}
    k.ROPE_MAX = rmax
    seen = "rope_max" in got and not (got - base_fail - {"rope_max"})
    ok_all &= seen
    print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} трос 80 м прийнято -> {'OK' if seen else sorted(got)}", flush=True)

    def far_post(t, hands, info):
        if t["id"] != "T13":
            return hands, info
        return hands, dict(info, post_xy=(info["post_xy"][0] + 6.0 * (1 if info["post_xy"][0] < info["drive_x"] else -1), info["post_xy"][1]))

    def rope_in_casing(t, hands, info):
        if t["id"] != "T9":
            return hands, info
        v, f = hands["estop_red"]
        v = np.asarray(v, float).copy()
        sel = np.abs(v[:, 2] - (info["floor_z"] + k.ROPE_Z)) < 0.01
        v[sel, 1] = t["row_y"]
        return dict(hands, estop_red=(v, f)), info

    for rid, title, tamper in (("post_T13", "пост T13 за 6 м від приводу", far_post),
                               ("clash_T9", "трос T9 усередині кожуха", rope_in_casing)):
        got = {r for r, ok, _ in checks(build()) + placement(SITE, tamper) if not ok}
        seen = rid in got and not (got - base_fail - {rid})
        ok_all &= seen
        print(f"{'EXPECTED FAIL' if seen else 'FAIL  variant'} {title} -> {'OK' if seen else sorted(got)}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
