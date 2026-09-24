"""K2. Noria tower 4.4 x 4.4 m with bucket elevator Н-100.

Local frame: tower centre at (0, 0), Z = 0 at grade (site ±0.000).
Plan (EST, consistent with PDF p.6 tower plans): stair in the west half, elevator legs in the east half.
Source tags as in silo_msvu220.py.
"""

import math

import numpy as np

from . import common as c
from . import noria_n100 as nn
from . import steel as st

HALF = 2.2                      # PDF p.3, p.6: 4400 x 4400 column grid
STAIR_X = (-1.65, -0.75)        # EST: two flights side by side, 0.8 m each
STAIR_W = 0.80
STAIR_Y = (-1.25, 1.35)         # EST: flight zone, landings beyond it
STAIR_STEP_Z = 2.35             # EST: storey height of the switchback stair

# ------------------------------------------------------------------ elevator Н-100
LEG_X = nn.LEG_CENTRES_X        # detailed elevator, see noria_n100.py
LEG_Y = nn.BELT_Y
LEG_W, LEG_D = nn.LEG_SIZE_X, nn.LEG_SIZE_Y
MOTOR_KW = nn.MOTOR_KW


def _col(x, y, z0, z1, prof):
    return st.member((x, y, z0), (x, y, z1), prof, up=(1, 0, 0))


def build_frame(top_z, levels):
    """Columns, girts at every level, X bracing on each face between levels."""
    parts_heavy, parts_light = [], []
    corners = [(-HALF, -HALF), (HALF, -HALF), (HALF, HALF), (-HALF, HALF)]
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
    # roof frame over the head
    for (x0, y0), (x1, y1) in zip(corners, corners[1:] + corners[:1]):
        parts_heavy.append(st.member((x0, y0, top_z + 1.2), (x1, y1, top_z + 1.2), st.SHS_100))
    parts_heavy.append(st.member((LEG_X[0] - 0.8, -HALF, top_z + 3.1), (LEG_X[0] - 0.8, HALF, top_z + 3.1),
                                 st.IPE160))   # hoist beam over the head, EST
    for x, y in ((LEG_X[0] - 0.8, -HALF), (LEG_X[0] - 0.8, HALF)):
        parts_heavy.append(_col(x, y, top_z + 1.2, top_z + 3.2, st.SHS_100))
    return c.merge_parts(parts_heavy), c.merge_parts(parts_light)


GRADE_FLOOR = 0.3               # EST: grating over the pit, level with the pit walls


def stair_levels(first_platform):
    rise = first_platform - GRADE_FLOOR
    n = max(1, int(round(rise / STAIR_STEP_Z)))
    return [GRADE_FLOOR + rise * k / n for k in range(n + 1)]


def build_stairs(levels, top_z):
    """Switchback stair: each storey is one flight, landings alternate north / south."""
    zs = stair_levels(levels[0]) + [z for z in levels[1:] if z <= top_z]
    stringers, treads, rails, landings = [], [], [], []
    for i, (za, zb) in enumerate(zip(zs, zs[1:])):
        up_north = i % 2 == 0
        x = STAIR_X[i % 2]
        y0 = STAIR_Y[0] if up_north else STAIR_Y[1]
        s, t, r, y_end = st.stair_flight(x, y0, za, zb, STAIR_W, 1 if up_north else -1)
        stringers.append(s)
        treads.append(t)
        rails.append(r)
        if up_north:
            landings.append(st.grating_panel(-HALF + 0.1, y_end, -0.3, HALF - 0.1, zb))
        else:
            landings.append(st.grating_panel(-HALF + 0.1, -HALF + 0.1, -0.3, y_end, zb))
    return (c.merge_parts(stringers), c.merge_parts(treads), c.merge_parts(rails),
            c.merge_parts(landings), zs)


def build_platforms(levels, top_z):
    """Full grating at the main levels around the elevator legs (legs pass through holes)."""
    parts = []
    hole_x0, hole_x1 = LEG_X[0] - LEG_W / 2 - 0.08, LEG_X[1] + LEG_W / 2 + 0.08
    hole_y0, hole_y1 = LEG_Y - LEG_D / 2 - 0.08, LEG_Y + LEG_D / 2 + 0.08
    for z in [GRADE_FLOOR] + list(levels):
        if z > top_z + 1e-6:
            continue
        x0 = -HALF + 0.1 if z == GRADE_FLOOR else -0.3
        x1, y0, y1 = HALF - 0.1, -HALF + 0.1, HALF - 0.1
        parts.append(st.grating_panel(x0, y0, x1, hole_y0, z))
        parts.append(st.grating_panel(x0, hole_y1, x1, y1, z))
        parts.append(st.grating_panel(x0, hole_y0, hole_x0, hole_y1, z))
        parts.append(st.grating_panel(hole_x1, hole_y0, x1, hole_y1, z))
    return c.merge_parts(parts)


def build_guards(zs):
    """Perimeter guard rail at every walking level (stair landings and platforms)."""
    tubes, toes = [], []
    ring = [(-HALF + 0.12, -HALF + 0.12), (HALF - 0.12, -HALF + 0.12), (HALF - 0.12, HALF - 0.12),
            (-HALF + 0.12, HALF - 0.12)]
    for z in zs[1:]:
        t, o = st.guard_rail(ring, z, closed=True)
        tubes.append(t)
        toes.append(o)
    return c.merge_parts(tubes), c.merge_parts(toes)


