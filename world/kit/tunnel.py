"""K4. Tunnel under a silo row with the closed belt conveyor У13-ТЛ-50К and the gate stacks.

Site frame (same as SITE.json), Z = 0 at grade. Every number comes from SITE.json
(`tunnels`, `silo_gates`, `noria_towers`) measured on PDF p.2, p.6, p.7 and the spec p.9, p.11,
p.12 (research/tunnel_k4.md), except the ones marked EST here.
"""

import math

import numpy as np

from . import common as c
from . import noria_tower as tower
from . import steel as st

BELT_W = 0.50                  # research: Лубнимаш ТЛ-50, belt 500 mm (rec_7b968f77)
TROUGH_DEG = 20.0              # EST: 3-roll troughed idler
ROLL_R = 0.054                 # EST: Ø108 idler roll
PULLEY_R = 0.20                # EST: analog Brock head pulley 356 mm, rounded up
IDLER_STEP = 1.5               # research analog: carrying idlers every 1.5 m
IDLER_STEP_LOADING = 0.9       # research analog: closer under the loading spouts
SUPPORT_STEP = 3.0             # EST: support frame spacing
SHEET = 0.003                  # EST: casing sheet
COVER_SECTION = 2.0            # EST: cover section length with a bolted rib between sections
LAMP_STEP = 6.0                # EST: ceiling lamp spacing
MIN_SPOUT_DEG = 45.0           # EST rule of thumb for grain spouts


def _gate_positions(site, t):
    """(x, size) for every loading spout of this conveyor, silo by silo, west to east."""
    silos = {s["id"]: s for s in site["silos"]}
    g = site["silo_gates"]
    pos = []
    for sid in t["conveyor"]["silos"]:
        for off, mm in zip(g["offsets_along_row"], g["sizes_mm"]):
            pos.append((silos[sid]["x"] + off, mm / 1000))
    return sorted(pos)


def pit_face_x(site, t):
    """Inner face of the noria pit wall that the tunnel runs into (site X)."""
    spec = next(s for s in site["noria_towers"] if s["id"] == t["tower"])
    x0, _, x1, _ = tower.pit_inner(spec)
    return spec["x"] + (x0 if t["end_x"] < spec["x"] else x1)


def inner_box(site, t):
    """Tunnel clear space: (x0, y0, x1, y1, floor_z, ceiling_z) in the site frame."""
    xf = pit_face_x(site, t)
    y0, y1 = (t["row_y"] + d for d in t["inner_y_rel_row"])
    return min(t["end_x"], xf), y0, max(t["end_x"], xf), y1, t["floor_z"], t["ceiling_z"]


def boot_inlet(site, t):
    """Mouth of the noria boot inlet this conveyor discharges into (site frame)."""
    spec = next(s for s in site["noria_towers"] if s["id"] == t["tower"])
    _, _, _, anchors = tower.build_noria(spec)
    p = tower.noria_frame(spec)(anchors["inlet_mouth"])
    return np.array([p[0] + spec["x"], p[1] + spec["y"], p[2]])


def _roof_with_holes(x0, x1, y0, y1, z0, z1, holes):
    """Slab with square holes on the row axis. holes: [(x, half_size, y)]."""
    parts, cur = [], x0
    for hx, hs, hy in sorted(holes):
        parts.append(c.box((cur, y0, z0), (hx - hs, y1, z1)))
        parts.append(c.box((hx - hs, y0, z0), (hx + hs, hy - hs, z1)))
        parts.append(c.box((hx - hs, hy + hs, z0), (hx + hs, y1, z1)))
        cur = hx + hs
    parts.append(c.box((cur, y0, z0), (x1, y1, z1)))
    return parts


def _wall_with_gap(x0, x1, y0, y1, z0, z1, gap):
    """Wall box along X with one full-height gap (gx0, gx1) or None."""
    if gap is None:
        return [c.box((x0, y0, z0), (x1, y1, z1))]
    return [c.box((x0, y0, z0), (gap[0], y1, z1)), c.box((gap[1], y0, z0), (x1, y1, z1))]


