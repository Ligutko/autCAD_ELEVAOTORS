"""Phase 7C: the grain path of a process route in 3D, for route highlighting and the «шлях зерна» reel.

Needs no scene: check_routes and the reel read the same path. The path is assembled from the SITE.json
blocks and kit functions the model itself is built from, so it goes where the model's equipment is:

  conveyor  the casing centreline, entered under the spout that feeds it, left at the outlet that
            empties it (T1 from SITE receiving, T7 / T10 / T11 / T14 bridges, T8 / T12 / T15 galleries,
            T9 / T13 / T16 tunnels);
  noria     the kit's own belt path (noria_n100.BeltPath through noria_tower.noria_frame): boot inlet
            mouth, round the boot pulley, up the loaded leg, over the head pulley, out of the discharge
            outlet; H1-H4 of the existing block are boxes, their loaded leg is a judgment;
  spouts    the distribution spouts (SITE distribution), the receiving tie-ins (receiving.spouts),
            the silo drops, the silo outlet stacks, the tunnel discharge into the boot;
  trucks    the one-way lanes of the site plan at trailer height;
  silo      roof spout -> floor, floor -> the central outlet.

Each piece is a Leg: owner (node id, or "A->B" for an edge), kind, points, basis, meta.
  kind   drive | fall | convey | lift | store
  basis  drawn | existing | designed : the layer of the edge or node the geometry comes from;
         judgment : the model has no geometry there (open edges of the process graph, the separator
         position), the leg is a straight connector and check_routes reports its size.
Legs are built from their own geometry only, never stretched to meet the neighbour: the gap between
one leg's end and the next leg's start is what check_routes measures.
"""

import math
from dataclasses import dataclass, field

import numpy as np

from . import noria_n100 as nn
from . import noria_tower as ntw
from . import process as pr
from . import receiving as rc

TRUCK_Z = 2.3              # judgment: flow line on a truck at trailer mid-height (body 1.25-3.49, kit/trucks.py)
TRUCK_STOP = {"PIT": None, "TRUCK_OUT": None}     # stops are taken from SITE (pit outlet, Ш1 outlet)
SILO_FLOOR_OVER_BASE = 0.30  # judgment: grain line drawn 0.3 m over the silo floor

# The reel's grain cycle, user decision 2026-09-28 («повний цикл»): receiving with cleaning into S1,
# then shipping out of S1 back through the cleaning to a truck. Each list must be a route of the graph.
CYCLES = {
    "full_cycle": [
        ["TRUCK_IN", "SCALES_IN", "PIT", "T1", "H1", "NODE_1", "GRAVITY_PIPE", "SEP5", "SH1", "TOWER_PIT",
         "H3", "T7", "T8", "S1"],
        ["S1", "T9", "H5", "T10", "GRAVITY_PIPE", "SEP5", "SH1", "TRUCK_OUT", "SCALES_OUT", "TRUCK_EXIT"],
    ],
}


