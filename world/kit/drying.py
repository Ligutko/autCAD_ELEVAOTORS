"""Phase 5A. Drying loop (designed layer, research/design/drying_loop.md): tower dryer of the STRAHL
3000 FR class in building «4», T3 from the receiving tower onto the dryer, T5 from the tower over the
wet silos «2», «3» on a truss gallery with two trestles, and the spouts that close the loop:
H2 / H3 -> T3, H4 -> T5, T3 -> dryer, dryer -> T4, T5 -> wet silos, T2 / T6 -> H2, T4 -> H3.

Site frame. Data: SITE.json `designed.dryer`, `designed.drying_geom`, `receiving` (building «4»,
old silos, norias). The building «4» shell stays as drawn (plan) and becomes the dryer's base enclosure.
"""

import math

import numpy as np

from . import common as c
from . import gallery as gal
from . import steel as st

SPOUT_MM = 300                      # as the drawn spouts (SITE receiving.joints.spout_mm)
MODULE_H = 1.2                      # dryer column module seams (STRAHL FR: stacked modules, EST pitch)
TRESTLE_FOOT = 0.25                 # half size of a trestle leg footing (EST)


def _site():
    from . import receiving as rc
    return rc._site()


def geom(site=None):
    return (site or _site())["designed"]["drying_geom"]


def dryer_rect(site=None):
    """(x0, y0, x1, y1) of the dryer column; long side along Y (SITE dryer_long_axis)."""
    site = site or _site()
    g, d = geom(site), site["designed"]["dryer"]
    cx, cy = g["dryer_centre"]
    L, W = d["size"][0], d["size"][1]
    hx, hy = (W / 2, L / 2) if g["dryer_long_axis"] == "Y" else (L / 2, W / 2)
    return cx - hx, cy - hy, cx + hx, cy + hy


def dryer_top(site=None):
    return (site or _site())["designed"]["dryer"]["size"][2]


def conv_axis(cid, site=None):
    """Tail and head pulley axis points of T3 / T5 (they run along X)."""
    t = geom(site)[cid]
    z = t["z_bot"] + t["h"] / 2
    (xa, xb), y = t["x"], t["y"]
    return np.array([xa, y, z]), np.array([xb, y, z])


def conv_top(cid, site=None):
    t = geom(site)[cid]
    return t["z_bot"] + t["h"]


def wet_silo_top(s):
    """Roof peak of an old silo (30° roof, as receiving.build_old_silos)."""
    return s["floor_z"] + s["wall_h"] + s["wall_r"] * math.tan(math.radians(30.0))


def spouts(site=None):
    """[(name, p0, p1, size_mm)] of the drying-loop spouts."""
    from . import receiving as rc
    site = site or _site()
    r, g = site["receiving"], geom(site)
    nor = {n["id"]: n for n in r["norias"]}
    out = []

    def head_start(nid, toward_y, x):
        """Outlet under the head, on its end facing the conveyor; x as the spout end when the head spans it."""
        hb = rc.noria_boxes(nor[nid], r)["head"]
        y = min(max(toward_y, hb[1] + 0.15), hb[4] - 0.15)
        x = min(max(x, hb[0] + 0.15), hb[3] - 0.15)
        return np.array([x, y, hb[2]])

    def boot_inlet(nid, side, x):
        """Inlet on the boot end face (side -1: face y0, +1: face y1), 0.4 m under the boot top: the legs
        stand on the top, so a spout cannot come in there."""
        bb = rc.noria_boxes(nor[nid], r)["boot"]
        y = bb[1] - 0.05 if side < 0 else bb[4] + 0.05
        return np.array([x, y, bb[5] - 0.4])

    t3y, t5y = g["T3"]["y"], g["T5"]["y"]
    for name, nid, cid in (("H2->T3", "H2", "T3"), ("H3->T3", "H3", "T3"), ("H4->T5", "H4", "T5")):
        y = t3y if cid == "T3" else t5y
        xe = g["spout_ends"][name]
        p0 = head_start(nid, y, xe)
        out.append((name, p0, np.array([xe, y, conv_top(cid, site)]), SPOUT_MM))
    (x0, y0, x1, y1) = dryer_rect(site)
    head3 = conv_axis("T3", site)[1]
    out.append(("T3->dryer", head3 - [0, 0, g["T3"]["h"] / 2], np.array([head3[0], (y0 + y1) / 2, dryer_top(site) + 0.05]), SPOUT_MM))
    t4 = next(cv for cv in r["conveyors"] if cv["id"] == "T4")
    out.append(("dryer->T4", np.array([head3[0], t4["y"], 0.9]), np.array([head3[0], t4["y"], t4["z"] + 0.40]), SPOUT_MM))
    t5_bot = g["T5"]["z_bot"]
    for s in r["old_silos"]:
        out.append((f"T5->{ 'OS' + s['label'] }", np.array([s["x"], t5y, t5_bot]), np.array([s["x"], s["y"], wet_silo_top(s) + 0.1]), SPOUT_MM))
    conv = {cv["id"]: cv for cv in r["conveyors"]}

    def plan_end(cid):                                   # tower end of a plan conveyor (east end of T2 / T6 / west of T4)
        cv = conv[cid]
        x = max(cv["x"]) if cid in ("T2", "T6") else min(cv["x"])
        return np.array([x, cv["y"], cv["z"] + 0.2])

    out.append(("T2->H2", plan_end("T2"), boot_inlet("H2", -1, 2.90), 250))
    out.append(("T6->H2", plan_end("T6"), boot_inlet("H2", -1, 2.45), 250))
    out.append(("T4->H3", plan_end("T4"), boot_inlet("H3", +1, 2.645), 250))
    return out