def build_civil(site, t):
    """Concrete: floor slab, side walls, far end wall, roof slab with sleeve holes, exit stair well."""
    x0, y0, x1, y1, fz, cz = inner_box(site, t)
    w, ew, fs, rz = t["wall_t"], t["end_wall_t"], t["floor_slab_t"], t["roof_top_z"]
    far_west = t["end_x"] < 0
    xa, xb = (x0 - ew, x1) if far_west else (x0, x1 + ew)
    es = t["exit_stair"]
    sx0, sx1 = es["x_inner"]
    sy1 = t["row_y"] + es["y_rel_row"][1]
    parts = [c.box((xa, y0 - w, fz - fs), (xb, y1 + w, fz))]                       # floor slab
    parts += _wall_with_gap(xa, xb, y0 - w, y0, fz, rz, None)                        # south wall
    parts += _wall_with_gap(xa, xb, y1, y1 + w, fz, rz, (sx0, sx1))                  # north wall, stair opening
    parts.append(c.box((x0 - ew, y0, fz), (x0, y1, rz)) if far_west else c.box((x1, y0, fz), (x1 + ew, y1, rz)))
    holes = [(x, s / 2 + 0.01, t["row_y"]) for x, s in _gate_positions(site, t)]
    parts += _roof_with_holes(xa, xb, y0, y1, cz, rz, holes)
    # exit stair well north of the far end (PDF p.2); open at grade, EST
    parts += [c.box((sx0 - w, y1, fz - fs), (sx1 + w, sy1 + w, fz)),
              c.box((sx0 - w, y1 + w, fz), (sx0, sy1 + w, rz)),
              c.box((sx1, y1 + w, fz), (sx1 + w, sy1 + w, rz)),
              c.box((sx0, sy1, fz), (sx1, sy1 + w, rz))]
    return c.merge_parts(parts)


def build_exit_stair(t):
    es = t["exit_stair"]
    x = sum(es["x_inner"]) / 2
    y0 = t["row_y"] + es["y_rel_row"][0] + 0.3
    s, tr, r, _ = st.stair_flight(x, y0, t["floor_z"], 0.0, width=0.7, direction=1)
    return s, tr, r


def _trough_profile():
    """Belt cross-section (u across, v up) for a 3-roll troughed idler."""
    a = math.radians(TROUGH_DEG)
    mid = BELT_W * 0.38 / 2
    wing = (BELT_W - 2 * mid)
    top = [(-mid - wing * math.cos(a), wing * math.sin(a)), (-mid, 0.0), (mid, 0.0), (mid + wing * math.cos(a), wing * math.sin(a))]
    th = 0.008
    bottom = [(u, v - th) for u, v in top[::-1]]
    return np.array(top + bottom)


