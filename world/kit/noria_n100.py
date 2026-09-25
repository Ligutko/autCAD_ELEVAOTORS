"""Bucket elevators У13-УН175 (H5) and У13-УН100 (H6), detailed: belt loop with buckets, pulleys,
head and boot with removable front covers (cutaway), drive, sensors, explosion vent.
Spec PDF p.8 / p.10: both 100 t/h real, 22 kW; H5 fed on the return leg (hence the bigger УН-175,
p.8 note 2: -30 %), H6 fed on the working leg.

Local frame: the tower frame of noria_tower.py. Belt runs in the XZ plane at y = BELT_Y,
up leg on -X, down leg on +X. Z = 0 at grade.

Sizing (cards in inbox/records; research/lubnymash_equipment.md, research/tunnel_k4.md):
  pulleys Ø750 both models, speed, pitch, belt width, table bucket volume   [LUB table on bizorg]
  leg width across the belt 499 (H5) / 393 (H6) and housing 0.61 / 0.49   [drawing p.2, p.6, p.7]
  -> the LUB УН-175 column's 376 leg is a copy of the УН-100 column; its 400 belt fits the drawn leg
  leg depth 256 across the buckets                                          [LUB table]
  bucket sized to the table volume and to clear the leg, volume computed from the mesh  [derived]
  leg sheet >= 2 mm, head and boot >= 3 mm                                  [LUB news]
"""

import math

import numpy as np

from . import common as c
from . import steel as st

PULLEY_R = 0.375
LAGGING = 0.012
BELT_T = 0.010
BELT_R = PULLEY_R + LAGGING + BELT_T / 2          # belt centreline radius on the pulleys
# Per model, LUB table on bizorg (research/lubnymash_equipment.md): both have Ø750 pulleys, 376 x 256
# legs, 22 kW. Bucket (width, projection, depth) is sized to the table volume and to clear the leg;
# its volume is computed from the mesh profile.
MODELS = {
    "У13-УН175": {"belt_speed": 2.87, "pitch": 0.21, "belt_w": 0.40, "leg_clear": (0.256, 0.499),
                  "housing_half_y": 0.305, "bucket": (0.380, 0.150, 0.165), "table_volume_l": 7.8},
    "У13-УН100": {"belt_speed": 2.40, "pitch": 0.18, "belt_w": 0.30, "leg_clear": (0.256, 0.393),
                  "housing_half_y": 0.245, "bucket": (0.280, 0.125, 0.130), "table_volume_l": 3.6},
}
GRAIN_RHO, FILL = 0.75, 0.75         # wheat t/m3, bucket fill factor (calc)
RETURN_FEED_LOSS = 0.30              # PDF p.8 note 2: -30 % when fed on the return leg
BUCKET_T = 0.0065                  # research: Tapco CC-HD 12x6 wall 6.4 mm
LEG_SHEET = 0.002
HEAD_SHEET = 0.003
SECTION = 2.0
BELT_Y = 0.35
CX = 0.95                                          # pulley axis in the tower frame
# legs: casing centred on belt + bucket projection
LEG_OFFSET = BELT_R + 0.068
LEG_CENTRES_X = (CX - LEG_OFFSET, CX + LEG_OFFSET)
MOTOR_KW = 22


def leg_size(mdl):
    """Outer leg casing (across the bucket projection = local X, across the belt = local Y)."""
    return mdl["leg_clear"][0] + 2 * LEG_SHEET, mdl["leg_clear"][1] + 2 * LEG_SHEET


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


def build_belt(path, mdl):
    ss = path.samples()
    rows = []
    for s in ss:
        p, _, n = path.frame(s)
        hw = mdl["belt_w"] / 2
        for du, dy in ((-BELT_T / 2, -hw), (BELT_T / 2, -hw), (BELT_T / 2, hw), (-BELT_T / 2, hw)):
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


