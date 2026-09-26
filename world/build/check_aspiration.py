"""Aspiration (block E) check. The dust bins are drawn; units and duct routes are a judgment,
so this check holds them to the norms, to independent numbers from the research and to the
geometry already in the model.

Norms and numbers:
- flanges per tunnel conveyor = spec (15: 14 inlets + discharge box);
- fan air within the range the research derived independently (rec_533cc352);
- design-load speed >= 18 m/s on sloped and horizontal runs, >= 12 m/s on verticals («Указания» 1998);
  <= 25 m/s (recommendation); collector diameters never shrink along the flow;
- partial load (open gates downstream of a segment) is reported as a finding, not hidden.

Geometry, on the real meshes (Blender BVH overlap), ducts against:
- tunnel concrete with the riser roof holes, pit walls and slabs with the riser cover hole;
- gate stacks, conveyor casing, cover, drive, discharge hood, supports;
- noria legs, boot and head, tower frame;
- dust bin frame, shell and ladder.

Plus: walkway headroom under the main, clearance to silo walls and aeration fans, dust bins clear
of silos and towers.

Dust bin vs aeration fans: on the fan geometry of the silo kit (plan hulls). Touching fails; less than a
service gap is reported as a finding (the bins are drawn, the fan positions are EST).

Broken variants that must fail: riser A on silo S1, roof hole not cut, pit cover hole not cut,
T9 collector on the row axis, main at +1.0.

Run:
    blender --background --python world/build/check_aspiration.py
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

from kit import aspiration as asp  # noqa: E402
from kit import common as c  # noqa: E402
from kit import noria_tower as tower  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402
from kit import tunnel as tun  # noqa: E402

SPEC_FLANGES_PER_TUNNEL = 15                 # PDF p.9, p.11, p.12
RESEARCH_AIR = {"A": (4000, 6200), "B": (4800, 7100)}   # rec_533cc352, derived independently
HEADROOM = 2.2                               # clear height over a walkway (ISO 14122-2 / ДБН)
SILO_WALL = silo.R + silo.OMEGA[2][0] + 0.05  # wall + stiffeners
CLEAR = 0.2
FAN_SERVICE = 0.6                            # judgment: service gap around a fan motor
POST_HALF = 0.075                            # SHS 150 bin posts


def _slope(a, b):
    run = np.linalg.norm((np.array(b) - np.array(a))[:2])
    return 90.0 if run < 1e-6 else math.degrees(math.atan2(abs(b[2] - a[2]), run))


def _bvh(data, offset=(0.0, 0.0, 0.0)):
    if data is None:
        return None
    v, f = data
    v = np.asarray(v, float) + offset
    polys = [tuple(int(i) for i in row) for block in (f if isinstance(f, list) else [f]) for row in np.asarray(block)]
    return BVHTree.FromPolygons([tuple(p) for p in v], polys) if polys else None


def _seg_dist_2d(p, a, b):
    a, b, p = np.asarray(a[:2], float), np.asarray(b[:2], float), np.asarray(p, float)
    d = b - a
    t = 0.0 if d @ d < 1e-12 else float(np.clip((p - a) @ d / (d @ d), 0.0, 1.0))
    return float(np.linalg.norm(p - (a + d * t)))


def _hull(pts):
    pts = sorted(set(map(tuple, np.round(pts, 4))))
    if len(pts) < 3:
        return pts

    def half(seq):
        h = []
        for p in seq:
            while len(h) >= 2 and np.cross(np.subtract(h[-1], h[-2]), np.subtract(p, h[-2])) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(pts), half(pts[::-1])
    return lo[:-1] + up[:-1]


def _inside(p, poly):
    if len(poly) < 3:
        return False
    s = [np.cross(np.subtract(b, a), np.subtract(p, a)) for a, b in zip(poly, poly[1:] + poly[:1])]
    return all(v >= 0 for v in s) or all(v <= 0 for v in s)


def _edges(poly):
    return list(zip(poly, poly[1:] + poly[:1])) if len(poly) > 2 else [tuple(poly)]


def _cross(a, b, c_, d):
    o = lambda p, q, r: np.sign(np.cross(np.subtract(q, p), np.subtract(r, p)))  # noqa: E731
    return o(a, b, c_) != o(a, b, d) and o(c_, d, a) != o(c_, d, b)


def poly_dist(P, Q):
    """Plan distance between two convex polygons (a 2-point list is a segment); 0 when they touch."""
    if _inside(P[0], Q) or _inside(Q[0], P) or any(_cross(*e, *g) for e in _edges(P) for g in _edges(Q)):
        return 0.0
    return min(min(_seg_dist_2d(p, *e) for p in P for e in _edges(Q)), min(_seg_dist_2d(q, *e) for q in Q for e in _edges(P)))


def fans(site):
    """[(silo id, plan hull, top z)] of every aeration fan with its pad, motor and outlet, site frame (kit geometry)."""
    parts = silo.build_fans()
    v = np.concatenate([np.asarray(p[0], float) for p in parts])
    ang = np.degrees(np.arctan2(v[:, 1], v[:, 0])) % 360
    out = []
    for s in site["silos"]:
        for a in silo.FAN_ANGLES:
            sel = v[np.abs((ang - a + 180) % 360 - 180) < 30]
            out.append((s["id"], _hull(sel[:, :2] + [s["x"], s["y"]]), float(sel[:, 2].max()) + s["z"]))
    return out


def obstacles(site, roof_holes, cover_holes):
    """{name: BVH} of everything the ducts must not cut, in the site frame."""
    obs = {}
    for t in site["tunnels"]:
        obs[f"{t['id']} concrete"] = _bvh(tun.build_civil(site, t, roof_holes.get(t["id"], ())))
        for k, data in tun.build_gate_stacks(site, t).items():
            obs[f"{t['id']} {k}"] = _bvh(data)
        conv, _ = tun.build_conveyor(site, t, tun.boot_inlet(site, t))
        for k in ("casing", "cover", "drive", "motor", "discharge", "supports", "inlets"):
            obs[f"{t['id']} conveyor {k}"] = _bvh(conv.get(k))
    for spec in site["noria_towers"]:
        off = (spec["x"], spec["y"], 0.0)
        parts, _, _, anchors = tower.build_noria(spec)
        frame = tower.noria_frame(spec)
        for k in ("legs", "leg_flanges", "leg_doors", "boot", "boot_cover", "head", "drive", "motor"):
            if parts.get(k) is not None:
                v, f = parts[k]
                obs[f"{spec['id']} noria {k}"] = _bvh((frame(v), f), off)
        heavy, light = tower.build_frame(spec["top_z"], sorted(spec["levels_z"]), spec["size"][0] / 2,
                                         spec["size"][1] / 2, spec["noria_axis"][0] - spec["x"])
        obs[f"{spec['id']} frame"] = _bvh(heavy, off)
        obs[f"{spec['id']} bracing"] = _bvh(light, off)
        openings = [tun.pit_opening(site, t) for t in site["tunnels"] if t["tower"] == spec["id"]]
        holes = [(x0 - spec["x"], y0 - spec["y"], x1 - spec["x"], y1 - spec["y"]) for x0, y0, x1, y1 in cover_holes.get(spec["id"], ())]
        leg_hole, deck_hole = tower.pit_holes(spec, anchors)
        walls, slabs = tower.build_pit(spec, leg_hole, openings, deck_hole, holes)
        obs[f"{spec['id']} pit walls"] = _bvh(walls, off)
        obs[f"{spec['id']} pit slabs"] = _bvh(slabs, off)
    a = site["aspiration"]
    for sysd in a["systems"]:
        b = next(b for b in a["dust_bins"] if b["id"] == sysd["unit_at"])
        for k, data in asp.build_bin(b, sysd["riser_xy"][1]).items():
            if k != "bin_gate":
                obs[f"bin {b['id']} {k}"] = _bvh(data)
    return {k: v for k, v in obs.items() if v is not None}


def checks(site, roof_holes=None, cover_holes=None):
    out = []
    rh, ch = asp.riser_holes(site, tun)
    roof_holes = rh if roof_holes is None else roof_holes
    cover_holes = ch if cover_holes is None else cover_holes
    routes = asp.routes(site, tower, tun)
    tunnels = {t["id"]: t for t in site["tunnels"]}
    obs = obstacles(site, roof_holes, cover_holes)
    fan_xy = fans(site)
    a = site["aspiration"]
    for sysd in a["systems"]:
        sid = sysd["id"]
        r = routes[sid]
        out.append((f"{sid} flanges = spec", r["flanges"] == SPEC_FLANGES_PER_TUNNEL * len(sysd["tunnels"]),
                    f"{r['flanges']} for {sysd['tunnels']}"))
        lo, hi = RESEARCH_AIR[sid]
        out.append((f"{sid} fan air within the research range", lo <= r["air_m3h"] <= hi,
                    f"{r['air_m3h']:.0f} m3/h vs {lo}..{hi} (rec_533cc352)"))
        slow, fast, partial = [], [], []
        for dct in r["ducts"]:
            v_lo, v_hi = asp.speed_ms(dct["air_m3h"], dct["d_mm"]), asp.speed_ms(dct["air_max_m3h"], dct["d_mm"])
            for p, q in zip(dct["path"], dct["path"][1:]):
                vmin = asp.V_MIN_VERTICAL if _slope(p, q) >= 60 else asp.V_MIN_SLOPED
                if v_lo < vmin - 1e-9:
                    slow.append(f"{dct['kind']} Ø{dct['d_mm']} {v_lo:.1f}<{vmin:.0f}")
            if v_hi > asp.V_MAX:
                fast.append(f"{dct['kind']} Ø{dct['d_mm']} {v_hi:.1f}")
            if "dusty_min_m3h" in dct and asp.speed_ms(dct["dusty_min_m3h"], dct["d_mm"]) < asp.V_MIN_SLOPED:
                partial.append(asp.speed_ms(dct["dusty_min_m3h"], dct["d_mm"]))
        out.append((f"{sid} design-load speeds meet the norm", not slow,
                    f"{r['states']} operating states; main Ø{r['d_main']} {asp.speed_ms(r['air_m3h'], r['d_main']):.1f} m/s, "
                    f"branch Ø{r['d_branch']}, boot Ø{r['d_boot']}; below the norm: {sorted(set(slow))}"))
        out.append((f"{sid} speeds <= {asp.V_MAX:.0f} m/s (recommendation)", not fast, f"above: {sorted(set(fast))}"))
        for tid in sysd["tunnels"]:
            cols = [d for d in r["ducts"] if d["kind"] == "collector" and abs(d["path"][0][1] - (tunnels[tid]["row_y"] + sysd["collector_y_rel"][tid])) < 1e-6
                    and tun.inner_box(site, tunnels[tid])[0] - 0.01 <= d["path"][0][0] <= tun.inner_box(site, tunnels[tid])[2] + 0.01]
            rx = sysd["riser_xy"][0]
            arms = {}
            for d in cols:                                  # a riser in the tunnel splits it into two arms
                arms.setdefault(d["path"][0][0] > rx, []).append(d)
            ds = [[d["d_mm"] for d in sorted(arm, key=lambda d: abs(d["path"][0][0] - rx), reverse=True)] for arm in arms.values()]
            ok = all(b >= a_ for arm in ds for a_, b in zip(arm, arm[1:]))
            out.append((f"{sid} collector in {tid} never shrinks along the flow", ok, f"Ø by arm {ds}"))
        out.append((f"{sid} partial load: FINDING, not a model error", True,
                    f"{len(partial)} collector runs drop below 18 m/s when the open gates are downstream "
                    f"(lowest {min(partial) if partial else 0:.1f} m/s): dust settling risk, cleaning hatches needed"))

        # tunnel collectors: ceiling, walls, lamps, cable tray, gate stacks
        for tid in sysd["tunnels"]:
            t = tunnels[tid]
            x0, y0, x1, y1, fz, cz = tun.inner_box(site, t)
            yc = t["row_y"] + sysd["collector_y_rel"][tid]
            rad = max(d["d_mm"] for d in r["ducts"] if d["kind"] == "collector" and abs(d["path"][0][1] - yc) < 1e-6) / 2000
            zc = a["collector_z"]
            _, _, lamps = tun.build_services(site, t)
            lamp_y = lamps[0][1]
            wide = y1 if lamp_y > t["row_y"] else y0
            tray_y = wide - 0.12 if wide == y1 else wide + 0.12
            gaps = {"ceiling": cz - (zc + rad), "wall": min(yc - rad - y0, y1 - (yc + rad)),
                    "lamps": abs(yc - lamp_y) - rad - 0.07, "tray": abs(yc - tray_y) - rad - 0.10}
            out.append((f"{sid} collector in {tid} clear of ceiling, walls, lamps, tray", min(gaps.values()) >= 0.02,
                        ", ".join(f"{k} {v:.3f}" for k, v in gaps.items())))
        if sysd["riser_in_pit"]:
            ok = all(abs(sysd["collector_y_rel"][tid] + tunnels[tid]["row_y"] - sysd["riser_xy"][1]) < 1e-6 for tid in sysd["tunnels"])
            out.append((f"{sid} collectors cross the pit straight to the riser", ok, f"riser y {sysd['riser_xy'][1]}"))

        # above grade: headroom, silo walls, aeration fans
        low, near_silo, near_fan = [], [], []
        for dct in r["ducts"]:
            rad = dct["d_mm"] / 2000
            for p, q in zip(dct["path"], dct["path"][1:]):
                if max(p[2], q[2]) <= 0.6:
                    continue
                if _slope(p, q) < 10 and min(p[2], q[2]) - rad < HEADROOM:
                    low.append(f"{dct['kind']} at z {min(p[2], q[2]):.2f}")
                for s in site["silos"]:
                    g = _seg_dist_2d((s["x"], s["y"]), p, q) - rad - SILO_WALL
                    if g < CLEAR:
                        near_silo.append(f"{dct['kind']} {s['id']} {g:.2f}")
                for fid, hull, top in fan_xy:
                    if min(p[2], q[2]) - rad < top:
                        g = poly_dist([tuple(p[:2]), tuple(q[:2])], hull) - rad
                        if g < CLEAR:
                            near_fan.append(f"{dct['kind']} {fid} {g:.2f}")
        out.append((f"{sid} main leaves >= {HEADROOM} m walkway headroom", not low, f"too low: {low}"))
        out.append((f"{sid} ducts clear of silo walls and aeration fans", not near_silo and not near_fan,
                    f"silos: {near_silo}, fans: {near_fan}"))

        # real geometry: duct meshes against everything else
        hits = []
        for dct in r["ducts"]:
            dv = _bvh(c.merge_parts(asp.duct(dct["path"], dct["d_mm"])))
            for name, bvh in obs.items():
                if dv.overlap(bvh):
                    hits.append(f"{dct['kind']} Ø{dct['d_mm']} x {name}")
        out.append((f"{sid} ducts cut no concrete, steel or equipment", not hits, f"{len(r['ducts'])} ducts; clashes: {sorted(set(hits))[:8]}"))

    for b in a["dust_bins"]:
        cx, cy = b["center"]
        fx, fy = b["frame"]
        s_gap = min(math.hypot(max(abs(cx - s["x"]) - fx / 2, 0), max(abs(cy - s["y"]) - fy / 2, 0))
                    for s in site["silos"]) - silo.FOUND_R
        t_gap = min(max(abs(cx - s["x"]) - fx / 2 - s["size"][0] / 2, abs(cy - s["y"]) - fy / 2 - s["size"][1] / 2)
                    for s in site["noria_towers"])
        hx, hy = fx / 2 + POST_HALF, fy / 2 + POST_HALF
        rect = [(cx - hx, cy - hy), (cx + hx, cy - hy), (cx + hx, cy + hy), (cx - hx, cy + hy)]
        f_gap, f_id = min((poly_dist(rect, hull), fid) for fid, hull, _ in fan_xy)
        out.append((f"dust bin {b['id']} clear of silos and towers", min(s_gap, t_gap) >= CLEAR,
                    f"silo foundation {s_gap:.2f} m, tower {t_gap:.2f} m"))
        out.append((f"dust bin {b['id']} does not touch an aeration fan (kit geometry)", f_gap > 0.0,
                    f"nearest fan of {f_id}: {f_gap:.2f} m to its pad"))
        if f_gap < FAN_SERVICE:
            out.append((f"dust bin {b['id']} vs fan of {f_id}: FINDING, not a model error", True,
                        f"only {f_gap:.2f} m to the fan pad (< {FAN_SERVICE} m service gap). The bin is drawn (PDF p.3), "
                        f"the fan radius is EST (silo_msvu220 build_fans): measure the fan symbols on sheet 2"))
    return out


def _failed(site, **kw):
    return [n for n, ok, _ in checks(site, **kw) if not ok]


def main():
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    ok_all = True
    for name, ok, info in checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    broken = []
    bad = copy.deepcopy(site)
    bad["aspiration"]["systems"][0]["riser_xy"] = [-38.5, 26.25]
    broken.append(("riser A moved onto silo S1", bad, {}))
    broken.append(("roof hole for riser A not cut", site, {"roof_holes": {}}))
    broken.append(("pit cover hole for riser B not cut", site, {"cover_holes": {}}))
    bad = copy.deepcopy(site)
    bad["aspiration"]["systems"][0]["collector_y_rel"]["T9"] = 0.0
    broken.append(("T9 collector on the row axis", bad, {}))
    bad = copy.deepcopy(site)
    bad["aspiration"]["main_z"] = 1.0
    broken.append(("main at +1.0", bad, {}))
    for name, s, kw in broken:
        failed = _failed(s, **kw)
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
