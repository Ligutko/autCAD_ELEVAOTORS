"""Silo МСВУ 220 foundation (phase 3): ring beam under the wall, footing, floor slab, anchors,
deformation marks, soil section. SITE.json `silo_foundation`, `ground_z`; research/foundation.md.

Local frame as silo_msvu220.py: silo axis at (0, 0), Z = 0 on the silo floor (site +0.600).
The ring breaks at the outer faces of the tunnel walls (PDF p.2): there the tunnel box carries the
wall and its 0.40 roof slab is the silo floor. A silo without a tunnel (standalone scenes) gets a
closed ring.
"""

import functools
import json
import math

import numpy as np

from . import common as c
from . import silo_msvu220 as silo
from . import steel as st

STEP_DEG = 0.25                 # polar sampling of the ring and slab outlines


@functools.lru_cache(maxsize=1)
def _site():
    return json.loads(c.SITE_JSON.read_text(encoding="utf-8"))


def spec():
    return _site()["silo_foundation"]


def to_local(z_site):
    return z_site - silo.FLOOR_Z


def tunnel_band(site, silo_spec):
    """(outer y0, outer y1, inner y0, inner y1) of the tunnel under this silo, silo frame; None if none."""
    for t in site["tunnels"]:
        if abs(t["row_y"] - silo_spec["y"]) > 1e-6:
            continue
        cx0, cx1 = t["conveyor"]["casing_x"]
        if not (min(cx0, cx1) - 1.0 <= silo_spec["x"] <= max(cx0, cx1) + 1.0):
            continue
        iy0, iy1 = t["inner_y_rel_row"]
        w = t["wall_t"]
        return iy0 - w, iy1 + w, iy0, iy1
    return None


# ================================================================== polar outlines

def _intervals(theta, r0, r1, band):
    """Radial interval [a, b] of the annulus r0..r1 at angle theta that lies outside the tunnel band
    (y <= y0 or y >= y1); None when empty."""
    if band is None:
        return r0, r1
    y0, y1 = band[0], band[1]
    s = math.sin(theta)
    if abs(s) < 1e-12:
        return None
    lo = y1 / s if s > 0 else y0 / s
    a = max(r0, lo)
    return (a, r1) if a < r1 - 1e-9 else None


def _angles(extra):
    base = np.arange(0.0, 360.0, STEP_DEG)
    return np.unique(np.round(np.concatenate([base, np.asarray(extra, float) % 360.0]), 9))


def _critical(r0, r1, band):
    """Angles (deg) where the band edge meets the circles r0, r1."""
    if band is None:
        return []
    out = []
    for y in band[:2]:
        for r in (r0, r1):
            if abs(y) < r:
                a = math.degrees(math.asin(y / r))
                out += [a, 180.0 - a]
    return out


def _runs(angles, ok):
    """Contiguous runs of angles (wrapping at 360) where ok[i] holds."""
    n = len(angles)
    if all(ok):
        return [list(range(n)) + [0]]
    start = next(i for i in range(n) if not ok[i])
    runs, cur = [], []
    for k in range(1, n + 1):
        i = (start + k) % n
        if ok[i]:
            cur.append(i)
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


def _extrude_run(pts, z0, z1, closed):
    """pts: [(theta, a, b)] along a run; prism between the inner curve a and outer curve b."""
    m = len(pts)
    inner = [(a * math.cos(t), a * math.sin(t)) for t, a, _ in pts]
    outer = [(b * math.cos(t), b * math.sin(t)) for t, _, b in pts]
    v = []
    for z in (z0, z1):
        v += [(x, y, z) for x, y in inner] + [(x, y, z) for x, y in outer]
    v = np.array(v)
    bi, bo, ti, to = 0, m, 2 * m, 3 * m
    last = m if closed else m - 1
    f = []
    for i in range(last):
        j = (i + 1) % m
        f += [(ti + i, to + i, to + j, ti + j), (bi + i, bi + j, bo + j, bo + i),
              (bo + i, bo + j, to + j, to + i), (bi + i, ti + i, ti + j, bi + j)]
    if not closed:
        for i in (0, m - 1):
            f.append((bi + i, bo + i, to + i, ti + i) if i == 0 else (bi + i, ti + i, to + i, bo + i))
    return v, np.array(f)