def build_conveyor(site, t, inlet):
    """Casing, cover, belt, idlers, pulleys, drive, supports, inlets, aspiration flanges, discharge spout."""
    cv = t["conveyor"]
    y = t["row_y"]
    z0, z1 = cv["casing_z"]
    cx0, cx1 = cv["casing_x"]
    hw = cv["width"] / 2
    tail, drive = cv["tail_x"], cv["drive_x"]
    east = drive > tail
    parts = {k: [] for k in ("casing", "cover", "belt", "idlers", "pulleys", "drive", "motor", "supports",
                             "inlets", "aspiration", "discharge")}

    # casing: sides and bottom; the cover goes separately so a cutaway can hide it
    parts["casing"] += [c.box((cx0, y - hw, z0), (cx1, y - hw + SHEET, z1 - 0.06)),
                        c.box((cx0, y + hw - SHEET, z0), (cx1, y + hw, z1 - 0.06)),
                        c.box((cx0, y - hw, z0), (cx1, y + hw, z0 + SHEET))]
    for xs in np.arange(cx0, cx1, COVER_SECTION):
        xe = min(xs + COVER_SECTION, cx1)
        for side in (-1, 1):                                    # gable cover, two sloped plates
            prof = np.array([(0.0, 0.0), (side * hw, -0.06), (side * hw, -0.063), (0.0, -0.003)])
            parts["cover"].append(st.member((xs + 0.005, y, z1), (xe - 0.005, y, z1), prof, up=(0, 0, 1)))
        parts["casing"].append(c.box((xe - 0.01, y - hw - 0.02, z1 - 0.08), (xe + 0.01, y + hw + 0.02, z1 - 0.04)))

    # belt: troughed carrying run on idlers, flat return run on the casing bottom
    zb = z0 + 0.36
    belt_x0, belt_x1 = sorted((tail, drive))
    parts["belt"].append(st.member((belt_x0, y, zb), (belt_x1, y, zb), _trough_profile(), up=(0, 0, 1)))
    parts["belt"].append(c.box((belt_x0, y - BELT_W / 2, z0 + 0.05), (belt_x1, y + BELT_W / 2, z0 + 0.058)))
    gates = _gate_positions(site, t)
    loading = [x for x, _ in gates]
    xs, x = [], belt_x0 + 0.8
    while x < belt_x1 - 0.8:
        xs.append(x)
        x += IDLER_STEP_LOADING if min(abs(x - g) for g in loading) < 1.0 else IDLER_STEP
    a = math.radians(TROUGH_DEG)
    mid = BELT_W * 0.38 / 2
    wing = BELT_W - 2 * mid
    for xi in xs:
        zr = zb - 0.008 - ROLL_R
        parts["idlers"].append(st.rod((xi, y - mid, zr), (xi, y + mid, zr), ROLL_R, 12))
        for s in (-1, 1):
            p0 = np.array([xi, y + s * mid, zr])
            p1 = p0 + [0, s * wing * math.cos(a), wing * math.sin(a)]
            parts["idlers"].append(st.rod(p0 + [0, s * 0.01, 0], p1, ROLL_R, 12))
        parts["idlers"].append(c.box((xi - 0.025, y - hw + 0.02, z0 + 0.1), (xi + 0.025, y + hw - 0.02, z0 + 0.12)))

    # pulleys (EST Ø400), drive on the +Y side outside the casing (PDF p.2: motors on the north side)
    for xp in (tail, drive):
        parts["pulleys"].append(st.rod((xp, y - BELT_W / 2 - 0.05, zb - PULLEY_R + 0.05),
                                       (xp, y + BELT_W / 2 + 0.05, zb - PULLEY_R + 0.05), PULLEY_R, 32))
        parts["pulleys"].append(st.rod((xp, y - hw - 0.08, zb - PULLEY_R + 0.05), (xp, y + hw + 0.08, zb - PULLEY_R + 0.05), 0.03, 12))
    zs = zb - PULLEY_R + 0.05
    parts["drive"].append(c.box((drive - 0.16, y + hw + 0.08, zs - 0.18), (drive + 0.16, y + hw + 0.36, zs + 0.18)))
    back = -1 if east else 1
    parts["motor"].append(st.rod((drive, y + hw + 0.22, zs + 0.34), (drive + back * 0.42, y + hw + 0.22, zs + 0.34), 0.11, 24))
    parts["drive"].append(c.box((drive - 0.12, y + hw + 0.1, zs + 0.18), (drive + 0.12, y + hw + 0.34, zs + 0.24)))
    for s in (-1, 1):                                            # screw take-up at the tail
        parts["drive"].append(st.rod((tail + back * 0.05, y + s * (hw + 0.05), zs), (tail + back * 0.55, y + s * (hw + 0.05), zs), 0.012, 8))

    # supports: two legs and a cross beam, floor to casing
    fz = t["floor_z"]
    for xs_ in np.arange(cx0 + 0.5, cx1 - 0.3, SUPPORT_STEP):
        for s in (-1, 1):
            parts["supports"].append(st.member((xs_, y + s * (hw - 0.03), fz), (xs_, y + s * (hw - 0.03), z0), st.shs(0.06)))
        parts["supports"].append(st.member((xs_, y - hw, z0 - 0.03), (xs_, y + hw, z0 - 0.03), st.shs(0.06)))

    # loading inlets under the gates and aspiration flanges next to them (spec: 14 + 1 = 15 x □350)
    for xg, s in gates:
        parts["inlets"].append(c.box((xg - s / 2 - 0.08, y - s / 2 - 0.08, z1 - 0.06), (xg + s / 2 + 0.08, y + s / 2 + 0.08, z1 + 0.02)))
        xa = xg + 0.55
        parts["aspiration"] += [c.box((xa - 0.175, y - 0.175, z1 - 0.03), (xa + 0.175, y + 0.175, z1 + 0.12)),
                                c.box((xa - 0.215, y - 0.215, z1 + 0.12), (xa + 0.215, y + 0.215, z1 + 0.14))]

    # discharge hood around the drive pulley and the spout into the noria boot inlet
    hx0, hx1 = (drive - 0.35, cx1) if east else (cx0, drive + 0.35)
    parts["discharge"].append(c.box((hx0, y - hw - 0.05, z0 - 0.25), (hx1, y + hw + 0.05, z1 + 0.1)))
    xa = drive + (0.55 if east else -0.55)
    parts["aspiration"] += [c.box((xa - 0.175, y - 0.175, z1 + 0.1), (xa + 0.175, y + 0.175, z1 + 0.25))]
    ox, oz = cv["outlet_xz"]                                   # head outlet measured on p.6, p.7
    spout_start = np.array([ox, y, oz])
    parts["discharge"].append(st.member(spout_start, inlet, st.shs(0.30)))

    merged = {k: c.merge_parts(v) for k, v in parts.items() if v}
    run = np.linalg.norm((inlet - spout_start)[:2])
    measure = {
        "id": cv["id"],
        "type": cv["type"],
        "length_between_pulleys_m": round(abs(drive - tail), 3),
        "spec_length_m": cv["spec_length_m"],
        "belt_width_m": BELT_W,
        "loading_inlets": len(gates),
        "inlet_sizes_mm": sorted(round(s * 1000) for _, s in gates),
        "aspiration_flanges": len(gates) + 1,
        "idlers": len(xs),
        "supports": len(np.arange(cx0 + 0.5, cx1 - 0.3, SUPPORT_STEP)),
        "spout_start": [round(v, 3) for v in spout_start],
        "spout_end": [round(v, 3) for v in inlet],
        "spout_angle_deg": round(math.degrees(math.atan2(spout_start[2] - inlet[2], run)), 1),
        "gate_x": [round(x, 3) for x, _ in gates],
    }
    return merged, measure


