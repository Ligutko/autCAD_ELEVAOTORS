"""K5. Silo МСВУ 220 interior: aeration floor, discharge gates, sweep auger, temperature
cables, roof rafters, level sensors, roof hatch and ladder, grain heap, light shaft.

Local frame as silo_msvu220.py: axis at (0, 0), Z = 0 on the floor (site +0.600).
Tunnel and gates run along X (PDF p.2, p.6). Source tags as in silo_msvu220.py plus
`research` = research/PARTS_DIMENSIONS.md.
"""

import math

import numpy as np

from . import common as c
from . import silo_msvu220 as silo
from . import steel as st

R_IN = silo.R - 0.5 * silo.WAVE_DEPTH - silo.SHEET_T_BOTTOM      # inner face of the wall

# ------------------------------------------------------------------ aeration floor (PDF p.2 vectors, SITE.json silo_aeration)
AER = silo.aeration()
CHANNEL_W = AER["channel_w"]       # PDF p.2: 0.28 m (research analog Symaga SBH 505 mm is superseded by the drawing)
FAN_ANGLES = silo.FAN_ANGLES       # each collector runs from its fan towards the silo axis
MIN_BRANCH = 0.85                  # PDF p.2: the shortest drawn branch is 1.05 m, a 0.645 m piece at the tunnel is left out

# ------------------------------------------------------------------ gates (PDF p.2, p.6, p.7; research/tunnel_k4.md)
# openings are symmetric at 3250 on all three sheets; the "2750" chain on p.6 misses the openings
GATE_STEP = 3.25
GATE_OFFSETS = [k * GATE_STEP for k in range(-3, 4)]
GATE_SIZES = [0.35, 0.35, 0.35, 0.40, 0.35, 0.35, 0.35]

# ------------------------------------------------------------------ silo equipment (SITE.json silo_equipment, phase 2)
EQ = silo.equipment()
SWEEP = EQ["sweep"]

# ------------------------------------------------------------------ temperature cables (research/silo_equipment.md)
CABLE_R = 0.006                    # research: Ø10.8-13 mm
SENSOR_STEP = EQ["thermo"]["sensor_step_m"]   # sourced Лубнимаш: sensors every 2 m

# ------------------------------------------------------------------ sweep auger (research/silo_equipment.md)
SWEEP_ANGLE = SWEEP["park_angle_deg"]   # judgment: parked position
SWEEP_R = SWEEP["screw_d_m"] / 2        # LUB fork УРПК-315 / 400.М2: Ø315
SWEEP_LEN = SWEEP["length_m"]           # judgment: centre to wall clearance

# ------------------------------------------------------------------ roof structure (EST)
RAFTERS = 40                       # every second roof rib carries a rafter
RAFTER_HALF = 0.03                 # channel 160 x 60: half the flange width
PURLIN_R = [3.0, 6.0, 9.0]
REPOSE = math.radians(27.0)        # STD: wheat angle of repose 25-28 deg


def roof_underside_z(r):
    return silo.WALL_TOP + (silo.R - r) * math.tan(silo.ROOF_SLOPE) - silo.ROOF_T - 0.01


# ================================================================== floor

def _branch_pieces(u, s):
    """Branch across the collector ray u at distance s from the axis, clipped like PDF p.2:
    the outer corner of the channel rectangle on corner_r (about 0.5 m from the wall), the centreline
    end at |x| = axis_x (vertical centreline) and at the tunnel band y (north / south).
    Two pieces, one each side of the collector."""
    lim = AER["limits"]
    w = np.array([-u[1], u[0]])
    p = u * s
    reach = math.sqrt(max(lim["corner_r"] ** 2 - (s + CHANNEL_W / 2) ** 2, 0.0))
    lo, hi = -reach, reach
    sx, north = math.copysign(1.0, u[0]), u[1] > 0
    for k, bound, sign in ((0, sx * lim["axis_x"], sx), (1, lim["tunnel_y"]["n" if north else "s"], 1.0 if north else -1.0)):
        if abs(w[k]) < 1e-9:
            continue
        lam = (bound - p[k]) / w[k]                       # sign * (p[k] + lam * w[k]) >= sign * bound
        if sign * w[k] > 0:
            lo = max(lo, lam)
        else:
            hi = min(hi, lam)
    half = CHANNEL_W / 2
    pieces = []
    for a0, a1 in ((lo, -half), (half, hi)):
        if a1 - a0 >= MIN_BRANCH:
            pieces.append((p + w * a0, p + w * a1))
    return pieces


def channel_layout():
    """Aeration channels as (kind, a, b) plan segments, silo frame: per fan a collector from r0 to r1
    along the fan direction and branches square to it at branch_s (PDF p.2 vectors)."""
    segs = []
    for deg in FAN_ANGLES:
        u = np.array([math.cos(math.radians(deg)), math.sin(math.radians(deg))])
        h = "n" if u[1] > 0 else "s"
        segs.append(("collector", u * AER["collector_r0"][h], u * AER["collector_r1"]))
        for s in AER["branch_s"]:
            for a, b in _branch_pieces(u, s):
                segs.append(("branch", a, b))
    return segs


