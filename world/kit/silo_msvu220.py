"""K1. Silo МСВУ 220.13.В12, exterior.

Local frame: silo axis at (0, 0), Z = 0 on top of the foundation (site +0.600).
Source tags: PDF p.N, LUB (Lubnymash catalogue), STD (standard / trade practice), EST (engineering estimate).
"""

import math

import numpy as np

from . import common as c

# ------------------------------------------------------------------ wall
R = 11.0                    # PDF p.6 Ø22000, LUB: nominal (mean) radius of corrugated wall
RINGS = 13                  # LUB table: 21422 mm -> 13 tiers
RING_H = 1.152              # LUB: useful sheet height
WAVE_PITCH = 0.064          # LUB: corrugation pitch
WAVE_DEPTH = 0.013          # EST: crest-to-valley, typical for ~64 mm pitch profiles
SHEET_T_BOTTOM = 0.003      # LUB: 1-3 mm by tier
SHEET_T_TOP = 0.001
WALL_TOP = RINGS * RING_H   # 14.976
SHEETS_PER_RING = 20        # EST: 3.46 m sheets, every 4th stiffener
AROUND = 640                # mesh resolution around

# ------------------------------------------------------------------ stiffeners
STIFFENERS = 80             # PDF p.6: 80 vertical lines at 4.5 deg
OMEGA = [(0.0, -0.080), (0.0, -0.042), (0.075, -0.030), (0.075, 0.030), (0.0, 0.042), (0.0, 0.080)]  # EST (r, s) m
OMEGA_T = 0.003             # LUB: stiffener 1-6 mm

# ------------------------------------------------------------------ bolts
BOLT_ACROSS_CORNERS = 0.0185  # STD ISO 4017 M10: s = 16 mm -> e = 18.5 mm
BOLT_HEAD_H = 0.0064          # STD ISO 4017 M10: k = 6.4 mm
H_SEAM_BOLT_STEP = 0.144      # EST: along circumferential lap seam
V_SEAM_BOLT_STEP = 0.128      # EST: two waves
STIFF_BOLT_STEP = 0.288       # EST: stiffener flange to wall

# ------------------------------------------------------------------ roof
ROOF_SLOPE = math.radians(30.0)  # LUB: all roofs 30 deg
EAVE_OVERHANG = 0.22             # EST
ROOF_RIBS = 80                   # PDF p.6: roof lines match stiffeners
ROOF_RIB_H = 0.045               # EST standing rib
ROOF_T = 0.0015                  # EST
COLLAR_R = 0.65                  # EST: top ring
SPOUT_R = 0.2                    # EST: Ø400 loading spout
SPOUT_TOP = 21.422               # PDF p.8 / LUB: height to loading spout

# ------------------------------------------------------------------ base
FOUND_R = 11.6                   # PDF p.2/p.4: foundation ring a bit wider than wall, EST 0.6 m
FOUND_H = 0.6                    # PDF p.4, p.6: silo base at +0.600
AERATION_FANS = 4                # PDF p.2: four fan symbols per silo at 45 deg
FAN_ANGLES = [45.0, 135.0, 225.0, 315.0]
DOOR_ANGLE = 180.0 + 9.0         # EST: between stiffeners, towards the tunnel side
LADDER_ANGLE = 270.0 - 6.75      # EST: west side, between stiffeners


def sheet_thickness(ring):
    f = ring / (RINGS - 1)
    return SHEET_T_BOTTOM + (SHEET_T_TOP - SHEET_T_BOTTOM) * f


def corrugation(z):
    return 0.5 * WAVE_DEPTH * np.cos(2 * math.pi * z / WAVE_PITCH)


# ================================================================== geometry

