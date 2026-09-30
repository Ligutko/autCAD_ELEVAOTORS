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
# judgment (7C, 2026-09-28): the step put a cross beam exactly on every silo drop (24 m = 16 x 1.5),
# the □300 spout ran through it. The opening is framed instead: spout half 0.15 + 0.05 clear + beam half 0.04
DROP_OPENING_HALF = 0.24
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
        if any(abs(x - dx) < DROP_OPENING_HALF for dx in line["drops_x"]):
            continue                                                # the silo drop passes here: no beam
        heavy.append(c.box((x - 0.04, ya, bz1 - 0.12), (x + 0.04, yb, bz1)))
    for dx in line["drops_x"]:                                      # trimmer beams frame the drop opening
        for s in (-1.0, 1.0):
            xt = dx + s * DROP_OPENING_HALF
            heavy.append(c.box((xt - 0.04, ya, bz1 - 0.12), (xt + 0.04, yb, bz1)))
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
    # the drive on the walkway (+Y) side: conveyor() puts drive_side +1 on cross(Z, run), which is -Y for a run
    # to -X (T8, T12 had it hanging past the deck edge, outside the rail, until 2026-09-30)
    walk = 1.0 if g.get("walkway_side", "+Y") == "+Y" else -1.0
    conv = conveyor((line["tail_x"], y, axis_z), (line["head_x"], y, axis_z), w, h,
                    drive_side=walk * math.copysign(1.0, line["head_x"] - line["tail_x"]))
    for dx in line["drops_x"]:                                      # drop gate on the casing and spout to the roof spout
        gates.append(c.box((dx - 0.25, y - w / 2 - 0.06, cz0 - 0.18), (dx + 0.25, y + w / 2 + 0.06, cz0)))
        gates.append(c.box((dx + 0.25, y - 0.07, cz0 - 0.15), (dx + 0.6, y + 0.07, cz0 - 0.03)))
        spouts.append(st.member((dx, y, cz0 - 0.18), (dx, y, g["roof_spout_z"]), st.shs(0.30)))
    return {"heavy": c.merge_parts(heavy), "light": c.merge_parts(light), "deck": c.merge_parts(deck),
            "rails": c.merge_parts(rails), "toes": c.merge_parts(toes), "posts": c.merge_parts(posts),
            "spouts": c.merge_parts(spouts), "gates": c.merge_parts(gates),
            **{"conv_" + k: v for k, v in conv.items()}}


def bridge(b, by_conveyor=False):
    """Truss bridge between towers along Y: horizontal deck, two side trusses below it, rails,
    and its conveyors side by side, each with its own measured tail and head (sloped ~1.5 deg).
    by_conveyor: one part per conveyor ("t7_conv_casing", ...) instead of both merged ("conv_casing"),
    so the scene can highlight one process node (routes.py, phase 7C)."""
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
        if by_conveyor:
            for spec, cv in zip(b["conveyors"], convs):
                merged[f"{spec['id'].lower()}_conv_{key}"] = cv[key]
        else:
            merged["conv_" + key] = c.merge_parts([cv[key] for cv in convs])
    return merged


ESTOP_NEAR = (0.6, 4.0)     # judgment: station in sight of the drive (bridge drives sit in the tower head rooms,
                            # 2.5-3.5 m past the bridge end)
ESTOP_CLEAR = 0.15          # EST: station clear of casings, drives and gates in plan
ESTOP_ALONG = 0.07          # station half length along the rail (box 116.5 mm)
ESTOP_POST_GAP = 0.10       # stand pipe this far from a rail post along the rail
ROPE_OFF = 0.08             # EST: rope this far out of the casing side, on brackets bolted to it (as in the tunnels)
ROPE_UNDER_TOP = 0.0        # EST: rope level with the casing top edge (follows a sloped casing; 0.63-1.4 m
                            # over the deck, the reach band is 0.6-1.7 m)
ROPE_END_GAP = 1.0          # EST: rope anchor 1 m short of the deck end
ROPE_DRIVE_GAP = 1.2        # EST: switch 1.2 m from the head (drive) end, as in the tunnels


def upper_conveyors(site):
    """Ids of the conveyors on the silo-top galleries and the bridges."""
    return [l["id"] for l in site["silo_top_galleries"]["lines"]] + [cv["id"] for b in site["bridges"] for cv in b["conveyors"]]


