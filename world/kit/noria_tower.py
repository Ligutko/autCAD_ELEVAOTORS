"""K2. Noria tower with bucket elevator У13-УН175 and its pit.

Local frame: centre of the tower column grid at (0, 0), Z = 0 at grade (site ±0.000).
All positions come from SITE.json (`x`, `y` = grid centre, `size`, `pit`, `noria_axis`,
`legs_along`), measured on PDF p.2, p.4, p.6, p.7 (research/tunnel_k4.md).
The elevator is built by noria_n100.py in its own frame and placed here with `noria_frame`.
Access: the process drawing has no tower stairs, so each tower gets a caged ladder in the strip
the drawing leaves free of equipment and spouts (SITE.json `access`, a judgment), ISO 14122-4.
"""

import math

import numpy as np

from . import common as c
from . import distribution as dist
from . import noria_n100 as nn
from . import steel as st

LADDER_W = 0.50                 # ISO 14122-4: clear width 0.4-0.6 m
RUNG_STEP = 0.30                # ISO 14122-4: 0.25-0.30 m
MAX_FLIGHT = 6.0                # ISO 14122-4: rest platform at least every 6 m
CAGE_FROM = 2.2                 # ISO 14122-4: cage starts 2.2-3.0 m above the standing level
HOOP_STEP = 0.9                 # EST, ISO 14122-4 allows up to 1.5 m
FLIGHT_SHIFT = 0.35             # flights alternate +-0.35 m along Y so each starts from a rest platform
REST = (0.8, 1.6)               # rest platform plan size (x, y); the free strip is 0.95-1.05 m wide
CAGE_REACH = FLIGHT_SHIFT + 0.70  # ladder with its cage occupies y +- this around the ladder centre
MOTOR_KW = nn.MOTOR_KW
HOLE_MARGIN = 0.08              # gap between a leg and the grating / slab edge


def build_noria(spec, phase=0.0):
    """noria_n100.build with this tower's data (SITE.json)."""
    return nn.build(spec["top_z"], spec["pit_z"], spec["tube_mm"] / 1000, spec["noria_model"], spec["feed"], phase)


def noria_frame(spec):
    """Map points from the noria_n100 frame into this tower frame.

    Legs run along Y (the only layout drawn). The rotation turns the fed leg (local +X for a
    return-leg feed, -X for a working-leg feed) towards `boot_inlet_towards`; a mirror across the
    belt plane puts the drive (local -Y) on the `drive_towards` side. The noria axis (midpoint between
    the legs) lands on `noria_axis`. f.mirrored tells callers to flip face winding.
    """
    if spec["legs_along"] != "Y":
        raise ValueError(f"{spec['id']}: only legs_along 'Y' is drawn, got {spec['legs_along']!r}")
    ax = spec["noria_axis"][0] - spec["x"]
    ay = spec["noria_axis"][1] - spec["y"]
    fed = 1 if spec["feed"] == "return" else -1
    inlet = 1 if spec["boot_inlet_towards"] == "+Y" else -1
    rot = -1 if -fed == inlet else 1          # -1: local +X -> -Y;  +1: local +X -> +Y
    drive_if_plain = -1 if rot == -1 else 1   # where local -Y (the drive) lands in X without a mirror
    mirror = drive_if_plain != (1 if spec["drive_towards"] == "+X" else -1)

    def f(p):
        p = np.array(p, dtype=float)
        dx, dy = p[..., 0] - nn.CX, p[..., 1] - nn.BELT_Y
        if mirror:
            dy = -dy
        if rot == -1:
            p[..., 0], p[..., 1] = ax + dy, ay - dx
        else:
            p[..., 0], p[..., 1] = ax - dy, ay + dx
        return p
    f.mirrored = mirror
    f.discharge_towards = "-Y" if rot == -1 else "+Y"   # throat is on the down leg, local +X
    return f


def leg_footprints(spec):
    """Plan rectangles (x0, y0, x1, y1) of both leg casings in the tower frame."""
    f = noria_frame(spec)
    sx, sy = nn.leg_size(nn.MODELS[spec["noria_model"]])
    rects = []
    for xc in nn.LEG_CENTRES_X:
        corners = f([(xc - sx / 2, nn.BELT_Y - sy / 2, 0.0), (xc + sx / 2, nn.BELT_Y + sy / 2, 0.0)])
        rects.append((corners[:, 0].min(), corners[:, 1].min(), corners[:, 0].max(), corners[:, 1].max()))
    return rects