def annulus(r0, r1, z0, z1, band=None, gaps=()):
    """Annulus r0..r1 between z0 and z1, cut by the tunnel band and by angular gaps [(deg0, deg1)]."""
    extra = _critical(r0, r1, band) + [d for g in gaps for d in g]
    ang = _angles(extra)
    iv = [_intervals(math.radians(a), r0, r1, band) for a in ang]

    def in_gap(a):
        return any((a - g0) % 360.0 < (g1 - g0) % 360.0 - 1e-9 and (a - g0) % 360.0 > 1e-9 for g0, g1 in gaps)

    ok = [iv[i] is not None and not in_gap(a) for i, a in enumerate(ang)]
    parts = []
    closed_all = all(ok)
    for run in _runs(list(ang), ok):
        pts = [(math.radians(ang[i]), *iv[i]) for i in run]
        if closed_all:
            pts = pts[:-1]
        if len(pts) >= 2:
            parts.append(_extrude_run(pts, z0, z1, closed_all))
    return c.merge_parts(parts) if parts else None


# ================================================================== parts

def fan_gaps(width):
    half = math.degrees(width / 2 / spec()["ring"]["r_out"])
    return [(a - half, a + half) for a in silo.FAN_ANGLES]


def build_ring(band=None):
    """Ring beam in three layers so the fan ducts pass through openings in the middle one."""
    r = spec()["ring"]
    z_top, z_bot = to_local(r["top_z"]), to_local(r["stem_bottom_z"])
    oz0, oz1 = (to_local(z) for z in r["fan_duct_opening"]["z"])
    gaps = fan_gaps(r["fan_duct_opening"]["w"])
    layers = [annulus(r["r_in"], r["r_out"], z_bot, oz0, band), annulus(r["r_in"], r["r_out"], oz0, oz1, band, gaps),
              annulus(r["r_in"], r["r_out"], oz1, z_top, band)]
    return c.merge_parts([p for p in layers if p is not None])


def build_footing(band=None):
    r = spec()["ring"]
    rc = (r["r_in"] + r["r_out"]) / 2
    fw = r["footing"]
    return annulus(rc - fw["w"] / 2, rc + fw["w"] / 2, to_local(fw["bottom_z"]), to_local(fw["bottom_z"] + fw["t"]), band)


def build_floor_slab(band=None):
    s, r = spec()["floor_slab"], spec()["ring"]
    return annulus(0.0, r["r_in"] - s["joint_to_ring_m"], -s["t"], -0.002, band)


def anchor_layout(band=None, state=None):
    """One anchor per stiffener: dicts with angle, x, y, kind ('ring' | 'tunnel_wall' | 'through_bolt'),
    z_bottom, z_top (silo frame), embedment."""
    a = spec()["anchors"]
    hef = (state or {}).get("hef", a["hef"])
    slab_bottom = to_local(0.2)                   # tunnel roof slab +0.600 ... +0.200 (rec_ce0a202f)
    out = []
    for th in silo.stiffener_angles():
        x, y = a["r"] * math.cos(th), a["r"] * math.sin(th)
        kind = "ring"
        if band is not None and band[0] <= y <= band[1]:
            kind = "through_bolt" if band[2] <= y <= band[3] else "tunnel_wall"
        if kind == "through_bolt":
            zb, emb = slab_bottom - a["over_tunnel"]["plate"][2], -slab_bottom
        else:
            zb, emb = -hef, hef
        out.append(dict(deg=math.degrees(th) % 360.0, x=x, y=y, kind=kind, z_bottom=zb, z_top=a["projection"], embed=emb))
    return out