def hands_layout(site, cid):
    """Where the hands of an upper conveyor go. Returns a dict: host id, deck z, the walkway normal n (plan unit
    vector from the casing to the walkway: +Y on the galleries, out to the nearer bridge side on the bridges), the rail
    line on that side (point, unit direction, span), the conveyor axis, casing size, the drive centre, the deck span
    along the run and the plan boxes (x0, y0, x1, y1, z_top) of everything on the deck."""
    g = site["silo_top_galleries"]
    for line in g["lines"]:
        if line["id"] != cid:
            continue
        y = line["row_y"]
        x0, x1 = sorted(line["x_ends"])
        ya, yb = (y + v for v in g["y_rel_row"])
        tail, head, w, h = conveyor_axis(site, cid)
        parts = silo_row_gallery(g, line)
        rail_y = yb - 0.05
        out = dict(host=cid, kind="gallery", deck_z=g["deck_z"], n=np.array([0.0, 1.0]),
                   rail=(np.array([x0, rail_y]), np.array([1.0, 0.0]), x1 - x0), deck_span=(x0, x1), along=0,
                   tail=tail, head=head, w=w, h=h, drive=_centre(parts["conv_drive"]), casing=_plan_box(parts["conv_casing"]),
                   boxes=[_plan_box(parts[k]) for k in ("conv_casing", "conv_drive", "conv_motor")] +
                   [_plan_box(p) for p in _split_boxes(parts["gates"], line["drops_x"])])
        return out
    for b in site["bridges"]:
        for cv in b["conveyors"]:
            if cv["id"] != cid:
                continue
            xa, xb = b["x"]
            ya, yb = b["y"]
            sign = 1.0 if cv["x"] > (xa + xb) / 2 else -1.0
            tail, head, w, h = conveyor_axis(site, cid)
            parts = bridge(b, by_conveyor=True)
            rail_x = xb - 0.05 if sign > 0 else xa + 0.05
            boxes = []
            for other in b["conveyors"]:
                k = other["id"].lower()
                boxes += [_plan_box(parts[f"{k}_conv_{p}"]) for p in ("casing", "drive", "motor")]
            return dict(host=b["id"], kind="bridge", deck_z=b["deck_top_z"], n=np.array([sign, 0.0]),
                        rail=(np.array([rail_x, ya]), np.array([0.0, 1.0]), yb - ya), deck_span=(ya, yb), along=1,
                        tail=tail, head=head, w=w, h=h, drive=_centre(parts[f"{cid.lower()}_conv_drive"]),
                        casing=_plan_box(parts[f"{cid.lower()}_conv_casing"]), boxes=boxes)
    raise KeyError(cid)


def _centre(data):
    v = np.asarray(data[0], float)
    return (v.min(0) + v.max(0)) / 2


def _plan_box(data):
    v = np.asarray(data[0], float)
    return (v[:, 0].min(), v[:, 1].min(), v[:, 0].max(), v[:, 1].max(), v[:, 2].max())


def _split_boxes(data, xs):
    """A merged part split by the nearest x of `xs` (one box per drop gate)."""
    v, f = data
    v = np.asarray(v, float)
    out = []
    for x in xs:
        sel = np.abs(v[:, 0] - x) < 1.0
        if sel.any():
            out.append((v[sel], None))
    return out


def estop_place(site, cid, lay=None):
    """(x, y, z, angle, rail_t) of the rail-mounted E-stop station of an upper conveyor: on the walkway rail, clear of
    the rail posts, casings, drives and gates that reach over the stand pipe start, ESTOP_NEAR from the drive;
    a spot past the casing end (full walkway width) wins over one beside a casing, then the nearest to the drive."""
    from . import controls as ctl
    lay = lay or hands_layout(site, cid)
    post = ctl.ex_estop_post(-1, stand="rail")
    off, dp = post["dims"]["rail_offset"], post["dims"]["box"][2]
    p0, u, length = lay["rail"]
    n = lay["n"]
    n_post = max(1, int(math.ceil(length / st.POST_STEP)))
    posts_t = [length * k / n_post for k in range(n_post + 1)]
    z_low = lay["deck_z"] + ctl.RAIL_PIPE_FROM
    casing = lay["casing"]
    best = None
    for t in np.arange(0.2, length - 0.2 + 1e-9, 0.05):
        if any(abs(t - pt) < ESTOP_POST_GAP for pt in posts_t):
            continue
        rail_pt = p0 + u * t
        centre = rail_pt + n * off                                 # outside the rail
        front, back = centre - n * (dp / 2 + 0.05), centre + n * dp / 2
        pts = np.array([back + u * ESTOP_ALONG, back - u * ESTOP_ALONG, front + u * ESTOP_ALONG, front - u * ESTOP_ALONG])
        lo, hi = pts.min(0), pts.max(0)
        if any(bx[4] > z_low and lo[0] < bx[2] + ESTOP_CLEAR and hi[0] > bx[0] - ESTOP_CLEAR and lo[1] < bx[3] + ESTOP_CLEAR
               and hi[1] > bx[1] - ESTOP_CLEAR for bx in lay["boxes"]):
            continue
        d = math.hypot(*(centre - lay["drive"][:2]))
        if not ESTOP_NEAR[0] <= d <= ESTOP_NEAR[1]:
            continue
        beside = casing[lay["along"]] - 0.1 < centre[lay["along"]] < casing[lay["along"] + 2] + 0.1
        key = (beside, d)
        if best is None or key < best[0]:
            best = (key, centre, t)
    if best is None:
        raise ValueError(f"{cid}: no free spot on the walkway rail for the E-stop station")
    _, (x, y), t = best
    ang = math.atan2(n[1], n[0]) - math.pi / 2                    # local +Y (the back) turns to n: faces the walkway
    return float(x), float(y), float(lay["deck_z"]), ang, float(t)