def _bbox(rects, margin=0.0):
    return (min(r[0] for r in rects) - margin, min(r[1] for r in rects) - margin,
            max(r[2] for r in rects) + margin, max(r[3] for r in rects) + margin)


def _col(x, y, z0, z1, prof):
    return st.member((x, y, z0), (x, y, z1), prof, up=(1, 0, 0))


def build_frame(top_z, levels, hx, hy, hoist_x):
    """Columns, girts at every level, X bracing on each face between levels."""
    parts_heavy, parts_light = [], []
    corners = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)]
    for x, y in corners:
        parts_heavy.append(_col(x, y, 0.0, top_z + 1.2, st.SHS_200))
    zs = sorted(set([0.3] + list(levels) + [top_z]))
    for z in zs:
        for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
            parts_heavy.append(st.member((x0, y0, z), (x1, y1, z), st.SHS_150))
    for za, zb in zip(zs, zs[1:]):
        if zb - za < 1.0:
            continue
        for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
            parts_light.append(st.member((x0, y0, za + 0.08), (x1, y1, zb - 0.08), st.L75))
            parts_light.append(st.member((x1, y1, za + 0.08), (x0, y0, zb - 0.08), st.L75))
    # roof frame over the head and a hoist beam along the head, over the noria axis (EST)
    for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
        parts_heavy.append(st.member((x0, y0, top_z + 1.2), (x1, y1, top_z + 1.2), st.SHS_100))
    parts_heavy.append(st.member((hoist_x, -hy, top_z + 3.1), (hoist_x, hy, top_z + 3.1), st.IPE160))
    for y in (-hy, hy):
        parts_heavy.append(_col(hoist_x, y, top_z + 1.2, top_z + 3.2, st.SHS_100))
    return c.merge_parts(parts_heavy), c.merge_parts(parts_light)


def access_rect(spec):
    """Plan rectangle (x0, y0, x1, y1) taken by the ladder flights, cages and rest platforms, tower frame."""
    a = spec["access"]
    lx, ly = a["x"] - spec["x"], a["y"] - spec["y"]
    return lx - REST[0] / 2, ly - CAGE_REACH, lx + REST[0] / 2, ly + CAGE_REACH


def ladder_flights(levels, top_z, grade):
    """(z0, z1) of every ladder flight: served levels split into flights <= MAX_FLIGHT."""
    served = [grade] + [z for z in levels if z <= top_z + 1e-6]
    flights = []
    for za, zb in zip(served, served[1:]):
        k = max(1, math.ceil((zb - za) / MAX_FLIGHT - 1e-9))
        flights += [(za + (zb - za) * i / k, za + (zb - za) * (i + 1) / k) for i in range(k)]
    return flights, served


def build_access(spec, levels, top_z, grade):
    """Caged ladder flights with rest platforms between the served levels."""
    x0, y0, x1, y1 = access_rect(spec)
    lx, ly = (x0 + x1) / 2, (y0 + y1) / 2
    flights, served = ladder_flights(levels, top_z, grade)
    stiles, rungs, cage, rest, rails, toes = [], [], [], [], [], []
    for i, (za, zb) in enumerate(flights):
        y = ly + (FLIGHT_SHIFT if i % 2 else -FLIGHT_SHIFT)
        for sx in (lx - LADDER_W / 2, lx + LADDER_W / 2):
            stiles.append(st.member((sx, y, za), (sx, y, zb + 1.1), st.flat(0.06, 0.012)))
        for z in np.arange(za + RUNG_STEP, zb + 1e-6, RUNG_STEP):
            rungs.append(st.rod((lx - LADDER_W / 2, y, z), (lx + LADDER_W / 2, y, z), 0.012, 8))
        side = -1 if y < ly else 1                          # cage on the open side, away from the platform centre
        for z in np.arange(za + CAGE_FROM, zb + 1.0, HOOP_STEP):
            ring = [(lx - 0.35, y), (lx - 0.35, y + side * 0.7), (lx + 0.35, y + side * 0.7), (lx + 0.35, y)]
            for (ax, ay), (bx, by) in zip(ring, ring[1:]):
                cage.append(st.member((ax, ay, z), (bx, by, z), st.flat(0.05, 0.006)))
        for cx in (lx - 0.35, lx, lx + 0.35):
            cage.append(st.member((cx, y + side * 0.7, za + CAGE_FROM), (cx, y + side * 0.7, zb + 1.0), st.flat(0.05, 0.006)))
        if zb not in served:                                # rest platform with guard rail
            ry0, ry1 = ly - REST[1] / 2, ly + REST[1] / 2
            rest.append(st.grating_panel(x0, ry0, x1, ry1, zb))
            tube, toe = st.guard_rail([(x0 + 0.05, ry0 + 0.05), (x1 - 0.05, ry0 + 0.05), (x1 - 0.05, ry1 - 0.05),
                                       (x0 + 0.05, ry1 - 0.05)], zb, closed=True)
            rails.append(tube)
            toes.append(toe)
    return (c.merge_parts(stiles), c.merge_parts(rungs), c.merge_parts(cage), c.merge_parts(rest),
            c.merge_parts(rails), c.merge_parts(toes), served, flights)


