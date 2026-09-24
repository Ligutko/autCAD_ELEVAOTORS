"""Bucket elevator Н-100 (100 t/h, 22 kW), detailed: belt loop with buckets, pulleys,
head and boot with removable front covers (cutaway), drive, sensors, explosion vent.

Local frame: the tower frame of noria_tower.py. Belt runs in the XZ plane at y = BELT_Y,
up leg on -X, down leg on +X. Z = 0 at grade.

Sizing (sources in brackets; see FIELD_CASES / inbox/reports/noria_dims.md):
  Q = 100 t/h, 22 kW                                    [catalogue, PDF p.8]
  belt speed 2.2-2.7 m/s -> 2.5                         [LUB UN-100]
  bucket volume: Q = 3.6 v (i/a) rho phi, rho 0.75, phi 0.75, a 0.18 -> i = 3.6 l   [calc]
  bucket 300 x 175 x 190 mm for ~3.6 l                  [EST, calc]
  pitch 180 mm, leg clear 376 x 256 mm                  [ad 2017; bucket fits: calc]
  head/tail pulley Ø630: n = 76 rpm, pole distance 895/n^2 = 0.156 m < r = 0.315 m,
  so the discharge is centrifugal                       [STD pulley series, calc]
  leg sheet >= 2 mm, head and boot >= 3 mm              [LUB news]
"""

import math

import numpy as np

from . import common as c
from . import steel as st

BELT_SPEED = 2.5
PULLEY_R = 0.315
LAGGING = 0.012
BELT_W = 0.325
BELT_T = 0.010
BELT_R = PULLEY_R + LAGGING + BELT_T / 2          # belt centreline radius on the pulleys
BUCKET_PITCH = 0.18
BUCKET_W = 0.300
BUCKET_T = 0.004
BUCKET_PROFILE = np.array([(0.0, 0.19), (0.0, 0.03), (0.03, 0.0), (0.12, 0.0), (0.165, 0.05), (0.175, 0.17)])
LEG_CLEAR_X = 0.256                               # across bucket projection
LEG_CLEAR_Y = 0.376                               # across belt width
LEG_SHEET = 0.002
HEAD_SHEET = 0.003
SECTION = 2.0
BELT_Y = 0.35
CX = 0.95                                          # pulley axis in the tower frame
# legs: casing centred on belt + bucket projection
LEG_OFFSET = BELT_R + 0.068
LEG_CENTRES_X = (CX - LEG_OFFSET, CX + LEG_OFFSET)
LEG_SIZE_X = LEG_CLEAR_X + 2 * LEG_SHEET
LEG_SIZE_Y = LEG_CLEAR_Y + 2 * LEG_SHEET
MOTOR_KW = 22


# ================================================================== belt path

class BeltPath:
    """Closed belt centreline: up leg, head arc, down leg, boot arc. Arc length parameter s."""

    def __init__(self, z_boot, z_head):
        self.zb, self.zh = z_boot, z_head
        self.h = z_head - z_boot
        self.arc = math.pi * BELT_R
        self.length = 2 * self.h + 2 * self.arc

    def frame(self, s):
        """(point xz, tangent xz, outward normal xz) at arc length s."""
        s = s % self.length
        h, arc = self.h, self.arc
        if s < h:                                            # up leg, travelling +Z
            return np.array([CX - BELT_R, self.zb + s]), np.array([0.0, 1.0]), np.array([-1.0, 0.0])
        s -= h
        if s < arc:                                          # over the head pulley, left -> right
            a = math.pi - s / BELT_R
            p = np.array([CX + BELT_R * math.cos(a), self.zh + BELT_R * math.sin(a)])
            n = np.array([math.cos(a), math.sin(a)])
            return p, np.array([n[1], -n[0]]), n
        s -= arc
        if s < h:                                            # down leg, travelling -Z
            return np.array([CX + BELT_R, self.zh - s]), np.array([0.0, -1.0]), np.array([1.0, 0.0])
        s -= h
        a = -s / BELT_R                                      # under the boot pulley, right -> left
        p = np.array([CX + BELT_R * math.cos(a), self.zb + BELT_R * math.sin(a)])
        n = np.array([math.cos(a), math.sin(a)])
        return p, np.array([n[1], -n[0]]), n

    def samples(self, step_straight=2.0, arc_segments=24):
        ss = list(np.arange(0.0, self.h, step_straight))
        ss += list(self.h + np.linspace(0, self.arc, arc_segments, endpoint=False))
        ss += list(self.h + self.arc + np.arange(0.0, self.h, step_straight))
        ss += list(2 * self.h + self.arc + np.linspace(0, self.arc, arc_segments, endpoint=False))
        return ss