def _bucket_profile(mdl, n_arc=8):
    """Outer profile (u outward from the belt, v along travel) of a CC-style bucket:
    straight back on the belt, radiused bottom, sloped front ending in a rolled lip."""
    # depth 160 mm < pitch 180 mm; CC-HD depth is 0.9-1.0 x projection (research/PARTS_DIMENSIONS.md)
    pts = [(0.0, 0.16), (0.0, 0.045)]
    for a in np.linspace(math.pi, 1.5 * math.pi, n_arc)[1:]:                  # bottom radius 45 mm
        pts.append((0.045 + 0.045 * math.cos(a), 0.045 + 0.045 * math.sin(a)))
    p0, p1, p2 = np.array([0.09, 0.0]), np.array([0.172, 0.0]), np.array([0.172, 0.138])
    for t in np.linspace(0, 1, n_arc)[1:]:                                     # sloped front
        pts.append(tuple((1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t ** 2 * p2))
    pts.append((0.180, 0.152))                                                  # rolled lip
    pts = np.array(pts)
    _, proj, depth = mdl["bucket"]
    pts[:, 0] *= proj / 0.180
    pts[:, 1] *= depth / 0.16
    return pts


def bucket_volume_l(mdl):
    """Gross volume to the lip, from the same profile the mesh is built from."""
    p = _bucket_profile(mdl)
    x, y = p[:, 0], p[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))
    return area * (mdl["bucket"][0] - 2 * BUCKET_T) * 1000


def capacity_t_h(mdl, feed):
    """Q = 3.6 v rho phi i / a from the modelled bucket volume, minus the return-leg loss."""
    q = 3.6 * mdl["belt_speed"] * GRAIN_RHO * FILL * bucket_volume_l(mdl) / mdl["pitch"]
    return q * (1 - RETURN_FEED_LOSS) if feed == "return" else q


def _offset_inward(prof, d):
    """Offset an open polyline by d towards the inside of the bucket (left of travel)."""
    out = []
    for i in range(len(prof)):
        a = prof[max(i - 1, 0)]
        b = prof[min(i + 1, len(prof) - 1)]
        t = (b - a) / np.linalg.norm(b - a)
        n = np.array([t[1], -t[0]])                                            # right normal
        out.append(prof[i] - n * d)
    return np.array(out)


def _bucket_local(mdl):
    """Bucket shell (4 mm) with end plates and two fang bolts on the back, open at the top."""
    prof = _bucket_profile(mdl)
    width, _, depth = mdl["bucket"]
    inner = _offset_inward(prof, BUCKET_T)
    inner[0] = prof[0] + [BUCKET_T, 0.0]
    loop = np.concatenate([prof, inner[::-1]])
    k = len(loop)
    hw = width / 2
    verts = [(u, v, w) for w in (-hw, hw) for u, v in loop]
    faces = [c.grid_faces(2, k, wrap_cols=True)]
    base = len(verts)
    m = len(prof)
    for w in (-hw, -hw + BUCKET_T, hw - BUCKET_T, hw):
        verts += [(u, v, w) for u, v in prof]
    faces.append(np.arange(base, base + m)[None, :])
    faces.append(np.arange(base + m, base + 2 * m)[::-1][None, :])
    faces.append(np.arange(base + 2 * m, base + 3 * m)[None, :])
    faces.append(np.arange(base + 3 * m, base + 4 * m)[::-1][None, :])
    parts = [(np.array(verts), faces)]
    # 4 x M8 DIN 15237 fang bolts, Ø28 head, 88 mm pitch, 57 mm below the top edge (research)
    for w in np.array((-0.11, -0.037, 0.037, 0.11)) * width / 0.28:
        parts.append(st.member((BUCKET_T, depth - 0.057, w), (BUCKET_T + 0.004, depth - 0.057, w),
                               np.column_stack([0.014 * np.cos(np.arange(12) * math.pi / 6),
                                                0.014 * np.sin(np.arange(12) * math.pi / 6)]), up=(0, 1, 0)))
    return c.merge_parts(parts)


