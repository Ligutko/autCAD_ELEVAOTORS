"""K3. Silo-top gallery with chain conveyor, and truss bridges between towers.

Works in site coordinates (metres). Source tags as in silo_msvu220.py.
"""

import math

import numpy as np

from . import common as c
from . import steel as st

# ------------------------------------------------------------------ silo-top gallery (PDF p.3, p.6, p.7)
GAL_WIDTH = 1.30            # PDF p.3: strip ~1.3 m on plan
GAL_TRUSS_H = 1.13          # PDF p.6, p.7: 1130
GAL_PANEL = 1.5             # EST: truss panel length
SUPPORT_OFFSET = 11.35      # PDF p.6: posts just outside the eave, ±11.3 m from the silo axis
KICKER_OFFSET = 8.8         # PDF p.6: diagonal strut meets the gallery at ±8.8 m

# ------------------------------------------------------------------ chain conveyor У13-ТЦС-320
CONV_W = 0.42               # EST: casing outside, 320 mm trough (catalogue) + walls and flanges
CONV_H = 0.46               # EST
CONV_SECTION = 2.0          # EST: bolted casing sections
CONV_Y = -0.25              # EST: conveyor off-centre, walkway on the +Y side
CONV_KW = 11.0              # catalogue / PDF p.8

# ------------------------------------------------------------------ tower bridge (PDF p.3, p.4)
BRIDGE_W = 2.80             # PDF p.3: 950 + 900 + 950
BRIDGE_H = 2.40             # PDF p.4: truss between +23.2 and +25.6