def _to3(xz, y):
    return np.array([xz[0], y, xz[1]])


def build_belt(path):
    ss = path.samples()
    rows = []
    for s in ss:
        p, _, n = path.frame(s)
        for du, dy in ((-BELT_T / 2, -BELT_W / 2), (BELT_T / 2, -BELT_W / 2), (BELT_T / 2, BELT_W / 2),
                       (-BELT_T / 2, BELT_W / 2)):
            rows.append(_to3(p + n * du, BELT_Y + dy))
    v = np.array(rows)
    n_rows = len(ss)
    faces = []
    for i in range(n_rows):
        j = (i + 1) % n_rows
        for k in range(4):
            k2 = (k + 1) % 4
            faces.append((i * 4 + k, i * 4 + k2, j * 4 + k2, j * 4 + k))
    return v, np.array(faces)


def _bucket_local():
    """Bucket shell in local (u outward, v along travel, w across), open at the top."""
    prof = BUCKET_PROFILE
    inner = prof + np.array([BUCKET_T, BUCKET_T])
    inner[0, 1] = prof[0, 1]
    inner[-1] = prof[-1] - np.array([BUCKET_T, 0.0])
    loop = np.concatenate([prof, inner[::-1]])
    k = len(loop)
    hw = BUCKET_W / 2
    verts = [(u, v, w) for w in (-hw, hw) for u, v in loop]
    faces = [c.grid_faces(2, k, wrap_cols=True)]
    # end plates: full outer profile at both ends, BUCKET_T thick
    base = len(verts)
    for w in (-hw, hw - BUCKET_T, hw, -hw + BUCKET_T):
        verts += [(u, v, w) for u, v in prof]
    m = len(prof)
    faces.append(np.arange(base, base + m)[None, :])
    faces.append(np.arange(base + m, base + 2 * m)[None, :])
    faces.append(np.arange(base + 2 * m, base + 3 * m)[::-1][None, :])
    faces.append(np.arange(base + 3 * m, base + 4 * m)[::-1][None, :])
    return np.array(verts), faces