def build_floor(segs):
    """Perforated channel covers flush with the floor, with angle edge frames."""
    covers, frames = [], []
    for _, a, b in segs:
        a3 = np.array([a[0], a[1], 0.006])
        b3 = np.array([b[0], b[1], 0.006])
        covers.append(st.member(a3, b3, np.array([(-CHANNEL_W / 2, -0.003), (CHANNEL_W / 2, -0.003),
                                                  (CHANNEL_W / 2, 0.003), (-CHANNEL_W / 2, 0.003)])))
        for side in (-1, 1):
            off = np.array([0, 0, 0.0])
            d = (b3 - a3) / np.linalg.norm(b3 - a3)
            n = np.array([-d[1], d[0], 0.0]) * side * (CHANNEL_W / 2 + 0.02)
            frames.append(st.member(a3 + n + off, b3 + n + off, np.array([(-0.02, -0.004), (0.02, -0.004),
                                                                          (0.02, 0.006), (-0.02, 0.006)])))
    slab = c.cylinder(R_IN - 0.005, -0.05, 0.001, steps=256)
    return c.merge_parts(covers), c.merge_parts(frames), slab


def build_gates():
    """Discharge openings over the tunnel: dark well, gate frame, grating on top."""
    wells, frames, gratings = [], [], []
    for x, size in zip(GATE_OFFSETS, GATE_SIZES):
        h = size / 2
        wells.append(c.box((x - h, -h, 0.0015), (x + h, h, 0.003)))                  # dark opening under grating
        for p0, p1 in (((x - h - 0.06, -h - 0.06, -0.01), (x + h + 0.06, -h, 0.02)),
                       ((x - h - 0.06, h, -0.01), (x + h + 0.06, h + 0.06, 0.02)),
                       ((x - h - 0.06, -h, -0.01), (x - h, h, 0.02)),
                       ((x + h, -h, -0.01), (x + h + 0.06, h, 0.02))):
            frames.append(c.box(p0, p1))
        gratings.append(c.box((x - h, -h, 0.004), (x + h, h, 0.016)))
    return c.merge_parts(wells), c.merge_parts(frames), c.merge_parts(gratings)


# ================================================================== sweep auger

def sweep_height_at(r):
    """Top of the sweep envelope at radius r from the axis: it turns through every angle, so
    thermometry cables must clear this height everywhere on their ring. Centre drive housing over
    the gate (SITE `sweep.drive`), tractor with its own motor near `tractor.at_frac` of the arm
    (SITE render, sourced), tube + flight + back shield along the rest (SITE `sweep.shield_h_m`)."""
    drive, tractor = SWEEP["drive"], SWEEP["tractor"]
    if r <= drive["w_m"] / 2:
        return drive["h_m"]
    t_at = tractor["at_frac"] * SWEEP_LEN
    if abs(r - t_at) <= 0.5:
        return max(SWEEP["shield_h_m"], tractor["wheel_d_m"]) + 0.30    # judgment: motor sits above the wheel
    return SWEEP["shield_h_m"] + 0.02


# ---- sweep centre drive and tractor on real parts (C7a). Everything not in SITE `sweep` is EST (research/silo_equipment.md §3).
# Centre drive: a stationary vertical stack on the rotation axis inside the housing: IEC motor (shaft down) -> coupling ->
# helical reducer -> coupling -> bevel box on the slewing ring (turns with the arm) -> shaft along the arm to the auger tube.
# Tractor: wheel behind the back shield (axle along the arm, the wheel rolls round the silo), cheek plates on a bracket plate
# bolted to the shield, worm reducer on the axle, IEC motor on a shelf, counterweight plates outside a cheek plate.
DRIVE_BASE_Z = 0.03          # EST: base plate on the gate frame (frame top 0.02)
DRIVE_SKIRT_Z = 0.40         # EST: cover panels start above the turning hub
DRIVE_POST = 0.060           # EST: SHS 60 corner posts
DRIVE_PANEL_T = 0.003        # EST: sheet
DRIVE_MOTOR_Z = 0.95         # EST: motor drive-end shoulder, coupling under it
TRACTOR_N = -0.42            # EST: wheel centre behind the shield (shield back face at -0.19)
TRACTOR_WHEEL_W = 0.10       # EST: tyre width along the arm
TRACTOR_LUGS = 24            # EST: tread blocks round the tyre
TRACTOR_GAP = 0.0005         # parts that bear on each other keep 0.5 mm, so BVH does not read contact
SWEEP_PART_KEYS = ("arm", "flight", "mid_wheel", "drive_frame", "drive_cover", "drive_hub", "drive_gear", "drive_motor",
                   "drive_bracket", "tractor_wheel", "tractor_frame", "tractor_motor", "tractor_shelf", "tractor_weights")


def _sw_axes():
    ang = math.radians(SWEEP_ANGLE)
    d = np.array([math.cos(ang), math.sin(ang), 0.0])
    return d, np.array([-d[1], d[0], 0.0])


def _wall_axis(d):
    """Axis-aligned wall of the drive housing nearest to the direction away from the arm: (sx, sy)."""
    cands = ((1, 0), (-1, 0), (0, 1), (0, -1))
    return max(cands, key=lambda s: -(s[0] * d[0] + s[1] * d[1]))


def _iec(kw, detail):
    from . import components as comp
    return comp.iec_motor(kw, detail=detail)


def _rect(u, v):
    """Profile rectangle u0..u1 x v0..v1 for st.member."""
    return np.array([(u[0], v[0]), (u[1], v[0]), (u[1], v[1]), (u[0], v[1])])