def build_wall():
    samples_per_wave = 8
    n_z = int(round(WALL_TOP / WAVE_PITCH)) * samples_per_wave + 1
    z = np.linspace(0.0, WALL_TOP, n_z)
    a = np.linspace(0, 2 * math.pi, AROUND, endpoint=False)
    ring_idx = np.minimum((z / RING_H).astype(int), RINGS - 1)
    t = np.array([sheet_thickness(i) for i in ring_idx])
    r_out = R + corrugation(z) + t * 0.5
    r_in = r_out - t
    cos_a, sin_a = np.cos(a), np.sin(a)

    def surface(r):
        return np.stack([r[:, None] * cos_a[None, :], r[:, None] * sin_a[None, :],
                         np.repeat(z[:, None], AROUND, axis=1)], axis=-1).reshape(-1, 3)

    outer = surface(r_out)
    inner = surface(r_in)
    f_out = c.grid_faces(n_z, AROUND, wrap_cols=True)
    f_in = c.grid_faces(n_z, AROUND, wrap_cols=True)[:, ::-1] + len(outer)
    # top and bottom lips
    n = len(outer)
    i = np.arange(AROUND)
    j = (i + 1) % AROUND
    bottom = np.stack([i, i + n, j + n, j], axis=-1)
    top_o = (n_z - 1) * AROUND
    top = np.stack([top_o + i, top_o + j, top_o + j + n, top_o + i + n], axis=-1)
    verts = np.concatenate([outer, inner])
    return verts, np.concatenate([f_out, f_in, bottom, top])


def stiffener_angles():
    return np.arange(STIFFENERS) * 2 * math.pi / STIFFENERS + math.pi / STIFFENERS


def build_stiffeners():
    prof = np.array(OMEGA)
    outer = prof + np.array([OMEGA_T, 0.0])
    loop = np.concatenate([prof, outer[::-1]])            # closed (r, s) profile, 12 points
    k = len(loop)
    base_r = R + 0.5 * WAVE_DEPTH + SHEET_T_BOTTOM
    parts = []
    for ang in stiffener_angles():
        r = base_r + loop[:, 0]
        s = loop[:, 1]
        x = r * math.cos(ang) - s * math.sin(ang)
        y = r * math.sin(ang) + s * math.cos(ang)
        v = np.concatenate([np.column_stack([x, y, np.full(k, 0.0)]),
                            np.column_stack([x, y, np.full(k, WALL_TOP)])])
        f = [c.grid_faces(2, k, wrap_cols=True)[:, ::-1],
             np.arange(k)[None, :], np.arange(k, 2 * k)[::-1][None, :]]
        parts.append((v, f))
    return c.merge_parts(parts)


def hex_heads(theta, z, r_base, axis="radial"):
    """Vectorised M10 hex heads. theta, z, r_base: arrays of equal length. Head axis is radial."""
    n = len(theta)
    e = BOLT_ACROSS_CORNERS / 2
    hex_a = np.arange(6) * math.pi / 3 + math.pi / 6
    ds = e * np.cos(hex_a)             # tangential
    dz = e * np.sin(hex_a)             # vertical
    verts = np.empty((n, 12, 3))
    for layer, dr in enumerate((0.0, BOLT_HEAD_H)):
        rr = (r_base + dr)[:, None]
        th = theta[:, None]
        verts[:, layer * 6:(layer + 1) * 6, 0] = rr * np.cos(th) - ds[None, :] * np.sin(th)
        verts[:, layer * 6:(layer + 1) * 6, 1] = rr * np.sin(th) + ds[None, :] * np.cos(th)
        verts[:, layer * 6:(layer + 1) * 6, 2] = z[:, None] + dz[None, :]
    base = (np.arange(n) * 12)[:, None]
    i = np.arange(6)
    j = (i + 1) % 6
    sides = (np.stack([i, j, j + 6, i + 6], axis=-1)[None, :, :] + base[:, :, None]).reshape(-1, 4)
    caps_top = (np.arange(6, 12)[None, :] + base).reshape(-1, 6)
    caps_bot = (np.arange(6)[::-1][None, :] + base).reshape(-1, 6)
    return verts.reshape(-1, 3), [sides, caps_top, caps_bot]