def build_anchors(band=None, state=None):
    a = spec()["anchors"]
    rods, plates = [], []
    for k in anchor_layout(band, state):
        rods.append(st.rod((k["x"], k["y"], k["z_bottom"]), (k["x"], k["y"], k["z_top"]), a["d_mm"] / 2000, 12))
        if k["kind"] == "through_bolt":
            pw, _, pt = a["over_tunnel"]["plate"]
            plates.append(c.box((k["x"] - pw / 2, k["y"] - pw / 2, k["z_bottom"]), (k["x"] + pw / 2, k["y"] + pw / 2, k["z_bottom"] + pt)))
        else:
            p = a["plate"] / 2
            plates.append(c.box((k["x"] - p, k["y"] - p, k["z_bottom"]), (k["x"] + p, k["y"] + p, k["z_bottom"] + 0.01)))
    return c.merge_parts(rods), c.merge_parts(plates)


def mark_positions():
    m, r = spec()["deformation_marks"], spec()["ring"]
    return [(r["r_out"] * math.cos(math.radians(d)), r["r_out"] * math.sin(math.radians(d)), to_local(m["z"]), d)
            for d in m["angles_deg"]]


def build_marks():
    """Wall settlement marks: a short steel bracket with a ball head on the plinth face."""
    parts = []
    for x, y, z, d in mark_positions():
        u = np.array([math.cos(math.radians(d)), math.sin(math.radians(d)), 0.0])
        p = np.array([x, y, z])
        parts.append(st.rod(p - u * 0.02, p + u * 0.06, 0.008, 8))
        parts.append(c.cylinder(0.018, z - 0.018, z + 0.018, steps=12, center=tuple((p + u * 0.07)[:2])))
    return c.merge_parts(parts)


def build(band=None, state=None):
    """{name: (verts, faces)} of the foundation parts."""
    out = {"ring": build_ring(band), "footing": build_footing(band), "floor_slab": build_floor_slab(band),
           "marks": build_marks()}
    out["anchor_rods"], out["anchor_plates"] = build_anchors(band, state)
    return {k: v for k, v in out.items() if v is not None}


# ================================================================== section faces (cutaway scenes)
# A vertical cut through the silo axis: every part meets the plane in rectangles (s0, s1, z0, z1),
# s along the plane direction t = (-ny, nx), z in the silo frame.

def _line_intervals(theta, r0, r1, band):
    """s-intervals where the ray at theta and the opposite ray cross the annulus r0..r1 outside the band."""
    out = []
    for th, sign in ((theta, 1.0), (theta + math.pi, -1.0)):
        iv = _intervals(th, r0, r1, band)
        if iv is not None:
            a, b = iv
            out.append((a, b) if sign > 0 else (-b, -a))
    if r0 <= 1e-9 and len(out) == 2 and abs(out[0][0]) < 1e-9 and abs(out[1][1]) < 1e-9:
        out = [(out[1][0], out[0][1])]                     # a full chord through the axis
    return out