def _cells(x0, y0, x1, y1, holes, z, panel):
    """Panels covering a rectangle minus rectangular holes (split along every hole edge)."""
    xs = sorted({x0, x1} | {min(max(h[0], x0), x1) for h in holes} | {min(max(h[2], x0), x1) for h in holes})
    ys = sorted({y0, y1} | {min(max(h[1], y0), y1) for h in holes} | {min(max(h[3], y0), y1) for h in holes})
    out = []
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            if xb - xa > 1e-6 and yb - ya > 1e-6 and not any(h[0] <= mx <= h[2] and h[1] <= my <= h[3] for h in holes):
                out.append(panel(xa, ya, xb, yb, z))
    return out


def _around_hole(x0, y0, x1, y1, hole, z, panel):
    hx0, hy0, hx1, hy1 = hole
    return [panel(x0, y0, x1, hy0, z), panel(x0, hy1, x1, y1, z),
            panel(x0, hy0, hx0, hy1, z), panel(hx1, hy0, x1, hy1, z)]


def build_platforms(levels, top_z, hx, hy, holes):
    """Grating at the main levels, with holes for the elevator legs and the ladder."""
    parts = []
    for z in levels:
        if z > top_z + 1e-6:
            continue
        parts += _cells(-hx + 0.1, -hy + 0.1, hx - 0.1, hy - 0.1, holes, z, st.grating_panel)
    return c.merge_parts(parts)


def build_guards(zs, hx, hy):
    """Perimeter guard rail at every walking level (stair landings and platforms)."""
    tubes, toes = [], []
    ring = [(-hx + 0.12, -hy + 0.12), (hx - 0.12, -hy + 0.12), (hx - 0.12, hy - 0.12), (-hx + 0.12, hy - 0.12)]
    for z in zs[1:]:
        t, o = st.guard_rail(ring, z, closed=True)
        tubes.append(t)
        toes.append(o)
    return c.merge_parts(tubes), c.merge_parts(toes)


def pit_inner(spec):
    """Inner plan rectangle (x0, y0, x1, y1) of the pit in the tower frame."""
    p = spec["pit"]
    cx, cy = p["inner_center"][0] - spec["x"], p["inner_center"][1] - spec["y"]
    sx, sy = p["inner_size"]
    return cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2


def _x_wall(xa, xb, ya, yb, z0, z1, opening):
    """Wall across X (west or east pit wall) with an optional tunnel opening (y0, y1, z0, z1)."""
    if opening is None:
        return [c.box((xa, ya, z0), (xb, yb, z1))]
    oy0, oy1, oz0, oz1 = opening
    return [c.box((xa, ya, z0), (xb, yb, oz0)), c.box((xa, ya, oz1), (xb, yb, z1)),
            c.box((xa, ya, oz0), (xb, oy0, oz1)), c.box((xa, oy1, oz0), (xb, yb, oz1))]