def build_sweep_parts(detail="lod", faults=None):
    """The sweep as named (verts, faces) parts (SWEEP_PART_KEYS, plus the per-part motor dicts), silo frame, parked at
    SWEEP_ANGLE. The auger tube, flight, back shield and the intermediate wheel are the original geometry (they define
    sweep_height_at); the centre drive and the tractor are real parts. `faults` inject the check's broken cases:
    drive_motor_dx (m), drive_motor_kw, tractor_motor_dz (m), tractor_n (m), wheel_scale, counterweights (int)."""
    faults = faults or {}
    d, n = _sw_axes()
    up = np.array([0.0, 0.0, 1.0])
    z = SWEEP_R + SWEEP["floor_gap_m"]
    out = {}
    lod = detail == "lod"
    # ------------------------------------------------ auger arm (original geometry)
    arm, flight, rubber = [], [], []
    arm.append(st.rod(d * 0.5 + [0, 0, z], d * SWEEP_LEN + [0, 0, z], 0.06, 20))
    turns = int((SWEEP_LEN - 0.6) / (2 * SWEEP_R))
    k = 24
    tt = np.linspace(0, turns * 2 * math.pi, turns * k)
    s = 0.6 + (tt / (2 * math.pi)) * 2 * SWEEP_R
    rows = []
    for rr in (0.06, SWEEP_R):
        rows.append(d[None, :] * s[:, None] + n[None, :] * (rr * np.cos(tt))[:, None] + up[None, :] * (z + rr * np.sin(tt))[:, None])
    v = np.concatenate([rows[0], rows[1], rows[0] + d * 0.006, rows[1] + d * 0.006])
    m = len(tt)
    faces = []
    for i in range(m - 1):
        for a0, a1 in ((0, m), (2 * m, 3 * m), (0, 2 * m), (m, 3 * m)):
            faces.append((a0 + i, a0 + i + 1, a1 + i + 1, a1 + i))
    flight.append((v, np.array(faces)))
    shield_h = SWEEP["shield_h_m"]
    arm.append(st.member(d * 0.6 - n * (SWEEP_R + 0.03) + [0, 0, 0.02], d * SWEEP_LEN - n * (SWEEP_R + 0.03) + [0, 0, 0.02],
                         np.array([(-0.003, 0.0), (0.003, 0.0), (0.003, shield_h), (-0.003, shield_h)])))
    p_mid = d * (SWEEP_LEN * 0.4)
    rr_mid = 0.18
    rubber.append(st.rod(p_mid - n * 0.07 + [0, 0, rr_mid], p_mid + n * 0.07 + [0, 0, rr_mid], rr_mid, 32))
    arm.append(c.box(tuple(p_mid - n * 0.12 + [-0.05, 0, rr_mid]), tuple(p_mid + n * 0.12 + [0.05, 0, rr_mid + 0.20])))
    out["arm"] = c.merge_parts(arm)
    out["flight"] = c.merge_parts(flight)
    out["mid_wheel"] = c.merge_parts(rubber)

    # ------------------------------------------------ centre drive: housing
    drive = SWEEP["drive"]
    hw, hh = drive["w_m"] / 2, drive["h_m"]
    kw = float(faults.get("drive_motor_kw", drive["kw"]))
    b = DRIVE_POST / 2
    t = DRIVE_PANEL_T
    frame, cover = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            frame.append(c.box((sx * (hw - b) - b, sy * (hw - b) - b, 0.0), (sx * (hw - b) + b, sy * (hw - b) + b, hh - 0.06)))
    for z0, z1 in ((0.0, 0.08), (hh - 0.14, hh - 0.06)):                  # base ring and top frame between the posts
        for p0_, p1_ in (((-hw, -hw, z0), (hw, -hw + 0.012, z1)), ((-hw, hw - 0.012, z0), (hw, hw, z1)),
                         ((-hw, -hw, z0), (-hw + 0.012, hw, z1)), ((hw - 0.012, -hw, z0), (hw, hw, z1))):
            frame.append(c.box(p0_, p1_))
    frame.append(c.box((-0.31, -0.31, DRIVE_BASE_Z - 0.01), (0.31, 0.31, DRIVE_BASE_Z)))   # base plate under the slewing ring
    pz0, pz1 = DRIVE_SKIRT_Z, hh - 0.14
    wall_s = _wall_axis(d)

    def wall_box(sx, sy, z0, z1):
        """Panel of sheet t on the wall (sx, sy) between the posts."""
        lo, hi = -hw + 2 * b, hw - 2 * b
        if sx:
            x0, x1 = (sx * hw - t, sx * hw) if sx > 0 else (sx * hw, sx * hw + t)
            return c.box((x0, lo, z0), (x1, hi, z1))
        y0, y1 = (sy * hw - t, sy * hw) if sy > 0 else (sy * hw, sy * hw + t)
        return c.box((lo, y0, z0), (hi, y1, z1))

    for sx, sy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        if (sx, sy) == wall_s:                                            # louvre panel for the motor, slats with gaps
            span = pz1 - pz0 - 0.08
            for k_ in range(9):
                cover.append(wall_box(sx, sy, pz0 + 0.04 + k_ * span / 9, pz0 + 0.04 + k_ * span / 9 + 0.07))
        else:
            cover.append(wall_box(sx, sy, pz0, pz1))
    for k_ in (0, 1):                                                     # two removable lids with a handle and bolt rows
        y0 = -hw + 0.02 + k_ * (hw - 0.01)
        y1 = y0 + hw - 0.03
        cover.append(c.box((-hw + 0.02, y0, hh - 0.06), (hw - 0.02, y1, hh - 0.056)))
        ym = (y0 + y1) / 2
        cover.append(c.box((-0.12, ym - 0.012, hh - 0.056), (0.12, ym + 0.012, hh - 0.04)))
        for bx in np.linspace(-hw + 0.06, hw - 0.06, 5):
            for by in (y0 + 0.02, y1 - 0.02):
                cover.append(st.rod((bx, by, hh - 0.056), (bx, by, hh - 0.050), 0.007, 6))
    out["drive_frame"] = c.merge_parts(frame)
    out["drive_cover"] = c.merge_parts(cover)

    # ------------------------------------------------ centre drive: slewing ring + bevel box (turn with the arm)
    zb0, zb1 = 0.08, 0.34
    hub = [st.rod((0, 0, DRIVE_BASE_Z), (0, 0, zb0), 0.30, 40 if not lod else 20),
           st.member(np.array([0, 0, zb0]), np.array([0, 0, zb1]), _rect((-0.17, 0.17), (-0.17, 0.17)), up=tuple(d)),
           st.rod(d * 0.17 + [0, 0, z], d * 0.50 + [0, 0, z], 0.04, 16),
           st.rod(d * 0.46 + [0, 0, z], d * 0.50 + [0, 0, z], 0.09, 20)]
    out["drive_hub"] = c.merge_parts(hub)
    # ------------------------------------------------ centre drive: helical reducer on the axis, couplings, feet on a cross frame
    gear = [st.rod((0, 0, 0.42), (0, 0, 0.76), 0.15, 32 if not lod else 16),
            c.box((-0.17, -0.17, 0.76), (0.17, 0.17, 0.78)),
            st.rod((0, 0, zb1), (0, 0, 0.42), 0.035, 12),                 # output shaft down to the bevel box
            st.rod((0, 0, 0.35), (0, 0, 0.405), 0.060, 16),               # lower coupling
            st.rod((0, 0, 0.78), (0, 0, 0.83), 0.024, 12),                # input shaft up
            st.rod((0, 0, 0.80), (0, 0, DRIVE_MOTOR_Z - 0.02), 0.055, 16)]   # upper coupling under the motor shoulder
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        gear.append(st.member(np.array([sx * 0.12, sy * 0.12, 0.41]), np.array([sx * (hw - 2 * b), sy * (hw - 2 * b), 0.41]),
                              _rect((-0.02, 0.02), (-0.01, 0.01))))
    out["drive_gear"] = c.merge_parts(gear)

    # ------------------------------------------------ centre drive: motor, shaft down, feet toward the wall behind the arm
    item = _iec(kw, detail)
    mp = item["parts"]
    H = float(item["dims"]["H"])
    shoulder = float(np.asarray(mp["endshield_de"][0])[:, 0].max())
    e = np.array([wall_s[0], wall_s[1], 0.0], float)
    s_ = np.array([-e[1], e[0], 0.0])
    mdx = float(faults.get("drive_motor_dx", 0.0))

    def m_fn(v):
        x, y, zl = v[:, 0] - shoulder, v[:, 1], v[:, 2] - H
        # motor shaft +X -> world -Z; lateral y -> s_; crown (z - H) -> -e (feet toward +e)
        pos = y[:, None] * s_[None, :] - zl[:, None] * e[None, :]
        return np.column_stack([pos[:, 0] + mdx, pos[:, 1], DRIVE_MOTOR_Z - x])

    motor = {k_: (m_fn(np.asarray(p[0], float).reshape(-1, 3)), p[1]) for k_, p in mp.items()}
    out["drive_motor"] = c.merge_parts(list(motor.values()))
    out["drive_motor_parts"] = motor
    fv = np.asarray(motor["feet"][0], float)
    t_pl = 0.012
    off = H + TRACTOR_GAP
    q0, q1 = float(fv[:, 2].min()) - 0.02, float(fv[:, 2].max()) + 0.02
    half_w = float(np.ptp(fv @ s_)) / 2.0 + 0.02
    br = [st.member(e * off + [0, 0, q0], e * off + [0, 0, q1], _rect((-half_w, half_w), (0.0, t_pl)), up=tuple(e))]
    wall_in = hw - t - 0.002
    for zr in (q0 + 0.05, q1 - 0.05):
        br.append(st.member(e * (wall_in - 0.012) - s_ * (hw - 2 * b) + [0, 0, zr], e * (wall_in - 0.012) + s_ * (hw - 2 * b) + [0, 0, zr],
                            _rect((-0.04, 0.04), (0.0, 0.012)), up=(0.0, 0.0, 1.0)))
        for sgn in (-1, 1):
            xs = s_ * sgn * (half_w - 0.03)
            br.append(st.member(e * (off + t_pl - 0.001) + xs + [0, 0, zr], e * (wall_in - 0.001) + xs + [0, 0, zr],
                                _rect((-0.012, 0.012), (-0.04, 0.04)), up=(0.0, 0.0, 1.0)))
    out["drive_bracket"] = c.merge_parts(br)

    # ------------------------------------------------ tractor
    tr = SWEEP["tractor"]
    p0 = d * (tr["at_frac"] * SWEEP_LEN)
    rw = tr["wheel_d_m"] / 2 * float(faults.get("wheel_scale", 1.0))
    n_c = float(faults.get("tractor_n", TRACTOR_N))
    c0 = p0 + n * n_c + [0, 0, rw]
    hwid = TRACTOR_WHEEL_W / 2
    n_lug = 12 if lod else TRACTOR_LUGS
    parts = [st.rod(c0 - d * hwid, c0 + d * hwid, rw - 0.013, 24 if lod else 48)]
    for k_ in range(n_lug):
        a = 2 * math.pi * k_ / n_lug
        rad = n * math.cos(a) + up * math.sin(a)
        parts.append(st.member(c0 + rad * (rw - 0.014), c0 + rad * rw, _rect((-0.014, 0.014), (-0.045, 0.045)), up=tuple(d)))
    out["tractor_wheel"] = c.merge_parts(parts)

    cw = 0.07 + TRACTOR_GAP                                               # cheek plates stand outside the tyre sides
    n_att = -(SWEEP_R + 0.03 + 0.003 + TRACTOR_GAP)                       # bracket plate on the back of the shield
    steel = [st.rod(c0 - d * 0.0655, c0 + d * 0.0655, 0.045, 16),         # hub between the cheeks
             st.rod(c0 - d * 0.055, c0 + d * 0.055, 0.12, 24),            # rim disc
             st.rod(c0 - d * 0.0755, c0 + d * 0.19, 0.025, 12)]           # axle through both cheeks to the reducer
    for sgn in (-1, 1):
        a0 = p0 + d * sgn * cw
        steel.append(st.member(a0 + n * (n_att - 0.009) + [0, 0, 0.05], a0 + n * (n_c - rw - 0.02) + [0, 0, 0.05],
                               _rect((-0.005, 0.005), (0.0, 0.45)), up=tuple(up)))
    steel.append(st.member(p0 + n * (n_att - 0.010) + [0, 0, 0.05], p0 + n * n_att + [0, 0, 0.05],
                           _rect((-0.14, 0.14), (0.0, 0.47)), up=tuple(up)))
    d_r = 0.19
    gear_c = p0 + d * d_r + n * n_c
    steel.append(st.member(gear_c + [0, 0, 0.08], gear_c + [0, 0, 0.40], _rect((-0.09, 0.09), (-0.08, 0.08)), up=tuple(d)))   # worm box
    steel.append(st.rod(gear_c - n * 0.12 + [0, 0, 0.32], gear_c - n * 0.09 + [0, 0, 0.32], 0.09, 20))                       # adapter ring
    out["tractor_frame"] = c.merge_parts(steel)

    mk = _iec(tr["kw"], detail)
    mH = float(mk["dims"]["H"])
    m_sh = float(np.asarray(mk["parts"]["endshield_de"][0])[:, 0].max())
    mdz = float(faults.get("tractor_motor_dz", 0.0))
    n_sh = n_c - 0.12
    gz = 0.32

    def t_fn(v):
        x, y, zl = v[:, 0] - m_sh, v[:, 1], v[:, 2]
        pos = gear_c[None, :] + n[None, :] * (n_sh - n_c + x)[:, None] - d[None, :] * y[:, None]
        pos[:, 2] = gz - mH + zl + mdz
        return pos

    tm = {k_: (t_fn(np.asarray(p[0], float).reshape(-1, 3)), p[1]) for k_, p in mk["parts"].items()}
    out["tractor_motor"] = c.merge_parts(list(tm.values()))
    out["tractor_motor_parts"] = tm
    sole = float(np.asarray(tm["feet"][0])[:, 2].min()) - mdz
    z_sh0 = sole - 0.012 - TRACTOR_GAP
    shelf = [st.member(gear_c + n * (n_sh - n_c - 0.32) + [0, 0, z_sh0], gear_c + n * (0.001 - 0.09) + [0, 0, z_sh0],
                       _rect((-0.10, 0.10), (0.0, 0.012)), up=tuple(up)),
             st.member(gear_c + n * (n_sh - n_c - 0.31) + [0, 0, 0.0], gear_c + n * (n_sh - n_c - 0.30) + [0, 0, 0.0],
                       _rect((-0.10, 0.10), (0.0, z_sh0 + 0.001)), up=tuple(up))]
    out["tractor_shelf"] = c.merge_parts(shelf)
    ncw = int(faults.get("counterweights", tr["counterweights"]))
    cws = []
    for k_ in range(ncw):
        a0 = p0 - d * (cw + 0.005 + TRACTOR_GAP + k_ * (0.050 + TRACTOR_GAP))
        cws.append(st.member(a0 + n * (n_c - 0.13) + [0, 0, 0.27], a0 + n * (n_c + 0.13) + [0, 0, 0.27],
                             _rect((-0.050, 0.0), (0.0, 0.22)), up=tuple(up)))
    out["tractor_weights"] = c.merge_parts(cws) if cws else None
    return out


