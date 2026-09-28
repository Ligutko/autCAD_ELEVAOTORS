"""F. Receiving block of sheet 2 (existing, simplified): truck pit with its drive-through shed, receiving
tower +33 with norias H1-H4, old silos «2», «3», building «4», cleaning tower with bin Ш1 and the
separator room. Detailed only where the new stage ties in: T7 inlets under the noria head spouts,
T10 outlets into the gravity pipe to the separator and the splitter to T5 / T3.

Site frame (SITE.json). Data: SITE.json `receiving` (research/receiving.md, inbox/extract_receiving_p2.py).
Heights the drawing does not give are `judgment` in SITE and labelled so in the frames.
"""

import functools
import json
import math

import numpy as np

from . import common as c
from . import noria_tower as tower
from . import steel as st


@functools.lru_cache(maxsize=1)
def _site():
    return json.loads(c.SITE_JSON.read_text(encoding="utf-8"))


def spec():
    return _site()["receiving"]


def tower_centre(r=None):
    t = (r or spec())["tower"]
    return (sum(t["cols_x"]) / 2, sum(t["cols_y"]) / 2)


def conveyor_z(bridge_conv, y):
    """Axis z of a bridge conveyor (SITE bridges) at plan y, straight between its pulleys."""
    (y0, z0), (y1, z1) = bridge_conv["tail"], bridge_conv["head"]
    return z0 + (z1 - z0) * (y - y0) / (y1 - y0)


def bridge_conveyor(cid, site=None):
    for b in (site or _site())["bridges"]:
        for cv in b["conveyors"]:
            if cv["id"] == cid:
                return cv
    raise KeyError(cid)


# ================================================================== norias (simplified)

def noria_boxes(n, r=None):
    """{part: (x0, y0, z0, x1, y1, z1)} of one noria: two legs, boot, head, drive (site frame)."""
    r = r or spec()
    g = r["noria_generic"]
    x, y = n["axis"]
    along_y = n["legs_along"] == "Y"
    half_gap, w = g["leg_axis_gap"] / 2, g["leg_w"] / 2
    head_len = n["head_len"]
    z_boot_top, z_head0, z_head1 = n["boot_top_z"], n["head_z"][0], n["head_z"][1]
    floor = r["tower"]["pit"]["floor_z"]

    def box(a0, a1, b0, b1, z0, z1):                      # a along the legs, b across
        return (x + b0, y + a0, z0, x + b1, y + a1, z1) if along_y else (x + a0, y + b0, z0, x + a1, y + b1, z1)

    out = {"leg_a": box(-half_gap - w, -half_gap + w, -w, w, z_boot_top, z_head0),
           "leg_b": box(half_gap - w, half_gap + w, -w, w, z_boot_top, z_head0),
           "boot": box(-g["boot_len"] / 2, g["boot_len"] / 2, -g["boot_w"] / 2, g["boot_w"] / 2, floor + 0.2, z_boot_top),
           "head": box(-head_len / 2, head_len / 2, -g["head_w"] / 2, g["head_w"] / 2, z_head0, z_head1)}
    s = 1.0 if n.get("drive_towards", "+X") in ("+X", "+Y") else -1.0
    dz0 = z_head0 + (z_head1 - z_head0) * 0.35
    if along_y:
        dx0 = s * (g["head_w"] / 2) if s > 0 else s * (g["head_w"] / 2 + g["drive"][0])
        out["drive"] = (x + dx0, y - g["drive"][1] / 2, dz0, x + dx0 + g["drive"][0], y + g["drive"][1] / 2, dz0 + g["drive"][2])
    else:
        dy0 = s * (g["head_w"] / 2) if s > 0 else s * (g["head_w"] / 2 + g["drive"][0])
        out["drive"] = (x - g["drive"][1] / 2, y + dy0, dz0, x + g["drive"][1] / 2, y + dy0 + g["drive"][0], dz0 + g["drive"][2])
    return out


def _b(bx):
    return c.box(bx[:3], bx[3:])