def pit_holes(spec, anchors):
    """(leg hole, deck hole) in the tower frame: legs pass both slabs, the deck also lets the tunnel
    conveyor spouts down to the boot inlet. anchors: from build_noria."""
    hole = _bbox(leg_footprints(spec), HOLE_MARGIN)
    inlet = noria_frame(spec)(anchors["inlet_mouth"])
    deck_hole = (min(hole[0], inlet[0] - 0.3), min(hole[1], inlet[1] - 0.3),
                 max(hole[2], inlet[0] + 0.3), max(hole[3], inlet[1] + 0.3))
    return hole, deck_hole


def build_pit(spec, hole, openings=(), deck_hole=None, cover_holes=()):
    """Concrete pit (PDF p.2, p.4): walls and bottom slab, deck at the tunnel floor, cover slab
    at grade; both slabs have the leg hole. openings: tunnel openings ("W"|"E", y0, y1, z0, z1)
    in the tower frame (tunnel.pit_opening). cover_holes: more cover holes (x0, y0, x1, y1), tower frame,
    e.g. an aspiration riser."""
    p = spec["pit"]
    x0, y0, x1, y1 = pit_inner(spec)
    t, tb = p["wall_t"], p["bottom_t"]
    z_bot, z_top = spec["pit_z"], p["cover_top_z"]
    side = {o[0]: o[1:] for o in openings}
    walls = [c.box((x0 - t, y0 - t, z_bot - tb), (x1 + t, y1 + t, z_bot)),
             c.box((x0, y0 - t, z_bot), (x1, y0, z_top)),
             c.box((x0, y1, z_bot), (x1, y1 + t, z_top))]
    walls += _x_wall(x0 - t, x0, y0 - t, y1 + t, z_bot, z_top, side.get("W"))
    walls += _x_wall(x1, x1 + t, y0 - t, y1 + t, z_bot, z_top, side.get("E"))
    slab = lambda a, b, a1, b1, z: c.box((a, b, z - p["deck_t"]), (a1, b1, z))  # noqa: E731
    deck = _around_hole(x0, y0, x1, y1, deck_hole or hole, p["deck_top_z"], slab)
    cover = _cells(x0 - t, y0 - t, x1 + t, y1 + t, [hole] + list(cover_holes), z_top, slab)
    return c.merge_parts(walls), c.merge_parts(deck + cover)


