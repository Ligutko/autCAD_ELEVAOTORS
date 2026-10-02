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
    q4 = screw_outlet(site)                                # A20 outlet flange under the screw trough (C5)
    out.append(("dryer->T4", q4, np.array([q4[0], t4["y"], t4["z"] + 0.40]), SPOUT_MM))
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


# ---------------------------------------------------------------- C5: fans A12 / A13, discharge A24, dry-grain screw A20
# Sources: GCS «Опис конструкції» p.2 (section: A12 on the exhaust roof, A13 at the bottom of the exhaust chamber next
# to the column base, A24 under the column, A11 hopper with the A20 screw in its V), p.4 (axial fans Ø1000, direct
# drive, vanes under the rotor carry the motor; discharge and dry-grain hopper one monoblock, hopper raised so the
# recirculated air passes under it), p.6 (discharge: a swinging flap under every parallel channel, all flaps tied by
# two guides, one pneumatic cylinder, 0.5-1 s); catalogue 2022 p.6 (screw in the dry-grain hopper with a gearmotor).
FAN_D = 1.0                     # rotor Ø1000 mm, GCS p.4 (the text speaks of the dryer's fans in the plural: A12 and A13)
FAN_TOP_IN_DZ = 0.10            # EST: top fan shroud inlet 0.10 m over the louvre-box top (fan_louvre_top)
FAN_LOW_AXIS_Z = 0.90           # EST: A13 axis height (GCS p.2 scaled: A13 centre ~1.0 m, A14 louvre 0.1-1.4 m)
FAN_LOW_INLET_Y = 1.25          # EST: A13 shroud inlet plane 1.25 m from the column face (the cooling tube clears the doors)
FAN_LOW_LOUVRE = 1.30           # EST: A14 dust louvre frame, square side (GCS p.2 scaled 1.3 m tall)
DIS_CHANNELS = 8                # EST: channels are not lettered; GCS p.6 draws 8 across one frame, taken over the 2.01 m column
DIS_NECK = 0.070                # EST: channel neck width (GCS p.6 drawing, ~0.26 of the channel pitch)
DIS_Z_NECK = 1.94               # EST: neck bottom; ridges 50 deg up to the column bottom (base_top)
DIS_NECK_H = 0.07               # EST: neck height
DIS_BAY = 0.25                  # EST: mechanism bay between the frame end wall and the base side wall
DIS_TRAY = (0.085, 0.020)       # EST: tray half width, gap under the neck
DIS_PIVOT = (0.100, 1.93)       # EST: flap pivot off the channel centre, pivot height
DIS_CRANK = 0.080               # EST: crank radius pivot -> guide pin (cylinder stroke 50 mm swings the flap ~39 deg)
DIS_GUIDE = (0.060, 0.012)      # EST: guide flat bar height x thickness
DIS_CYL = (0.032, 0.175, 0.010)  # EST: cylinder body radius (bore 50, ISO 15552 class), body length, piston rod radius
REPOSE_DEG = 25.0               # wheat angle of repose ~23-28 deg; the lower bound keeps the closed-flap rule on the safe side
SCREW_D = 0.30                  # EST: A20 flight Ø300 (~36 m3/h at 100 rpm for 29 t/h; size not in the sources)
SCREW_PITCH = 0.30              # EST: full pitch = D
SCREW_Z = 0.78                  # EST: A20 axis, GCS p.2 scaled (V bottom ~0.6 m, screw centre ~0.78 m)
SCREW_TROUGH_R = 0.165          # EST: trough radius, 15 mm clear of the flight
SCREW_PIPE_R = 0.0445           # EST: Ø89 core pipe
SCREW_DRIVE_KW = 5.5            # EST: gearmotor named by the catalogue 2022 p.6, kW not given; smallest tabulated KA (KA67)
SCREW_OUTLET_Z = 0.50           # EST: outlet flange; the spout drops to the T4 top (+0.40)
SHEET = 0.004
GAP = 0.0005                    # parts that bear on each other keep 0.5 mm (components.RD_GAP), BVH reads no contact


def _ring_z(cx, cy, r_in, r_out, z0, z1, steps=64):
    from . import components as comp
    v, f = comp._x_to_z(comp._ring_x(z0, z1, r_in, r_out, steps))
    return v + [cx, cy, 0.0], f


def _plate(outline, x0, x1, hole_r=0.0, at=(0.0, 0.0, 0.0)):
    """Plate normal to X between x0 and x1, outline (y, z) about `at` (y, z), optional round hole round `at`."""
    from . import components as comp
    v, f = comp._plate_x(np.asarray(outline, float), x0, x1, hole_r, 32)
    return np.asarray(v) + [0.0, at[1], at[2]], f