def head_outlet(n, r=None):
    """Discharge point under the head, at the head end facing the T7 inlet it feeds (judgment)."""
    hb = noria_boxes(n, r)["head"]
    return np.array([(hb[0] + hb[3]) / 2, (hb[1] + hb[4]) / 2, hb[2]])


# ================================================================== tie-ins

def spouts(r=None, site=None):
    """[(name, p0, p1, size)] of the spouts at the joints: noria heads -> T7 inlets, T10 outlets ->
    gravity pipe / splitter -> T5, T3 ends; plus the gravity pipes to and from the cleaning tower."""
    r, site = r or spec(), site or _site()
    j = r["joints"]
    t7, t10 = bridge_conveyor("T7", site), bridge_conveyor("T10", site)
    norias = {n["id"]: n for n in r["norias"]}
    out = []
    for inlet in j["T7"]["inlets"]:
        y = inlet["y"]
        top = conveyor_z(t7, y) + j["T7"]["casing_h"] / 2
        p0 = head_outlet(norias[inlet["from"]], r)
        p0[1] = min(max(y, p0[1] - 1.0), p0[1] + 1.0)         # outlet on the head end nearest the inlet
        out.append((f"{inlet['from']}->T7@{y}", p0, np.array([j["T7"]["x"], y, top]), j["spout_mm"]))
    tz = t10["tail"][1] - j["T10"]["casing_h"] / 2
    gp = r["cleaning_tower"]["gravity_pipe"]
    x_p = gp["x"]
    for o in j["T10"]["outlets"]:
        p0 = np.array([j["T10"]["x"], o["y"], tz])
        if o["to"] == "gravity_pipe":
            out.append(("T10->gravity_pipe", p0, np.array([x_p, *o["join"]]), j["spout_mm"]))
        else:
            split = np.array([j["T10"]["x"], o["y"], o["splitter_z"]])
            out.append(("T10->splitter_7", p0, split, j["spout_mm"]))
            for br in o["branches"]:
                out.append((f"splitter_7->{br['to']}", split, np.array([br.get("end_x", j["T10"]["x"]), *br["end"]]), j["spout_mm"]))
    a, b = gp["from"], gp["to"]
    out.append(("node_1->gravity_pipe", np.array([x_p, gp["node_1"][0], gp["node_1"][1]]), np.array([x_p, *a]), gp["d_mm"]))
    out.append(("gravity_pipe->separator", np.array([x_p, *a]), np.array([x_p, *b]), gp["d_mm"]))
    sh = r["cleaning_tower"]["bin_Sh1_to_tower"]
    out.append(("Sh1->tower_pit", np.array([sh["x"], *sh["from"]]), np.array([sh["x"], *sh["to"]]), gp["d_mm"]))
    if "drying_geom" in site.get("designed", {}):                      # phase 5A: drying loop (designed)
        from . import drying
        out += drying.spouts(site)
    return out


def _spout_mesh(p0, p1, size_mm):
    h = size_mm / 2000
    d = np.asarray(p1, float) - np.asarray(p0, float)
    horiz = np.array([d[0], d[1], 0.0])
    up = (1.0, 0.0, 0.0) if np.linalg.norm(horiz) < 1e-6 else (0.0, 0.0, 1.0)
    return st.member(p0, p1, np.array([(-h, -h), (h, -h), (h, h), (-h, h)]), up=up)


# ================================================================== build

def _conveyor(cv, h=0.40):
    w = cv["w"] / 2
    if "y" in cv and isinstance(cv["y"], list):                        # along Y, sloped (T1)
        (ya, yb), (za, zb) = cv["y"], cv["z_ends"]
        return st.member((cv["x"], ya, za), (cv["x"], yb, zb), np.array([(-w, -h / 2), (w, -h / 2), (w, h / 2), (-w, h / 2)]))
    xa, xb = cv["x"]
    z = cv["z"] + h / 2
    return st.member((xa, cv["y"], z), (xb, cv["y"], z), np.array([(-w, -h / 2), (w, -h / 2), (w, h / 2), (-w, h / 2)]))