def _grain_local(mdl):
    """Grain in a loaded bucket: a low mound filling ~75 %."""
    width, proj, depth = mdl["bucket"]
    k, u, hw = depth / 0.16, proj / 0.18, width / 2 - 0.01
    v = np.array([(0.01, 0.01, -hw), (0.16 * u, 0.01, -hw), (0.165 * u, 0.12 * k, -hw), (0.01, 0.145 * k, -hw),
                  (0.01, 0.01, hw), (0.16 * u, 0.01, hw), (0.165 * u, 0.12 * k, hw), (0.01, 0.145 * k, hw)])
    f = np.array([(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])
    return v, f


def build_buckets(path, mdl, phase=0.0):
    """All buckets placed along the belt at the model pitch, shifted by `phase` metres (animation)."""
    pitch = mdl["pitch"]
    bv, bf = _bucket_local(mdl)
    gv, gf = _grain_local(mdl)
    n = int(path.length // pitch)
    buckets, grain = [], []
    for k in range(n):
        s = k * pitch + phase
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


def build_legs(z0, z1, mdl):
    LEG_SIZE_X, LEG_SIZE_Y = leg_size(mdl)  # noqa: N806
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
    # explosion vents: leg over 32 m, NFPA 61 spacing <= 6.1 m, each >= 0.064 m2 (research)
    for xc, sign in ((LEG_CENTRES_X[0], -1), (LEG_CENTRES_X[1], 1)):
        xf = xc + sign * LEG_SIZE_X / 2
        for z in np.arange(z0 + 3.0, z1 - 1.0, 6.1):
            doors.append(c.box((min(xf, xf + sign * 0.025), BELT_Y - 0.16, z), (max(xf, xf + sign * 0.025), BELT_Y + 0.16, z + 0.30)))
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


SHAFT_R = 0.045                     # Ø90: 22 kW at 76 rpm is ~2.8 kN*m, EST
HUB_R = 0.095


def _hub(y, z, sign):
    """Hub with a taper-lock bushing and 6 bolts, on the outside of an end disc."""
    parts = [st.rod((CX, y, z), (CX, y + sign * 0.07, z), HUB_R, 32),
             st.rod((CX, y + sign * 0.07, z), (CX, y + sign * 0.085, z), 0.07, 24)]
    for k in range(6):
        a = k * math.pi / 3
        px, pz = CX + 0.055 * math.cos(a), z + 0.055 * math.sin(a)
        parts.append(st.rod((px, y + sign * 0.085, pz), (px, y + sign * 0.095, pz), 0.008, 6))
    return parts


def _pulley(z, mdl, wing=False):
    """Head drum (crowned shell, end discs, hubs, lagging) or self-cleaning wing tail pulley."""
    lag, drum, shaft = [], [], []
    width = mdl["belt_w"] + 0.05
    y0, y1 = BELT_Y - width / 2, BELT_Y + width / 2
    if wing:
        for k in range(10):                                   # 10 radial wings, "squirrel cage"
            a = k * math.pi / 5
            mid = np.array([CX + 0.67 * PULLEY_R * math.cos(a), z + 0.67 * PULLEY_R * math.sin(a)])
            plate = np.array([(-0.005, -PULLEY_R * 0.33), (0.005, -PULLEY_R * 0.33),
                              (0.005, PULLEY_R * 0.33), (-0.005, PULLEY_R * 0.33)])
            drum.append(st.member(_to3(mid, y0), _to3(mid, y1), plate, up=(math.cos(a), 0.0, math.sin(a))))
        for yy in (y0, BELT_Y, y1):                           # spider plates: ends and middle
            drum.append(st.rod((CX, yy - 0.006, z), (CX, yy + 0.006, z), 0.45 * PULLEY_R, 24))
    else:
        drum.append(st.rod((CX, y0, z), (CX, y1, z), PULLEY_R, 64))
        lag.append(st.rod((CX, y0 + 0.012, z), (CX, y1 - 0.012, z), PULLEY_R + LAGGING, 64))
        for yy in (y0, y1):
            drum.append(st.rod((CX, yy - 0.012, z), (CX, yy + 0.012, z), PULLEY_R + 0.004, 64))
    drum += _hub(y0, z, -1) + _hub(y1, z, 1)
    shaft.append(st.rod((CX, BELT_Y - 0.62, z), (CX, BELT_Y + 0.62, z), SHAFT_R, 24))
    return c.merge_parts(drum), (c.merge_parts(lag) if lag else None), c.merge_parts(shaft)


def _bearing(y, z):
    """Split plummer block SKF SNL 520-617 for the Ø90 shaft (research: SKF catalogue p.1043):
    axis height 112, overall height 218, base 380 x 160 x 40, 2 x M24 at 320, cap width 110."""
    h, hb, bl, bw = 0.112, 0.040, 0.380, 0.160
    r_cap = 0.218 - h
    body = [c.box((CX - bl / 2, y - bw / 2, z - h), (CX + bl / 2, y + bw / 2, z - h + hb)),           # base
            c.box((CX - 0.12, y - 0.055, z - h + hb), (CX + 0.12, y + 0.055, z)),                     # lower half
            st.rod((CX, y - 0.055, z), (CX, y + 0.055, z), r_cap, 48),                                # cap
            c.box((CX - 0.15, y - 0.055, z - 0.014), (CX + 0.15, y + 0.055, z + 0.014))]              # split lugs
    for yy in (y - 0.062, y + 0.055):
        body.append(st.rod((CX, yy, z), (CX, yy + 0.007, z), 0.07, 32))                               # seals
    for x in (CX - 0.16, CX + 0.16):
        body.append(st.rod((x, y, z - h + hb), (x, y, z - h + hb + 0.022), 0.019, 6))               # M24 foot bolts
    for x in (CX - 0.135, CX + 0.135):
        body.append(st.rod((x, y, z + 0.014), (x, y, z + 0.032), 0.013, 6))                         # cap bolts
    body.append(st.rod((CX + 0.03, y, z + r_cap - 0.005), (CX + 0.03, y, z + r_cap + 0.02), 0.005, 6))
    sensor = [st.rod((CX - 0.03, y, z + r_cap - 0.01), (CX - 0.03, y, z + r_cap + 0.04), 0.011, 10),
              st.rod((CX - 0.03, y, z + r_cap + 0.04), (CX - 0.03, y + 0.12, z + r_cap + 0.09), 0.004, 6)]
    return body, sensor


def _rim_bolts(x0, x1, z0, z1, y, step=0.10):
    """M10 hex heads around a bolted cover flange (heads facing +Y)."""
    pts = []
    for x in np.arange(x0, x1 + 1e-6, step):
        pts += [(x, z0), (x, z1)]
    for zz in np.arange(z0 + step, z1 - step / 2, step):
        pts += [(x0, zz), (x1, zz)]
    hexp = np.column_stack([0.0092 * np.cos(np.arange(6) * math.pi / 3), 0.0092 * np.sin(np.arange(6) * math.pi / 3)])
    return [st.member((px, y, pz), (px, y + 0.0064, pz), hexp, up=(0, 0, 1)) for px, pz in pts]


# vertical geometry measured on sections p.4, p.6, p.7, same for H5 and H6 within 1 cm
# (research/tunnel_k4.md «Норія по вертикалі»)
BOOT_FLOOR_ABOVE_PIT = 0.23         # boot casing bottom above the pit floor
BOOT_AXIS_ABOVE_PIT = 1.095         # tail pulley axis above the pit floor (1.09 / 1.10)
BOOT_TOP_ABOVE_PIT = 1.96           # boot casing top = where the tubes start
HEAD_BELOW_AXIS = 1.025             # head pulley axis above the head casing base (1.03 / 1.02)
# head base vs top platform: the drawing shows the head on a support frame +0.25 (H5) / +0.36 (H6)
HEAD_BASE_TOLERANCE = (-0.05, 0.45)


def build(top_z, pit_z, tube_len, model, feed, phase=0.0):
    """Stack the elevator bottom-up: pit (drawing) -> boot -> legs of tube_len (spec "Нтруб",
    PDF p.8 note 1: noria heights are given by the tubes) -> head.

    top_z (tower top platform, drawing) is not used to place anything: it is the independent
    check. Raises ValueError when the head base misses the top platform.
    model: key of MODELS; feed: "return" (inlet on the down leg, local +X) or "working" (up leg, -X).
    Returns dict of parts (verts, faces) keyed by role, plus label anchors and measure.
    """
    mdl = MODELS[model]
    if feed not in ("return", "working"):
        raise ValueError(f"feed must be 'return' or 'working', got {feed!r}")
    z_boot = pit_z + BOOT_AXIS_ABOVE_PIT
    leg_z0 = pit_z + BOOT_TOP_ABOVE_PIT
    leg_z1 = leg_z0 + tube_len
    z_head = leg_z1 + HEAD_BELOW_AXIS
    head_base = leg_z1 - top_z
    if not HEAD_BASE_TOLERANCE[0] <= head_base <= HEAD_BASE_TOLERANCE[1]:
        raise ValueError(f"noria head base {head_base:+.3f} m from the top platform +{top_z}: "
                         f"tube {tube_len} m and pit {pit_z} m do not fit this tower")
    path = BeltPath(z_boot, z_head)
    parts, labels = {}, []

    parts["belt"] = build_belt(path, mdl)
    parts["buckets"], parts["grain"], n_buckets = build_buckets(path, mdl, phase)

    parts["legs"], parts["leg_flanges"], parts["leg_bolts"], parts["leg_doors"] = build_legs(leg_z0, leg_z1, mdl)

    # ---- head: housing with hood, front cover, pulley, discharge throat and spout
    sx, _ = leg_size(mdl)
    hy = mdl["housing_half_y"]                              # head and boot housing half width across the belt
    hx0 = LEG_CENTRES_X[0] - sx / 2 - 0.02
    hx1 = LEG_CENTRES_X[1] + sx / 2 + 0.30          # room for the discharge throat
    hood_r = (hx1 - hx0) / 2
    head_back, head_front, head_rim = _housing(hx0, hx1, leg_z1, z_head, hy,
                                               arc_top=((hx0 + hx1) / 2, z_head, hood_r))
    drum, lag, shaft = _pulley(z_head, mdl)
    throat = [c.box((hx1 - 0.02, BELT_Y - 0.2, z_head - 0.75), (hx1 + 0.25, BELT_Y + 0.2, z_head - 0.25))]
    spout_end = np.array([hx1 + 0.25, BELT_Y - 1.0, z_head - 1.75])
    spout = [st.rod((hx1 + 0.12, BELT_Y, z_head - 0.7), tuple(spout_end), 0.15, 20)]
    # explosion vent on the hood crown (framed rupture panel)
    vent = [c.box(((hx0 + hx1) / 2 - 0.25, BELT_Y - 0.22, z_head + hood_r - 0.02),
                  ((hx0 + hx1) / 2 + 0.25, BELT_Y + 0.22, z_head + hood_r + 0.05))]
    labels.append(("Вибухорозрядник голови", ((hx0 + hx1) / 2, BELT_Y, z_head + hood_r + 0.05)))
    parts["head"] = c.merge_parts([head_back] + throat)
    parts["head_cover"] = head_front
    parts["head_rim"] = c.merge_parts([head_rim] + _rim_bolts(hx0 - 0.015, hx1 + 0.015, leg_z1 - 0.015, z_head + 0.015,
                                                              BELT_Y + hy + 0.006))
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
    bx0 = LEG_CENTRES_X[0] - sx / 2 - 0.10
    bx1 = LEG_CENTRES_X[1] + sx / 2 + 0.10
    boot_back, boot_front, boot_rim = _housing(bx0, bx1, pit_z + BOOT_FLOOR_ABOVE_PIT, leg_z0, hy)
    wdrum, _, wshaft = _pulley(z_boot, mdl, wing=True)
    takeup = []
    for y in (BELT_Y - 0.42, BELT_Y + 0.42):
        b, s = _bearing(y, z_boot)
        takeup += b
        bsensors += s
        takeup.append(st.rod((CX, y, z_boot + 0.09), (CX, y, leg_z0 + 0.35), 0.015, 8))       # take-up screw
        takeup.append(c.box((CX - 0.2, y - 0.06, z_boot - 0.2), (CX - 0.17, y + 0.06, z_boot + 0.5)))  # slide
        takeup.append(c.box((CX + 0.17, y - 0.06, z_boot - 0.2), (CX + 0.2, y + 0.06, z_boot + 0.5)))
    labels.append(("Натяжний пристрій (гвинтовий)", (CX, BELT_Y + 0.42, leg_z0 + 0.35)))
    # spec PDF p.8: fed on the return (down, +X) leg
    # drawing: a short nozzle on the return-leg face, mouth level with the boot top, ~0.45 m out
    if feed == "return":
        mouth, entry, leg_name = (bx1 + 0.45, BELT_Y, leg_z0), (bx1 - 0.02, BELT_Y, leg_z0 - 0.12), "холосту"
    else:
        mouth, entry, leg_name = (bx0 - 0.45, BELT_Y, leg_z0), (bx0 + 0.02, BELT_Y, leg_z0 - 0.12), "робочу"
    inlet = [st.member(mouth, entry, st.shs(0.30))]
    labels.append((f"Завантажувальний патрубок башмака (на {leg_name} гілку)", (mouth[0], BELT_Y, leg_z0 + 0.1)))
    zc = pit_z + BOOT_FLOOR_ABOVE_PIT
    cleanout = [c.box((bx0 + 0.1, BELT_Y + hy, zc + 0.05), (bx0 + 0.45, BELT_Y + hy + 0.012, zc + 0.35)),
                c.box((bx1 - 0.45, BELT_Y + hy, zc + 0.05), (bx1 - 0.1, BELT_Y + hy + 0.012, zc + 0.35))]
    parts["boot"] = c.merge_parts([boot_back] + inlet)
    parts["boot_cover"] = boot_front
    parts["boot_rim"] = c.merge_parts([boot_rim] + cleanout + _rim_bolts(bx0 - 0.015, bx1 + 0.015, pit_z + BOOT_FLOOR_ABOVE_PIT - 0.015,
                                                                         leg_z0 + 0.015, BELT_Y + hy + 0.006))
    parts["boot_pulley"] = wdrum
    parts["shafts"] = c.merge_parts([parts["shafts"], wshaft])
    parts["takeup"] = c.merge_parts(takeup)

    # ---- sensors (yellow): belt alignment x4, speed, plug, bearing temperature x4
    sensors = list(bsensors)
    for zz in (z_head - 0.2, z_boot + 0.1):
        for xx in (LEG_CENTRES_X[0], LEG_CENTRES_X[1]):
            sensors.append(c.box((xx - 0.035, BELT_Y + hy + 0.006, zz - 0.05),
                                 (xx + 0.035, BELT_Y + hy + 0.09, zz + 0.05)))
    labels.append(("Датчик сходу стрічки", (LEG_CENTRES_X[0], BELT_Y + hy + 0.09, z_head - 0.2)))
    labels.append((f"Барабан голови Ø{round(2000 * PULLEY_R)}, футерований", (CX, BELT_Y + 0.16, z_head + PULLEY_R)))
    labels.append((f"Ківш {bucket_volume_l(mdl):.1f} л, крок {round(1000 * mdl['pitch'])} мм".replace(".", ","),
                   (CX - BELT_R - 0.1, BELT_Y, z_head - 0.5)))
    labels.append(("Барабан башмака самоочисний (крильчастий)", (CX, BELT_Y + 0.16, z_boot + PULLEY_R)))
    sensors.append(st.rod((CX, BELT_Y + 0.62, z_boot), (CX, BELT_Y + 0.72, z_boot), 0.03, 12))
    labels.append(("Датчик швидкості (контроль руху стрічки)", (CX, BELT_Y + 0.72, z_boot)))
    ps = (np.array([hx1 + 0.12, BELT_Y, z_head - 0.7]) + spout_end) / 2
    sensors.append(st.rod(tuple(ps + [0.14, 0, 0]), tuple(ps + [0.26, 0, 0]), 0.025, 12))
    labels.append(("Датчик підпору самопливу", tuple(ps + [0.26, 0, 0])))
    parts["sensors"] = c.merge_parts(sensors)

    measure = {
        "model": model,
        "feed": feed,
        "belt_speed_m_s": mdl["belt_speed"],
        "pulley_diameter_m": 2 * PULLEY_R,
        "pulley_rpm": round(60 * mdl["belt_speed"] / (math.pi * 2 * PULLEY_R), 1),
        "pole_distance_m": round(895 / (60 * mdl["belt_speed"] / (math.pi * 2 * PULLEY_R)) ** 2, 3),
        "discharge": "centrifugal" if 895 / (60 * mdl["belt_speed"] / (math.pi * 2 * PULLEY_R)) ** 2 < PULLEY_R else "gravity",
        "bucket_volume_l_model": round(bucket_volume_l(mdl), 2),
        "bucket_volume_l_table": mdl["table_volume_l"],
        "capacity_t_h_model": round(capacity_t_h(mdl, feed), 1),
        "bucket_mm": [round(1000 * v) for v in mdl["bucket"]],
        "belt_width_mm": round(1000 * mdl["belt_w"]),
        "leg_length_m": round(leg_z1 - leg_z0, 3),
        "head_base_above_top_platform_m": round(head_base, 3),
        "bucket_wall_mm": 6.5,
        "bucket_bolts": "4 x M8 DIN 15237, 74 mm pitch",
        "bucket_pitch_m": mdl["pitch"],
        "buckets": n_buckets,
        "belt_loop_m": round(path.length, 2),
        "leg_clear_mm": [round(1000 * mdl["leg_clear"][1]), round(1000 * mdl["leg_clear"][0])],
        "housing_width_m": round(2 * hy, 3),
        "leg_centres_x_m": [round(x, 3) for x in LEG_CENTRES_X],
        "head_pulley_z_m": round(z_head, 3),
        "boot_pulley_z_m": round(z_boot, 3),
        "motor_kw": MOTOR_KW,
    }
    anchors = {"spout_end": tuple(spout_end), "z_head": z_head, "z_boot": z_boot,
               "inlet_mouth": mouth,
               "boot_box": ((bx0, BELT_Y - hy, pit_z + BOOT_FLOOR_ABOVE_PIT), (bx1, BELT_Y + hy, leg_z0))}
    return parts, labels, measure, anchors
