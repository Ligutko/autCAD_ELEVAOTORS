"""Phase 5A. Drying loop (designed layer, research/design/drying_loop.md): tower dryer of the STRAHL
3000 FR class in building «4» (after the GCS p.2 section: exhaust chamber, column, hot-air chamber), T3 from the receiving tower onto the dryer, T5 from the tower over the
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
RIB_STEP = 0.75                     # EST: vertical stiffener pitch on the dryer panels (photos show ribs, no pitch given)
LOUVRE_STEP = 0.12                  # EST: louvre blade pitch
SCREW_KW = 4.0                      # EST: wet-grain screw drive on the column ridge (not in the STRAHL tables)
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
    q = inlet_point(site)                                  # the wet-grain screw on the column ridge
    out.append(("T3->dryer", head3 - [0, 0, g["T3"]["h"] / 2], np.array([head3[0], q[1], q[2] + 0.05]), SPOUT_MM))
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


def section(site=None):
    """Zones of the dryer along its long side and the heights (SITE designed.dryer.section, GCS p.2 scaled):
    {"exhaust" | "column" | "hot": (y_a, y_b), "z": {...}, "x": (x0, x1), "north": exhaust at the north end}."""
    site = site or _site()
    sec = site["designed"]["dryer"]["section"]
    x0, y0, x1, y1 = dryer_rect(site)
    a = sec["along_long_m"]
    k = (y1 - y0) / (a["exhaust"] + a["column"] + a["hot"])      # 1.0 when the three add up to the length
    north = sec["exhaust_end"] == "N"
    if north:
        ex, co, ho = (y1 - a["exhaust"] * k, y1), (y0 + a["hot"] * k, y1 - a["exhaust"] * k), (y0, y0 + a["hot"] * k)
    else:
        ex, co, ho = (y0, y0 + a["exhaust"] * k), (y0 + a["exhaust"] * k, y1 - a["hot"] * k), (y1 - a["hot"] * k, y1)
    return {"exhaust": ex, "column": co, "hot": ho, "z": sec["z_m"], "x": (x0, x1), "north": north}


def inlet_point(site=None):
    """Top of the wet-grain screw trough on the column ridge, where T3 drops (A25 in GCS p.2)."""
    site = site or _site()
    s = section(site)
    return np.array([conv_axis("T3", site)[1][0], sum(s["column"]) / 2, s["z"]["inlet_top"]])


def column_roof_z(y, site=None):
    """Gable roof of the column (ridge along X on the column centre line)."""
    s = section(site)
    ya, yb = s["column"]
    t = min(abs(y - (ya + yb) / 2) / ((yb - ya) / 2), 1.0)
    return s["z"]["column_ridge"] - t * (s["z"]["column_ridge"] - s["z"]["column_eave"])


def _ribs(axis, fixed, span, z0, z1, out):
    """Vertical hat stiffeners (EST pitch RIB_STEP) on a flat face: axis "x" = face x = fixed spanning y."""
    parts = []
    n = max(2, int((span[1] - span[0]) / RIB_STEP))
    lo, hi = sorted((fixed, fixed + out * 0.05))
    for k in range(1, n):
        u = span[0] + (span[1] - span[0]) * k / n
        if axis == "x":
            parts.append(c.box((lo, u - 0.04, z0), (hi, u + 0.04, z1)))
        else:
            parts.append(c.box((u - 0.04, lo, z0), (u + 0.04, hi, z1)))
    return parts


def _louvres(axis, fixed, span, z0, z1, out):
    """Louvre panel standing out of a face: a frame and blades inclined down and out."""
    parts = []
    for z in np.arange(z0 + 0.08, z1 - 0.04, LOUVRE_STEP):
        a, b = (fixed, fixed + out * 0.09)
        if axis == "x":
            v = np.array([(a, span[0], z), (a, span[1], z), (b, span[1], z - 0.07), (b, span[0], z - 0.07)])
        else:
            v = np.array([(span[0], a, z), (span[1], a, z), (span[1], b, z - 0.07), (span[0], b, z - 0.07)])
        parts.append((v, np.array([(0, 1, 2, 3)])))
    lo, hi = sorted((fixed, fixed + out * 0.1))
    if axis == "x":
        parts += [c.box((lo, span[0], z0), (hi, span[0] + 0.05, z1)), c.box((lo, span[1] - 0.05, z0), (hi, span[1], z1)),
                  c.box((lo, span[0], z1 - 0.05), (hi, span[1], z1)), c.box((lo, span[0], z0), (hi, span[1], z0 + 0.05))]
    else:
        parts += [c.box((span[0], lo, z0), (span[0] + 0.05, hi, z1)), c.box((span[1] - 0.05, lo, z0), (span[1], hi, z1)),
                  c.box((span[0], lo, z1 - 0.05), (span[1], hi, z1)), c.box((span[0], lo, z0), (span[1], hi, z0 + 0.05))]
    return parts


def build_dryer(site=None):
    """Tower dryer of the STRAHL FR type after the GCS p.2 section. Along its long side: the exhaust chamber (top
    fan 22 kW on its roof, the 11 kW recirculation fan stays inside), the grain column (gable roof with the
    wet-grain screw on the ridge, discharge base over T4, cold-air louvres low on its sides) and the hot-air
    chamber (linear gas burner at the bottom behind louvres, gas train). Building «4» stays the drawn base
    enclosure with an air-intake louvre on the burner end."""
    site = site or _site()
    b4, g = site["receiving"]["building_4"], geom(site)
    (bx0, bx1), (by0, by1) = b4["outer_x"], b4["outer_y"]
    x0, y0, x1, y1 = dryer_rect(site)
    s = section(site)
    z = s["z"]
    sec = site["designed"]["dryer"]["section"]
    gz, eave = c.ground_z(), g["enclosure_eave"]
    pad = [c.box((bx0 - 0.3, by0 - 0.3, gz), (bx1 + 0.3, by1 + 0.3, 0.0))]
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
    (ea, eb), (ca, cb), (ha, hb) = s["exhaust"], s["column"], s["hot"]
    cxm, ym = (x0 + x1) / 2, (ca + cb) / 2
    hot_end, hs = (y0, -1) if s["north"] else (y1, 1)          # the burner end face and its outward direction

    chambers = [c.box((x0, ea, 0.0), (x1, eb, z["chamber_roof"])), c.box((x0, ha, 0.0), (x1, hb, z["chamber_roof"]))]
    # discharge base: sheet walls around the dry-grain hopper, open on both sides where T4 passes under the column
    tw = t4["w"] / 2 + 0.25
    zt = t4["z"] + 0.9
    column = [c.box((x0, ca, z["base_top"]), (x1, cb, z["column_eave"]))]
    for xa, xb in ((x0, x0 + w), (x1 - w, x1)):
        column += [c.box((xa, ca, 0.0), (xb, t4["y"] - tw, z["base_top"])), c.box((xa, t4["y"] + tw, 0.0), (xb, cb, z["base_top"])),
                   c.box((xa, t4["y"] - tw, zt), (xb, t4["y"] + tw, z["base_top"]))]
    lv = np.array([(x0 + w, ca, z["base_top"]), (x1 - w, ca, z["base_top"]), (x1 - w, cb, z["base_top"]), (x0 + w, cb, z["base_top"]),
                   (cxm - 0.2, t4["y"] - 0.2, 0.9), (cxm + 0.2, t4["y"] - 0.2, 0.9), (cxm + 0.2, t4["y"] + 0.2, 0.9), (cxm - 0.2, t4["y"] + 0.2, 0.9)])
    column.append((lv, np.array([(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (7, 6, 5, 4)])))

    # column top: gable roof, ridge along X (A22), wet-grain screw trough on the ridge (A25) with its drive
    rv = np.array([(x0 - 0.05, ca, z["column_eave"]), (x1 + 0.05, ca, z["column_eave"]), (x1 + 0.05, ym, z["column_ridge"]),
                   (x0 - 0.05, ym, z["column_ridge"]), (x1 + 0.05, cb, z["column_eave"]), (x0 - 0.05, cb, z["column_eave"])])
    hopper = [(rv, [np.array([(0, 1, 2, 3), (3, 2, 4, 5)]), np.array([(0, 3, 5), (1, 4, 2)])])]
    tx0, tx1 = x0 + 0.45, x1 - 0.1
    hopper.append(c.box((tx0, ym - 0.175, z["column_ridge"] - 0.05), (tx1, ym + 0.175, z["inlet_top"])))
    hopper += [c.box((xx, ym - 0.22, z["column_ridge"] - 0.25), (xx + 0.06, ym + 0.22, z["column_ridge"] - 0.02)) for xx in (tx0 + 0.2, tx1 - 0.26)]
    from . import components as comp
    m = comp.iec_motor(SCREW_KW)
    de = float(np.asarray(m["parts"]["endshield_de"][0])[:, 0].max())
    mv = []
    for v, f in (p for n, p in m["parts"].items() if n != "feet"):
        v = np.array(v, float) - (de, 0.0, m["dims"]["H"])
        v[:, 0], v[:, 1] = -v[:, 0], -v[:, 1]                           # shaft towards +X, into the trough end
        mv.append((v + (tx0, ym, z["column_ridge"] + 0.12), f))
    screw_motor = c.merge_parts(mv)

    # stiffeners above the building «4» roof and flashing bands at the roof edges
    ribs = []
    zr0 = eave + 0.2
    for (ya, yb), top in (((ea, eb), z["chamber_roof"]), ((ha, hb), z["chamber_roof"]), ((ca, cb), z["column_eave"])):
        ribs += _ribs("x", x0, (ya, yb), zr0, top, -1) + _ribs("x", x1, (ya, yb), zr0, top, 1)
    for yf, sg in ((y0, -1), (y1, 1)):
        ribs += _ribs("y", yf, (x0, x1), zr0, z["chamber_roof"], sg)
    for ya, yb in ((ea, eb), (ha, hb)):
        ribs.append(c.box((x0 - 0.06, min(ya, yb) - (0.06 if ya == y0 else 0.0), z["chamber_roof"] - 0.12),
                          (x1 + 0.06, max(ya, yb) + (0.06 if yb == y1 else 0.0), z["chamber_roof"])))
    ribs.append(c.box((x0 - 0.06, ca, z["column_eave"] - 0.12), (x1 + 0.06, cb, z["column_eave"])))

    # louvres: burner intake A19 on the hot end and the last metres of its sides; cold-air intake A16 low on the
    # column sides; building «4» air intake on the same end wall (judgment: the burner breathes inside the building)
    lb = sec["burner_louvre_from_end_m"]
    band = (hot_end, hot_end + lb) if hs < 0 else (hot_end - lb, hot_end)
    louv = _louvres("y", hot_end, (x0 + 0.1, x1 - 0.1), 0.1, z["base_top"], hs)
    for xf, sg in ((x0, -1), (x1, 1)):
        louv += _louvres("x", xf, (band[0] + 0.05, band[1] - 0.05), 0.1, z["base_top"], sg)
        louv += _louvres("x", xf, (ca + 0.15, cb - 0.15), z["base_top"] + 0.2, z["base_top"] + 1.8, sg)
    wall_y = by0 if hs < 0 else by1
    louv += _louvres("y", wall_y, (x0 - 0.6, x1 + 0.6), 3.4, 5.4, hs)

    # top fan unit on the exhaust roof: A14 dust louvres, A12 casing over the Ø1000 rotor, A15 rain louvres and cap
    side, off = sec["fan_unit_m"]["side"], sec["fan_unit_m"]["from_end"]
    fy1 = y1 - off if s["north"] else y0 + off + side
    fy0 = fy1 - side
    fx0, fx1 = cxm - side / 2, cxm + side / 2
    fyc = (fy0 + fy1) / 2
    zr = z["chamber_roof"]
    fan = [c.box((fx0 - 0.05, fy0 - 0.05, zr), (fx1 + 0.05, fy1 + 0.05, zr + 0.12)),
           c.box((fx0 + 0.03, fy0 + 0.03, zr + 0.12), (fx1 - 0.03, fy1 - 0.03, z["fan_louvre_top"]))]
    for yy, sg in ((fy0, -1), (fy1, 1)):
        fan += _louvres("y", yy, (fx0, fx1), zr + 0.12, z["fan_louvre_top"], sg)
    for xx, sg in ((fx0, -1), (fx1, 1)):
        fan += _louvres("x", xx, (fy0, fy1), zr + 0.12, z["fan_louvre_top"], sg)
    zmid = (z["fan_louvre_top"] + z["fan_casing_top"]) / 2               # two casing sections with a joint ring
    fan.append(c.cylinder(side / 2, z["fan_louvre_top"], zmid, steps=40, center=(cxm, fyc)))
    fan.append(c.cylinder(side / 2, zmid, z["fan_casing_top"], steps=40, center=(cxm, fyc)))
    for zf in (z["fan_louvre_top"] + 0.03, zmid, z["fan_casing_top"] - 0.03):
        fan.append(c.cylinder(side / 2 + 0.04, zf - 0.03, zf + 0.03, steps=40, center=(cxm, fyc)))
    top = dryer_top(site)
    fan.append(c.box((fx0 - 0.08, fy0 - 0.08, z["fan_casing_top"]), (fx1 + 0.08, fy1 + 0.08, z["fan_casing_top"] + 0.06)))
    for yy, sg in ((fy0 - 0.08, -1), (fy1 + 0.08, 1)):
        fan += _louvres("y", yy, (fx0 - 0.08, fx1 + 0.08), z["fan_casing_top"] + 0.06, top - 0.05, sg)
    fan.append(c.box((fx0 - 0.15, fy0 - 0.15, top - 0.05), (fx1 + 0.15, fy1 + 0.15, top)))
    fan.append(st.rod((fx1, fyc, z["fan_casing_top"] - 0.3), (fx1 + 0.25, fyc, z["fan_casing_top"] - 0.3), 0.05, 12))   # motor cooling tube (GCS p.5)

    # gas train to the linear burner A1, inside building «4»: yellow pipe and a valve cabinet (EST sizes)
    gy = (ha + hb) / 2
    gas = [st.rod((x0 - 0.35, gy, 0.0), (x0 - 0.35, gy, z["burner"]), 0.045, 12),
           st.rod((x0 - 0.35, gy, z["burner"]), (x0, gy, z["burner"]), 0.045, 12),
           c.box((x0 - 0.55, gy - 0.3, 1.2), (x0 - 0.2, gy + 0.3, 1.9))]
    # two doors low on the exhaust chamber sides (GCS p.7)
    yd = (ea + eb) / 2
    doors = [c.box((x0 - 0.03, yd - 0.4, 0.1), (x0, yd + 0.4, 2.1)), c.box((x1, yd - 0.4, 0.1), (x1 + 0.03, yd + 0.4, 2.1))]

    # chamber roofs: gratings with guard rails (A23), open towards the column; caged ladder on the burner end from
    # the building «4» roof (ISO 14122-4 flights <= 6 m)
    plat = [st.grating_panel(x0, ea, x1, eb, zr), st.grating_panel(x0, ha, x1, hb, zr)]
    rails, toes = [], []
    for (ya, yb) in ((ea, eb), (ha, hb)):
        inner, outer = (ya, yb) if abs(yb - y1) < 1e-6 else (yb, ya)          # the rail stays open towards the column
        r, t = st.guard_rail([(x0, inner), (x0, outer), (x1, outer), (x1, inner)], zr)
        rails.append(r)
        toes.append(t)
    from . import aspiration as asp
    stiles, rungs, cage, rest, lrails, ltoes = asp._caged_ladder(cxm, hot_end + hs * 0.05, hs, eave + 0.2, zr, 6.0)
    return {"dryer_pad": ("concrete", False, c.merge_parts(pad)),
            "dryer_enclosure": ("galv_old", False, c.merge_parts(shell)), "dryer_enclosure_roof": ("galv_old", False, c.merge_parts(roof)),
            "dryer_chambers": ("galv", False, c.merge_parts(chambers)), "dryer_column": ("galv", False, c.merge_parts(column)),
            "dryer_ribs": ("galv_old", False, c.merge_parts(ribs)), "dryer_louvres": ("galv_old", False, c.merge_parts(louv)),
            "dryer_hopper": ("galv", False, c.merge_parts(hopper)), "dryer_screw_motor": ("motor", True, screw_motor),
            "dryer_fans": ("galv", False, c.merge_parts(fan)), "dryer_gas": ("yellow", True, c.merge_parts(gas)),
            "dryer_doors": ("dark", False, c.merge_parts(doors)),
            "dryer_platform": ("grating", False, c.merge_parts(plat + rest)),
            "dryer_rails": ("yellow", False, c.merge_parts(rails + lrails)), "dryer_toes": ("yellow", False, c.merge_parts(toes + ltoes)),
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
    frame += [st.member((x, y + s * hw, column_roof_z(y + s * hw, site)), (x, y + s * hw, dz - 0.18), st.SHS_100, up=(1, 0, 0))
              for x in g["posts_x"] for s in (-1, 1)]               # posts stand on the column gable roof
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


WET_FAN_OFFSET = 0.9                  # fan pad centre beyond the plinth (judgment)


def build_wet_fans(site=None):
    """One aeration fan per wet silo (ВНТП п. 7.11: wet grain kept with active ventilation), on the north
    side (+Y): the south side is the truck lane under Ш1 (site plan), a pad by the plinth (judgment)."""
    site = site or _site()
    gz = c.ground_z()
    fans, pads = [], []
    for s in site["receiving"]["old_silos"]:
        x, y = s["x"], s["y"] + s["plinth_r"] + WET_FAN_OFFSET
        pads.append(c.box((x - 0.7, y - 0.6, gz), (x + 0.7, y + 0.6, gz + 0.15)))
        fans.append(c.cylinder(0.45, gz + 0.15, gz + 1.0, steps=24, center=(x, y)))
        fans.append(st.member((x, y - 0.3, gz + 0.6), (x, s["y"] + s["plinth_r"] + 0.005, gz + 0.6),
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
