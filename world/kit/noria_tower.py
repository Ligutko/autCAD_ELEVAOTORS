"""K2. Noria tower 4.4 x 4.4 m with bucket elevator Н-100.

Local frame: tower centre at (0, 0), Z = 0 at grade (site ±0.000).
Plan (EST, consistent with PDF p.6 tower plans): stair in the west half, elevator legs in the east half.
Source tags as in silo_msvu220.py.
"""

import math

import numpy as np

from . import common as c
from . import steel as st

HALF = 2.2                      # PDF p.3, p.6: 4400 x 4400 column grid
STAIR_X = (-1.65, -0.75)        # EST: two flights side by side, 0.8 m each
STAIR_W = 0.80
STAIR_Y = (-1.25, 1.35)         # EST: flight zone, landings beyond it
STAIR_STEP_Z = 2.35             # EST: storey height of the switchback stair

# ------------------------------------------------------------------ elevator Н-100
LEG_X = (0.45, 1.45)            # EST: up leg / down leg centres, 1.0 m apart for a Ø0.9 m head pulley
LEG_Y = 0.35
LEG_W, LEG_D = 0.32, 0.52       # EST: casing 320 x 520 for 100 t/h
LEG_FLANGE_STEP = 2.0           # EST: casing sections
HEAD_PULLEY_R = 0.45            # EST: Ø900 at ~3 m/s for 100 t/h
BOOT_H = 1.7                    # EST
MOTOR_KW = 22                   # catalogue: Н-100, 22 kW


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


def build_elevator(top_z, pit_z):
    casing, flanges, dark, motor, round_ = [], [], [], [], []
    boot_z0 = pit_z + 0.25
    boot_z1 = boot_z0 + BOOT_H
    head_z0 = top_z + 0.15
    pulley_z = head_z0 + 0.95
    # legs with bolted section flanges
    for x in LEG_X:
        casing.append(c.box((x - LEG_W / 2, LEG_Y - LEG_D / 2, boot_z1), (x + LEG_W / 2, LEG_Y + LEG_D / 2, head_z0)))
        for z in np.arange(boot_z1 + LEG_FLANGE_STEP, head_z0 - 0.2, LEG_FLANGE_STEP):
            flanges.append(c.box((x - LEG_W / 2 - 0.035, LEG_Y - LEG_D / 2 - 0.035, z - 0.02),
                                 (x + LEG_W / 2 + 0.035, LEG_Y + LEG_D / 2 + 0.035, z + 0.02)))
        # inspection door on the up leg, 1.2 m above each main platform, EST
    # head: box plus half-cylinder hood around the pulley (axis along Y)
    hx0, hx1 = LEG_X[0] - LEG_W / 2 - 0.05, LEG_X[1] + LEG_W / 2 + 0.05
    hy0, hy1 = LEG_Y - 0.36, LEG_Y + 0.36
    casing.append(c.box((hx0, hy0, head_z0), (hx1, hy1, pulley_z)))
    cxm = (hx0 + hx1) / 2
    rr = (hx1 - hx0) / 2
    a = np.linspace(0, math.pi, 24)
    arc = np.column_stack([cxm + rr * np.cos(a), np.zeros(24), pulley_z + rr * 0.85 * np.sin(a)])
    v = np.concatenate([arc + [0, hy0, 0], arc + [0, hy1, 0]])
    f = [c.grid_faces(2, 24), np.arange(24)[None, :], np.arange(24, 48)[::-1][None, :]]
    round_.append((v, f))
    # discharge throat and spout at 45 deg down towards -X (to the distributor)
    casing.append(c.box((hx0 - 0.35, hy0 + 0.1, pulley_z - 0.55), (hx0, hy1 - 0.1, pulley_z - 0.05)))
    spout_a = np.array([hx0 - 0.35, LEG_Y, pulley_z - 0.35])
    dist = np.array([hx0 - 1.45, LEG_Y, top_z - 1.0])
    round_.append(st.rod(spout_a, dist + [0, 0, 0.35], 0.16, 16))
    # 2-way distributor (flap valve) and outlet stubs to -X (silo row) and -Y (gallery)
    casing.append(c.box(tuple(dist - [0.3, 0.3, 0.35]), tuple(dist + [0.3, 0.3, 0.35])))
    dark.append(c.box(tuple(dist + [0.3, -0.12, -0.1]), tuple(dist + [0.55, 0.12, 0.2])))  # actuator
    round_.append(st.rod(dist - [0.3, 0, 0.2], dist - [1.2, 0, 1.1], 0.14, 16))
    round_.append(st.rod(dist - [0, 0.3, 0.2], dist - [0, 1.2, 1.1], 0.14, 16))
    # drive: shaft-mounted reducer + 22 kW motor + backstop on the +Y side of the head
    gx = cxm
    dark.append(c.box((gx - 0.22, hy1, pulley_z - 0.30), (gx + 0.22, hy1 + 0.45, pulley_z + 0.28)))
    v, f = st.rod((gx + 0.22, hy1 + 0.22, pulley_z - 0.05), (gx + 0.95, hy1 + 0.22, pulley_z - 0.05), 0.19, 24)
    motor.append((v, f))
    v, f = st.rod((gx + 0.95, hy1 + 0.22, pulley_z - 0.05), (gx + 1.08, hy1 + 0.22, pulley_z - 0.05), 0.14, 24)
    dark.append((v, f))
    dark.append(st.rod((gx, hy0 - 0.12, pulley_z), (gx, hy0, pulley_z), 0.12, 16))   # backstop
    # boot with take-up screws and inlet hopper on the down-leg side
    bx0, bx1 = LEG_X[0] - LEG_W / 2 - 0.10, LEG_X[1] + LEG_W / 2 + 0.10
    casing.append(c.box((bx0, LEG_Y - 0.36, boot_z0), (bx1, LEG_Y + 0.36, boot_z1)))
    for x in (bx0 + 0.15, bx1 - 0.15):
        dark.append(st.rod((x, LEG_Y + 0.36, boot_z1 - 0.1), (x, LEG_Y + 0.36, boot_z1 + 0.45), 0.018, 8))
    hop_top = boot_z1 + 0.9
    casing.append(st.member((bx1 + 0.55, LEG_Y, hop_top), (bx1, LEG_Y, boot_z1 - 0.4), st.shs(0.40)))
    return (c.merge_parts(casing), c.merge_parts(round_), c.merge_parts(flanges),
            c.merge_parts(dark), c.merge_parts(motor), pulley_z)


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
    casing, rounds, flanges, drive, mot, pulley_z = build_elevator(top_z, pit_z)
    add("elevator_casing", casing, galv)
    add("elevator_spouts", rounds, galv, smooth="quads")
    add("elevator_flanges", flanges, galv_old)
    add("elevator_drive", drive, dark, smooth="quads")
    add("elevator_motor", mot, motor, smooth="quads")
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
        "head_pulley_z_m": round(pulley_z, 3),
        "motor_kw": MOTOR_KW,
    }
    return objs, measure