# Blender objects of each process node / edge (fnmatch on object names, site.py naming: kit part keys,
# receiving and bridge conveyors split by node since 7C). Nodes missing here have no body of their own:
# trucks and lanes (the flow line shows them), NODE_1 (a point on the drawing).
# SCALES_IN and SCALES_OUT share the merged scale decks of the site plan; SEP5 is the cleaning room,
# the separator itself is not modelled.
NODE_OBJECTS = {
    "SCALES_IN": ["SITE_PLAN_SCALE_DECKS", "SITE_PLAN_SCALE_RAMPS"],
    "SCALES_OUT": ["SITE_PLAN_SCALE_DECKS", "SITE_PLAN_SCALE_RAMPS"],
    "PIT": ["RECEIVING_PIT_GRATING", "RECEIVING_PIT_HOPPERS"],
    "T1": ["RECEIVING_CONVEYOR_T1"],
    "H1": ["RECEIVING_NORIA_*_H1"], "H3": ["RECEIVING_NORIA_*_H3"],
    "GRAVITY_PIPE": ["RECEIVING_SPOUT_GRAVITY_PIPE_TO_SEPARATOR"],
    "SEP5": ["RECEIVING_CT_ROOM"], "SH1": ["RECEIVING_CT_BIN_SH1"], "TOWER_PIT": ["RECEIVING_PIT"],
    "T7": ["G_H14_H5_T7_CONV_*"], "T10": ["G_H14_H5_T10_CONV_*"],
    "T8": ["T8_CONV_*", "T8_GATES"], "T9": ["T9_CONV_*"],
    "H5": ["H5_NORIA_*", "H5_DIST_*"],
    "S1": ["S1", "S1_FOUNDATION_*"],
}
EDGE_OBJECTS = {
    "PIT->T1": ["RECEIVING_PIT_HOPPERS"],
    "NODE_1->GRAVITY_PIPE": ["RECEIVING_SPOUT_NODE_1_TO_GRAVITY_PIPE"],
    "SH1->TOWER_PIT": ["RECEIVING_SPOUT_SH1_TO_TOWER_PIT"],
    "H3->T7": ["RECEIVING_SPOUT_H3_TO_T7_AT_*"],
    "T7->T8": ["H5_DIST_SPOUTS"],
    "T8->S1": ["T8_SPOUTS"],
    "S1->T9": ["T9_SLEEVES", "T9_GATE_*", "T9_SPOUTS"],
    "T9->H5": ["T9_CONV_DISCHARGE"],
    "H5->T10": ["H5_DIST_*"],
    "T10->GRAVITY_PIPE": ["RECEIVING_SPOUT_T10_TO_GRAVITY_PIPE"],
    "GRAVITY_PIPE->SEP5": ["RECEIVING_SPOUT_GRAVITY_PIPE_TO_SEPARATOR"],
}


def owner_patterns(owner):
    o = owner.split(" (")[0]
    return NODE_OBJECTS.get(o) or EDGE_OBJECTS.get(o) or []


def match(names, patterns):
    """Object names matching any pattern."""
    from fnmatch import fnmatchcase
    return sorted({n for n in names for p in patterns if fnmatchcase(n, p)})


def highlight_names(names, legs):
    """Objects to highlight for these legs."""
    pats = []
    for lg in legs:
        pats += owner_patterns(lg.owner)
    return match(names, pats)


@dataclass
class Leg:
    owner: str
    kind: str
    pts: np.ndarray
    basis: str
    meta: dict = field(default_factory=dict)

    @property
    def length(self):
        return float(np.linalg.norm(np.diff(self.pts, axis=0), axis=1).sum())


def _p(*xyz):
    return np.array(xyz, dtype=float)


# ------------------------------------------------------------------ routes of the graph

def find_route(g, nodes):
    """The process route (list of edges) whose node sequence is exactly `nodes`."""
    for r in g.routes():
        if g.route_nodes(r) == list(nodes):
            return r
    raise KeyError("no route " + " -> ".join(nodes))


def cycle(name, site):
    """[(nodes, route edges)] of a named cycle."""
    g = pr.Graph(site)
    return [(nodes, find_route(g, nodes)) for nodes in CYCLES[name]]


# ------------------------------------------------------------------ conveyors

def conveyor_axis(site, cid):
    """(tail, head, half width, half height) of the casing centreline, site frame. Grain runs tail -> head."""
    g = site["silo_top_galleries"]
    for ln in g["lines"]:
        if ln["id"] == cid:
            z0, z1 = g["conveyor"]["casing_z"]
            z = (z0 + z1) / 2
            return _p(ln["tail_x"], ln["row_y"], z), _p(ln["head_x"], ln["row_y"], z), g["conveyor"]["casing_w"] / 2, (z1 - z0) / 2
    for br in site["bridges"]:
        for cv in br.get("conveyors", []):
            if cv["id"] == cid:
                return (_p(cv["x"], *cv["tail"]), _p(cv["x"], *cv["head"]),
                        cv.get("casing_w", 0.4) / 2, cv.get("casing_h", 0.5) / 2)
    for t in site["tunnels"]:
        cv = t["conveyor"]
        if cv["id"] == cid:
            z0, z1 = cv["casing_z"]
            z = (z0 + z1) / 2
            return _p(cv["tail_x"], t["row_y"], z), _p(cv["drive_x"], t["row_y"], z), cv["width"] / 2, (z1 - z0) / 2
    for cv in site["receiving"]["conveyors"]:
        if cv["id"] == cid and isinstance(cv.get("y"), list):          # T1: pit (tail) -> H1 boot (head)
            (ya, yb), (za, zb) = cv["y"], cv["z_ends"]
            return _p(cv["x"], ya, za), _p(cv["x"], yb, zb), cv["w"] / 2, 0.20
    raise KeyError(cid)