def build_sweep():
    """(steel, flight, rubber) merged, as before; build() uses build_sweep_parts for materials."""
    p = build_sweep_parts()
    steel = [p[k] for k in ("arm", "drive_frame", "drive_cover", "drive_hub", "drive_gear", "drive_bracket", "drive_motor",
                            "tractor_frame", "tractor_motor", "tractor_shelf", "tractor_weights") if p.get(k) is not None]
    return c.merge_parts(steel), p["flight"], c.merge_parts([p["mid_wheel"], p["tractor_wheel"]])


# ================================================================== roof structure, cables, sensors

def rafter_angles():
    """Rafters under every second roof rib (degrees)."""
    return silo.rib_angles()[::silo.ROOF_RIBS // RAFTERS]


def build_roof_structure():
    rafters, rings = [], []
    for deg in rafter_angles():
        a = math.radians(deg)
        u = np.array([math.cos(a), math.sin(a), 0.0])
        r0, r1 = R_IN - 0.05, silo.COLLAR_R + 0.05
        p0 = u * r0 + [0, 0, roof_underside_z(r0) - 0.08]
        p1 = u * r1 + [0, 0, roof_underside_z(r1) - 0.08]
        rafters.append(st.member(p0, p1, st.channel(0.16, 0.06, 0.004, 0.006), up=(0, 0, 1)))
    for rr in PURLIN_R:
        n = 96
        z = roof_underside_z(rr) - 0.2
        a = np.linspace(0, 2 * math.pi, n + 1)
        for a0, a1 in zip(a, a[1:]):
            rings.append(st.member((rr * math.cos(a0), rr * math.sin(a0), z), (rr * math.cos(a1), rr * math.sin(a1), z),
                                   st.angle(0.063, 0.005)))
    z = roof_underside_z(silo.COLLAR_R) - 0.1
    rings.append(c.cylinder(silo.COLLAR_R + 0.08, z - 0.2, z, steps=48, capped=False))
    return c.merge_parts(rafters), c.merge_parts(rings)


def cable_positions(rings=None):
    """Thermometry cable rack positions (x, y, r): rings evenly spaced from `a0_deg`
    (SITE.json silo_equipment.thermo.rings, analog OPI 72 ft table)."""
    return [(x, y, r) for x, y, r, _ in silo.ring_positions(rings if rings is not None else EQ["thermo"]["rings"])]


def cable_ends(r):
    """Cable bottom hangs free above the sweep envelope at that radius (no floor tie: the sweep
    turns round the whole floor); top is shackled to the roof frame (SITE `thermo.bottom_above_sweep_m`)."""
    bottom = sweep_height_at(r) + EQ["thermo"]["bottom_above_sweep_m"]
    top = roof_underside_z(max(r, silo.COLLAR_R + 0.3)) - 0.25
    return bottom, top


def sensor_z(bottom, top, step=None):
    """Sensor capsule heights along one cable, spaced `step` apart down from just below the shackle."""
    step = SENSOR_STEP if step is None else step
    zs = []
    z = top - 1.0
    while z > bottom + 0.3:
        zs.append(z)
        z -= step
    return zs


def level_sensor_positions():
    """Level sensor positions (x, y, r) from SITE.json silo_equipment.level_sensors (Lubnymash
    standard: one upper rotary sensor)."""
    out = []
    for s in EQ["level_sensors"]:
        a = math.radians(s["angle_deg"])
        out.append((s["r"] * math.cos(a), s["r"] * math.sin(a), s["r"]))
    return out


def build_cables(positions=None, sensor_step=None):
    """Temperature cables hung from the rafters: cable, sensor capsules, top shackle (SITE `thermo`)."""
    sensor_step = SENSOR_STEP if sensor_step is None else sensor_step
    cables, sensors, hardware = [], [], []
    for x, y, r in positions or cable_positions():
        bottom, top = cable_ends(r)
        cables.append(st.rod((x, y, bottom), (x, y, top), CABLE_R, 8))
        for z in sensor_z(bottom, top, sensor_step):
            sensors.append(st.rod((x, y, z - 0.05), (x, y, z + 0.05), 0.016, 12))
        hardware.append(c.box((x - 0.05, y - 0.02, top), (x + 0.05, y + 0.02, top + 0.2)))        # shackle plate
    return c.merge_parts(cables), c.merge_parts(sensors), c.merge_parts(hardware)


def build_level_sensors():
    """Rotary paddle level switches through the roof (SITE `level_sensors`; Lubnymash standard:
    one upper sensor, was 3 in the old kit)."""
    parts = []
    for x, y, r in level_sensor_positions():
        s = next(s for s in EQ["level_sensors"] if abs(s["r"] - r) < 1e-6)
        zr = roof_underside_z(r) - s["paddle_below_roof_m"]
        hd, hh = s["housing_d_m"], s["housing_h_m"]
        parts.append(st.rod((x, y, zr - 0.15), (x, y, zr), hd / 2, 8))                          # paddle shaft
        parts.append(c.box((x - hd, y - 0.004, zr - 0.15), (x + hd, y + 0.004, zr)))            # paddle
        parts.append(st.rod((x, y, zr), (x, y, zr + hh), hd / 2, 16))                           # housing
    return c.merge_parts(parts)


def build_hatch_and_ladder():
    """Roof hatch near the eave over the outside ladder. Inside ladder down the wall only if
    SITE `inside_ladder` is set (Lubnymash option; sourced default is "no", rec_6fa26e86)."""
    a = math.radians(silo.LADDER_ANGLE)
    u = np.array([math.cos(a), math.sin(a), 0.0])
    t = np.array([-u[1], u[0], 0.0])
    h = silo.hatch_spec()["roof_access"]
    uh = np.array([math.cos(math.radians(h["angle_deg"])), math.sin(math.radians(h["angle_deg"])), 0.0])
    th_ = np.array([-uh[1], uh[0], 0.0])
    r_h = h["r"]
    zh = roof_underside_z(r_h)
    frame = [c.box(tuple(uh * r_h - th_ * (h["w_m"] / 2 + 0.04) + [0, 0, zh - 0.05]),
                   tuple(uh * r_h + th_ * (h["w_m"] / 2 + 0.04) + [0, 0, zh + 0.12]))]
    ladder = []
    if EQ["inside_ladder"]:
        r_l = R_IN - 0.25
        for s in (-0.22, 0.22):
            ladder.append(st.member(u * r_l + t * s + [0, 0, 0.0], u * r_l + t * s + [0, 0, silo.WALL_TOP - 0.3],
                                    st.FLAT_60x10, up=tuple(u)))
        for z in np.arange(0.3, silo.WALL_TOP - 0.4, 0.3):
            ladder.append(st.rod(u * r_l - t * 0.22 + [0, 0, z], u * r_l + t * 0.22 + [0, 0, z], 0.011, 6))
        for z in np.arange(1.0, silo.WALL_TOP, 3.0):                                         # wall brackets
            ladder.append(st.member(u * r_l + [0, 0, z], u * (R_IN - 0.01) + [0, 0, z], st.flat(0.05, 0.008)))
    hatch_pos = uh * r_h + [0, 0, zh]
    return c.merge_parts(frame), (c.merge_parts(ladder) if ladder else None), hatch_pos


def build_roof_openings_inside():
    """From inside: dark discs where the vents, hatches and service holes pierce the sheet. The roof fan
    motors that hang under their vents are built with the fans (silo_msvu220.build_roof_vents, component
    components.duct_axial_fan), not here."""
    holes = []
    for o in silo.roof_openings():
        if o["kind"] == "level_sensor":
            continue
        z = roof_underside_z(o["r"]) - 0.004
        if o["round"]:
            holes.append(c.cylinder(o["w"] / 2, z - 0.002, z, steps=24, center=(o["x"], o["y"])))
        else:
            u = np.array([math.cos(math.radians(o["deg"])), math.sin(math.radians(o["deg"]))])
            t = np.array([-u[1], u[0]])
            p = np.array([o["x"], o["y"]])
            v = np.array([[*(p + s * o["w"] / 2 * t + q * o["l"] / 2 * u), roof_underside_z(o["r"] + q * o["l"] / 2) - 0.004]
                          for s, q in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            holes.append((v, np.array([(0, 1, 2, 3)])))
    return c.merge_parts(holes)


# ================================================================== grain

def build_grain(fill=0.3, draw=False, n_r=90, n_a=256):
    """Grain surface: cone under the centre spout at the angle of repose, level `fill` of the wall
    height at the wall; `draw` sinks a funnel over the centre gate. Returns (verts, faces) or None."""
    if fill <= 0:
        return None
    h_wall = fill * silo.WALL_TOP
    rr = np.linspace(0.0, R_IN - 0.01, n_r)
    z = h_wall + (R_IN - rr) * math.tan(REPOSE)
    if draw:
        z = np.minimum(z, h_wall - 1.2 + rr * math.tan(math.radians(35)))
    a = np.linspace(0, 2 * math.pi, n_a, endpoint=False)
    x = rr[:, None] * np.cos(a)[None, :]
    y = rr[:, None] * np.sin(a)[None, :]
    ripple = (0.035 * np.sin(1.7 * x + 0.4) * np.cos(1.3 * y) + 0.02 * np.sin(4.1 * x - 2.3 * y)
              + 0.012 * np.cos(7.3 * y + 1.1 * x))                                # EST: loose surface
    top = np.stack([x, y, z[:, None] + ripple * (rr[:, None] / R_IN)], axis=-1).reshape(-1, 3)
    wall = np.column_stack([(R_IN - 0.01) * np.cos(a), (R_IN - 0.01) * np.sin(a), np.full(n_a, 0.01)])
    verts = np.concatenate([top, wall])
    faces = [c.grid_faces(n_r, n_a, wrap_cols=True)[:, ::-1]]
    i = np.arange(n_a)
    j = (i + 1) % n_a
    last = (n_r - 1) * n_a
    faces.append(np.stack([last + i, last + j, len(top) + j, len(top) + i], axis=-1))
    return verts, faces


def grain_section(fill=0.3, normal=(1.0, 0.0), n=120):
    """Vertical section face of the grain heap on the cut plane (for cutaways and heat maps)."""
    if fill <= 0:
        return None
    nx, ny = normal
    t = np.array([-ny, nx])                                                     # direction along the cut
    h_wall = fill * silo.WALL_TOP
    s = np.linspace(-(R_IN - 0.01), R_IN - 0.01, n)
    z = h_wall + (R_IN - np.abs(s)) * math.tan(REPOSE)
    top = np.column_stack([t[0] * s, t[1] * s, z])
    bot = np.column_stack([t[0] * s, t[1] * s, np.full(n, 0.01)])
    v = np.concatenate([bot, top])
    f = np.array([(i, i + 1, n + i + 1, n + i) for i in range(n - 1)])
    return v, f


def mat_grain(name="WHEAT"):
    """Wheat in bulk: warm golden base, grain-sized voronoi bump, darker hollows."""
    import bpy

    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexCoord")
    vor = nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 180.0
    links.new(tex.outputs["Object"], vor.inputs["Vector"])
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.0
    links.new(tex.outputs["Object"], noise.inputs["Vector"])
    mix = nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs[6].default_value = (0.55, 0.38, 0.16, 1.0)
    mix.inputs[7].default_value = (0.36, 0.23, 0.09, 1.0)
    links.new(vor.outputs["Distance"], mix.inputs["Factor"])
    links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.65
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.8
    bump.inputs["Distance"].default_value = 0.004
    links.new(vor.outputs["Distance"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def mat_perforated(name="PERFORATED"):
    """Perforated channel cover: galvanised plate with a dense dark hole pattern (23 % open)."""
    mat = c.mat_galvanized(name, age=0.55, spangle_scale=40.0)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    tex = nodes.new("ShaderNodeTexCoord")
    holes = nodes.new("ShaderNodeTexVoronoi")
    holes.voronoi_dimensions = "2D"
    holes.inputs["Scale"].default_value = 90.0
    holes.inputs["Randomness"].default_value = 0.0
    links.new(tex.outputs["Object"], holes.inputs["Vector"])
    thr = nodes.new("ShaderNodeMath")
    thr.operation = "LESS_THAN"
    thr.inputs[1].default_value = 0.27
    links.new(holes.outputs["Distance"], thr.inputs[0])
    dark = nodes.new("ShaderNodeMix")
    dark.data_type = "RGBA"
    dark.inputs[7].default_value = (0.01, 0.01, 0.01, 1.0)
    links.new(thr.outputs[0], dark.inputs["Factor"])
    base_link = next(lk for lk in links if lk.to_socket == bsdf.inputs["Base Color"])
    links.new(base_link.from_socket, dark.inputs[6])
    links.new(dark.outputs[2], bsdf.inputs["Base Color"])
    return mat


# ================================================================== assembly

def build(collection=None, fill=0.3, draw=False, cable_positions_override=None, sensor_step=SENSOR_STEP, cut=None, detail="lod"):
    import bpy

    m = {
        "galv": bpy.data.materials.get("SILO_GALV") or c.mat_galvanized("SILO_GALV_IN", age=0.4),
        "perf": mat_perforated("AERATION_COVER"),
        "dark": c.mat_painted("GATE_WELL", (0.015, 0.015, 0.015), 0.9, grime=0.0),
        "grating": st.mat_grating("GATE_GRATING"),
        "concrete": c.mat_concrete("SILO_FLOOR_CONCRETE", tint=(0.36, 0.35, 0.33)),
        "cable": c.mat_painted("THERMO_CABLE", (0.02, 0.02, 0.02), 0.5, grime=0.0),
        "sensor": c.mat_painted("THERMO_SENSOR", (0.55, 0.57, 0.6), 0.35, grime=0.1),
        "auger": c.mat_painted("SWEEP_PAINT", (0.62, 0.64, 0.66), 0.4, grime=0.4),
        "rubber": c.mat_rubber("SWEEP_TYRE"),
        "gear": c.mat_painted("SWEEP_GEARBOX", (0.10, 0.30, 0.18), 0.4, grime=0.2),
        "dark_steel": c.mat_painted("SWEEP_DARK_STEEL", (0.14, 0.14, 0.15), 0.5, grime=0.2),
        "motor": c.mat_painted("SWEEP_MOTOR", (0.05, 0.16, 0.35), 0.35),
        "grain": mat_grain(),
        "yellow": c.mat_painted("LEVEL_SENSOR", (0.9, 0.7, 0.05), 0.4, grime=0.1),
    }
    objs, labels = {}, []

    def add(key, data, mat, smooth=False):
        if data is None:
            return
        v, f = data
        if cut is not None:
            v, f = c.cut_mesh(v, f, cut)
            if not f:
                return
        objs[key] = c.mesh_from_arrays(f"SILO_IN_{key.upper()}", v, f, m[mat], smooth=smooth, collection=collection)

    segs = channel_layout()
    covers, frames, slab = build_floor(segs)
    add("floor", slab, "concrete")
    add("aeration_covers", covers, "perf")
    add("aeration_frames", frames, "galv")
    labels.append((f"Аераційний канал {CHANNEL_W * 1000:.0f} мм, перфорований настил", tuple(np.append(segs[1][1], 0.0))))
    wells, gframes, gratings = build_gates()
    add("gate_wells", wells, "dark")
    add("gate_frames", gframes, "galv")
    add("gate_gratings", gratings, "grating")
    labels.append(("Засувка вивантаження 400×400 (над тунелем)", (0.0, 0.0, 0.02)))
    sw = build_sweep_parts(detail=detail)
    for key, mat, sm in (("arm", "auger", "quads"), ("flight", "auger", True), ("mid_wheel", "rubber", "quads"),
                         ("drive_frame", "galv", False), ("drive_cover", "galv", False), ("drive_hub", "gear", "quads"),
                         ("drive_gear", "gear", "quads"), ("drive_motor", "motor", "quads"), ("drive_bracket", "dark_steel", False),
                         ("tractor_wheel", "rubber", "quads"), ("tractor_frame", "gear", "quads"), ("tractor_motor", "motor", "quads"),
                         ("tractor_shelf", "dark_steel", False), ("tractor_weights", "dark_steel", False)):
        add("sweep_" + key, sw[key], mat, sm)
    ang = math.radians(SWEEP_ANGLE)
    labels.append((f"Зачисний шнек (до стіни {SWEEP_LEN:.1f} м)", (5.0 * math.cos(ang), 5.0 * math.sin(ang), 0.35)))
    rafters, rings = build_roof_structure()
    add("rafters", rafters, "galv")
    add("purlins", rings, "galv")
    cables, sensors, hardware = build_cables(cable_positions_override, sensor_step)
    add("thermo_cables", cables, "cable", "quads")
    add("thermo_sensors", sensors, "sensor", "quads")
    add("thermo_hardware", hardware, "galv")
    x, y, r = cable_positions()[5]
    labels.append(("Термопідвіска: датчики через 2 м", (x, y, 4.0)))
    labels.append(("Датчик температури", (x, y, roof_underside_z(r) - 1.25)))
    add("level_sensors", build_level_sensors(), "yellow", "quads")
    lx, ly, lr = level_sensor_positions()[0]
    labels.append(("Датчик рівня (роторний, 1 верхній — стандарт Лубнимаш)", (lx, ly, roof_underside_z(lr) - 0.7)))
    hframe, ladder, hatch = build_hatch_and_ladder()
    add("hatch_frame", hframe, "galv")
    add("inside_ladder", ladder, "galv", "quads")
    labels.append(("Люк даху 610×700", tuple(hatch)))
    add("roof_holes", build_roof_openings_inside(), "dark")
    fan = next(o for o in silo.roof_openings() if o["kind"] == "fan_vent")
    labels.append(("Даховий вентилятор 0.25 кВт у провітрювачі", (fan["x"], fan["y"], roof_underside_z(fan["r"]) - 0.4)))
    add("grain", build_grain(fill, draw), "grain", True)
    measure = {
        "channels": len(segs),
        "channel_width_m": CHANNEL_W,
        "gates": len(GATE_OFFSETS),
        "cables": len(cable_positions_override or cable_positions()),
        "sensor_step_m": sensor_step,
        "sweep_length_m": SWEEP_LEN,
        "rafters": RAFTERS,
        "fill": fill,
        "grain_repose_deg": 27.0,
        "grain_mass_t_full": round(6381 * 0.75),
        "aeration_required_m3h": 10 * round(6381 * 0.75),
    }
    return objs, labels, measure, hatch