def bolt_positions():
    crest = R + 0.5 * WAVE_DEPTH
    th, zz, rr = [], [], []
    # circumferential lap seams at every ring joint
    n_h = int(round(2 * math.pi * R / H_SEAM_BOLT_STEP))
    ang = np.arange(n_h) * 2 * math.pi / n_h
    for k in range(1, RINGS):
        for dz in (-0.024, 0.024):
            z = k * RING_H + dz
            th.append(ang)
            zz.append(np.full(n_h, z))
            rr.append(np.full(n_h, R + corrugation(z) + sheet_thickness(k)))
    # vertical sheet seams, staggered every other ring
    seam_step = 2 * math.pi / SHEETS_PER_RING
    for k in range(RINGS):
        shift = 0.5 * seam_step * (k % 2)
        z_rows = np.arange(k * RING_H + 0.06, (k + 1) * RING_H - 0.04, V_SEAM_BOLT_STEP)
        for sheet in range(SHEETS_PER_RING):
            base_a = sheet * seam_step + shift + 0.5 * math.pi / STIFFENERS
            for col in (-0.045, 0.0, 0.045):
                th.append(np.full(len(z_rows), base_a + col / R))
                zz.append(z_rows)
                rr.append(R + corrugation(z_rows) + sheet_thickness(k))
    # stiffener flanges
    z_rows = np.arange(0.15, WALL_TOP - 0.05, STIFF_BOLT_STEP)
    for a in stiffener_angles():
        for s in (-0.062, 0.062):
            th.append(np.full(len(z_rows), a + s / R))
            zz.append(z_rows)
            rr.append(np.full(len(z_rows), crest + SHEET_T_BOTTOM + OMEGA_T))
    return np.concatenate(th), np.concatenate(zz), np.concatenate(rr)


def build_roof():
    """Cone at 30 deg with standing radial ribs; underside separate so the roof has thickness."""
    r0 = R + EAVE_OVERHANG
    z0 = WALL_TOP - EAVE_OVERHANG * math.tan(ROOF_SLOPE)
    peak_z = WALL_TOP + (R - COLLAR_R) * math.tan(ROOF_SLOPE)
    n_r = 40
    a = np.linspace(0, 2 * math.pi, ROOF_RIBS * 12, endpoint=False)
    radii = np.linspace(r0, COLLAR_R, n_r)
    zs = z0 + (r0 - radii) * math.tan(ROOF_SLOPE)
    # rib bump: raised trapezoid across ~1/6 of each panel near the rib line
    phase = (a * ROOF_RIBS / (2 * math.pi)) % 1.0
    bump = np.clip(1.0 - np.abs(phase - 0.0) * 14, 0, 1) + np.clip(1.0 - np.abs(phase - 1.0) * 14, 0, 1)
    rib = ROOF_RIB_H * np.clip(bump * 1.6, 0, 1)
    top = np.stack([radii[:, None] * np.cos(a)[None, :], radii[:, None] * np.sin(a)[None, :],
                    zs[:, None] + rib[None, :] / math.cos(ROOF_SLOPE)], axis=-1).reshape(-1, 3)
    under = np.stack([radii[:, None] * np.cos(a)[None, :], radii[:, None] * np.sin(a)[None, :],
                      np.repeat((zs - ROOF_T / math.cos(ROOF_SLOPE))[:, None], len(a), axis=1)],
                     axis=-1).reshape(-1, 3)
    n_a = len(a)
    f_top = c.grid_faces(n_r, n_a, wrap_cols=True)[:, ::-1]
    f_under = c.grid_faces(n_r, n_a, wrap_cols=True) + len(top)
    i = np.arange(n_a)
    j = (i + 1) % n_a
    n = len(top)
    edge = np.stack([i, j, j + n, i + n], axis=-1)
    verts = np.concatenate([top, under])
    return (verts, np.concatenate([f_top, f_under, edge])), peak_z