def along(site, cid, p_in, p_out):
    """Leg along a conveyor between the projections of the feeding spout end and the outlet start."""
    a, b, hw, hh = conveyor_axis(site, cid)
    d = b - a
    L2 = float(d @ d)

    def proj(p):
        t = float((p - a) @ d / L2)
        q = a + d * t
        return t, q, float(np.linalg.norm((p - q)[:2]))

    t_in, q_in, off_in = proj(p_in)
    t_out, q_out, off_out = proj(p_out)
    meta = {"t_in": t_in, "t_out": t_out, "off_in": off_in, "off_out": off_out, "half_w": hw, "half_h": hh,
            "run_m": float(math.sqrt(L2))}
    return [Leg(cid, "convey", np.array([q_in, q_out]), None, meta)]


# ------------------------------------------------------------------ norias

def tower_noria_points(site, tid):
    """Belt path points of a tower noria (H5, H6) in the site frame: inlet mouth, the loaded leg,
    the head pulley, the discharge outlet. The loaded leg is the kit's up leg (local -X)."""
    spec = next(s for s in site["noria_towers"] if s["id"] == tid)
    f = ntw.noria_frame(spec)
    _, _, _, anchors = ntw.build_noria(spec)
    z_boot = spec["pit_z"] + nn.BOOT_AXIS_ABOVE_PIT
    z_head = spec["pit_z"] + nn.BOOT_TOP_ABOVE_PIT + spec["tube_mm"] / 1000 + nn.HEAD_BELOW_AXIS
    path = nn.BeltPath(z_boot, z_head)
    loc = []
    s0 = path.length - path.arc                        # boot arc start: down leg bottom -> up leg bottom
    for s in np.linspace(s0, path.length, 9):
        loc.append(nn._to3(path.frame(s)[0], nn.BELT_Y))
    for s in np.linspace(0.0, path.h, 12)[1:]:
        loc.append(nn._to3(path.frame(s)[0], nn.BELT_Y))
    for s in np.linspace(path.h, path.h + path.arc * 0.55, 7)[1:]:
        loc.append(nn._to3(path.frame(s)[0], nn.BELT_Y))
    outlet = np.array([nn.CX + nn.OUTLET_OFFSET, nn.BELT_Y, z_head - nn.OUTLET_BELOW_AXIS])
    off = _p(spec["x"], spec["y"], 0.0)
    mouth = f(np.asarray(anchors["inlet_mouth"], float)) + off
    belt = f(np.array(loc)) + off
    out = f(outlet) + off
    up = f(np.array([nn._to3(path.frame(0.0)[0], nn.BELT_Y), nn._to3(path.frame(path.h - 1e-6)[0], nn.BELT_Y)])) + off
    return mouth, belt, out, {"z_boot": z_boot, "z_head": z_head, "up_leg": up}


def receiving_noria_points(site, nid):
    """H1-H4 (boxes): boot, leg_a as the loaded leg (judgment: the drawing does not say which), head,
    discharge point under the head (receiving.head_outlet)."""
    r = site["receiving"]
    n = next(n for n in r["norias"] if n["id"] == nid)
    bx = rc.noria_boxes(n, r)
    c_a = [(bx["leg_a"][i] + bx["leg_a"][i + 3]) / 2 for i in range(2)]
    boot, head = bx["boot"], bx["head"]
    zb = (boot[2] + boot[5]) / 2
    zh = (head[2] + head[5]) / 2
    pts = np.array([(c_a[0], c_a[1], zb), (c_a[0], c_a[1], zh)])
    return pts, rc.head_outlet(n, r), bx