def _frame(p0, p1):
    """Unit vectors along the run (d), across (s) and up for a straight run p0 -> p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    length = np.linalg.norm(d)
    d = d / length
    s = np.cross([0, 0, 1.0], d)
    s /= np.linalg.norm(s)
    return p0, d, s, length


def conveyor(p0, p1, drive_at_end=True, y_off=0.0):
    """Chain conveyor casing along p0 -> p1 at casing bottom height. Returns parts dict."""
    o, d, s, length = _frame(p0, p1)
    o = o + s * y_off
    casing, flanges, drive, motor = [], [], [], []
    hw = CONV_W / 2

    def at(t, side, up):
        return o + d * t + s * side + np.array([0, 0, up])

    casing.append(st.member(at(0, 0, CONV_H / 2), at(length, 0, CONV_H / 2),
                            np.array([(-hw, -CONV_H / 2), (hw, -CONV_H / 2), (hw, CONV_H / 2), (-hw, CONV_H / 2)]),
                            up=(0, 0, 1)))
    for t in np.arange(0.0, length + 1e-6, CONV_SECTION):
        flanges.append(st.member(at(t - 0.012, 0, CONV_H / 2), at(t + 0.012, 0, CONV_H / 2),
                                 np.array([(-hw - 0.04, -CONV_H / 2 - 0.04), (hw + 0.04, -CONV_H / 2 - 0.04),
                                           (hw + 0.04, CONV_H / 2 + 0.03), (-hw - 0.04, CONV_H / 2 + 0.03)])))
    # head (drive) and tail boxes
    t_head = length if drive_at_end else 0.0
    sign = 1.0 if drive_at_end else -1.0
    casing.append(st.member(at(t_head - sign * 0.2, 0, 0.35), at(t_head + sign * 0.6, 0, 0.35),
                            np.array([(-hw - 0.05, -0.37), (hw + 0.05, -0.37), (hw + 0.05, 0.40),
                                      (-hw - 0.05, 0.40)])))
    t_tail = 0.0 if drive_at_end else length
    casing.append(st.member(at(t_tail + sign * 0.2, 0, 0.3), at(t_tail - sign * 0.5, 0, 0.3),
                            np.array([(-hw - 0.04, -0.32), (hw + 0.04, -0.32), (hw + 0.04, 0.33),
                                      (-hw - 0.04, 0.33)])))
    # shaft-mounted reducer + 11 kW motor on the walkway side of the head
    gb = at(t_head + sign * 0.25, hw + 0.05, 0.40)
    drive.append(c.box(tuple(gb - [0.2, 0.2, 0.25]), tuple(gb + [0.2, 0.2, 0.25])))
    drive[-1] = (drive[-1][0] + s * 0.18, drive[-1][1])
    motor.append(st.rod(gb + s * 0.35 + d * 0.0, gb + s * 0.35 - d * sign * 0.62, 0.17, 20))
    return {"casing": c.merge_parts(casing), "flanges": c.merge_parts(flanges),
            "drive": c.merge_parts(drive), "motor": c.merge_parts(motor)}


def silo_row_gallery(p0, p1, deck_z, silo_positions, silo_eave_z=14.976 + 0.6, silo_spout_z=21.422 + 0.6):
    """Open truss gallery on posts carried by the silo walls, with conveyor and silo spouts.

    p0, p1: (x, y) plan end points. silo_positions: (x, y) of the silos under it.
    """
    a = np.array([p0[0], p0[1], deck_z])
    b = np.array([p1[0], p1[1], deck_z])
    o, d, s, length = _frame(a, b)
    hw = GAL_WIDTH / 2
    heavy, light, deck, rails, spouts, gates, posts = [], [], [], [], [], [], []

    def at(t, side, up=0.0):
        return o + d * t + s * side + np.array([0, 0, up])

    # two side trusses: bottom chord UPN160, top chord doubles as handrail, verticals + diagonals L50
    n = max(1, int(round(length / GAL_PANEL)))
    for side in (-hw, hw):
        heavy.append(st.member(at(0, side), at(length, side), st.UPN160, roll=0.0))
        rails.append(st.rod(at(0, side, GAL_TRUSS_H), at(length, side, GAL_TRUSS_H), 0.030, 10))
        rails.append(st.rod(at(0, side, 0.55), at(length, side, 0.55), st.RAIL_R, 8))
        for k in range(n + 1):
            t = length * k / n
            light.append(st.member(at(t, side, 0.08), at(t, side, GAL_TRUSS_H), st.L50))
            if k < n:
                t2 = length * (k + 1) / n
                if k % 2 == 0:
                    light.append(st.member(at(t, side, 0.08), at(t2, side, GAL_TRUSS_H - 0.03), st.L50))
                else:
                    light.append(st.member(at(t, side, GAL_TRUSS_H - 0.03), at(t2, side, 0.08), st.L50))
    for k in range(n + 1):
        t = length * k / n
        heavy.append(st.member(at(t, -hw, -0.04), at(t, hw, -0.04), st.L75))       # floor beams
    # deck grating on the walkway side and under the conveyor
    deck.append(_deck_panel(o, d, s, length, -hw, hw, deck_z))
    # conveyor on the deck
    conv = conveyor(at(0, CONV_Y, 0.03), at(length, CONV_Y, 0.03), drive_at_end=True)
    # supports on every silo: posts on wall brackets at ±SUPPORT_OFFSET, kickers to ±KICKER_OFFSET
    for sx, sy in silo_positions:
        t_c = np.dot(np.array([sx, sy, deck_z]) - o, d)
        for sign in (-1, 1):
            t_post = t_c + sign * SUPPORT_OFFSET
            if not (-0.5 <= t_post <= length + 0.5):
                continue
            base_z = silo_eave_z - 1.5
            for side in (-hw, hw):
                posts.append(st.member(at(t_post, side, base_z - deck_z), at(t_post, side, -0.1), st.SHS_100))
                light.append(st.member(at(t_post, side, base_z - deck_z + 1.2),
                                       at(t_c + sign * KICKER_OFFSET, side, -0.12), st.L75))
            heavy.append(st.member(at(t_post, -hw - 0.1, -0.12), at(t_post, hw + 0.1, -0.12), st.HEA200))
            heavy.append(st.member(at(t_post, -hw, base_z - deck_z + 0.2), at(t_post, hw, base_z - deck_z + 0.2),
                                   st.SHS_100))
            # wall bracket: plate on the silo stiffeners
            bracket = at(t_post, 0, base_z - deck_z)
            posts.append(c.box(tuple(bracket - [0.25, hw + 0.15, 0.3]), tuple(bracket + [0.25, hw + 0.15, 0.05])))
        # discharge gate and spout down to the silo loading spout
        gate = at(t_c, CONV_Y, 0.0)
        gates.append(c.box(tuple(gate - [0.3, 0.3, 0.35]), tuple(gate + [0.3, 0.3, -0.02])))
        gates.append(c.box(tuple(gate + [0.3, -0.08, -0.3]), tuple(gate + [0.75, 0.08, -0.12])))   # actuator
        spouts.append(st.rod(gate - [0, 0, 0.35], (sx, sy, silo_spout_z), 0.2, 20))
    return {
        "heavy": c.merge_parts(heavy), "light": c.merge_parts(light), "deck": c.merge_parts(deck),
        "rails": c.merge_parts(rails), "posts": c.merge_parts(posts), "spouts": c.merge_parts(spouts),
        "gates": c.merge_parts(gates), **{"conv_" + k: v for k, v in conv.items()},
    }


def _deck_panel(o, d, s, length, s0, s1, z):
    corners = [o + d * 0 + s * s0, o + d * length + s * s0, o + d * length + s * s1, o + d * 0 + s * s1]
    top = np.array([[p[0], p[1], z] for p in corners])
    bottom = top - [0, 0, 0.03]
    v = np.concatenate([bottom, top])
    f = np.array([(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    return v, f


def tower_bridge(p0, p1, z0, z1, conveyors=2):
    """Warren truss bridge, deck on the top chords (conveyors ride on top, PDF p.4)."""
    a = np.array([p0[0], p0[1], z0])
    b = np.array([p1[0], p1[1], z1])
    o, d, s, length = _frame(a, b)
    hw = BRIDGE_W / 2
    heavy, light, deck, rails, toes = [], [], [], [], []
    rise = z1 - z0

    def at(t, side, up=0.0):
        return o + d * t + s * side + np.array([0, 0, up + rise * t / length - (d[2] * t)])

    n = max(2, int(round(length / 2.4)))
    for side in (-hw, hw):
        heavy.append(st.member(at(0, side), at(length, side), st.HEA200))
        heavy.append(st.member(at(0, side, -BRIDGE_H), at(length, side, -BRIDGE_H), st.HEA200))
        for k in range(n):
            t0, t1 = length * k / n, length * (k + 1) / n
            tm = (t0 + t1) / 2
            light.append(st.member(at(t0, side, -BRIDGE_H), at(tm, side, -0.1), st.shs(0.12)))
            light.append(st.member(at(tm, side, -0.1), at(t1, side, -BRIDGE_H), st.shs(0.12)))
    for k in range(n + 1):
        t = length * k / n
        heavy.append(st.member(at(t, -hw, -0.1), at(t, hw, -0.1), st.IPE160))
        heavy.append(st.member(at(t, -hw, -BRIDGE_H), at(t, hw, -BRIDGE_H), st.L90))
        if k < n:
            t1 = length * (k + 1) / n
            light.append(st.member(at(t, -hw, -BRIDGE_H), at(t1, hw, -BRIDGE_H), st.L75))   # plan bracing
    deck.append(_deck_panel(o, d, s, length, -hw, hw, 0.0) if abs(rise) < 1e-6 else _sloped_deck(at, length, hw))
    for side in (-hw + 0.05, hw - 0.05):
        pts = [at(t, side, 0.0) for t in np.linspace(0, length, 2)]
        tubes, toe = _rail_line(pts)
        rails.append(tubes)
        toes.append(toe)
    convs = []
    for k in range(conveyors):
        off = -hw + 0.95 * 0.5 + k * (0.95 + 0.9)
        convs.append(conveyor(at(0, off, 0.05), at(length, off, 0.05), drive_at_end=(k == 0)))
    merged = {"heavy": c.merge_parts(heavy), "light": c.merge_parts(light), "deck": c.merge_parts(deck),
              "rails": c.merge_parts(rails), "toes": c.merge_parts(toes)}
    for key in ("casing", "flanges", "drive", "motor"):
        merged["conv_" + key] = c.merge_parts([cv[key] for cv in convs])
    return merged


def _sloped_deck(at, length, hw):
    p = [at(0, -hw), at(length, -hw), at(length, hw), at(0, hw)]
    top = np.array(p)
    v = np.concatenate([top - [0, 0, 0.03], top])
    f = np.array([(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
    return v, f


def _rail_line(pts):
    """Guard rail along a possibly sloped straight line."""
    a, b = np.asarray(pts[0]), np.asarray(pts[-1])
    length = np.linalg.norm(b - a)
    n = max(1, int(math.ceil(length / st.POST_STEP)))
    tubes, toes = [], []
    for k in range(n + 1):
        p = a + (b - a) * k / n
        tubes.append(st.rod(p, p + [0, 0, st.RAIL_TOP], 0.024, 8))
    for h in (st.RAIL_TOP, st.RAIL_KNEE):
        tubes.append(st.rod(a + [0, 0, h], b + [0, 0, h], st.RAIL_R, 10))
    toes.append(st.member(a + [0, 0, st.TOE_H / 2], b + [0, 0, st.TOE_H / 2], st.flat(st.TOE_H, 0.004)))
    return c.merge_parts(tubes), c.merge_parts(toes)