def build_eave_and_collar(peak_z):
    parts = []
    # eave angle ring where roof sits on wall
    parts.append(c.cylinder(R + 0.5 * WAVE_DEPTH + 0.06, WALL_TOP - 0.10, WALL_TOP, steps=AROUND // 2, capped=False))
    # top collar ring and spout (Ø400) up to +21.422
    parts.append(c.cylinder(COLLAR_R + 0.04, peak_z - 0.05, peak_z + 0.25, steps=64, capped=False))
    parts.append(c.cylinder(SPOUT_R, peak_z + 0.25, SPOUT_TOP, steps=32))
    parts.append(c.cylinder(SPOUT_R + 0.05, SPOUT_TOP - 0.02, SPOUT_TOP, steps=32))
    return c.merge_parts(parts)


def build_foundation():
    parts = [c.cylinder(FOUND_R, -FOUND_H, 0.0, steps=256)]
    return c.merge_parts(parts)


def build_anchors():
    """Anchor chair at the foot of every stiffener: two gusset plates, top plate, nut."""
    parts = []
    base_r = R + 0.5 * WAVE_DEPTH + SHEET_T_BOTTOM
    for ang in stiffener_angles():
        for s in (-0.05, 0.05):
            v, f = c.box((0.0, s - 0.004, 0.0), (0.16, s + 0.004, 0.22))
            parts.append((c.transform(v + np.array([base_r, 0, 0]), rot_z=0) , f))
            parts[-1] = (c.transform(parts[-1][0], rot_z=ang), f)
        v, f = c.box((0.0, -0.06, 0.20), (0.17, 0.06, 0.215))
        parts.append((c.transform(v + np.array([base_r, 0, 0]), rot_z=ang), f))
        v, f = c.cylinder(0.014, 0.215, 0.26, steps=6, center=(base_r + 0.11, 0.0))
        parts.append((c.transform(v, rot_z=ang), f))
    return c.merge_parts(parts)


def build_door():
    """Ground-level access door 700 x 1100 with bolted frame (EST)."""
    ang = math.radians(DOOR_ANGLE)
    r = R + 0.5 * WAVE_DEPTH + SHEET_T_BOTTOM
    frame = []
    w, h, z0 = 0.70, 1.10, 0.35
    for p0, p1 in (((0, -w / 2 - 0.06, z0 - 0.06), (0.04, w / 2 + 0.06, z0)),
                   ((0, -w / 2 - 0.06, z0 + h), (0.04, w / 2 + 0.06, z0 + h + 0.06)),
                   ((0, -w / 2 - 0.06, z0), (0.04, -w / 2, z0 + h)),
                   ((0, w / 2, z0), (0.04, w / 2 + 0.06, z0 + h))):
        v, f = c.box(p0, p1)
        frame.append((c.transform(v + np.array([r, 0, 0]), rot_z=ang), f))
    v, f = c.box((0.005, -w / 2, z0), (0.025, w / 2, z0 + h))
    panel = (c.transform(v + np.array([r, 0, 0]), rot_z=ang), f)
    handles = []
    for dz in (0.35, 0.75):
        v, f = c.box((0.025, w / 2 - 0.12, z0 + dz), (0.07, w / 2 - 0.08, z0 + dz + 0.03))
        handles.append((c.transform(v + np.array([r, 0, 0]), rot_z=ang), f))
    return c.merge_parts(frame), c.merge_parts([panel] + handles)


def _tube_between(p0, p1, radius, steps=8):
    """Round bar from p0 to p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    length = np.linalg.norm(d)
    d /= length
    side = np.cross(d, [0, 0, 1.0])
    if np.linalg.norm(side) < 1e-6:
        side = np.cross(d, [1.0, 0, 0])
    side /= np.linalg.norm(side)
    up = np.cross(side, d)
    a = np.linspace(0, 2 * math.pi, steps, endpoint=False)
    ring = radius * (np.cos(a)[:, None] * side[None, :] + np.sin(a)[:, None] * up[None, :])
    v = np.concatenate([p0 + ring, p1 + ring])
    return v, c.grid_faces(2, steps, wrap_cols=True)


def build_ladder():
    """Caged ladder from grade to the eave, then a roof ladder with handrail to the collar.

    STD ISO 14122-4: rung pitch 300 mm, clear width 400-600 mm, cage from 2.2 m, hoops <= 1.5 m, 5 bars.
    """
    ang = math.radians(LADDER_ANGLE)
    wall_r = R + 0.5 * WAVE_DEPTH + SHEET_T_BOTTOM + OMEGA[2][0] + 0.12   # clear of stiffeners
    stand = 0.20                        # EST: ladder axis from wall face
    half_w = 0.25                       # STD: 500 mm between stiles
    parts = []
    top_z = WALL_TOP + 1.1

    def w(r_off, s, z):
        r = wall_r + stand + r_off
        return (r * math.cos(ang) - s * math.sin(ang), r * math.sin(ang) + s * math.cos(ang), z)

    for s in (-half_w, half_w):
        v, f = c.box((-0.005, s - 0.03, -FOUND_H), (0.005, s + 0.03, top_z))
        v = c.transform(v + np.array([wall_r + stand, 0, 0]), rot_z=ang)
        parts.append((v, f))
    for z in np.arange(0.30, top_z - 0.2, 0.30):
        parts.append(_tube_between(w(0, -half_w, z), w(0, half_w, z), 0.011, 6))
    # cage: hoops every 0.9 m from 2.2 m, 5 vertical flat bars
    cage_r = 0.36
    for z in np.arange(2.2, top_z + 0.01, 0.9):
        hoop_a = np.linspace(-math.pi / 2 - 0.2, math.pi / 2 + 0.2, 13)
        pts = [w(0.02 + cage_r + cage_r * math.cos(t), cage_r * math.sin(t) * 1.0, z) for t in hoop_a]
        for p0, p1 in zip(pts, pts[1:]):
            parts.append(_tube_between(p0, p1, 0.01, 4))
    for t in np.linspace(-math.pi / 2, math.pi / 2, 5):
        parts.append(_tube_between(w(0.02 + cage_r + cage_r * math.cos(t), cage_r * math.sin(t), 2.2),
                                   w(0.02 + cage_r + cage_r * math.cos(t), cage_r * math.sin(t), top_z),
                                   0.009, 4))
    # roof ladder: from eave up the 30 deg slope to the collar, stiles + rungs + one handrail
    r_start = R + EAVE_OVERHANG
    r_end = COLLAR_R + 0.5
    for s in (-0.22, 0.22):
        p0 = (r_start * math.cos(ang) - s * math.sin(ang), r_start * math.sin(ang) + s * math.cos(ang),
              WALL_TOP + 0.08)
        p1 = (r_end * math.cos(ang) - s * math.sin(ang), r_end * math.sin(ang) + s * math.cos(ang),
              WALL_TOP + (R - r_end) * math.tan(ROOF_SLOPE) + 0.08)
        parts.append(_tube_between(p0, p1, 0.02, 6))
        # handrail 1.0 m above the stiles
        parts.append(_tube_between((p0[0], p0[1], p0[2] + 1.0), (p1[0], p1[1], p1[2] + 1.0), 0.021, 8))
        for rr in np.linspace(r_start - 0.2, r_end + 0.2, 7):
            zb = WALL_TOP + (R - rr) * math.tan(ROOF_SLOPE) + 0.08
            px = (rr * math.cos(ang) - s * math.sin(ang), rr * math.sin(ang) + s * math.cos(ang))
            parts.append(_tube_between((px[0], px[1], zb), (px[0], px[1], zb + 1.0), 0.018, 6))
    n_steps = int((r_start - r_end) / 0.3)
    for k in range(n_steps + 1):
        rr = r_start - k * (r_start - r_end) / n_steps
        zb = WALL_TOP + (R - rr) * math.tan(ROOF_SLOPE) + 0.1
        a0 = (rr * math.cos(ang) + 0.22 * math.sin(ang), rr * math.sin(ang) - 0.22 * math.cos(ang), zb)
        a1 = (rr * math.cos(ang) - 0.22 * math.sin(ang), rr * math.sin(ang) + 0.22 * math.cos(ang), zb)
        parts.append(_tube_between(a0, a1, 0.012, 6))
    return c.merge_parts(parts)


def _cone_y(r0, r1, y0, y1, x, z, steps=32):
    """Open truncated cone along +Y (inlet bell), no caps."""
    a = np.linspace(0, 2 * math.pi, steps, endpoint=False)
    v = np.concatenate([np.column_stack([x + r0 * np.cos(a), np.full(steps, y0), z + r0 * np.sin(a)]),
                        np.column_stack([x + r1 * np.cos(a), np.full(steps, y1), z + r1 * np.sin(a)])])
    return v, c.grid_faces(2, steps, wrap_cols=True)


def _disc_y(radius_fn, y0, y1, x, z, steps=48):
    """Closed prism along +Y whose outline is radius_fn(angle) around (x, z)."""
    a = np.linspace(0, 2 * math.pi, steps, endpoint=False)
    r = radius_fn(a)
    ring = np.column_stack([x + r * np.cos(a), np.zeros(steps), z + r * np.sin(a)])
    v = np.concatenate([ring + [0, y0, 0], ring + [0, y1, 0]])
    f = [c.grid_faces(2, steps, wrap_cols=True), np.arange(steps)[::-1][None, :],
         np.arange(steps, 2 * steps)[None, :]]
    return v, f


def build_fans():
    """Centrifugal aeration fan, 11 kW (catalogue), on its own slab at grade.

    Local Z = 0 is the silo floor (+0.600). Grade is -FOUND_H. Sizes EST for an 11 kW
    medium-pressure fan: impeller housing Ø1.25 m scroll, width 0.5 m, outlet 0.45 x 0.5 m.
    """
    housings, motors, ducts, pads, dark = [], [], [], [], []
    wall = R + 0.5 * WAVE_DEPTH + SHEET_T_BOTTOM
    grade = -FOUND_H
    for deg in FAN_ANGLES:
        ang = math.radians(deg)
        cx = wall + 2.2
        cz = grade + 0.95
        scroll = lambda a: 0.48 + 0.14 * ((a - 1.2) % (2 * math.pi)) / (2 * math.pi)  # noqa: E731
        v, f = _disc_y(scroll, -0.25, 0.25, cx, cz)
        housings.append((c.transform(v, rot_z=ang), f))
        for y0, y1 in ((-0.27, -0.25), (0.25, 0.27)):                                # side flanges
            v, f = _disc_y(lambda a: scroll(a) + 0.03, y0, y1, cx, cz)
            dark.append((c.transform(v, rot_z=ang), f))
        # outlet duct: horizontal, from the top of the scroll to the wall
        v, f = c.box((wall + 0.03, -0.25, cz + 0.10), (cx, 0.25, cz + 0.60))
        ducts.append((c.transform(v, rot_z=ang), f))
        # transition into the wall: flange plate and a short transition piece
        v, f = c.box((wall - 0.005, -0.34, 0.02), (wall + 0.03, 0.34, cz + 0.70))
        ducts.append((c.transform(v, rot_z=ang), f))
        # inlet bell and guard ring
        v, f = _cone_y(0.30, 0.36, 0.27, 0.46, cx, cz)
        housings.append((c.transform(v, rot_z=ang), f))
        v, f = _disc_y(lambda a: np.full_like(a, 0.37), 0.46, 0.48, cx, cz, steps=32)
        dark.append((c.transform(v, rot_z=ang), f))
        # motor: body, fins ring, fan cover, feet
        v, f = _disc_y(lambda a: np.full_like(a, 0.19), -0.95, -0.32, cx, cz, steps=24)
        motors.append((c.transform(v, rot_z=ang), f))
        v, f = _disc_y(lambda a: np.full_like(a, 0.205), -0.90, -0.40, cx, cz, steps=12)
        motors.append((c.transform(v, rot_z=ang), f))
        v, f = _disc_y(lambda a: np.full_like(a, 0.13), -1.05, -0.95, cx, cz, steps=24)
        dark.append((c.transform(v, rot_z=ang), f))
        v, f = c.box((cx - 0.17, -0.90, grade + 0.30), (cx + 0.17, -0.40, cz - 0.17))
        dark.append((c.transform(v, rot_z=ang), f))
        # base frame (channel) and pedestal under the scroll
        for y0, y1 in ((-1.05, -0.97), (0.30, 0.38)):
            v, f = c.box((cx - 0.75, y0, grade + 0.15), (cx + 0.65, y1, grade + 0.30))
            dark.append((c.transform(v, rot_z=ang), f))
        v, f = c.box((cx - 0.40, -0.25, grade + 0.30), (cx + 0.40, 0.25, cz - 0.45))
        housings.append((c.transform(v, rot_z=ang), f))
        # slab
        v, f = c.box((cx - 1.0, -1.35, grade), (cx + 0.95, 0.70, grade + 0.15))
        pads.append((c.transform(v, rot_z=ang), f))
    return (c.merge_parts(housings), c.merge_parts(motors), c.merge_parts(ducts),
            c.merge_parts(pads), c.merge_parts(dark))


def build_roof_vents():
    """Two gravity vents with hoods half-way up the roof (EST)."""
    parts = []
    for deg in (0.0, 180.0):
        ang = math.radians(deg)
        rr = 5.5
        zb = WALL_TOP + (R - rr) * math.tan(ROOF_SLOPE)
        v, f = c.box((-0.35, -0.30, zb - 0.1), (0.35, 0.30, zb + 0.45))
        parts.append((c.transform(v + [rr, 0, 0], rot_z=ang), f))
        v, f = c.box((-0.45, -0.40, zb + 0.45), (0.45, 0.40, zb + 0.52))
        parts.append((c.transform(v + [rr, 0, 0], rot_z=ang), f))
    return c.merge_parts(parts)


# ================================================================== assembly

def build(collection=None, materials=None, cut=None):
    """Build the silo into `collection`. Returns (objects, measure)."""
    m = materials or {
        "galv": c.mat_galvanized("SILO_GALV", age=0.30),
        "galv_old": c.mat_galvanized("SILO_GALV_ROOF", age=0.45, spangle_scale=60.0),
        "concrete": c.mat_concrete("SILO_FOUNDATION"),
        "paint_motor": c.mat_painted("FAN_MOTOR", (0.08, 0.22, 0.42), 0.4),
        "paint_yellow": c.mat_painted("SAFETY_YELLOW", (0.85, 0.62, 0.05), 0.45),
        "dark": c.mat_painted("DARK_STEEL", (0.12, 0.12, 0.12), 0.5),
        "fan_paint": c.mat_painted("FAN_HOUSING", (0.42, 0.45, 0.46), 0.35, grime=0.35),
    }
    objs = {}

    def mk(name, v, f, *args, **kw):
        if cut is not None:
            v, f = c.cut_mesh(v, f, cut)
            if not f:
                return None
        return c.mesh_from_arrays(name, v, f, *args, **kw)

    v, f = build_wall()
    objs["wall"] = mk("SILO_WALL", v, f, m["galv"], smooth=True, collection=collection)
    v, f = build_stiffeners()
    objs["stiffeners"] = mk("SILO_STIFFENERS", v, f, m["galv"], collection=collection)
    th, zz, rr = bolt_positions()
    v, f = hex_heads(th, zz, rr)
    objs["bolts"] = mk("SILO_BOLTS", v, f, m["galv_old"], collection=collection)
    (v, f), peak_z = build_roof()
    objs["roof"] = mk("SILO_ROOF", v, f, m["galv_old"], smooth=True, collection=collection)
    v, f = build_eave_and_collar(peak_z)
    objs["collar"] = mk("SILO_EAVE_COLLAR", v, f, m["galv"], smooth="quads", collection=collection)
    v, f = build_foundation()
    objs["foundation"] = mk("SILO_FOUNDATION", v, f, m["concrete"], collection=collection)
    v, f = build_anchors()
    objs["anchors"] = mk("SILO_ANCHORS", v, f, m["galv_old"], collection=collection)
    (vf, ff), (vp, fp) = build_door()
    objs["door_frame"] = mk("SILO_DOOR_FRAME", vf, ff, m["galv"], collection=collection)
    objs["door"] = mk("SILO_DOOR", vp, fp, m["galv_old"], collection=collection)
    v, f = build_ladder()
    objs["ladder"] = mk("SILO_LADDER", v, f, m["galv_old"], smooth="quads", collection=collection)
    (vh, fh), (vm, fm), (vd, fd), (vpad, fpad), (vk, fk) = build_fans()
    objs["fan_dark"] = mk("SILO_FAN_FRAME", vk, fk, m["dark"], smooth="quads", collection=collection)
    objs["fan_housing"] = mk("SILO_FAN_HOUSING", vh, fh, m["fan_paint"], smooth="quads", collection=collection)
    objs["fan_motor"] = mk("SILO_FAN_MOTOR", vm, fm, m["paint_motor"], smooth="quads", collection=collection)
    objs["fan_duct"] = mk("SILO_FAN_DUCT", vd, fd, m["galv"], collection=collection)
    objs["fan_pad"] = mk("SILO_FAN_PAD", vpad, fpad, m["concrete"], collection=collection)
    v, f = build_roof_vents()
    objs["vents"] = mk("SILO_ROOF_VENTS", v, f, m["galv"], collection=collection)

    measure = {
        "outer_radius_m": R,
        "rings": RINGS,
        "ring_height_m": RING_H,
        "wall_top_z_m": round(WALL_TOP, 4),
        "waves_per_ring": int(round(RING_H / WAVE_PITCH)),
        "wave_pitch_m": WAVE_PITCH,
        "wave_depth_m_EST": WAVE_DEPTH,
        "sheet_thickness_mm": [round(sheet_thickness(k) * 1000, 2) for k in range(RINGS)],
        "stiffeners": STIFFENERS,
        "roof_slope_deg": 30.0,
        "roof_peak_z_m": round(peak_z, 4),
        "spout_top_z_m": SPOUT_TOP,
        "bolts": int(len(th)),
        "aeration_fans": AERATION_FANS,
        "vertices_total": int(sum(len(o.data.vertices) for o in objs.values() if o is not None)),
    }
    return objs, measure