def build_gate_stacks(site, t):
    """Per opening: sleeve through the slab, electric gate ТЗА (rack + 0.18 kW motor), manual gate ТЗР
    (handwheel), spout into the conveyor inlet. Heights from SITE.json silo_gates.stack_z."""
    sz = site["silo_gates"]["stack_z"]
    y = t["row_y"]
    parts = {"sleeves": [], "gates": [], "gate_motors": [], "handwheels": [], "spouts": []}
    for x, s in _gate_positions(site, t):
        h = s / 2
        parts["sleeves"].append(c.box((x - h - 0.01, y - h - 0.01, sz["sleeve"][1]), (x + h + 0.01, y + h + 0.01, sz["sleeve"][0] - 0.02)))
        za0, za1 = sz["tza"][1], sz["tza"][0]
        parts["gates"].append(c.box((x - h - 0.1, y - h - 0.06, za0), (x + h + 0.1, y + h + 0.06, za1)))
        parts["gates"].append(c.box((x + h + 0.1, y - 0.08, za0 + 0.06), (x + h + 0.55, y + 0.08, za1 - 0.06)))   # rack housing
        parts["gate_motors"].append(st.rod((x + h + 0.45, y + 0.08, za0 + 0.125), (x + h + 0.45, y + 0.30, za0 + 0.125), 0.06, 16))
        zr0, zr1 = sz["tzr"][1], sz["tzr"][0]
        parts["gates"].append(c.box((x - h - 0.1, y - h - 0.06, zr0), (x + h + 0.1, y + h + 0.06, zr1)))
        zw = (zr0 + zr1) / 2
        parts["handwheels"].append(st.rod((x, y - h - 0.06, zw), (x, y - h - 0.25, zw), 0.012, 8))
        parts["handwheels"].append(st.rod((x, y - h - 0.25, zw), (x, y - h - 0.27, zw), 0.15, 24))
        parts["spouts"].append(c.box((x - h, y - h, sz["spout_bottom"] + 0.02), (x + h, y + h, zr0)))
    return {k: c.merge_parts(v) for k, v in parts.items()}


def build_services(site, t):
    """Ceiling lamps over the walkway and a cable tray on the wall (EST)."""
    x0, y0, x1, y1, fz, cz = inner_box(site, t)
    y_mid = t["row_y"]
    wide_side = y1 if (y1 - y_mid) > (y_mid - y0) else y0
    yl = (y_mid + wide_side) / 2
    lamps, tray, lamp_pts = [], [], []
    for x in np.arange(x0 + 1.5, x1 - 1.0, LAMP_STEP):
        lamps.append(c.box((x - 0.35, yl - 0.07, cz - 0.08), (x + 0.35, yl + 0.07, cz)))
        lamp_pts.append((x, yl, cz - 0.1))
    ty = wide_side - 0.12 if wide_side == y1 else wide_side + 0.12
    tray.append(c.box((x0, ty - 0.1, cz - 0.35), (x1, ty + 0.1, cz - 0.3)))
    return c.merge_parts(lamps), c.merge_parts(tray), lamp_pts