def build(spec, collection=None, materials=None, openings=(), distribution=None, cover_holes=()):
    top_z = spec["top_z"]
    pit_z = spec["pit_z"]
    grade = spec["pit"]["cover_top_z"]
    hx, hy = spec["size"][0] / 2, spec["size"][1] / 2
    levels = sorted(spec["levels_z"])
    m = materials or {}
    galv = m.get("galv") or c.mat_galvanized("TOWER_GALV", age=0.4, spangle_scale=60.0)
    galv_old = m.get("galv_old") or c.mat_galvanized("TOWER_GALV_OLD", age=0.6, spangle_scale=50.0)
    grating = m.get("grating") or st.mat_grating()
    yellow = m.get("yellow") or c.mat_painted("RAIL_YELLOW", (0.80, 0.55, 0.03), 0.45)
    dark = m.get("dark") or c.mat_painted("DRIVE_GREY", (0.20, 0.23, 0.24), 0.4)
    motor = m.get("motor") or c.mat_painted("MOTOR_BLUE", (0.05, 0.16, 0.35), 0.35)
    concrete = m.get("concrete") or c.mat_concrete("PIT_CONCRETE")

    tag = spec["id"]
    objs = {}
    frame = noria_frame(spec)
    hole = _bbox(leg_footprints(spec), HOLE_MARGIN)
    hoist_x = spec["noria_axis"][0] - spec["x"]

    def add(key, data, mat, smooth=False):
        v, f = data
        objs[key] = c.mesh_from_arrays(f"{tag}_{key.upper()}", v, f, mat, smooth=smooth, collection=collection)

    heavy, light = build_frame(top_z, levels, hx, hy, hoist_x)
    add("frame", heavy, galv)
    add("bracing", light, galv_old)
    stiles, rungs, cage, rest, rrails, rtoes, zs, flights = build_access(spec, levels, top_z, grade)
    add("ladder_stiles", stiles, galv)
    add("ladder_rungs", rungs, galv, smooth="quads")
    add("ladder_cage", cage, galv)
    add("rest_platforms", rest, grating)
    add("rest_rails", rrails, yellow, smooth="quads")
    add("rest_toes", rtoes, yellow)
    lx0, ly0, lx1, ly1 = access_rect(spec)
    ladder_hole = (lx0 + 0.2, ly0 + 0.1, lx1 - 0.2, ly1 - 0.1)
    add("platforms", build_platforms(levels, top_z, hx, hy, [hole, ladder_hole]), grating)
    tubes, toes = build_guards(zs, hx, hy)
    add("guard_rails", tubes, yellow, smooth="quads")
    add("toe_boards", toes, yellow)
    rubber = m.get("rubber") or c.mat_rubber("BELT_RUBBER")
    bucket = m.get("bucket") or c.mat_painted("BUCKET_POLY", (0.85, 0.32, 0.04), 0.45, grime=0.3)
    grain = m.get("grain") or c.mat_painted("GRAIN_WHEAT", (0.62, 0.44, 0.20), 0.8, grime=0.2)
    sensor = m.get("sensor") or c.mat_painted("SENSOR_YELLOW", (0.9, 0.7, 0.05), 0.4, grime=0.1)
    parts, labels, noria_measure, anchors = build_noria(spec)
    look = {
        "belt": (rubber, False), "buckets": (bucket, "quads"), "grain": (grain, False),
        "legs": (galv, False), "leg_flanges": (galv_old, False), "leg_bolts": (galv_old, "quads"),
        "leg_doors": (galv_old, False), "head": (galv, False), "head_cover": (galv, False),
        "head_rim": (galv_old, False), "vent": (dark, False),
        "pulley_drum": (dark, "quads"), "pulley_lagging": (rubber, "quads"), "shafts": (dark, "quads"),
        "drive": (dark, "quads"), "motor": (motor, "quads"), "boot": (galv, False),
        "boot_cover": (galv, False), "boot_rim": (galv_old, False), "boot_pulley": (dark, "quads"),
        "takeup": (dark, "quads"), "sensors": (sensor, "quads"),
    }
    for key, data in parts.items():
        if data is None:
            continue
        mat, smooth = look[key]
        v, f = data
        if frame.mirrored:                   # a mirror flips handedness: keep normals pointing out
            f = [np.asarray(b)[:, ::-1] for b in (f if isinstance(f, list) else [f])]
        add("noria_" + key, (frame(v), f), mat, smooth)
    if distribution is not None:            # site data, see distribution.py
        red = m.get("red") or c.mat_painted("GATE_RED", (0.55, 0.06, 0.04), 0.45, grime=0.3)
        dparts = dist.build(distribution, spec["x"], spec["y"], frame(anchors["outlet"]))
        look_d = {"splitters": (galv, False), "gates": (red, False), "gate_motors": (motor, "quads"), "spouts": (galv, False)}
        for key, data in dparts.items():
            add("dist_" + key, data, *look_d[key])
    label_objs = c.labels([(text, tuple(frame(p))) for text, p in labels], tag, collection)
    leg_hole, deck_hole = pit_holes(spec, anchors)
    pit_walls, pit_slabs = build_pit(spec, leg_hole, openings, deck_hole, cover_holes)
    add("pit", pit_walls, concrete)
    add("pit_slabs", pit_slabs, concrete)
    measure = {
        "id": tag,
        "column_grid_m": list(spec["size"]),
        "top_z_m": top_z,
        "pit_z_m": pit_z,
        "grade_z_m": grade,
        "levels_z_m": levels,
        "access": spec["access"]["type"],
        "served_levels_z_m": [round(z, 3) for z in zs],
        "ladder_flights_m": [round(b - a, 2) for a, b in flights],
        "rail_height_m": st.RAIL_TOP,
        "motor_kw": MOTOR_KW,
        "noria_axis_site_m": list(spec["noria_axis"]),
        "legs_along": spec["legs_along"],
        "noria_model": spec["noria_model"],
        "feed": spec["feed"],
        "noria_mirrored": frame.mirrored,
        "head_discharge_towards": frame.discharge_towards,
        "noria": noria_measure,
    }
    objs["labels_root"] = label_objs[0]
    measure["labels"] = [t for t, _ in labels]
    return objs, measure