def _poly_x(pts_yz, x_of):
    """Planar polygon (y, z), x = x_of(z); ear-clipped (concave allowed)."""
    from . import components as comp
    pts = np.asarray(pts_yz, float)
    if comp._poly_area(pts) < 0:
        pts = pts[::-1]
    tris = comp._earclip([tuple(p) for p in pts])
    v = np.column_stack([[x_of(z) for z in pts[:, 1]], pts])
    return v, np.array(tris, np.int64)


def fan_top_centre(site=None):
    """(x, y) of the roof fan unit axis on the exhaust chamber."""
    site = site or _site()
    s = section(site)
    sec = site["designed"]["dryer"]["section"]
    x0, y0, x1, y1 = dryer_rect(site)
    side, off = sec["fan_unit_m"]["side"], sec["fan_unit_m"]["from_end"]
    fy1 = y1 - off if s["north"] else y0 + off + side
    return (x0 + x1) / 2, fy1 - side / 2


def top_fan(site=None, faults=None):
    """A12: axial_fan Ø1000 22 kW in the roof casing, shaft up; deck ring short of the casing wall, cooling tube out
    through the dust-louvre box on +X. {"parts": {...}, "dims": axial_fan dims, "origin": (x, y, z)}."""
    from . import components as comp
    site = site or _site()
    faults = faults or {}
    z = section(site)["z"]
    side = site["designed"]["dryer"]["section"]["fan_unit_m"]["side"]
    cx, cy = fan_top_centre(site)
    kw = site["designed"]["dryer"]["fans_kw"][0]
    fan = comp.axial_fan(FAN_D, kw, deck_r=side / 2 - 0.005, cool_reach=side / 2 + 0.25)
    o = (cx, cy, z["fan_louvre_top"] + FAN_TOP_IN_DZ + float(faults.get("top_fan_dz", 0.0)))
    placed = comp.place_frame(dict(fan["parts"], blades=fan["sub"]["blades"]), o, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    return {"parts": placed, "dims": fan["dims"], "origin": o}


def low_fan(site=None, faults=None):
    """A13: axial_fan Ø1000 11 kW at the bottom of the exhaust chamber, axis along Y blowing toward the column base
    (into the recirculation path under the raised hopper, GCS p.2 / p.4), motor feet down, cooling tube out through
    the chamber side wall on +X; stand, outlet duct to the column face, A14 dust louvre frame at the inlet."""
    from . import components as comp
    site = site or _site()
    s = section(site)
    x0, y0, x1, y1 = dryer_rect(site)
    cx = (x0 + x1) / 2
    toward = -1.0 if s["north"] else 1.0                     # from the exhaust chamber toward the column
    face = s["column"][1] if s["north"] else s["column"][0]
    kw = site["designed"]["dryer"]["fans_kw"][1]
    y_in = face - toward * FAN_LOW_INLET_Y
    reach = x1 + 0.15 - cx
    fan = comp.axial_fan(FAN_D, kw, cool_reach=reach)
    d = fan["dims"]
    o = (cx, y_in, FAN_LOW_AXIS_Z)
    ez = (0.0, toward, 0.0)
    ey = (0.0, 0.0, 1.0)
    ex = tuple(np.cross(ey, ez))
    placed = comp.place_frame(dict(fan["parts"], blades=fan["sub"]["blades"]), o, ex, ey, up=ez)
    r_o = d["r_shroud"] + SHEET
    y_out = y_in + toward * d["z_outlet"]
    y_face = face - toward * GAP
    ya, yb = sorted((y_out, y_face))
    dv, df = comp._shell_x(ya, yb, r_o, r_o, SHEET, 96)          # built along X, swapped to Y (faces reversed)
    dv = np.asarray(dv)
    duct = [(np.column_stack([cx + dv[:, 1], dv[:, 0], FAN_LOW_AXIS_Z + dv[:, 2]]), [np.asarray(b)[:, ::-1] for b in df])]
    sq = 0.60
    yf0, yf1 = sorted((y_face, y_face - toward * 0.012))
    fl, ff = comp._plate_x(np.array([(-sq, -sq), (sq, -sq), (sq, sq), (-sq, sq)]), yf0, yf1, r_o - 0.002, 64)
    fl = np.asarray(fl)
    duct.append((np.column_stack([cx + fl[:, 1], fl[:, 0], FAN_LOW_AXIS_Z + fl[:, 2]]), [np.asarray(b)[:, ::-1] for b in ff]))
    # stand: two frames of SHS 60 legs under the shroud, base plates 1 mm off the chamber floor
    legs = []
    for az in (0.03, d["z_outlet"] - 0.03):
        yy = y_in + toward * az
        for sx in (-0.30, 0.30):
            ztop = FAN_LOW_AXIS_Z - float(np.sqrt(r_o ** 2 - sx ** 2)) + 0.006
            legs.append(st.member((cx + sx, yy, 0.013), (cx + sx, yy, ztop), st.shs(0.06), up=(1, 0, 0)))
            legs.append(c.box((cx + sx - 0.075, yy - 0.075, 0.001), (cx + sx + 0.075, yy + 0.075, 0.013)))
        legs.append(st.member((cx - 0.33, yy, 0.25), (cx + 0.33, yy, 0.25), st.shs(0.05)))
    # A14 dust louvre frame at the inlet: posts to the floor, head bar, blades inclined down and out
    yl = y_in - toward * (-d["cool_end"][2] + 0.10)
    half = FAN_LOW_LOUVRE / 2
    zl0, zl1 = FAN_LOW_AXIS_Z - half, FAN_LOW_AXIS_Z + half
    lv = [st.member((cx + sx, yl, 0.001), (cx + sx, yl, zl1), st.shs(0.05), up=(1, 0, 0)) for sx in (-half, half)]
    lv += [st.member((cx - half, yl, zz), (cx + half, yl, zz), st.shs(0.05)) for zz in (zl0, zl1)]
    blade = np.array([(-0.045, -0.0015), (0.045, -0.0015), (0.045, 0.0015), (-0.045, 0.0015)])
    ang = np.radians(35.0)
    rot = np.array([[np.cos(ang), -np.sin(ang)], [np.sin(ang), np.cos(ang)]])
    for zz in np.arange(zl0 + 0.09, zl1 - 0.05, 0.10):
        lv.append(st.member((cx - half + 0.026, yl, zz), (cx + half - 0.026, yl, zz), blade @ rot.T))
    shroud = c.merge_parts([placed["shroud"], placed["vanes"], placed["bracket"]] + duct + legs + lv)
    return {"parts": dict(placed, shroud_all=shroud), "dims": d, "origin": o, "toward": toward}


def discharge(site=None, faults=None):
    """A24 under the column: fixed ridges and channel necks between two end walls, a swinging flap under every
    channel (tray, hangers, pivot pin, crank outside each end wall), two guide bars tying the cranks, one pneumatic
    cylinder in the +X bay on a clevis bracket off the end wall. Closed state. Channels run along X (GCS p.4 iso: the
    ridges cross the column from side to side), stacked along Y over the 2.01 m column.
    {"frame", "flaps", "rods", "cylinder": (verts, faces), "sub": {"trays": [...], "necks": [(y0, y1, z_bottom)], ...}}."""
    site = site or _site()
    faults = faults or {}
    s = section(site)
    z = s["z"]
    x0, y0, x1, y1 = dryer_rect(site)
    ca, cb = s["column"]
    w = 0.05
    xa, xb = x0 + DIS_BAY, x1 - DIS_BAY
    zt = z["base_top"] - GAP
    p = (cb - ca) / DIS_CHANNELS
    yc = [ca + p * (i + 0.5) for i in range(DIS_CHANNELS)]
    hn = DIS_NECK / 2
    z_nb, z_rb = DIS_Z_NECK, DIS_Z_NECK + DIS_NECK_H

    def quad(a, b, cc, d):
        return np.array([a, b, cc, d], float), np.array([[0, 1, 2, 3]])

    frame = []
    edges = [ca + 0.002] + [yy for i in range(DIS_CHANNELS - 1) for yy in (yc[i] + hn, yc[i + 1] - hn)] + [cb - 0.002]
    # ridges: half ridge at each column wall, full ridges between channels, apex just under the column bottom
    frame.append(quad((xa, ca + 0.002, zt - 0.0015), (xb, ca + 0.002, zt - 0.0015), (xb, yc[0] - hn, z_rb), (xa, yc[0] - hn, z_rb)))
    frame.append(quad((xa, yc[-1] + hn, z_rb), (xb, yc[-1] + hn, z_rb), (xb, cb - 0.002, zt - 0.0015), (xa, cb - 0.002, zt - 0.0015)))
    for i in range(DIS_CHANNELS - 1):
        ya_, yb_ = yc[i] + hn, yc[i + 1] - hn
        ym = 0.5 * (ya_ + yb_)
        zap = min(zt - 0.0015, z_rb + (ym - ya_) * np.tan(np.radians(50.0)))
        frame.append(quad((xa, ya_, z_rb), (xb, ya_, z_rb), (xb, ym, zap), (xa, ym, zap)))
        frame.append(quad((xa, ym, zap), (xb, ym, zap), (xb, yb_, z_rb), (xa, yb_, z_rb)))
    for yy in yc:
        for sgn in (-1.0, 1.0):
            frame.append(quad((xa, yy + sgn * hn, z_nb), (xb, yy + sgn * hn, z_nb), (xb, yy + sgn * hn, z_rb), (xa, yy + sgn * hn, z_rb)))
    # end walls (5 mm) and bay covers closing the column bottom over the mechanism bays
    for xe, sg in ((xa, -1.0), (xb, 1.0)):
        lo_, hi_ = sorted((xe, xe + sg * 0.005))
        frame.append(c.box((lo_, ca + 0.002, 1.955), (hi_, cb - 0.002, zt)))
    frame.append(c.box((x0 + w + GAP, ca + 0.002, zt - 0.006), (xa - 0.005, cb - 0.002, zt)))
    frame.append(c.box((xb + 0.005, ca + 0.002, zt - 0.006), (x1 - w - GAP, cb - 0.002, zt)))
    del edges

    # flaps: tray under each neck with lips, hanger plates at the tray ends, pivot pin out under the end wall,
    # bearing ring (frame) round the pin outside the wall, crank down to the guide pin
    tw, tg = DIS_TRAY
    tw_plus = tw + float(faults.get("tray_w", 0.0))
    t_top = z_nb - tg
    pvy, pvz = DIS_PIVOT
    tx0 = xa + 0.006 + float(faults.get("tray_dx0", 0.0))
    tx1 = xb - 0.006
    flaps, trays, rods, cyl = [], [], [], []
    rdz = float(faults.get("rods_dz", 0.0))
    z_pin = pvz - DIS_CRANK
    hang = [(-tw, t_top - 0.006), (pvy + 0.012, t_top - 0.006), (pvy + 0.018, pvz), (pvy + 0.010, pvz + 0.016),
            (pvy - 0.010, pvz + 0.016), (0.060, t_top + 0.011), (-tw, t_top + 0.011)]
    crank_outline = [(0.016 * np.cos(a), 0.016 * np.sin(a)) for a in np.linspace(np.pi, 2 * np.pi, 9)] + \
                    [(0.016 * np.cos(a), DIS_CRANK + 0.016 * np.sin(a)) for a in np.linspace(0.0, np.pi, 9)]
    for i, yy in enumerate(yc):
        tray = [c.box((tx0, yy - tw, t_top - SHEET), (tx1, yy + tw_plus, t_top)),
                c.box((tx0, yy - tw, t_top), (tx1, yy - tw + SHEET, t_top + 0.010)),
                c.box((tx0, yy + tw_plus - SHEET, t_top), (tx1, yy + tw_plus, t_top + 0.010))]
        trays.append(c.merge_parts(tray))
        flaps += tray
        py_ = yy + pvy
        for xe, sg in ((xa, -1.0), (xb, 1.0)):
            hx0, hx1 = sorted((xe - sg * 0.006, xe - sg * 0.012))
            outline = [(yy + a, b) for a, b in hang]
            flaps.append(_plate([(a - py_, b - pvz) for a, b in outline], hx0, hx1, at=(0.0, py_, pvz)))
            flaps.append(st.rod((xe - sg * 0.009, py_, pvz), (xe + sg * 0.047, py_, pvz), 0.010, 16))
            kx0, kx1 = sorted((xe + sg * 0.037, xe + sg * 0.045))
            flaps.append(_plate(crank_outline, kx0, kx1, 0.0085, at=(0.0, py_, z_pin)))
            # bearing ring with its L-lug to the end wall (frame)
            rx0, rx1 = sorted((xe + sg * 0.010, xe + sg * 0.030))
            frame.append(_plate([(0.022 * np.cos(a), 0.022 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 24, endpoint=False)],
                                rx0, rx1, 0.012, at=(0.0, py_, pvz)))
            frame.append(c.box((rx0, py_ - 0.012, pvz + 0.017), (rx1, py_ + 0.012, 1.975)))
            lx0, lx1 = sorted((xe + sg * 0.030, xe - sg * 0.002))
            frame.append(c.box((lx0, py_ - 0.012, 1.965), (lx1, py_ + 0.012, 1.975)))
            # guide pin through the crank hole (rods)
            gx0, gx1 = sorted((xe + sg * 0.034, xe + sg * 0.068))
            rods.append(st.rod((gx0, py_, z_pin + rdz), (gx1, py_, z_pin + rdz), 0.008, 16))
    gy0, gy1 = yc[0] + pvy - 0.030, yc[-1] + pvy + 0.020
    for xe, sg in ((xa, -1.0), (xb, 1.0)):
        bx0, bx1 = sorted((xe + sg * 0.053, xe + sg * 0.065))
        rods.append(c.box((bx0, gy0, z_pin - DIS_GUIDE[0] / 2 + rdz), (bx1, gy1, z_pin + DIS_GUIDE[0] / 2 + rdz)))

    # pneumatic cylinder in the +X bay, under the +X guide, axis along Y: clevis bracket off the end wall (frame),
    # rear eye and pin, body with square caps and tie rods, piston rod, rod-end fork and pin through a lug on the guide
    xc = xb + 0.059
    zc = z_pin - 0.08
    yr = ca + 0.06
    cr, cl, rr = DIS_CYL
    yb0 = yr + 0.020
    yb1 = yb0 + cl
    yrod = yb1 + 0.045
    ylug = yrod + 0.030
    for kx in ((xb + 0.030, xb + 0.036), (xb + 0.082, xb + 0.088)):
        frame.append(_plate([(-0.015, -0.020), (0.015, -0.020), (0.015, 1.975 - zc), (-0.015, 1.975 - zc)], kx[0], kx[1], 0.0075,
                            at=(0.0, yr, zc)))
    frame.append(c.box((xb - 0.002, yr - 0.015, 1.965), (xb + 0.088, yr + 0.015, 1.975)))
    cyl.append(c.box((xb + 0.053, yr - 0.012, zc - 0.018), (xb + 0.065, yb0 + 0.002, zc + 0.018)))
    cyl.append(st.rod((xb + 0.026, yr, zc), (xb + 0.092, yr, zc), 0.006, 16))
    cyl.append(st.rod((xc, yb0 + 0.012, zc), (xc, yb1 - 0.012, zc), cr, 32))
    for ya_ in (yb0, yb1 - 0.014):
        cyl.append(c.box((xc - 0.035, ya_, zc - 0.035), (xc + 0.035, ya_ + 0.014, zc + 0.035)))
    for dx in (-0.026, 0.026):
        for dz in (-0.026, 0.026):
            cyl.append(st.rod((xc + dx, yb0 - 0.004, zc + dz), (xc + dx, yb1 + 0.004, zc + dz), 0.004, 8))
    cyl.append(st.rod((xc, yb1, zc), (xc, yrod, zc), rr, 16))
    cyl.append(c.box((xb + 0.040, yrod - 0.002, zc - 0.015), (xb + 0.078, yrod + 0.012, zc + 0.015)))
    for kx in ((xb + 0.040, xb + 0.047), (xb + 0.071, xb + 0.078)):
        cyl.append(c.box((kx[0], yrod + 0.012, zc - 0.015), (kx[1], ylug + 0.015, zc + 0.015)))
    cyl.append(st.rod((xb + 0.036, ylug, zc), (xb + 0.082, ylug, zc), 0.006, 16))
    # lug on the guide bar (rods), hole round the fork pin
    rods.append(_plate([(-0.015, -0.020), (0.015, -0.020), (0.015, z_pin - DIS_GUIDE[0] / 2 + 0.010 - zc),
                        (-0.015, z_pin - DIS_GUIDE[0] / 2 + 0.010 - zc)], xb + 0.053, xb + 0.065, 0.0075, at=(0.0, ylug, zc + rdz)))
    necks = [(yy - hn, yy + hn, z_nb) for yy in yc]
    return {"frame": c.merge_parts(frame), "flaps": c.merge_parts(flaps), "rods": c.merge_parts(rods),
            "cylinder": c.merge_parts(cyl),
            "sub": {"trays": trays, "necks": necks, "x_frame": (xa, xb), "base_inner": (x0 + w, x1 - w, ca, cb),
                    "tray_top": t_top, "stroke": 0.05, "channels": DIS_CHANNELS}}


def screw_outlet(site=None):
    """(x, y, z) of the A20 outlet flange (the spout onto T4 starts here)."""
    site = site or _site()
    g = _screw_geom(site)
    return np.array([g["x_out"], g["y"], SCREW_OUTLET_Z])


def _screw_geom(site):
    s = section(site)
    x0, y0, x1, y1 = dryer_rect(site)
    t4 = next(cv for cv in site["receiving"]["conveyors"] if cv["id"] == "T4")
    ca, cb = s["column"]
    w = 0.05
    r = SCREW_TROUGH_R
    k = np.sqrt(0.5)
    y = t4["y"]
    top_l = SCREW_Z - r * k + ((y - r * k) - (ca + GAP))
    top_r = SCREW_Z - r * k + ((cb - GAP) - (y + r * k))
    x_k = (x1 - w - GAP) - (max(top_l, top_r) - SCREW_Z)
    x_out = x_k + 0.20
    return {"y": y, "z": SCREW_Z, "x_a": x0 + w + 0.06, "x_k": x_k, "x_out": x_out, "x_e": x_out + 0.17,
            "top": (top_l, top_r), "ca": ca, "cb": cb}


def dry_hopper_and_screw(site=None):
    """A11 dry-grain hopper (45 deg V tangent to the A20 trough, raised over T4), the screw (flight, core pipe, end
    stubs, -X flange bearing), the outlet onto T4 and the shaft-mounted gearmotor on the +X trough end plate.
    {"hopper", "screw", "gear", "gearmotor": (verts, faces), "dims": {...}}."""
    from . import components as comp
    site = site or _site()
    g = _screw_geom(site)
    y, zs, r = g["y"], g["z"], SCREW_TROUGH_R
    k = np.sqrt(0.5)
    ca, cb = g["ca"], g["cb"]
    x_a, x_k, x_out, x_e = g["x_a"], g["x_k"], g["x_out"], g["x_e"]
    arc = [(r * np.cos(a), r * np.sin(a)) for a in np.radians(np.linspace(225.0, 315.0, 13))]
    prof = [(ca + GAP - y, g["top"][0] - zs)] + arc + [(cb - GAP - y, g["top"][1] - zs)]
    prof = np.array(prof)                                    # relative to the axis (y, z)
    n = len(prof)
    xe_of = [x_k + max(0.0, pz) for pz in prof[:, 1]]
    sheet_v = np.vstack([np.column_stack([np.full(n, x_a), y + prof[:, 0], zs + prof[:, 1]]),
                         np.column_stack([xe_of, y + prof[:, 0], zs + prof[:, 1]])])
    hopper = [(sheet_v, c.grid_faces(2, n))]
    gm_row = comp.gm_size(SCREW_DRIVE_KW)[1]
    stub_r = comp._gv(gm_row, "U") / 2.0 - 0.0005
    hopper.append(_plate(prof, x_a, x_a + 0.010, 0.023, at=(0.0, y, zs)))
    # +X: sloped end plate over the tube, closing plates at x_k between the V and the tube, tube, end plate, outlet
    ro = r + SHEET
    yw = r * k + r * k                                       # V wall offset from the axis at the axis height
    top_pts = [(ca + GAP, g["top"][0]), (cb - GAP, g["top"][1])]
    arc_top = [(y + ro * np.cos(a), zs + ro * np.sin(a)) for a in np.radians(np.linspace(0.0, 180.0, 19))]
    slope = [(y + yw, zs)] + arc_top + [(y - yw, zs), top_pts[0], top_pts[1]]
    hopper.append(_poly_x(slope, lambda zz: x_k + max(0.0, zz - zs)))
    for sg in (-1.0, 1.0):
        pts = [(y + sg * r * k, zs - r * k), (y + sg * yw, zs), (y + sg * ro, zs)]
        pts += [(y + sg * ro * abs(np.cos(a)), zs - ro * np.sin(a)) for a in np.radians(np.linspace(5.0, 40.0, 6))]
        hopper.append(_poly_x(pts, lambda zz: x_k))
    tv, tf = comp._shell_x(x_k, x_e, ro, ro, SHEET, 64)
    hopper.append((np.asarray(tv) + [0.0, y, zs], tf))
    sq = 0.21
    hopper.append(_plate([(-sq, -sq), (sq, -sq), (sq, sq), (-sq, sq)], x_e, x_e + 0.010, stub_r + 0.0035, at=(0.0, y, zs)))
    zo = SCREW_OUTLET_Z
    h = 0.15
    zw = zs - float(np.sqrt(ro ** 2 - h ** 2)) + 0.002
    for sg in (-1.0, 1.0):
        hopper.append(c.box((x_out - h, y + sg * h - (SHEET if sg > 0 else 0.0), zo), (x_out + h, y + sg * h + (0.0 if sg > 0 else SHEET), zw)))
        top = [(yy, zs - float(np.sqrt(ro ** 2 - yy ** 2)) + 0.002) for yy in np.linspace(h, -h, 9)]
        xw0, xw1 = sorted((x_out + sg * h, x_out + sg * (h - SHEET)))
        hopper.append(_plate([(-h, zo - zs), (h, zo - zs)] + [(a, b - zs) for a, b in top], xw0, xw1, at=(0.0, y, zs)))
    fl = [c.box((x_out - 0.18, y - 0.18, zo), (x_out + 0.18, y - h, zo + 0.012)), c.box((x_out - 0.18, y + h, zo), (x_out + 0.18, y + 0.18, zo + 0.012)),
          c.box((x_out - 0.18, y - h, zo), (x_out - h, y + h, zo + 0.012)), c.box((x_out + h, y - h, zo), (x_out + 0.18, y + h, zo + 0.012))]
    hopper += fl

    # screw: core pipe, flight helix, stubs, -X flange bearing (0.5 mm off the end plate)
    rf = SCREW_D / 2
    th = 0.006
    xf0, xf1 = x_a + 0.03, x_out + 0.05
    turns = (xf1 - xf0) / SCREW_PITCH
    nt = int(np.ceil(turns * 32)) + 1
    tt = np.linspace(0.0, turns, nt)
    ang = 2 * np.pi * tt
    xs = xf0 + SCREW_PITCH * tt
    sec = [(SCREW_PIPE_R - 0.001, -th / 2), (rf, -th / 2), (rf, th / 2), (SCREW_PIPE_R - 0.001, th / 2)]
    fv = np.array([[xs[i] + da, y + rr * np.cos(ang[i]), zs + rr * np.sin(ang[i])] for i in range(nt) for rr, da in sec])
    flight = (fv, [c.grid_faces(nt, 4, wrap_cols=True), np.array([[3, 2, 1, 0]]), np.array([[4 * (nt - 1) + j for j in range(4)]])])
    screw = [flight, st.rod((x_a + 0.015, y, zs), (x_e - 0.015, y, zs), SCREW_PIPE_R, 24),
             st.rod((x_a - 0.045, y, zs), (x_a + 0.016, y, zs), 0.020, 16),
             st.rod((x_e - 0.016, y, zs), (x_e - 0.001, y, zs), stub_r, 16)]
    screw.append(c.box((x_a - 0.0125, y - 0.06, zs - 0.06), (x_a - GAP, y + 0.06, zs + 0.06)))
    screw.append(comp._shift(comp._ring_x(x_a - 0.045, x_a - 0.0125, 0.0195, 0.045, 32), dy=y, dz=zs))

    # drive: KA..T shaft-mounted gearmotor on the stub through the +X end plate, motor toward -Y, arm down
    gm = comp.shaft_gearmotor(SCREW_DRIVE_KW, wall_z=(-sq, sq))
    o = (x_e + 0.010 - gm["dims"]["wall_y"] + GAP, y, zs)
    placed = comp.place_frame(gm["parts"], o, (0.0, -1.0, 0.0), (1.0, 0.0, 0.0))
    gear = c.merge_parts([v for kk, v in placed.items() if kk != "motor"])
    return {"hopper": c.merge_parts(hopper), "screw": c.merge_parts(screw), "gear": gear, "gearmotor": placed["motor"],
            "dims": dict(g, flight_r=rf, pitch=SCREW_PITCH, drive=gm["dims"]["size"], drive_kw=SCREW_DRIVE_KW)}


def build_dryer(site=None, faults=None):
    """Tower dryer of the STRAHL FR type after the GCS p.2 section. Along its long side: the exhaust chamber (top
    fan 22 kW on its roof, the 11 kW recirculation fan stays inside), the grain column (gable roof with the
    wet-grain screw on the ridge, discharge base over T4, cold-air louvres low on its sides) and the hot-air
    chamber (linear gas burner at the bottom behind louvres, gas train). Building «4» stays the drawn base
    enclosure with an air-intake louvre on the burner end.
    C5: the roof casing holds a real axial fan A12 (rotor, vanes, motor, cooling tube), the exhaust chamber the
    recirculation fan A13, the column base the discharge A24 (flaps, guides, cylinder) over the A11 hopper with the
    A20 screw and its gearmotor. `faults` reach those builders (check_drying broken variants)."""
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
    # (C5) the old pyramid hopper is gone: discharge A24, hopper A11 and screw A20 come from discharge() and
    # dry_hopper_and_screw() below

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
    # (C5) hollow now: the curb and the louvre box are open frames round the roof opening, the casing is two open
    # shells with flange rings, the plate under the rain louvres has the round outlet; the fan itself is top_fan()
    zl = z["fan_louvre_top"]
    fan = [c.box((fx0 - 0.05, fy0 - 0.05, zr), (fx1 + 0.05, fy0 + 0.05, zr + 0.12)), c.box((fx0 - 0.05, fy1 - 0.05, zr), (fx1 + 0.05, fy1 + 0.05, zr + 0.12)),
           c.box((fx0 - 0.05, fy0 + 0.05, zr), (fx0 + 0.05, fy1 - 0.05, zr + 0.12)), c.box((fx1 - 0.05, fy0 + 0.05, zr), (fx1 + 0.05, fy1 - 0.05, zr + 0.12))]
    fan += [c.box((fx0 + 0.03, fy0 + 0.03, zr + 0.12), (fx1 - 0.03, fy0 + 0.05, zl)), c.box((fx0 + 0.03, fy1 - 0.05, zr + 0.12), (fx1 - 0.03, fy1 - 0.03, zl)),
            c.box((fx0 + 0.03, fy0 + 0.05, zr + 0.12), (fx0 + 0.05, fy1 - 0.05, zl)), c.box((fx1 - 0.05, fy0 + 0.05, zr + 0.12), (fx1 - 0.03, fy1 - 0.05, zl))]
    for yy, sg in ((fy0, -1), (fy1, 1)):
        fan += _louvres("y", yy, (fx0, fx1), zr + 0.12, zl, sg)
    for xx, sg in ((fx0, -1), (fx1, 1)):
        fan += _louvres("x", xx, (fy0, fy1), zr + 0.12, zl, sg)
    zmid = (zl + z["fan_casing_top"]) / 2                                # two casing sections with a joint ring
    fan.append(c.cylinder(side / 2, zl, zmid, steps=64, center=(cxm, fyc), capped=False))
    fan.append(c.cylinder(side / 2, zmid, z["fan_casing_top"], steps=64, center=(cxm, fyc), capped=False))
    for zf in (zl + 0.03, zmid, z["fan_casing_top"] - 0.03):
        fan.append(_ring_z(cxm, fyc, side / 2 + 0.0005, side / 2 + 0.04, zf - 0.03, zf + 0.03))
    top = dryer_top(site)
    sq = side / 2 + 0.08
    pv, pf = _plate([(-sq, -sq), (sq, -sq), (sq, sq), (-sq, sq)], z["fan_casing_top"], z["fan_casing_top"] + 0.06, side / 2)
    from . import components as comp
    pv = comp._x_to_z((pv, pf))[0] + [cxm, fyc, 0.0]
    fan.append((pv, pf))
    for yy, sg in ((fy0 - 0.08, -1), (fy1 + 0.08, 1)):
        fan += _louvres("y", yy, (fx0 - 0.08, fx1 + 0.08), z["fan_casing_top"] + 0.06, top - 0.05, sg)
    fan.append(c.box((fx0 - 0.15, fy0 - 0.15, top - 0.05), (fx1 + 0.15, fy1 + 0.15, top)))
    tf = top_fan(site, faults)["parts"]
    lf = low_fan(site, faults)
    lp = lf["parts"]
    dis = discharge(site, faults)
    dry = dry_hopper_and_screw(site)

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
            "dryer_fan_top_shroud": ("galv", False, c.merge_parts([tf["shroud"], tf["vanes"], tf["bracket"]])),
            "dryer_fan_top_rotor": ("dark", False, tf["rotor"]), "dryer_fan_top_motor": ("motor", True, tf["motor"]),
            "dryer_fan_top_cooling": ("galv_old", False, tf["cooling"]),
            "dryer_fan_low_shroud": ("galv", False, lp["shroud_all"]), "dryer_fan_low_rotor": ("dark", False, lp["rotor"]),
            "dryer_fan_low_motor": ("motor", True, lp["motor"]), "dryer_fan_low_cooling": ("galv_old", False, lp["cooling"]),
            "dryer_discharge_frame": ("galv", False, dis["frame"]), "dryer_flaps": ("galv_old", False, dis["flaps"]),
            "dryer_flap_rods": ("dark", False, dis["rods"]), "dryer_cylinder": ("galv", True, dis["cylinder"]),
            "dryer_hopper_dry": ("galv", False, dry["hopper"]), "dryer_screw": ("dark", False, dry["screw"]),
            "dryer_screw_gear": ("dark", False, dry["gear"]), "dryer_screw_gearmotor": ("motor", True, dry["gearmotor"]),
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