def rope_points(site, cid, lay=None):
    """(a, b) rope ends of the ZQ 900 pull-cord: along the walkway side of the casing, ROPE_UNDER_TOP under its top
    edge (following the slope), from ROPE_DRIVE_GAP off the head to the tail, both kept ROPE_END_GAP inside the deck."""
    lay = lay or hands_layout(site, cid)
    tail, head = lay["tail"], lay["head"]
    k = lay["along"]
    s0, s1 = lay["deck_span"]
    lo, hi = s0 + ROPE_END_GAP, s1 - ROPE_END_GAP
    step = 1.0 if tail[k] > head[k] else -1.0                      # from the head towards the tail

    def at(s):
        f = (s - tail[k]) / (head[k] - tail[k])
        p = tail + (head - tail) * f
        q = p.copy()
        q[:2] = p[:2] + lay["n"] * (lay["w"] / 2 + ROPE_OFF)
        q[2] = p[2] + lay["h"] / 2 - ROPE_UNDER_TOP
        return q

    sa = min(max(head[k] + step * ROPE_DRIVE_GAP, lo), hi)
    sb = min(max(tail[k], lo), hi)
    return at(sa), at(sb)


def build_controls(site, cid, lay=None):
    """Hands of an upper conveyor ({group: mesh}, info): the rail-mounted Ex E-stop station by the drive end and the
    ZQ 900 rope-pull along the walkway side of the casing (kit/controls.py)."""
    from . import controls as ctl
    lay = lay or hands_layout(site, cid)
    x, y, z, ang, _ = estop_place(site, cid, lay)
    post = ctl.ex_estop_post(-1, stand="rail")
    groups = {}
    for name, (v, f) in post["parts"].items():
        key = "estop_red" if name == "mushroom" else ("estop_tag" if name == "plate" else "estop")
        groups.setdefault(key, []).append((c.transform(np.asarray(v, float), ang, (x, y, z)), f))
    a, b = rope_points(site, cid, lay)
    n3 = np.array([*lay["n"], 0.0])
    tail, head = lay["tail"], lay["head"]
    run_d = (head - tail) / np.linalg.norm(head - tail)
    rope_d = (b - a) / np.linalg.norm(b - a)
    flanges = [tail + run_d * t for t in np.arange(-CONV_END, np.linalg.norm(head - tail) + CONV_END + 1e-6, CONV_SECTION)]
    avoid = [float(np.dot(p - a, rope_d)) for p in flanges]
    end = float(np.linalg.norm(b - a))
    while any(abs(end + 0.2 - x) < ctl.SUPPORT_AVOID + 0.02 for x in avoid):     # the anchor (0.2 past the end) off a flange
        end -= 0.05
    b = a + rope_d * end
    cord = ctl.pull_cord(a - (0, 0, ctl.ROPE_Z), b - (0, 0, ctl.ROPE_Z), side=1, mount=tuple(-n3 * (ROPE_OFF - 0.005)), avoid=avoid)
    for name, part in cord["parts"].items():
        groups.setdefault({"rope": "estop_red", "reset": "estop_blue", "switch": "cord_switch"}.get(name, "estop"), []).append(part)
    info = {"post": (x, y, z), "angle": ang, "mushroom_z": post["dims"]["centre_z"] + 0.02, "rail_t": estop_place(site, cid, lay)[4], "rope": (a, b),
            "rope_run": cord["dims"]["run"], "rope_supports": cord["dims"]["supports"], "layout": lay}
    return {k: c.merge_parts(v) for k, v in groups.items()}, info


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
