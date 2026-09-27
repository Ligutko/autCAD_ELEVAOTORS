"""Phase 5B/5C. Site plan (designed layer, research/design/site_plan.md): one-way truck loop gate ->
scales in -> the drawn drive-through pit -> U-turn -> under bin Ш1 -> scales out -> gate; scales,
sampler, lab / control building (АПК), gatehouse with barriers, substation + MCC block with a cable
trestle to the H6 tower, fire water tanks with a pump house, hydrants.

Site frame. Data: SITE.json `designed.site_plan`. Everything stands on the finished ground (SITE ground_z).
"""

import math

import numpy as np

from . import common as c
from . import steel as st


def _site():
    from . import receiving as rc
    return rc._site()


def spec(site=None):
    return (site or _site())["designed"]["site_plan"]


def lane_polyline(lane, step=0.5):
    """Centreline points of a lane: straight polylines, or an arc {c, r, a:[deg0, deg1]}."""
    if "arc" in lane:
        a = lane["arc"]
        n = max(2, int(math.radians(abs(a["a"][1] - a["a"][0])) * a["r"] / step))
        t = np.radians(np.linspace(a["a"][0], a["a"][1], n + 1))
        return np.column_stack([a["c"][0] + a["r"] * np.cos(t), a["c"][1] + a["r"] * np.sin(t)])
    pts = []
    for (x0, y0), (x1, y1) in zip(lane["pts"], lane["pts"][1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        pts += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    pts.append(tuple(lane["pts"][-1]))
    return np.array(pts)


def lane_width(lane, x):
    nw = lane.get("narrow")
    return nw["w"] if nw and nw["x"][0] <= x <= nw["x"][1] else lane["w"]


def lane(sp, lid):
    return next(ln for ln in sp["lanes"] if ln["id"] == lid)


def _strip(pts, half_w, z):
    """Flat ribbon along a polyline (quads), half width per point."""
    pts = np.asarray(pts, float)
    hw = np.broadcast_to(np.asarray(half_w, float), (len(pts),))
    d = np.gradient(pts, axis=0)
    d /= np.linalg.norm(d, axis=1)[:, None]
    nrm = np.column_stack([-d[:, 1], d[:, 0]])
    left, right = pts + nrm * hw[:, None], pts - nrm * hw[:, None]
    v = np.concatenate([np.column_stack([left, np.full(len(pts), z)]), np.column_stack([right, np.full(len(pts), z)])])
    n = len(pts)
    f = np.array([(i, i + 1, n + i + 1, n + i) for i in range(n - 1)])
    e1, e2 = v[f[0][1]] - v[f[0][0]], v[f[0][3]] - v[f[0][0]]
    if np.cross(e1, e2)[2] < 0:                                      # face up whatever the run direction
        f = f[:, ::-1]
    return v, f


def scales_box(sp, key):
    s = sp[key]
    y = lane(sp, s["lane"])["pts"][0][1]
    return s["x"][0], y - 1.5, s["x"][1], y + 1.5


def build_roads(site=None):
    site = site or _site()
    sp = spec(site)
    z = c.ground_z() + sp["road_z_over_ground"]
    roads = []
    for k, ln in enumerate(sp["lanes"]):
        pts = lane_polyline(ln)
        hw = [lane_width(ln, p[0]) / 2 for p in pts] if "pts" in ln else ln["w"] / 2
        roads.append(_strip(pts, hw, z + 0.002 * k))                  # a few mm apart: no z-fighting at junctions
        if ln.get("end_pad"):                                        # 12 x 12 turnaround at a dead end
            x0, y0, x1, y1 = ln["end_pad"]
            roads.append(c.box((x0, y0, z - 0.02), (x1, y1, z)))
    hs = sp["fire_tanks"].get("hardstand")                           # fire engine pier by the tanks
    if hs:
        roads.append(c.box((hs[0], hs[1], z - 0.02), (hs[2], hs[3], z)))
    # scales: steel platform +0.35 over the road with a concrete ramp each end (естакадні, rec_767b01b7)
    decks, ramps = [], []
    g = c.ground_z() + sp["road_z_over_ground"]
    for key in ("scales_in", "scales_out"):
        x0, y0, x1, y1 = scales_box(sp, key)
        top = g + 0.35
        decks.append(c.box((x0, y0, g), (x1, y1, top)))
        r = sp[key]["ramp"]
        for xa, xb, za, zb in ((x0 - r, x0, g, top), (x1, x1 + r, top, g)):
            v = np.array([(xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za), (xa, y0, g), (xb, y0, g), (xb, y1, g), (xa, y1, g)])
            ramps.append((v, np.array([(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])))
    return {"roads": ("dark", False, c.merge_parts(roads)), "scale_decks": ("galv_old", False, c.merge_parts(decks)),
            "scale_ramps": ("concrete", False, c.merge_parts(ramps))}


def sampler_geometry(sp):
    """(post xy, probe xy over the lane axis)."""
    px, py = sp["sampler_post"]
    y = lane(sp, "in")["pts"][0][1]
    return (px, py), (px, y)


def build_buildings(site=None):
    site = site or _site()
    sp = spec(site)
    g = c.ground_z()
    walls, roofs, doors = [], [], []

    def block(x, y, h):
        walls.append(c.box((x[0], y[0], g), (x[1], y[1], g + h)))
        roofs.append(c.box((x[0] - 0.2, y[0] - 0.2, g + h), (x[1] + 0.2, y[1] + 0.2, g + h + 0.15)))

    block(sp["apk"]["x"], sp["apk"]["y"], sp["apk"]["h"])
    k = sp["gate"]["kpp"]
    block(k["x"], k["y"], k["h"])
    t = sp["ktp"]
    block(t["x"], t["y"], t["h"])
    for dx in (2.0, 5.0, 8.0):                                        # transformer and switchgear doors on the long side
        doors.append(c.box((t["x"][0] + dx, t["y"][0] - 0.03, g), (t["x"][0] + dx + 1.2, t["y"][0], g + 2.4)))
    ph = sp["fire_tanks"]["pump_house"]
    block(ph["x"], ph["y"], ph["h"])
    # barriers at the gate: post + arm across each lane
    barr = []
    bx = sp["gate"]["barrier_x"]
    for ln in ("in", "out"):
        y = lane(sp, ln)["pts"][0][1]
        side = 1 if ln == "in" else -1                                # posts on the KPP side of each lane
        py = y - side * (lane(sp, ln)["w"] / 2 + 0.4)
        barr.append(c.box((bx - 0.2, py - 0.2, g), (bx + 0.2, py + 0.2, g + 1.0)))
        barr.append(c.box((bx - 0.05, min(py, y + side * 1.8), g + 0.9), (bx + 0.05, max(py, y + side * 1.8), g + 1.0)))
    # sampler: post, boom to the lane axis, probe
    (px, py), (qx, qy) = sampler_geometry(sp)
    zb = sp["sampler_boom_z"] + g
    sam = [st.rod((px, py, g), (px, py, zb + 0.4), 0.2, 20), st.member((px, py, zb), (qx, qy, zb), st.SHS_150),
           st.rod((qx, qy, zb), (qx, qy, zb - 1.6), 0.06, 12)]
    return {"buildings": ("concrete", False, c.merge_parts(walls)), "building_roofs": ("galv_old", False, c.merge_parts(roofs)),
            "building_doors": ("dark", False, c.merge_parts(doors)), "barriers": ("red", False, c.merge_parts(barr)),
            "sampler": ("yellow", False, c.merge_parts(sam))}


def build_services(site=None):
    site = site or _site()
    sp = spec(site)
    g = c.ground_z()
    ct = sp["cable_trestle"]
    posts, beams, tray = [], [], []
    z = g + ct["z"]
    for (x0, y0), (x1, y1) in zip(ct["pts"], ct["pts"][1:]):
        n = max(1, math.ceil(math.hypot(x1 - x0, y1 - y0) / ct["post_step"]))
        for k in range(n + 1):
            x, y = x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n
            posts.append(st.member((x, y, g), (x, y, z), st.SHS_100, up=(1, 0, 0)))
        d = np.array([x1 - x0, y1 - y0]) / math.hypot(x1 - x0, y1 - y0)
        s = np.array([-d[1], d[0]]) * 0.25
        tray.append(c.box((min(x0, x1) - abs(s[0]), min(y0, y1) - abs(s[1]), z), (max(x0, x1) + abs(s[0]), max(y0, y1) + abs(s[1]), z + 0.12)))
    ft = sp["fire_tanks"]
    tanks = [c.cylinder(ft["d"] / 2, g, g + ft["h"], steps=64, center=tuple(cc)) for cc in ft["c"]]
    hyd = []
    for x, y in sp["hydrants"]:
        hyd += [c.cylinder(0.09, g, g + 0.85, steps=16, center=(x, y)), c.cylinder(0.12, g + 0.85, g + 1.0, steps=16, center=(x, y))]
    return {"cable_trestle": ("galv", False, c.merge_parts(posts)), "cable_tray": ("galv_old", False, c.merge_parts(tray)),
            "fire_tanks": ("galv", True, c.merge_parts(tanks)), "hydrants": ("red", True, c.merge_parts(hyd))}


def tank_volume(sp):
    ft = sp["fire_tanks"]
    return math.pi * (ft["d"] / 2) ** 2 * ft["h"]


def build(site=None):
    site = site or _site()
    parts = {}
    parts.update(build_roads(site))
    parts.update(build_buildings(site))
    parts.update(build_services(site))
    return parts