def noria_leg(site, nid, p_out):
    """Lift leg of a noria: boot inlet -> loaded leg -> head -> discharge point."""
    if any(t["id"] == nid for t in site["noria_towers"]):
        mouth, belt, out, meta = tower_noria_points(site, nid)
        meta["mouth"] = mouth
        return [Leg(nid, "lift", np.vstack([mouth, belt, out]), None, meta)]
    pts, outlet, bx = receiving_noria_points(site, nid)
    boot, head = bx["boot"], bx["head"]
    inlet = _p((boot[0] + boot[3]) / 2, (boot[1] + boot[4]) / 2, boot[5])       # boot top centre (judgment)
    meta = {"judgment": "loaded leg = leg_a, inlet on the boot top"}
    if p_out is not None and head[0] - 0.1 <= p_out[0] <= head[3] + 0.1 and head[1] - 0.1 <= p_out[1] <= head[4] + 0.1 \
            and head[2] - 0.3 <= p_out[2] <= head[5]:
        outlet = p_out                                   # receiving.spouts starts at the head end nearest the inlet
        meta["outlet"] = "head end of the spout (receiving.spouts)"
    return [Leg(nid, "lift", np.vstack([inlet, pts, outlet]), None, meta)]


# ------------------------------------------------------------------ edges

def _dist_spout(site, tower, to, frm):
    d = next(d for d in site["distribution"] if d["tower"] == tower)
    return d, next(s for s in d["spouts"] if s["to"] == to and s.get("from_conveyor") == frm)


def _rspouts(site):
    return {n: (np.asarray(p0, float), np.asarray(p1, float)) for n, p0, p1, _ in rc.spouts(site["receiving"], site)}


def _separator(site):
    """Centre x (judgment: over Ш1, the drawing gives only its Y and Z), y, top z, bottom z."""
    ct = site["receiving"]["cleaning_tower"]
    sep, b = ct["separator_5"], ct["bin_Sh1"]
    return sum(b["x"]) / 2, sum(sep["y"]) / 2, sep["z"][1], sep["z"][0]


def _lane_y(site, lane):
    return next(ln for ln in site["designed"]["site_plan"]["lanes"] if ln["id"] == lane)["pts"][0][1]


