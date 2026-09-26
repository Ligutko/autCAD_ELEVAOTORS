"""K3. Silo-top galleries with chain conveyors У13-ТЦС-320, and the bridges between the towers.

Site coordinates (metres). Every position comes from SITE.json `silo_top_galleries` and `bridges`,
measured by vectors on PDF p.3-p.7 (research/tunnel_k4.md «Естакади і мости (K3)»). EST where noted.
"""

import math

import numpy as np

from . import common as c
from . import steel as st

CONV_SECTION = 2.0          # EST: bolted casing sections
CONV_END = 0.30             # EST: casing beyond the pulley axis at head and tail
CROSS_BEAM_STEP = 1.5       # EST: cross beams under the gallery deck
BRIDGE_PANEL = 2.4          # EST: bridge truss panel (not dimensioned on the drawing)


def _frame(p0, p1):
    """Unit vectors along the run (d), across (s) and up for a straight run p0 -> p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    length = np.linalg.norm(d)
    d = d / length
    s = np.cross([0, 0, 1.0], d)
    s /= np.linalg.norm(s)
    return p0, d, s, length


def conveyor(tail, head, width, height, drive_side=1.0):
    """Chain conveyor casing between the tail and head pulley axes (x, y, z of the axis).

    The casing runs CONV_END beyond each axis; drive (reducer + motor) sits at the head on the
    `drive_side` of the run. Returns parts dict.
    """
    tail, head = np.asarray(tail, float), np.asarray(head, float)
    o, d, s, length = _frame(tail, head)
    casing, flanges, drive, motor = [], [], [], []
    hw, hh = width / 2, height / 2
    prof = np.array([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)])
    casing.append(st.member(o - d * CONV_END, o + d * (length + CONV_END), prof, up=(0, 0, 1)))
    for t in np.arange(-CONV_END, length + CONV_END + 1e-6, CONV_SECTION):
        flanges.append(st.member(o + d * (t - 0.012), o + d * (t + 0.012),
                                 np.array([(-hw - 0.04, -hh - 0.04), (hw + 0.04, -hh - 0.04),
                                           (hw + 0.04, hh + 0.03), (-hw - 0.04, hh + 0.03)]), up=(0, 0, 1)))
    for at, grow in ((o + d * length, 0.06), (o, 0.04)):           # head and tail boxes
        casing.append(st.member(at - d * 0.25, at + d * 0.25, prof * (1 + grow / hw), up=(0, 0, 1)))
    gb = o + d * length + s * drive_side * (hw + 0.25)
    drive.append(c.box(tuple(gb - [0.18, 0.18, 0.22]), tuple(gb + [0.18, 0.18, 0.22])))
    motor.append(st.rod(gb + [0, 0, 0.3], gb + [0, 0, 0.3] - d * 0.6, 0.15, 20))
    return {"casing": c.merge_parts(casing), "flanges": c.merge_parts(flanges),
            "drive": c.merge_parts(drive), "motor": c.merge_parts(motor)}


def silo_row_gallery(g, line):
    """Gallery over one silo row: box beams on posts carried by the silo walls, grating deck,
    platforms over the silo centres, handrails, the ТЦС conveyor on the row axis and its drops."""
    y = line["row_y"]
    x0, x1 = sorted(line["x_ends"])
    ya, yb = (y + v for v in g["y_rel_row"])
    bz0, bz1 = g["beam_z"]
    dz = g["deck_z"]
    heavy, light, deck, rails, toes, posts, gates, spouts = [], [], [], [], [], [], [], []
    for yy in (ya, yb):                                             # two edge box beams
        heavy.append(c.box((x0, yy - 0.08, bz0), (x1, yy + 0.08, bz1)))
    for x in np.arange(x0, x1 + 1e-6, CROSS_BEAM_STEP):
        heavy.append(c.box((x - 0.04, ya, bz1 - 0.12), (x + 0.04, yb, bz1)))
    deck.append(st.grating_panel(x0, ya, x1, yb, dz))
    pf = g["platforms_at_silo_centre"]
    for dx in line["drops_x"]:
        deck.append(st.grating_panel(dx - pf["len"] / 2, yb, dx + pf["len"] / 2, y + pf["y_to"], dz))
        heavy.append(c.box((dx - pf["len"] / 2, yb, bz0), (dx - pf["len"] / 2 + 0.16, y + pf["y_to"], bz1)))
        heavy.append(c.box((dx + pf["len"] / 2 - 0.16, yb, bz0), (dx + pf["len"] / 2, y + pf["y_to"], bz1)))
    for yy in (ya + 0.05, yb - 0.05):
        t, o = st.guard_rail([(x0, yy), (x1, yy)], dz)
        rails.append(t)
        toes.append(o)
    sp = g["supports"]
    pz0, pz1 = sp["post_z"]
    for px in sp["posts_x"]:
        if not x0 - 0.5 <= px <= x1 + 0.5:
            continue
        for yy in (ya, yb):
            posts.append(st.member((px, yy, pz0), (px, yy, pz1), st.SHS_100))
            reach = 1.0                                             # 45 deg knee braces
            for dxb in (-reach, reach):
                if x0 <= px + dxb <= x1:
                    light.append(st.member((px, yy, pz1 - reach), (px + dxb, yy, bz0), st.L75))
        posts.append(c.box((px - 0.2, ya - 0.15, pz0 - 0.25), (px + 0.2, yb + 0.15, pz0)))       # wall bracket
        heavy.append(st.member((px, ya, pz1 - 0.1), (px, yb, pz1 - 0.1), st.HEA200))
    cz0, cz1 = g["conveyor"]["casing_z"]
    axis_z = (cz0 + cz1) / 2
    w, h = g["conveyor"]["casing_w"], cz1 - cz0
    conv = conveyor((line["tail_x"], y, axis_z), (line["head_x"], y, axis_z), w, h, drive_side=1.0)
    for dx in line["drops_x"]:                                      # drop gate on the casing and spout to the roof spout
        gates.append(c.box((dx - 0.25, y - w / 2 - 0.06, cz0 - 0.18), (dx + 0.25, y + w / 2 + 0.06, cz0)))
        gates.append(c.box((dx + 0.25, y - 0.07, cz0 - 0.15), (dx + 0.6, y + 0.07, cz0 - 0.03)))
        spouts.append(st.member((dx, y, cz0 - 0.18), (dx, y, g["roof_spout_z"]), st.shs(0.30)))
    return {"heavy": c.merge_parts(heavy), "light": c.merge_parts(light), "deck": c.merge_parts(deck),
            "rails": c.merge_parts(rails), "toes": c.merge_parts(toes), "posts": c.merge_parts(posts),
            "spouts": c.merge_parts(spouts), "gates": c.merge_parts(gates),
            **{"conv_" + k: v for k, v in conv.items()}}


def bridge(b):
    """Truss bridge between towers along Y: horizontal deck, two side trusses below it, rails,
    and its conveyors side by side, each with its own measured tail and head (sloped ~1.5 deg)."""
    xa, xb = b["x"]
    ya, yb = b["y"]
    top, bot, tb = b["deck_top_z"], b["deck_bot_z"], b["truss_bottom_z"]
    heavy, light, deck, rails, toes = [], [], [], [], []
    n = max(2, int(round((yb - ya) / BRIDGE_PANEL)))
    for x in (xa, xb):
        heavy.append(st.member((x, ya, bot - 0.1), (x, yb, bot - 0.1), st.HEA200))
        heavy.append(st.member((x, ya, tb + 0.1), (x, yb, tb + 0.1), st.HEA200))
        for k in range(n):
            y0, y1 = ya + (yb - ya) * k / n, ya + (yb - ya) * (k + 1) / n
            ym = (y0 + y1) / 2
            light.append(st.member((x, y0, tb + 0.1), (x, ym, bot - 0.1), st.shs(0.12)))
            light.append(st.member((x, ym, bot - 0.1), (x, y1, tb + 0.1), st.shs(0.12)))
    for k in range(n + 1):
        yk = ya + (yb - ya) * k / n
        heavy.append(st.member((xa, yk, bot - 0.1), (xb, yk, bot - 0.1), st.IPE160))
        heavy.append(st.member((xa, yk, tb + 0.1), (xb, yk, tb + 0.1), st.L90))
        if k < n:
            light.append(st.member((xa, yk, tb + 0.1), (xb, ya + (yb - ya) * (k + 1) / n, tb + 0.1), st.L75))
    deck.append(c.box((xa, ya, bot), (xb, yb, top)))
    for x in (xa + 0.05, xb - 0.05):
        t, o = st.guard_rail([(x, ya), (x, yb)], top)
        rails.append(t)
        toes.append(o)
    convs = []
    for cv in b["conveyors"]:
        w, h = cv.get("casing_w", 0.40), cv.get("casing_h", 0.50)
        if "tail" in cv:
            tail = (cv["x"], cv["tail"][0], cv["tail"][1])
            head = (cv["x"], cv["head"][0], cv["head"][1])
        else:
            tail = (cv["x"], cv["y"][1], cv["axis_z"])
            head = (cv["x"], cv["y"][0], cv["axis_z"])
        side = 1.0 if cv["x"] > (xa + xb) / 2 else -1.0
        convs.append(conveyor(tail, head, w, h, drive_side=side))
    merged = {"heavy": c.merge_parts(heavy), "light": c.merge_parts(light), "deck": c.merge_parts(deck),
              "rails": c.merge_parts(rails), "toes": c.merge_parts(toes)}
    for key in ("casing", "flanges", "drive", "motor"):
        merged["conv_" + key] = c.merge_parts([cv[key] for cv in convs])
    return merged


def conveyor_axis(site, cid):
    """(tail, head) axis points and (width, height) of a named ТЦС conveyor, for checks."""
    g = site["silo_top_galleries"]
    for line in g["lines"]:
        if line["id"] == cid:
            cz0, cz1 = g["conveyor"]["casing_z"]
            z = (cz0 + cz1) / 2
            return (np.array([line["tail_x"], line["row_y"], z]), np.array([line["head_x"], line["row_y"], z]),
                    g["conveyor"]["casing_w"], cz1 - cz0)
    for b in site["bridges"]:
        for cv in b["conveyors"]:
            if cv["id"] == cid:
                if "tail" in cv:
                    t = np.array([cv["x"], cv["tail"][0], cv["tail"][1]])
                    h = np.array([cv["x"], cv["head"][0], cv["head"][1]])
                else:
                    t = np.array([cv["x"], cv["y"][1], cv["axis_z"]])
                    h = np.array([cv["x"], cv["y"][0], cv["axis_z"]])
                return t, h, cv.get("casing_w", 0.40), cv.get("casing_h", 0.50)
    raise KeyError(cid)


def slope_deg(tail, head):
    run = np.linalg.norm((head - tail)[:2])
    return math.degrees(math.atan2(head[2] - tail[2], run))