def section_rects(normal, band=None, tunnel=None, extent=16.0, soil_depth=None, state=None):
    """{kind: [(s0, s1, z0, z1)]} on the cut plane through the axis. tunnel: dict with inner y0, y1,
    wall_t, floor_z, floor_slab_t, roof_top_z, ceiling_z (site z) when a tunnel crosses the plane.
    soil_depth: show soil only this deep below ground. Anchors lying in the plane come as 'anchor'."""
    nx, ny = normal
    theta = math.atan2(nx, -ny)                             # direction of t = (-ny, nx)
    fs, r = spec(), spec()["ring"]
    rects = {"ring": [], "footing": [], "floor_slab": [], "tunnel": [], "fill": []}
    for a, b in _line_intervals(theta, r["r_in"], r["r_out"], band):
        rects["ring"].append((a, b, to_local(r["stem_bottom_z"]), 0.0))
    rc, fw = (r["r_in"] + r["r_out"]) / 2, r["footing"]
    for a, b in _line_intervals(theta, rc - fw["w"] / 2, rc + fw["w"] / 2, band):
        rects["footing"].append((a, b, to_local(fw["bottom_z"]), to_local(fw["bottom_z"] + fw["t"])))
    slab_r = r["r_in"] - fs["floor_slab"]["joint_to_ring_m"]
    g = to_local(c.ground_z())
    for a, b in _line_intervals(theta, 0.0, slab_r, band):
        rects["floor_slab"].append((a, b, -fs["floor_slab"]["t"], 0.0))
        rects["fill"].append((a, b, g, -fs["floor_slab"]["t"]))       # compacted fill inside the ring
    if tunnel:
        y0, y1, w = tunnel["y0"], tunnel["y1"], tunnel["wall_t"]
        fz, rz, cz = to_local(tunnel["floor_z"]), to_local(tunnel["roof_top_z"]), to_local(tunnel["ceiling_z"])
        bot = fz - tunnel["floor_slab_t"]
        rects["tunnel"] += [(y0 - w, y1 + w, bot, fz), (y0 - w, y0, fz, rz), (y1, y1 + w, fz, rz)]
        hole = tunnel.get("roof_hole")
        rects["tunnel"] += [(y0, hole[0], cz, rz), (hole[1], y1, cz, rz)] if hole else [(y0, y1, cz, rz)]
    solids = [q for k in ("ring", "footing", "floor_slab", "tunnel", "fill") for q in rects[k]]
    if tunnel:
        solids.append((tunnel["y0"], tunnel["y1"], to_local(tunnel["floor_z"]), to_local(tunnel["roof_top_z"])))  # cavity
    top = g
    floor = to_local(c.ground_z() - soil_depth) if soil_depth else -1e9
    for i, layer in enumerate(spec()["soil"]["layers_below_ground"]):
        low = max(to_local(c.ground_z() - layer["to_m"]), floor)
        if low < top:
            rects[f"soil_{i}"] = _subtract((-extent, extent, low, top), solids)
        top = low
    d = spec()["anchors"]["d_mm"] / 1000
    rects["anchor"] = []
    for k in anchor_layout(band, state):
        off = (k["deg"] - math.degrees(theta)) % 360.0
        for sign, target in ((1.0, 0.0), (-1.0, 180.0)):
            if abs((off - target + 180) % 360 - 180) < 1e-6:
                s = sign * math.hypot(k["x"], k["y"])
                rects["anchor"].append((s - d / 2, s + d / 2, k["z_bottom"], k["z_top"]))
    return rects


def _subtract(box, solids):
    """Rectangle minus a set of rectangles, as rectangles (z bands x s intervals)."""
    s0, s1, z0, z1 = box
    zs = sorted({z0, z1} | {z for q in solids for z in q[2:] if z0 < z < z1})
    out = []
    for za, zb in zip(zs, zs[1:]):
        zm = (za + zb) / 2
        cuts = sorted((max(q[0], s0), min(q[1], s1)) for q in solids if q[2] < zm < q[3] and q[1] > s0 and q[0] < s1)
        cur = s0
        for a, b in cuts:
            if a > cur + 1e-6:
                out.append((cur, a, za, zb))
            cur = max(cur, b)
        if cur < s1 - 1e-6:
            out.append((cur, s1, za, zb))
    return out


def section_mesh(rects, normal, lift=0.0):
    """Quads on the cut plane (moved `lift` towards the camera)."""
    nx, ny = normal
    t = np.array([-ny, nx])
    v, f = [], []
    for s0, s1, z0, z1 in rects:
        k = len(v)
        for s, z in ((s0, z0), (s1, z0), (s1, z1), (s0, z1)):
            v.append((t[0] * s + nx * lift, t[1] * s + ny * lift, z))
        f.append((k, k + 1, k + 2, k + 3))
    return (np.array(v), np.array(f)) if v else None