def edge_legs(site, e, p_prev):
    """Legs of edge e. p_prev: the end of the previous leg (used only to trim the gravity pipe)."""
    k, a, b = e["geom"]["k"], e["from"], e["to"]
    name, basis = f"{a}->{b}", e["layer"]
    sp = site["site_plan"] if "site_plan" in site else site["designed"]["site_plan"]
    if k == "dspout":
        gm = e["geom"]
        d, s = _dist_spout(site, gm["tower"], gm["to"], gm["from_conveyor"])
        pts = [np.asarray(p, float) for p in s["path"]]
        if gm["from_conveyor"] is None:                  # head outlet -> splitter under the head -> branch
            spl = next(x for x in d["splitters"] if abs(x["at"][0] - d["head_outlet"][0]) <= 0.05
                       and abs(x["at"][1] - d["head_outlet"][1]) <= 0.05)
            pts = [np.asarray(d["head_outlet"], float), np.asarray(spl["at"], float)] + pts
        return [Leg(name, "fall", np.array(pts), basis)]
    if k == "silo_drop":
        s = next(s for s in site["silos"] if s["id"] == b)
        _, _, _, hh = conveyor_axis(site, a)
        a0, _, _, _ = conveyor_axis(site, a)
        z_roof = site["silo_top_galleries"]["roof_spout_z"]
        return [Leg(name, "fall", np.array([(s["x"], a0[1], a0[2] - hh), (s["x"], s["y"], z_roof)]), basis)]
    if k == "silo_outlets":
        s = next(s for s in site["silos"] if s["id"] == a)
        gs = site["silo_gates"]
        x = s["x"] + gs["offsets_along_row"][len(gs["offsets_along_row"]) // 2]      # gate "<silo>.c": the centre
        return [Leg(name, "fall", np.array([(x, s["y"], gs["stack_z"]["sleeve"][0]), (x, s["y"], gs["stack_z"]["spout_bottom"])]),
                    basis, {"gate": f"{a}.c"})]
    if k == "boot_feed":
        t = next(t for t in site["tunnels"] if t["conveyor"]["id"] == a)
        ox, oz = t["conveyor"]["outlet_xz"]
        from . import tunnel
        inlet = tunnel.boot_inlet(site, t)
        return [Leg(name, "fall", np.array([(ox, t["row_y"], oz), inlet]), basis)]
    if k == "t1_pit":
        p = site["receiving"]["pit"]
        ox, oy = p["outlets"][0]                         # gate 6.24 = the first outlet (judgment)
        from . import receiving as recv
        return [Leg(name, "fall", np.array([(ox, oy, p["deck_z"]), (ox, oy, recv.outlet_z(p, oy, site["receiving"]))]), basis,
                    {"judgment": "gate 6.24 on the first pit outlet"})]
    if k == "t1_boot":
        tail, head, _, hh = conveyor_axis(site, "T1")
        n = next(n for n in site["receiving"]["norias"] if n["id"] == b)
        boot = rc.noria_boxes(n, site["receiving"])["boot"]
        return [Leg(name, "fall", np.array([head - (0, 0, hh), ((boot[0] + boot[3]) / 2, (boot[1] + boot[4]) / 2, boot[5])]), basis)]
    if k == "rspout":
        p0, p1 = _rspouts(site)[e["geom"]["name"]]
        if a == "GRAVITY_PIPE" and p_prev is not None:   # grain joins the pipe where its feed lands on it
            d = p1 - p0
            t = float(np.clip((p_prev - p0) @ d / (d @ d), 0.0, 1.0))
            p0 = p0 + d * t
        legs = [Leg(name, "fall", np.array([p0, p1]), basis)]
        if b == "SEP5":                                  # the pipe ends over the room; the separator is inside
            sx, sy, sz1, _ = _separator(site)
            legs.append(Leg(name + " (to separator)", "fall", np.array([p1, (sx, sy, sz1)]), "judgment",
                            {"judgment": "separator X not drawn; hidden drop from the pipe end into its inlet"}))
        return legs
    if k != "open":
        raise ValueError(f"{name}: unknown geometry kind {k}")

    # ---- open edges: the model has no geometry, straight connectors (judgment)
    gate_x = sp["gate"]["x"]
    y_in, y_out = _lane_y(site, "in"), _lane_y(site, "out")
    sc_in, sc_out = (sum(sp[k2]["x"]) / 2 for k2 in ("scales_in", "scales_out"))
    pit = site["receiving"]["pit"]
    ox, oy = pit["outlets"][0]
    b_sh1 = site["receiving"]["cleaning_tower"]["bin_Sh1"]
    sh1_x = sum(b_sh1["x"]) / 2
    J = {
        ("TRUCK_IN", "SCALES_IN"): ("drive", [(gate_x, y_in, TRUCK_Z), (sc_in, y_in, TRUCK_Z)]),
        ("SCALES_IN", "PIT"): ("drive", [(sc_in, y_in, TRUCK_Z), (ox, y_in, TRUCK_Z)]),
        ("TRUCK_OUT", "SCALES_OUT"): ("drive", [(sh1_x, y_out, TRUCK_Z), (sc_out, y_out, TRUCK_Z)]),
        ("SCALES_OUT", "TRUCK_EXIT"): ("drive", [(sc_out, y_out, TRUCK_Z), (gate_x, y_out, TRUCK_Z)]),
    }
    if (a, b) in J:
        kind, pts = J[(a, b)]
        return [Leg(name, kind, np.array(pts, float), "judgment", {"judgment": "truck on the site-plan lane"})]
    if (a, b) == ("H1", "NODE_1"):
        n = next(n for n in site["receiving"]["norias"] if n["id"] == "H1")
        gp = site["receiving"]["cleaning_tower"]["gravity_pipe"]
        return [Leg(name, "fall", np.array([rc.head_outlet(n, site["receiving"]), (gp["x"], *gp["node_1"])]), "judgment",
                    {"judgment": "H1 head -> node 1 not drawn"})]
    if (a, b) == ("SEP5", "SH1"):
        sx, sy, _, sz0 = _separator(site)
        return [Leg(name, "fall", np.array([(sx, sy, sz0), (sh1_x, sy, b_sh1["box_z"][1])]), "judgment",
                    {"judgment": "separator outlet straight into Ш1"})]
    if (a, b) == ("SH1", "TRUCK_OUT"):
        oy_, oz_ = b_sh1["outlet"]
        return [Leg(name, "fall", np.array([(sh1_x, oy_, oz_), (sh1_x, y_out, TRUCK_Z)]), "judgment",
                    {"judgment": "Ш1 gate into the trailer under it"})]
    if (a, b) == ("TOWER_PIT", "H3"):
        n = next(n for n in site["receiving"]["norias"] if n["id"] == "H3")
        boot = rc.noria_boxes(n, site["receiving"])["boot"]
        end = _rspouts(site)["Sh1->tower_pit"][1]
        return [Leg(name, "fall", np.array([end, ((boot[0] + boot[3]) / 2, (boot[1] + boot[4]) / 2, boot[5])]), "judgment",
                    {"judgment": "tower pit -> H3 boot not drawn (designed edge without geometry)"})]
    raise ValueError(f"{name}: open edge without a connector in routes.py")


# ------------------------------------------------------------------ nodes

def node_legs(site, g, node, p_in, p_out):
    """Legs inside a node between where its feed arrives (p_in) and where its outlet starts (p_out)."""
    kind = g.nodes[node]["kind"]
    layer = g.nodes[node]["layer"]
    if kind in ("conveyor", "conveyor_chain", "conveyor_belt"):
        legs = along(site, node, p_in, p_out)
    elif kind == "noria":
        legs = noria_leg(site, node, p_out)
    elif kind == "silo":
        s = next(s for s in site["silos"] if s["id"] == node)
        floor = _p(s["x"], s["y"], s["z"] + SILO_FLOOR_OVER_BASE)
        pts = [p for p in (p_in, floor, p_out) if p is not None]
        legs = [Leg(node, "store", np.array(pts), None, {"end": p_out is None, "start": p_in is None})]
    elif kind == "separator":
        sx, sy, z1, z0 = _separator(site)
        legs = [Leg(node, "fall", np.array([(sx, sy, z1), (sx, sy, z0)]), "judgment", {"judgment": "separator X"})]
    elif kind == "bin":
        b = site["receiving"]["cleaning_tower"]["bin_Sh1"]
        x = sum(b["x"]) / 2
        oy, oz = b["outlet"]
        legs = [Leg(node, "fall", np.array([(x, sum(b["y"]) / 2, b["box_z"][1]), (x, oy, oz)]), None)]
    elif kind == "pit" and node == "PIT":
        p = site["receiving"]["pit"]
        ox, oy = p["outlets"][0]
        y_in = _lane_y(site, "in")
        legs = [Leg(node, "fall", np.array([(ox, y_in, TRUCK_Z), (ox, oy, p["deck_z"])]), "judgment",
                    {"judgment": "trailer over the first pit outlet, tipping onto the grating"})]
    elif node == "TOWER_PIT" or kind in ("source", "sink", "scales", "truck_load", "gravity"):
        legs = [Leg(node, "transfer", np.array([p for p in (p_in, p_out) if p is not None] or [p_out]), None)]
    else:
        raise ValueError(f"{node}: no path rule for kind {kind}")
    for lg in legs:
        lg.basis = lg.basis or layer
    return legs


def route_legs(site, nodes, route):
    """Legs of one route: node, edge, node, ... Node legs are built after their out-edge so a
    conveyor knows where its outlet is; `joints` lists (leg i, leg i+1, gap m)."""
    g = pr.Graph(site)
    e_legs = []
    prev_end = None
    for e in route:
        el = edge_legs(site, e, prev_end)
        e_legs.append(el)
        prev_end = el[-1].pts[-1]
    legs = []
    for i, n in enumerate(nodes):
        p_in = e_legs[i - 1][-1].pts[-1] if i > 0 else None
        p_out = e_legs[i][0].pts[0] if i < len(route) else None
        legs += node_legs(site, g, n, p_in, p_out)
        if i < len(route):
            legs += e_legs[i]
    return legs


def joints(legs):
    """[(i, gap_m)] between the end of leg i and the start of leg i+1."""
    return [(i, float(np.linalg.norm(legs[i + 1].pts[0] - legs[i].pts[-1]))) for i in range(len(legs) - 1)]


def polyline(legs):
    """One continuous polyline through all legs (joint gaps bridged straight) with the leg index per point."""
    pts, idx = [], []
    for i, lg in enumerate(legs):
        for p in lg.pts:
            if pts and np.linalg.norm(p - pts[-1]) < 1e-6:
                continue
            pts.append(p)
            idx.append(i)
    return np.array(pts), idx


def slope_deg(a, b):
    d = np.asarray(b, float) - np.asarray(a, float)
    return math.degrees(math.atan2(-d[2], math.hypot(d[0], d[1]) + 1e-12))


def cycle_legs(name, site):
    """All legs of a named cycle, routes in order; the silo in between appears once as end and start."""
    out = []
    for nodes, route in cycle(name, site):
        out.append((nodes, route_legs(site, nodes, route)))
    return out