def ground_cells(extent, holes, z0=-0.2, z1=0.0):
    """Ground slab as rectangles, leaving out plan holes (x0, y0, x1, y1) such as tunnels and pits."""
    xs = sorted({-extent, extent} | {h[0] for h in holes} | {h[2] for h in holes})
    ys = sorted({-extent, extent} | {h[1] for h in holes} | {h[3] for h in holes})
    parts = []
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            if any(h[0] <= mx <= h[2] and h[1] <= my <= h[3] for h in holes):
                continue
            parts.append(c.box((xa, ya, z0), (xb, yb, z1)))
    return c.merge_parts(parts)


def footprint(site, t):
    """Outer plan rectangles of the tunnel and its stair well (for ground holes)."""
    x0, y0, x1, y1, _, _ = inner_box(site, t)
    w, ew = t["wall_t"], t["end_wall_t"]
    es = t["exit_stair"]
    tun = (x0 - ew if t["end_x"] < 0 else x0, y0 - w, x1 + ew if t["end_x"] > 0 else x1, y1 + w)
    well = (es["x_inner"][0] - w, y1, es["x_inner"][1] + w, t["row_y"] + es["y_rel_row"][1] + w)
    return [tun, well]


def pit_opening(site, t):
    """Opening this tunnel needs in its pit wall: (side, y0, y1, z0, z1) in the tower frame."""
    spec = next(s for s in site["noria_towers"] if s["id"] == t["tower"])
    _, y0, _, y1, fz, cz = inner_box(site, t)
    return ("W" if t["end_x"] < spec["x"] else "E", y0 - spec["y"], y1 - spec["y"], fz, cz)


def build(site, t, collection=None, materials=None):
    m = materials or {}
    concrete = m.get("concrete") or c.mat_concrete("TUNNEL_CONCRETE")
    galv = m.get("galv") or c.mat_galvanized("TUNNEL_GALV", age=0.5, spangle_scale=60.0)
    dark = m.get("dark") or c.mat_painted("TUNNEL_DRIVE_GREY", (0.20, 0.23, 0.24), 0.4)
    motor = m.get("motor") or c.mat_painted("TUNNEL_MOTOR_BLUE", (0.05, 0.16, 0.35), 0.35)
    rubber = m.get("rubber") or c.mat_rubber("TUNNEL_BELT")
    red = m.get("red") or c.mat_painted("GATE_RED", (0.55, 0.06, 0.04), 0.45, grime=0.3)
    grating = m.get("grating") or st.mat_grating()
    lamp_mat = m.get("lamp") or c.mat_painted("LAMP_WHITE", (0.9, 0.9, 0.85), 0.3, grime=0.1)
    tag = t["id"]
    objs = {}

    def add(key, data, mat, smooth=False):
        v, f = data
        objs[key] = c.mesh_from_arrays(f"{tag}_{key.upper()}", v, f, mat, smooth=smooth, collection=collection)

    add("civil", build_civil(site, t), concrete)
    s, tr, r = build_exit_stair(t)
    add("exit_stringers", s, galv)
    add("exit_treads", tr, grating)
    add("exit_rails", r, galv, smooth="quads")
    inlet = boot_inlet(site, t)
    conv, measure = build_conveyor(site, t, inlet)
    look = {"casing": galv, "cover": galv, "belt": rubber, "idlers": dark, "pulleys": dark, "drive": dark,
            "motor": motor, "supports": galv, "inlets": galv, "aspiration": galv, "discharge": galv}
    for k, data in conv.items():
        add("conv_" + k, data, look[k], smooth="quads" if k in ("idlers", "pulleys", "motor") else False)
    stacks = build_gate_stacks(site, t)
    look_g = {"sleeves": galv, "gates": red, "gate_motors": motor, "handwheels": dark, "spouts": galv}
    for k, data in stacks.items():
        add(k, data, look_g[k], smooth="quads" if k in ("gate_motors", "handwheels") else False)
    lamps, tray, lamp_pts = build_services(site, t)
    add("lamps", lamps, lamp_mat)
    add("cable_tray", tray, galv)
    x0, y0, x1, y1, fz, cz = inner_box(site, t)
    measure.update({
        "tunnel_inner_m": [round(y1 - y0, 3), round(cz - fz, 3)],
        "tunnel_x_m": [round(x0, 3), round(x1, 3)],
        "walkways_m": [round((t["row_y"] - t["conveyor"]["width"] / 2) - y0, 3),
                       round(y1 - (t["row_y"] + t["conveyor"]["width"] / 2), 3)],
    })
    return objs, measure, {"lamps": lamp_pts, "inlet": tuple(inlet)}