def slab_holes(r=None, site=None, level=None):
    """Plan holes (x0, y0, x1, y1) a slab at `level` needs: noria legs passing it, spouts crossing it."""
    r = r or spec()
    holes = []
    for n in r["norias"]:
        bx = noria_boxes(n, r)
        for k in ("leg_a", "leg_b"):
            b = bx[k]
            if b[2] < level < b[5]:
                holes.append((b[0] - 0.05, b[1] - 0.05, b[3] + 0.05, b[4] + 0.05))
    for _, p0, p1, size in spouts(r, site):
        lo, hi = sorted((p0[2], p1[2]))
        if lo < level < hi:
            t = (level - p0[2]) / (p1[2] - p0[2])
            q = p0 + (p1 - p0) * t
            e = size / 2000 + 0.1
            holes.append((q[0] - e, q[1] - e, q[0] + e, q[1] + e))
    return holes


def build_tower(r=None, site=None):
    r = r or spec()
    t = r["tower"]
    cx, cy = tower_centre(r)
    hx, hy = (t["cols_x"][1] - t["cols_x"][0]) / 2, (t["cols_y"][1] - t["cols_y"][0]) / 2
    levels = sorted(z for z in t["levels_z"] if z > 0.0)
    heavy, light = tower.build_frame(t["top_z"], levels, hx, hy, r["norias"][0]["axis"][0] - cx)
    off = np.array([cx, cy, 0.0])
    heavy = (heavy[0] + off, heavy[1])
    light = (light[0] + off, light[1])
    decks = []
    for lv in t["decks"]:
        z = lv["z"]
        for x0, y0, x1, y1 in lv["rects"]:
            decks += tower._cells(x0, y0, x1, y1, slab_holes(r, site, z), z, st.grating_panel)
    pit = t["pit"]
    (px0, px1), (py0, py1), w = pit["inner_x"], pit["inner_y"], pit["wall_t"]
    walls = [c.box((px0 - w, py0 - w, pit["floor_z"] - 0.4), (px1 + w, py1 + w, pit["floor_z"])),
             c.box((px0 - w, py0 - w, pit["floor_z"]), (px0, py1 + w, 0.0)), c.box((px1, py0 - w, pit["floor_z"]), (px1 + w, py1 + w, 0.0)),
             c.box((px0, py0 - w, pit["floor_z"]), (px1, py0, 0.0))]
    ch = r["pit"]["channel"]                                           # T1 channel breaks the north pit wall
    walls += [c.box((px0, py1, pit["floor_z"]), (ch["x"][0], py1 + w, 0.0)), c.box((ch["x"][1], py1, pit["floor_z"]), (px1, py1 + w, 0.0))]
    cover = tower._cells(px0 - w, py0 - w, px1 + w, py1 + w, slab_holes(r, site, 0.0) + [(ch["x"][0], py1 - 0.6, ch["x"][1], py1 + w)],
                         -0.2, lambda a, b, cc, d, z: c.box((a, b, z), (cc, d, z + 0.2)))
    return {"frame": ("galv_old", False, heavy), "bracing": ("galv_old", False, light),
            "decks": ("grating", False, c.merge_parts(decks)), "pit": ("concrete", False, c.merge_parts(walls)),
            "pit_cover": ("concrete", False, c.merge_parts(cover))}


def build_norias(r=None, by_node=False):
    """Legs, boots, heads, drives of H1-H4, merged by kind, or one set per noria with by_node
    ("noria_legs_h1", ...: the scene highlights one process node, routes.py)."""
    r = r or spec()
    look = {"legs": ("galv", []), "boots": ("galv_old", []), "heads": ("galv", []), "drives": ("motor", [])}
    out = {}
    for n in r["norias"]:
        bx = noria_boxes(n, r)
        mine = {"legs": [_b(bx["leg_a"]), _b(bx["leg_b"])], "boots": [_b(bx["boot"])],
                "heads": [_b(bx["head"])], "drives": [_b(bx["drive"])]}
        for k, v in mine.items():
            if by_node:
                out[f"noria_{k}_{n['id'].lower()}"] = (look[k][0], False, c.merge_parts(v))
            else:
                look[k][1].extend(v)
    if not by_node:
        out = {f"noria_{k}": (mat, False, c.merge_parts(v)) for k, (mat, v) in look.items()}
    return out