def _grain_local():
    """Grain in a loaded bucket: a low mound filling ~75 %."""
    v = np.array([(0.01, 0.01, -0.14), (0.16, 0.01, -0.14), (0.165, 0.14, -0.14), (0.01, 0.17, -0.14),
                  (0.01, 0.01, 0.14), (0.16, 0.01, 0.14), (0.165, 0.14, 0.14), (0.01, 0.17, 0.14)])
    f = np.array([(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
    return v, f


def build_buckets(path, phase=0.0):
    """All buckets placed along the belt at BUCKET_PITCH, shifted by `phase` metres (animation)."""
    bv, bf = _bucket_local()
    gv, gf = _grain_local()
    n = int(path.length // BUCKET_PITCH)
    buckets, grain = [], []
    for k in range(n):
        s = k * BUCKET_PITCH + phase
        p, t, nrm = path.frame(s)
        origin = _to3(p + nrm * BELT_T / 2, BELT_Y)
        u = _to3(nrm, 0.0)
        vv = _to3(t, 0.0)
        w = np.array([0.0, 1.0, 0.0])

        def place(local):
            return origin + local[:, 0:1] * u + local[:, 1:2] * vv + local[:, 2:3] * w

        buckets.append((place(bv), bf))
        s_mod = s % path.length
        if s_mod < path.h + 0.3 * path.arc and s_mod > 0.5 * path.arc / math.pi:   # loaded on the up leg
            grain.append((place(gv), gf))
    return c.merge_parts(buckets), c.merge_parts(grain), n


# ================================================================== casing

def _flange_frame(xc, yc, z, sx, sy, leg=0.04):
    """Angle frame around a leg section joint, 40 x 40 mm."""
    x0, x1 = xc - sx / 2 - leg, xc + sx / 2 + leg
    y0, y1 = yc - sy / 2 - leg, yc + sy / 2 + leg
    return c.box((x0, y0, z - 0.004), (x1, y1, z + 0.004))


def build_legs(z0, z1):
    casing, flanges, bolts, doors = [], [], [], []
    for xc in LEG_CENTRES_X:
        casing.append(c.box((xc - LEG_SIZE_X / 2, BELT_Y - LEG_SIZE_Y / 2, z0),
                            (xc + LEG_SIZE_X / 2, BELT_Y + LEG_SIZE_Y / 2, z1)))
        for z in np.arange(z0 + SECTION, z1 - 0.3, SECTION):
            flanges.append(_flange_frame(xc, BELT_Y, z, LEG_SIZE_X, LEG_SIZE_Y))
            # M8 bolts on the flange, ~100 mm pitch, two faces visible
            for yy in np.linspace(BELT_Y - LEG_SIZE_Y / 2 - 0.02, BELT_Y + LEG_SIZE_Y / 2 + 0.02, 5):
                for xx in (xc - LEG_SIZE_X / 2 - 0.02, xc + LEG_SIZE_X / 2 + 0.02):
                    bolts.append(st.rod((xx, yy, z + 0.004), (xx, yy, z + 0.012), 0.0075, 6))
    # inspection doors on the up leg: above the boot and under the head (EST 300 x 400)
    xc = LEG_CENTRES_X[0]
    for zd in (z0 + 0.8, z1 - 1.4):
        doors.append(c.box((xc - 0.12, BELT_Y + LEG_SIZE_Y / 2, zd), (xc + 0.12, BELT_Y + LEG_SIZE_Y / 2 + 0.012, zd + 0.4)))
        doors.append(c.box((xc - 0.14, BELT_Y + LEG_SIZE_Y / 2 + 0.012, zd + 0.17), (xc - 0.11, BELT_Y + LEG_SIZE_Y / 2 + 0.05, zd + 0.23)))
    return c.merge_parts(casing), c.merge_parts(flanges), c.merge_parts(bolts), c.merge_parts(doors)


def _housing(x0, x1, z0, z1, y_half, arc_top=None):
    """Box housing split into a back part and a removable front cover (the +Y wall).

    arc_top: (xc, zc, r) rounds the roof into a half cylinder (head hood).
    """
    y0, y1 = BELT_Y - y_half, BELT_Y + y_half
    back = [c.box((x0, y0, z0), (x1, y0 + HEAD_SHEET, z1)),                 # back wall
            c.box((x0, y0, z0), (x0 + HEAD_SHEET, y1, z1)),                 # left
            c.box((x1 - HEAD_SHEET, y0, z0), (x1, y1, z1))]                 # right
    if arc_top is None:
        back.append(c.box((x0, y0, z1 - HEAD_SHEET), (x1, y1, z1)))
    else:
        xc, zc, r = arc_top
        a = np.linspace(0, math.pi, 32)
        ring_o = np.column_stack([xc + r * np.cos(a), zc + r * np.sin(a)])
        ring_i = np.column_stack([xc + (r - HEAD_SHEET) * np.cos(a), zc + (r - HEAD_SHEET) * np.sin(a)])
        loop = np.concatenate([ring_o, ring_i[::-1]])
        k = len(loop)
        v = np.concatenate([np.column_stack([loop[:, 0], np.full(k, y0), loop[:, 1]]),
                            np.column_stack([loop[:, 0], np.full(k, y1), loop[:, 1]])])
        back.append((v, [c.grid_faces(2, k, wrap_cols=True), np.arange(k)[None, :], np.arange(k, 2 * k)[::-1][None, :]]))
        # back end plate of the hood
        pl = np.concatenate([ring_o, [[xc, zc]]])
        v = np.column_stack([pl[:, 0], np.full(len(pl), y0), pl[:, 1]])
        back.append((np.concatenate([v, v + [0, HEAD_SHEET, 0]]),
                     [np.arange(len(pl))[None, :], np.arange(len(pl), 2 * len(pl))[::-1][None, :]]))
    front = [c.box((x0, y1 - HEAD_SHEET, z0), (x1, y1, z1))]
    if arc_top is not None:
        xc, zc, r = arc_top
        a = np.linspace(0, math.pi, 32)
        pl = np.concatenate([np.column_stack([xc + r * np.cos(a), zc + r * np.sin(a)]), [[xc, zc]]])
        v = np.column_stack([pl[:, 0], np.full(len(pl), y1 - HEAD_SHEET), pl[:, 1]])
        front.append((np.concatenate([v, v + [0, HEAD_SHEET, 0]]),
                      [np.arange(len(pl))[::-1][None, :], np.arange(len(pl), 2 * len(pl))[None, :]]))
    # bolted flange around the front cover
    rim = [c.box((x0 - 0.03, y1, z0 - 0.03), (x1 + 0.03, y1 + 0.006, z0)),
           c.box((x0 - 0.03, y1, z1), (x1 + 0.03, y1 + 0.006, z1 + 0.03)),
           c.box((x0 - 0.03, y1, z0), (x0, y1 + 0.006, z1)),
           c.box((x1, y1, z0), (x1 + 0.03, y1 + 0.006, z1))]
    return c.merge_parts(back), c.merge_parts(front), c.merge_parts(rim)


def _pulley(z, wing=False):
    """Crowned drum with rubber lagging, or a self-cleaning wing pulley for the boot."""
    lag, drum, shaft = [], [], []
    y0, y1 = BELT_Y - BELT_W / 2 - 0.02, BELT_Y + BELT_W / 2 + 0.02
    if wing:
        for k in range(10):                                   # 10 radial wings, "squirrel cage"
            a = k * math.pi / 5
            mid = np.array([CX + 0.75 * PULLEY_R * math.cos(a), z + 0.75 * PULLEY_R * math.sin(a)])
            plate = np.array([(-0.004, -PULLEY_R * 0.25), (0.004, -PULLEY_R * 0.25),
                              (0.004, PULLEY_R * 0.25), (-0.004, PULLEY_R * 0.25)])
            drum.append(st.member(_to3(mid, y0), _to3(mid, y1), plate, up=(math.cos(a), 0.0, math.sin(a))))
        for yy in (y0, y1):
            drum.append(st.rod((CX, yy - 0.006, z), (CX, yy + 0.006, z), PULLEY_R, 32))
    else:
        drum.append(st.rod((CX, y0, z), (CX, y1, z), PULLEY_R, 48))
        lag.append(st.rod((CX, y0 + 0.01, z), (CX, y1 - 0.01, z), PULLEY_R + LAGGING, 48))
    shaft.append(st.rod((CX, BELT_Y - 0.62, z), (CX, BELT_Y + 0.62, z), 0.045, 20))
    return c.merge_parts(drum), (c.merge_parts(lag) if lag else None), c.merge_parts(shaft)


def _bearing(y, z):
    """Pillow block with a temperature sensor on top."""
    body = [c.box((CX - 0.17, y - 0.05, z - 0.09), (CX + 0.17, y + 0.05, z - 0.05)),
            st.rod((CX, y - 0.05, z), (CX, y + 0.05, z), 0.085, 24)]
    sensor = [st.rod((CX, y, z + 0.085), (CX, y, z + 0.13), 0.012, 10)]
    return body, sensor


def build(top_z, pit_z, phase=0.0):
    """Returns dict of parts (verts, faces) keyed by role, plus label anchors and measure."""
    z_boot = pit_z + 0.25 + 0.35 + BELT_R          # boot floor + clearance under the tail pulley
    z_head = top_z + 1.20
    path = BeltPath(z_boot, z_head)
    parts, labels = {}, []

    parts["belt"] = build_belt(path)
    parts["buckets"], parts["grain"], n_buckets = build_buckets(path, phase)

    leg_z0 = z_boot + 0.70
    leg_z1 = z_head - 0.75
    parts["legs"], parts["leg_flanges"], parts["leg_bolts"], parts["leg_doors"] = build_legs(leg_z0, leg_z1)

    # ---- head: housing with hood, front cover, pulley, discharge throat and spout
    hx0 = LEG_CENTRES_X[0] - LEG_SIZE_X / 2 - 0.02
    hx1 = LEG_CENTRES_X[1] + LEG_SIZE_X / 2 + 0.30          # room for the discharge throat
    hood_r = (hx1 - hx0) / 2
    head_back, head_front, head_rim = _housing(hx0, hx1, leg_z1, z_head, 0.30,
                                               arc_top=((hx0 + hx1) / 2, z_head, hood_r))
    drum, lag, shaft = _pulley(z_head)
    throat = [c.box((hx1 - 0.02, BELT_Y - 0.2, z_head - 0.75), (hx1 + 0.25, BELT_Y + 0.2, z_head - 0.25))]
    spout_end = np.array([hx1 + 0.25, BELT_Y - 1.0, z_head - 1.75])
    spout = [st.rod((hx1 + 0.12, BELT_Y, z_head - 0.7), tuple(spout_end), 0.15, 20)]
    # explosion vent on the hood crown (framed rupture panel)
    vent = [c.box(((hx0 + hx1) / 2 - 0.25, BELT_Y - 0.22, z_head + hood_r - 0.02),
                  ((hx0 + hx1) / 2 + 0.25, BELT_Y + 0.22, z_head + hood_r + 0.05))]
    labels.append(("Вибухорозрядник голови", ((hx0 + hx1) / 2, BELT_Y, z_head + hood_r + 0.05)))
    parts["head"] = c.merge_parts([head_back] + throat)
    parts["head_cover"] = head_front
    parts["head_rim"] = head_rim
    parts["head_spout"] = c.merge_parts(spout)
    parts["vent"] = c.merge_parts(vent)
    parts["pulley_drum"] = drum
    parts["pulley_lagging"] = lag
    parts["shafts"] = shaft

    # ---- drive: shaft-mounted reducer, 22 kW motor, torque arm, backstop, bearings
    gy = BELT_Y - 0.62                                   # drive on the -Y side, cutaway side stays clear
    drive = [c.box((CX - 0.24, gy - 0.40, z_head - 0.30), (CX + 0.24, gy + 0.02, z_head + 0.26))]
    drive.append(st.member((CX + 0.1, gy - 0.2, z_head - 0.3), (CX + 0.1, gy - 0.2, leg_z1 - 0.3), st.shs(0.06)))
    my = gy - 0.19
    motor = [st.rod((CX + 0.24, my, z_head - 0.05), (CX + 0.95, my, z_head - 0.05), 0.18, 32)]
    fins = []
    for k in range(24):                                   # longitudinal cooling ribs of a TEFC motor
        a = 2 * math.pi * k / 24
        mid = np.array([0.0, my + 0.195 * math.cos(a), z_head - 0.05 + 0.195 * math.sin(a)])
        fins.append(st.member((CX + 0.30, mid[1], mid[2]), (CX + 0.90, mid[1], mid[2]),
                              np.array([(-0.003, -0.02), (0.003, -0.02), (0.003, 0.02), (-0.003, 0.02)]),
                              up=(0.0, math.cos(a), math.sin(a))))
    fins.append(c.box((CX + 0.45, my - 0.11, z_head + 0.12), (CX + 0.70, my + 0.11, z_head + 0.22)))   # terminal box
    cover = [st.rod((CX + 0.95, my, z_head - 0.05), (CX + 1.10, my, z_head - 0.05), 0.16, 32)]
    backstop = [st.rod((CX, BELT_Y + 0.50, z_head), (CX, BELT_Y + 0.62, z_head), 0.13, 24)]
    labels.append((f"Привід {MOTOR_KW} кВт: мотор-редуктор на валу", (CX + 0.6, my, z_head + 0.22)))
    labels.append(("Стопор зворотного ходу", (CX, BELT_Y + 0.62, z_head + 0.13)))
    bearings, bsensors = [], []
    for y in (BELT_Y - 0.42, BELT_Y + 0.42):
        b, s = _bearing(y, z_head)
        bearings += b
        bsensors += s
    labels.append(("Датчик температури підшипника", (CX, BELT_Y + 0.42, z_head + 0.13)))
    parts["drive"] = c.merge_parts(drive + backstop + bearings)
    parts["motor"] = c.merge_parts(motor + fins + cover)

    # ---- boot: housing, wing pulley, take-up screws, inlet, clean-out doors
    bx0 = LEG_CENTRES_X[0] - LEG_SIZE_X / 2 - 0.10
    bx1 = LEG_CENTRES_X[1] + LEG_SIZE_X / 2 + 0.10
    boot_back, boot_front, boot_rim = _housing(bx0, bx1, pit_z + 0.25, leg_z0, 0.30)
    wdrum, _, wshaft = _pulley(z_boot, wing=True)
    takeup = []
    for y in (BELT_Y - 0.42, BELT_Y + 0.42):
        b, s = _bearing(y, z_boot)
        takeup += b
        bsensors += s
        takeup.append(st.rod((CX, y, z_boot + 0.09), (CX, y, leg_z0 + 0.35), 0.015, 8))       # take-up screw
        takeup.append(c.box((CX - 0.2, y - 0.06, z_boot - 0.2), (CX - 0.17, y + 0.06, z_boot + 0.5)))  # slide
        takeup.append(c.box((CX + 0.17, y - 0.06, z_boot - 0.2), (CX + 0.2, y + 0.06, z_boot + 0.5)))
    labels.append(("Натяжний пристрій (гвинтовий)", (CX, BELT_Y + 0.42, leg_z0 + 0.35)))
    inlet = [st.member((bx0 - 0.75, BELT_Y, leg_z0 + 0.65), (bx0 + 0.02, BELT_Y, leg_z0 - 0.15), st.shs(0.30))]
    labels.append(("Завантажувальний патрубок башмака", (bx0 - 0.6, BELT_Y, leg_z0 + 0.6)))
    cleanout = [c.box((bx0 + 0.1, BELT_Y + 0.30, pit_z + 0.3), (bx0 + 0.45, BELT_Y + 0.312, pit_z + 0.6)),
                c.box((bx1 - 0.45, BELT_Y + 0.30, pit_z + 0.3), (bx1 - 0.1, BELT_Y + 0.312, pit_z + 0.6))]
    parts["boot"] = c.merge_parts([boot_back] + inlet)
    parts["boot_cover"] = boot_front
    parts["boot_rim"] = c.merge_parts([boot_rim] + cleanout)
    parts["boot_pulley"] = wdrum
    parts["shafts"] = c.merge_parts([parts["shafts"], wshaft])
    parts["takeup"] = c.merge_parts(takeup)

    # ---- sensors (yellow): belt alignment x4, speed, plug, bearing temperature x4
    sensors = list(bsensors)
    for zz in (z_head - 0.2, z_boot + 0.1):
        for xx in (LEG_CENTRES_X[0], LEG_CENTRES_X[1]):
            sensors.append(c.box((xx - 0.035, BELT_Y + 0.30 + 0.006, zz - 0.05),
                                 (xx + 0.035, BELT_Y + 0.30 + 0.09, zz + 0.05)))
    labels.append(("Датчик сходу стрічки", (LEG_CENTRES_X[0], BELT_Y + 0.39, z_head - 0.2)))
    labels.append(("Барабан голови Ø630, футерований", (CX, BELT_Y + 0.16, z_head + PULLEY_R)))
    labels.append(("Ківш 3,6 л, крок 180 мм", (CX - BELT_R - 0.1, BELT_Y, z_head - 0.5)))
    labels.append(("Барабан башмака самоочисний (крильчастий)", (CX, BELT_Y + 0.16, z_boot + PULLEY_R)))
    sensors.append(st.rod((CX, BELT_Y + 0.62, z_boot), (CX, BELT_Y + 0.72, z_boot), 0.03, 12))
    labels.append(("Датчик швидкості (контроль руху стрічки)", (CX, BELT_Y + 0.72, z_boot)))
    ps = (np.array([hx1 + 0.12, BELT_Y, z_head - 0.7]) + spout_end) / 2
    sensors.append(st.rod(tuple(ps + [0.14, 0, 0]), tuple(ps + [0.26, 0, 0]), 0.025, 12))
    labels.append(("Датчик підпору самопливу", tuple(ps + [0.26, 0, 0])))
    parts["sensors"] = c.merge_parts(sensors)

    measure = {
        "belt_speed_m_s": BELT_SPEED,
        "pulley_diameter_m": 2 * PULLEY_R,
        "pulley_rpm": round(60 * BELT_SPEED / (math.pi * 2 * PULLEY_R), 1),
        "pole_distance_m": round(895 / (60 * BELT_SPEED / (math.pi * 2 * PULLEY_R)) ** 2, 3),
        "discharge": "centrifugal" if 895 / (60 * BELT_SPEED / (math.pi * 2 * PULLEY_R)) ** 2 < PULLEY_R else "gravity",
        "bucket_volume_l_calc": round(100 / (3.6 * BELT_SPEED * 0.75 * 0.75) * BUCKET_PITCH, 2),
        "bucket_mm": [300, 175, 190],
        "bucket_pitch_m": BUCKET_PITCH,
        "buckets": n_buckets,
        "belt_loop_m": round(path.length, 2),
        "leg_clear_mm": [int(LEG_CLEAR_Y * 1000), int(LEG_CLEAR_X * 1000)],
        "leg_centres_x_m": [round(x, 3) for x in LEG_CENTRES_X],
        "head_pulley_z_m": round(z_head, 3),
        "boot_pulley_z_m": round(z_boot, 3),
        "motor_kw": MOTOR_KW,
    }
    anchors = {"spout_end": tuple(spout_end), "z_head": z_head, "z_boot": z_boot}
    return parts, labels, measure, anchors