def _spout(p0, p1, size_mm):
    h = size_mm / 2000
    d = np.asarray(p1, float) - np.asarray(p0, float)
    up = (1.0, 0.0, 0.0) if np.linalg.norm(d[:2]) < 1e-6 else (0.0, 0.0, 1.0)
    return st.member(p0, p1, np.array([(-h, -h), (h, -h), (h, h), (-h, h)]), up=up)


def build_dryer(site=None):
    site = site or _site()
    b4, g = site["receiving"]["building_4"], geom(site)
    (bx0, bx1), (by0, by1) = b4["outer_x"], b4["outer_y"]
    x0, y0, x1, y1 = dryer_rect(site)
    top = dryer_top(site)
    gz, eave = c.ground_z(), g["enclosure_eave"]
    pad = [c.box((bx0 - 0.3, by0 - 0.3, gz), (bx1 + 0.3, by1 + 0.3, 0.0))]
    # base enclosure = the drawn building «4»: four walls to the eave, roof with the column through it
    w = 0.05
    t4 = next(cv for cv in site["receiving"]["conveyors"] if cv["id"] == "T4")
    oy0, oy1, oz = t4["y"] - 0.5, t4["y"] + 0.5, t4["z"] + 1.0          # T4 enters through the west wall
    shell = [c.box((bx0, by0, 0.0), (bx1, by0 + w, eave)), c.box((bx0, by1 - w, 0.0), (bx1, by1, eave)),
             c.box((bx0, by0, 0.0), (bx0 + w, oy0, eave)), c.box((bx0, oy1, 0.0), (bx0 + w, by1, eave)),
             c.box((bx0, oy0, oz), (bx0 + w, oy1, eave)), c.box((bx1 - w, by0, 0.0), (bx1, by1, eave))]
    roof = [c.box((bx0 - 0.2, by0 - 0.2, eave), (x0 - 0.05, by1 + 0.2, eave + 0.2)),
            c.box((x1 + 0.05, by0 - 0.2, eave), (bx1 + 0.2, by1 + 0.2, eave + 0.2)),
            c.box((x0 - 0.05, by0 - 0.2, eave), (x1 + 0.05, y0 - 0.05, eave + 0.2)),
            c.box((x0 - 0.05, y1 + 0.05, eave), (x1 + 0.05, by1 + 0.2, eave + 0.2))]
    body_top = top - 1.6                                      # wet-grain hopper on top of the column
    base, outlet = 1.6, 0.9                                   # discharge section on legs; T4 runs under it
    column = [c.box((x0, y0, base), (x1, y1, body_top))]
    cxm = (x0 + x1) / 2
    lv = np.array([(x0, y0, base), (x1, y0, base), (x1, y1, base), (x0, y1, base),
                   (cxm - 0.2, t4["y"] - 0.2, outlet), (cxm + 0.2, t4["y"] - 0.2, outlet),
                   (cxm + 0.2, t4["y"] + 0.2, outlet), (cxm - 0.2, t4["y"] + 0.2, outlet)])
    column.append((lv, np.array([(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (7, 6, 5, 4)])))
    legs = [st.member((x, y, 0.0), (x, y, base), st.SHS_150, up=(1, 0, 0)) for x in (x0 + 0.1, x1 - 0.1) for y in (y0 + 0.1, y1 - 0.1)]
    seams = []
    for z in np.arange(base + MODULE_H, body_top - 0.3, MODULE_H):
        seams.append(c.box((x0 - 0.04, y0 - 0.04, z - 0.03), (x1 + 0.04, y1 + 0.04, z + 0.03)))
    hv = np.array([(x0, y0, body_top), (x1, y0, body_top), (x1, y1, body_top), (x0, y1, body_top),
                   (x0 + 0.6, y0 + 1.2, top), (x1 - 0.6, y0 + 1.2, top), (x1 - 0.6, y1 - 1.2, top), (x0 + 0.6, y1 - 1.2, top)])
    hopper = [(hv, np.array([(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)]))]
    # exhaust and recirculation fans on the west face above the enclosure roof (STRAHL FR: 1 + 1)
    fans, motors = [], []
    for k, (yc, d_) in enumerate(((y0 + 2.0, 1.4), (y1 - 2.0, 1.1))):
        zc = eave + 2.2 + k * 0.4
        fans.append(st.rod((x0, yc, zc), (x0 - 0.9, yc, zc), d_ / 2, 32))
        motors.append(st.rod((x0 - 0.9, yc, zc), (x0 - 1.4, yc, zc), 0.22, 20))
    # top platform, rails and a caged ladder on the south face from the enclosure roof
    plat = [st.grating_panel(x0 - 0.4, y0 - 0.4, x1 + 0.4, y0 + 0.9, body_top)]
    rail, toe = st.guard_rail([(x0 - 0.4, y0 + 0.9), (x0 - 0.4, y0 - 0.4), (x1 + 0.4, y0 - 0.4), (x1 + 0.4, y0 + 0.9)], body_top)
    from . import aspiration as asp
    stiles, rungs, cage, rest, rails, toes = asp._caged_ladder((x0 + x1) / 2, y0 - 0.05, -1, eave + 0.2, body_top, 6.0)
    return {"dryer_pad": ("concrete", False, c.merge_parts(pad)),
            "dryer_enclosure": ("galv_old", False, c.merge_parts(shell)), "dryer_enclosure_roof": ("galv_old", False, c.merge_parts(roof)),
            "dryer_column": ("galv", False, c.merge_parts(column)), "dryer_legs": ("galv_old", False, c.merge_parts(legs)), "dryer_seams": ("galv_old", False, c.merge_parts(seams)),
            "dryer_hopper": ("galv", False, c.merge_parts(hopper)), "dryer_fans": ("galv", True, c.merge_parts(fans)),
            "dryer_fan_motors": ("motor", True, c.merge_parts(motors)),
            "dryer_platform": ("grating", False, c.merge_parts(plat + rest)),
            "dryer_rails": ("yellow", False, c.merge_parts([rail] + rails)), "dryer_toes": ("yellow", False, c.merge_parts([toe] + toes)),
            "dryer_ladder": ("galv", False, c.merge_parts(stiles + rungs + cage))}


def build_t3(site=None):
    site = site or _site()
    g = geom(site)["T3"]
    tail, head = conv_axis("T3", site)
    p = gal.conveyor(tail, head, g["w"], g["h"], g["drive_side"])
    br = g["bridge"]
    (bx0, bx1), dz, hw = br["x"], br["deck_z"], br["w"] / 2
    y = g["y"]
    hx = conv_axis("T3", site)[1][0]                          # hole for the spout onto the dryer
    deck = [st.grating_panel(bx0, y - hw, hx - 0.3, y + hw, dz), st.grating_panel(hx + 0.3, y - hw, bx1, y + hw, dz)]
    frame = [st.member((bx0, y + s * hw, dz - 0.1), (bx1, y + s * hw, dz - 0.1), st.UPN160) for s in (-1, 1)]
    top = dryer_top(site)
    frame += [st.member((x, y + s * hw, top), (x, y + s * hw, dz - 0.18), st.SHS_100, up=(1, 0, 0)) for x in g["posts_x"] for s in (-1, 1)]
    rail, toe = st.guard_rail([(bx0, y + hw), (bx1, y + hw), (bx1, y - hw)], dz)
    return {"t3_casing": ("galv", False, p["casing"]), "t3_flanges": ("galv_old", False, p["flanges"]),
            "t3_drive": ("motor", False, p["drive"]), "t3_motor": ("motor", True, p["motor"]),
            "t3_bridge_deck": ("grating", False, c.merge_parts(deck)), "t3_bridge_frame": ("galv", False, c.merge_parts(frame)),
            "t3_rails": ("yellow", False, rail), "t3_toes": ("yellow", False, toe)}


def build_t5(site=None):
    site = site or _site()
    g = geom(site)["T5"]
    tail, head = conv_axis("T5", site)
    p = gal.conveyor(tail, head, g["w"], g["h"], g["drive_side"])
    gl = g["gallery"]
    (gx0, gx1), dz, (ya, yb), th = gl["x"], gl["deck_z"], gl["y"], gl["truss_h"]
    xs = sorted((gx0, gx1))
    drops = [s["x"] for s in site["receiving"]["old_silos"]]
    deck, chords, webs = [], [], []
    cuts = sorted(drops)
    x = xs[0]
    for xd in cuts + [xs[1] + 1.0]:                       # grating in runs, open around the silo drops
        a, b = x, min(xd - 0.3, xs[1])
        if b > a:
            deck.append(st.grating_panel(a, ya, b, yb, dz))
        x = xd + 0.3
    for yy in (ya, yb):
        chords += [st.member((xs[0], yy, dz - 0.1), (xs[1], yy, dz - 0.1), st.SHS_150),
                   st.member((xs[0], yy, dz + th), (xs[1], yy, dz + th), st.SHS_100)]
        n = max(2, round((xs[1] - xs[0]) / gal.BRIDGE_PANEL))
        pts = np.linspace(xs[0], xs[1], n + 1)
        for k, (xa, xb) in enumerate(zip(pts, pts[1:])):
            webs.append(st.member((xa, yy, dz - 0.1), (xa, yy, dz + th), st.SHS_60, up=(1, 0, 0)))
            za, zb = (dz - 0.1, dz + th) if k % 2 else (dz + th, dz - 0.1)
            webs.append(st.member((xa, yy, za), (xb, yy, zb), st.L75))
        webs.append(st.member((xs[1], yy, dz - 0.1), (xs[1], yy, dz + th), st.SHS_60, up=(1, 0, 0)))
    for xx in np.linspace(xs[0], xs[1], max(2, round((xs[1] - xs[0]) / 1.5)) + 1):
        if min(abs(xx - xd) for xd in drops) < 0.35:
            continue
        chords.append(st.member((xx, ya, dz - 0.1), (xx, yb, dz - 0.1), st.SHS_100))
    gz = c.ground_z()
    legs, braces, feet = [], [], []
    for tr in g["trestles"]:
        cx, hx = tr["x"], tr["hx"]
        corners = [(cx - hx, tr["y"][0]), (cx + hx, tr["y"][0]), (cx + hx, tr["y"][1]), (cx - hx, tr["y"][1])]
        top = dz - 0.18
        for px, py in corners:
            legs.append(st.member((px, py, gz + 0.3), (px, py, top), st.SHS_150, up=(1, 0, 0)))
            feet.append(c.box((px - TRESTLE_FOOT, py - TRESTLE_FOOT, gz - 0.2), (px + TRESTLE_FOOT, py + TRESTLE_FOOT, gz + 0.3)))
        levels = np.linspace(1.0, top, max(2, math.ceil((top - 1.0) / 3.0)) + 1)
        for z in levels:
            for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
                braces.append(st.member((ax, ay, z), (bx, by, z), st.L75))
        for za, zb in zip(levels, levels[1:]):
            for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
                braces.append(st.member((ax, ay, za + 0.05), (bx, by, zb - 0.05), st.L50))
                braces.append(st.member((bx, by, za + 0.05), (ax, ay, zb - 0.05), st.L50))
        braces.append(st.member((cx - hx - 0.1, (ya + yb) / 2, top), (cx + hx + 0.1, (ya + yb) / 2, top), st.HEA200))
    # access: caged ladder on the south face of trestle A up to a landing at the deck (ISO 14122-4, <= 6 m flights)
    from . import aspiration as asp
    ta = g["trestles"][0]
    ly = ta["y"][0] - 0.1
    stiles, rungs, cage, rest, lrails, ltoes = asp._caged_ladder(ta["x"], ly, -1, gz + 0.3, dz, 6.0)
    landing = [st.grating_panel(ta["x"] - 0.8, ly - 0.9, ta["x"] + 0.8, ya, dz)]
    lr, lt = st.guard_rail([(ta["x"] - 0.8, ya), (ta["x"] - 0.8, ly - 0.9), (ta["x"] + 0.8, ly - 0.9), (ta["x"] + 0.8, ya)], dz)
    rail = [lr] + lrails
    toe = [lt] + ltoes
    for yy, pts in ((yb, [(xs[0], yb), (xs[1], yb)]), (ya, [(xs[0], ya), (ta["x"] - 0.8, ya)]), (ya, [(ta["x"] + 0.8, ya), (xs[1], ya)])):
        r_, t_ = st.guard_rail(pts, dz)
        rail.append(r_)
        toe.append(t_)
    return {"t5_casing": ("galv", False, p["casing"]), "t5_flanges": ("galv_old", False, p["flanges"]),
            "t5_drive": ("motor", False, p["drive"]), "t5_motor": ("motor", True, p["motor"]),
            "t5_deck": ("grating", False, c.merge_parts(deck)), "t5_truss": ("galv", False, c.merge_parts(chords + webs)),
            "t5_rails": ("yellow", False, c.merge_parts(rail)), "t5_toes": ("yellow", False, c.merge_parts(toe)),
            "t5_trestle_legs": ("galv", False, c.merge_parts(legs)), "t5_trestle_braces": ("galv", False, c.merge_parts(braces)),
            "t5_trestle_feet": ("concrete", False, c.merge_parts(feet)),
            "t5_ladder": ("galv", False, c.merge_parts(stiles + rungs + cage)), "t5_landing": ("grating", False, c.merge_parts(landing + rest))}


def build_wet_fans(site=None):
    """One aeration fan per wet silo (ВНТП п. 7.11: wet grain kept with active ventilation), on the side
    away from the tower (-Y), on a pad by the plinth (judgment)."""
    site = site or _site()
    gz = c.ground_z()
    fans, pads = [], []
    for s in site["receiving"]["old_silos"]:
        x, y = s["x"], s["y"] - s["plinth_r"] - 0.9
        pads.append(c.box((x - 0.7, y - 0.6, gz), (x + 0.7, y + 0.6, gz + 0.15)))
        fans.append(c.cylinder(0.45, gz + 0.15, gz + 1.0, steps=24, center=(x, y)))
        fans.append(st.member((x, y + 0.3, gz + 0.6), (x, s["y"] - s["plinth_r"] - 0.005, gz + 0.6),
                              np.array([(-0.2, -0.2), (0.2, -0.2), (0.2, 0.2), (-0.2, 0.2)])))
    return {"wet_fans": ("motor", False, c.merge_parts(fans)), "wet_fan_pads": ("concrete", False, c.merge_parts(pads))}


def build(site=None):
    """{name: (material key, smooth, (verts, faces))} of the drying loop, site frame (spouts: receiving.spouts)."""
    site = site or _site()
    parts = {}
    parts.update(build_dryer(site))
    parts.update(build_t3(site))
    parts.update(build_t5(site))
    parts.update(build_wet_fans(site))
    return parts                                          # the spouts come with receiving.spouts() (slab holes, clash checks)