def spout_key(name):
    """Part key of one tie-in spout with by_node: 'H1->T7@53.37' -> 'spout_h1_to_t7_at_53_37'."""
    return "spout_" + name.lower().replace("->", "_to_").replace("@", "_at_").replace(".", "_")


def build_pit_and_shed(r=None):
    r = r or spec()
    p, g = r["pit"], c.ground_z()
    (x0, x1), (y0, y1) = p["x"], p["y"]
    w = p["wall_t"]
    conc = [c.box((x0 - w, y0 - w, p["floor_z"] - 0.4), (x1 + w, y1 + w, p["floor_z"])),
            c.box((x0 - w, y0 - w, p["floor_z"]), (x0, y1 + w, p["deck_z"])), c.box((x1, y0 - w, p["floor_z"]), (x1 + w, y1 + w, p["deck_z"])),
            c.box((x0, y1, p["floor_z"]), (x1, y1 + w, p["deck_z"]))]
    ch = p["channel"]                                                  # south wall opened for T1, culvert to the tower
    conc += [c.box((x0, y0 - w, p["floor_z"]), (ch["x"][0], y0, p["deck_z"])), c.box((ch["x"][1], y0 - w, p["floor_z"]), (x1, y0, p["deck_z"])),
             c.box((ch["x"][0], y0 - w, -0.3), (ch["x"][1], y0, p["deck_z"]))]
    ty1 = r["tower"]["pit"]["inner_y"][1] + r["tower"]["pit"]["wall_t"]
    conc += [c.box((ch["x"][0] - 0.25, ty1, p["floor_z"] + 0.5), (ch["x"][0], y0 - w, 0.0)),
             c.box((ch["x"][1], ty1, p["floor_z"] + 0.5), (ch["x"][1] + 0.25, y0 - w, 0.0)),
             c.box((ch["x"][0] - 0.25, ty1, -0.25), (ch["x"][1] + 0.25, y0 - w, 0.0))]
    grate = [c.box((x0, y0, p["deck_z"] - 0.05), (x1, y1, p["deck_z"]))]
    hoppers = []
    for ox, oy in p["outlets"]:                                        # two hoppers under the grating (judgment slopes)
        top = [(x0, oy - 1.0), (x1, oy - 1.0), (x1, oy + 1.0), (x0, oy + 1.0)]
        v = np.array([(x, y, p["deck_z"] - 0.1) for x, y in top] + [(ox - 0.2, oy - 0.2, p["floor_z"] + 1.0), (ox + 0.2, oy - 0.2, p["floor_z"] + 1.0),
                                                                     (ox + 0.2, oy + 0.2, p["floor_z"] + 1.0), (ox - 0.2, oy + 0.2, p["floor_z"] + 1.0)])
        hoppers.append((v, np.array([(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])))
    d = p["drive"]
    (dy0, dy1), (dx0, dx1), (fx0, fx1) = d["y"], d["x"], d["flat_x"]
    z = d["deck_z"]

    def ramp(xa, za, xb, zb):
        v = np.array([(xa, dy0, za), (xb, dy0, zb), (xb, dy1, zb), (xa, dy1, za),
                      (xa, dy0, g - 0.05), (xb, dy0, g - 0.05), (xb, dy1, g - 0.05), (xa, dy1, g - 0.05)])
        return v, np.array([(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])

    road = [ramp(dx0, g, fx0, z), c.box((fx0, dy0, g - 0.05), (x0 - w, dy1, z)), c.box((x1 + w, dy0, g - 0.05), (fx1, dy1, z)),
            ramp(fx1, z, dx1, g)]
    b = p["building"]
    cols, walls, roof = [], [], []
    for cx in b["cols_x"]:
        for cy in b["cols_y"]:
            cols.append(st.member((cx, cy, p["deck_z"]), (cx, cy, b["eave_z"]), st.SHS_200, up=(1, 0, 0)))
    (bx0, bx1), (by0, by1) = b["x"], b["y"]
    for ya, yb in ((by0, by0 + 0.05), (by1 - 0.05, by1)):              # side walls along the drive, ends open for trucks
        walls.append(c.box((bx0, ya, p["deck_z"] + 0.3), (bx1, yb, b["eave_z"])))
    roof.append(c.box((bx0 - 0.2, by0 - 0.2, b["eave_z"]), (bx1 + 0.2, by1 + 0.2, b["eave_z"] + 0.3)))
    roof.append(c.box((bx0 + 1.0, by0 + 1.0, b["eave_z"] + 0.3), (bx1 - 1.0, by1 - 1.0, b["roof_top_z"])))
    posts = [c.box((x - 0.6, y - 0.6, g), (x + 0.6, y + 0.6, g + 0.3)) for x, y in p["outer_posts"]]
    posts += [st.member((x, y, g + 0.3), (x, y, g + 1.2), st.SHS_200, up=(1, 0, 0)) for x, y in p["outer_posts"]]
    return {"pit_concrete": ("concrete", False, c.merge_parts(conc)), "pit_grating": ("grating", False, c.merge_parts(grate)),
            "pit_hoppers": ("galv_old", False, c.merge_parts(hoppers)), "drive": ("concrete", False, c.merge_parts(road)),
            "shed_columns": ("galv_old", False, c.merge_parts(cols)), "shed_walls": ("galv", False, c.merge_parts(walls)),
            "shed_roof": ("galv_old", False, c.merge_parts(roof)), "outer_posts": ("concrete", False, c.merge_parts(posts))}


def build_old_silos(r=None):
    r = r or spec()
    g = c.ground_z()
    walls, roofs, plinths, chairs = [], [], [], []
    for s in r["old_silos"]:
        x, y, h = s["x"], s["y"], s["wall_h"]
        plinths.append(c.cylinder(s["plinth_r"], g, s["floor_z"], steps=96, center=(x, y)))
        walls.append(c.cylinder(s["wall_r"], s["floor_z"], s["floor_z"] + h, steps=128, center=(x, y), capped=False))
        a = np.linspace(0, 2 * math.pi, 96, endpoint=False)
        top = s["floor_z"] + h
        peak = top + s["wall_r"] * math.tan(math.radians(30.0))
        v = np.concatenate([np.column_stack([x + (s["wall_r"] + 0.15) * np.cos(a), y + (s["wall_r"] + 0.15) * np.sin(a), np.full(96, top - 0.09)]),
                            [[x, y, peak]]])
        f = [np.array([(i, (i + 1) % 96, 96) for i in range(96)])]
        roofs.append((v, f))
        for k in range(s["anchors"]):
            th = math.radians(s["anchor_a0_deg"] + 360.0 * k / s["anchors"])
            px, py = x + s["anchor_r"] * math.cos(th), y + s["anchor_r"] * math.sin(th)
            chairs.append(c.box((px - 0.12, py - 0.12, s["floor_z"]), (px + 0.12, py + 0.12, s["floor_z"] + 0.25)))
    return {"old_silo_walls": ("galv", "quads", c.merge_parts(walls)), "old_silo_roofs": ("galv_old", False, c.merge_parts(roofs)),
            "old_silo_plinths": ("concrete", False, c.merge_parts(plinths)), "old_silo_chairs": ("dark", False, c.merge_parts(chairs))}


def build_building_4(r=None):
    b = (r or spec())["building_4"]
    (x0, x1), (y0, y1) = b["outer_x"], b["outer_y"]
    g = c.ground_z()
    walls = [c.box((x0, y0, g), (x1, y1, b["floor_z"])), c.box((x0, y0, b["floor_z"]), (x1, y1, b["eave_z"]))]
    roof = [c.box((x0 - 0.3, y0 - 0.3, b["eave_z"]), (x1 + 0.3, y1 + 0.3, b["eave_z"] + 0.25))]
    return {"building_4": ("galv", False, c.merge_parts(walls)), "building_4_roof": ("galv_old", False, c.merge_parts(roof))}


def build_cleaning_tower(r=None):
    ct = (r or spec())["cleaning_tower"]
    g = c.ground_z()
    (x0, x1), (y0, y1) = ct["x_extent"], ct["room_y"]
    cols = [c.box((x - ct["col"] / 2, y - ct["col"] / 2, g), (x + ct["col"] / 2, y + ct["col"] / 2, ct["floor_z"] - 0.3))
            for x in ct["cols_x"] for y in ct["cols_y"]]
    footing = [c.box((min(ct["cols_x"]) - 0.5, y - 0.5, g - 0.05), (max(ct["cols_x"]) + 0.5, y + 0.5, g + 0.05)) for y in ct["cols_y"]]
    floor = [c.box((x0, ct["floor_y"][0], ct["floor_z"] - 0.3), (x1, ct["floor_y"][1], ct["floor_z"]))]
    room = [c.box((x0, y0, ct["floor_z"]), (x1, y1, ct["wall_top_z"])),
            c.box((x0 - 0.2, y0 - 0.2, ct["wall_top_z"]), (x1 + 0.2, y1 + 0.2, ct["roof_z"])),
            c.box((x0 + 0.5, ct["roof_raised"]["y"][0], ct["roof_z"]), (x1 - 0.5, ct["roof_raised"]["y"][1], ct["roof_raised"]["top_z"]))]
    b = ct["bin_Sh1"]
    bx0, bx1 = b["x"]
    (by0, by1), (bz0, bz1) = b["y"], b["box_z"]
    oy, oz = b["outlet"]
    hop = np.array([(bx0, by0, bz0), (bx1, by0, bz0), (bx1, by1, bz0), (bx0, by1, bz0),
                    (sum(b["x"]) / 2 - 0.2, oy - 0.2, oz), (sum(b["x"]) / 2 + 0.2, oy - 0.2, oz),
                    (sum(b["x"]) / 2 + 0.2, oy + 0.2, oz), (sum(b["x"]) / 2 - 0.2, oy + 0.2, oz)])
    bin_ = [c.box((bx0, by0, bz0), (bx1, by1, bz1 - 0.3)), (hop, np.array([(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (7, 6, 5, 4)]))]
    return {"ct_columns": ("concrete", False, c.merge_parts(cols + footing)), "ct_floor": ("concrete", False, c.merge_parts(floor)),
            "ct_room": ("galv", False, c.merge_parts(room)), "ct_bin_Sh1": ("galv_old", False, c.merge_parts(bin_))}


def build(r=None, site=None, by_node=False):
    """{name: (material key, smooth, (verts, faces))} of the whole receiving block, site frame.
    by_node: norias, conveyors and tie-in spouts one part each (process nodes for routes.py);
    default: merged by kind, as the checks read them."""
    r = r or spec()
    parts = {}
    parts.update(build_tower(r, site))
    parts.update(build_norias(r, by_node))
    parts.update(build_pit_and_shed(r))
    parts.update(build_old_silos(r))
    site = site or _site()
    if "drying_geom" in site.get("designed", {}):                      # building «4» = the dryer's base (phase 5A)
        from . import drying
        parts.update(drying.build(site))
    else:
        parts.update(build_building_4(r))
    parts.update(build_cleaning_tower(r))
    if by_node:
        for cv in r["conveyors"]:
            parts[f"conveyor_{cv['id'].lower()}"] = ("galv", False, _conveyor(cv))
        for name, p0, p1, s in spouts(r, site):
            parts[spout_key(name)] = ("galv", False, _spout_mesh(p0, p1, s))
        return parts
    parts["conveyors"] = ("galv", False, c.merge_parts([_conveyor(cv) for cv in r["conveyors"]]))
    parts["spouts"] = ("galv", False, c.merge_parts([_spout_mesh(p0, p1, s) for _, p0, p1, s in spouts(r, site)]))
    return parts