def build_distributor(spout_end, top_z):
    """2-way flap distributor under the head spout; outlets to -X (silo gallery) and -Y (bridge)."""
    d = np.asarray(spout_end, float) - [0, 0, 0.35]
    body = [c.box(tuple(d - [0.3, 0.3, 0.35]), tuple(d + [0.3, 0.3, 0.35]))]
    actuator = [c.box(tuple(d + [0.3, -0.12, -0.1]), tuple(d + [0.55, 0.12, 0.2]))]
    outlets = [st.rod(d - [0.3, 0, 0.2], d - [1.3, 0, 1.2], 0.14, 16),
               st.rod(d - [0, 0.3, 0.2], d - [0, 1.3, 1.2], 0.14, 16)]
    return c.merge_parts(body), c.merge_parts(actuator), c.merge_parts(outlets)


def build_pit(pit_z):
    """Concrete pit under the tower, 300 mm walls and slab; grating cover at grade."""
    t = 0.3
    x0, x1, y0, y1 = -HALF - t, HALF + t, -HALF - t, HALF + t
    walls = [c.box((x0, y0, pit_z - t), (x1, y1, pit_z)),
             c.box((x0, y0, pit_z), (x0 + t, y1, 0.3)),
             c.box((x1 - t, y0, pit_z), (x1, y1, 0.3)),
             c.box((x0, y0, pit_z), (x1, y0 + t, 0.3)),
             c.box((x0, y1 - t, pit_z), (x1, y1, 0.3))]
    return c.merge_parts(walls)


def build(spec, collection=None, materials=None):
    top_z = spec["top_z"]
    pit_z = spec["pit_z"]
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

    def add(key, data, mat, smooth=False):
        v, f = data
        objs[key] = c.mesh_from_arrays(f"{tag}_{key.upper()}", v, f, mat, smooth=smooth, collection=collection)

    heavy, light = build_frame(top_z, levels)
    add("frame", heavy, galv)
    add("bracing", light, galv_old)
    s, t, r, landings, zs = build_stairs(levels, top_z)
    add("stair_stringers", s, galv)
    add("stair_treads", t, grating)
    add("stair_rails", r, yellow, smooth="quads")
    add("landings", landings, grating)
    add("platforms", build_platforms(levels, top_z), grating)
    tubes, toes = build_guards(zs)
    add("guard_rails", tubes, yellow, smooth="quads")
    add("toe_boards", toes, yellow)
    rubber = m.get("rubber") or c.mat_rubber("BELT_RUBBER")
    bucket = m.get("bucket") or c.mat_painted("BUCKET_POLY", (0.85, 0.32, 0.04), 0.45, grime=0.3)
    grain = m.get("grain") or c.mat_painted("GRAIN_WHEAT", (0.62, 0.44, 0.20), 0.8, grime=0.2)
    sensor = m.get("sensor") or c.mat_painted("SENSOR_YELLOW", (0.9, 0.7, 0.05), 0.4, grime=0.1)
    parts, labels, noria_measure, anchors = nn.build(top_z, pit_z)
    look = {
        "belt": (rubber, False), "buckets": (bucket, "quads"), "grain": (grain, False),
        "legs": (galv, False), "leg_flanges": (galv_old, False), "leg_bolts": (galv_old, "quads"),
        "leg_doors": (galv_old, False), "head": (galv, False), "head_cover": (galv, False),
        "head_rim": (galv_old, False), "head_spout": (galv, "quads"), "vent": (dark, False),
        "pulley_drum": (dark, "quads"), "pulley_lagging": (rubber, "quads"), "shafts": (dark, "quads"),
        "drive": (dark, "quads"), "motor": (motor, "quads"), "boot": (galv, False),
        "boot_cover": (galv, False), "boot_rim": (galv_old, False), "boot_pulley": (dark, "quads"),
        "takeup": (dark, "quads"), "sensors": (sensor, "quads"),
    }
    for key, data in parts.items():
        if data is None:
            continue
        mat, smooth = look[key]
        add("noria_" + key, data, mat, smooth)
    body, act, outlets = build_distributor(anchors["spout_end"], top_z)
    add("distributor", body, galv)
    add("distributor_actuator", act, dark)
    add("distributor_outlets", outlets, galv, smooth="quads")
    label_objs = c.labels(labels, tag, collection)
    add("pit", build_pit(pit_z), concrete)
    measure = {
        "id": tag,
        "column_grid_m": [2 * HALF, 2 * HALF],
        "top_z_m": top_z,
        "pit_z_m": pit_z,
        "levels_z_m": levels,
        "stair_levels_z_m": [round(z, 3) for z in zs],
        "stair_riser_m": st.RISER,
        "stair_tread_m": st.TREAD,
        "rail_height_m": st.RAIL_TOP,
        "motor_kw": MOTOR_KW,
        "noria": noria_measure,
    }
    objs["labels_root"] = label_objs[0]
    measure["labels"] = [t for t, _ in labels]
    return objs, measure
