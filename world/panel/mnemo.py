"""Control center, module P: the process schematic (мнемосхема) as SVG, built from the process graph and
world/panel/layout.json. Plain Python: check_panel.py reads the same SVG and proves every node, edge and gate
of the graph is on it; the browser only changes classes and numbers by element id.

Ids:   n-<node>  the symbol of a node        e-<from>-><to>  the grain line of an edge
       g-<gate>  a gate on its line          lvl-<store>     the level inside a silo / bin
       st-<node> the state text under a node  val-<node>     the number under a node (t/h, t)
Layout (judgment: a schematic, not the plan; the order of outlets follows the graph `order`):
  shapes  noria (x, top, bot) | conveyor (x0 tail, x1 head, y) | silo (x, top, bot, w) | hopper (x, top, bot, w)
          | box (x, y, w, h) | point (x, y) | pipe (x, y0, y1) | truck (x, y)
  edges   "A->B": {"from_x", "to_x" (a point along a conveyor), "y" (the level of the horizontal run),
                   "pts" (the whole polyline), "gate_t" (where along the line the gates sit, 0..1)}
"""

import json
import math
from pathlib import Path
from xml.sax.saxutils import escape

LAYOUT = Path(__file__).resolve().parent / "layout.json"


def load_layout(path=None):
    return json.loads(Path(path or LAYOUT).read_text(encoding="utf-8"))


def _port(shape, side, at=None):
    """(x, y) where grain leaves (side 'out') or enters (side 'in') a symbol."""
    k = shape["shape"]
    if k == "noria":
        return (shape["x"], shape["top"]) if side == "out" else (shape["x"], shape["bot"])
    if k == "conveyor":
        x = at if at is not None else (shape["x1"] if side == "out" else shape["x0"])
        return x, shape["y"]
    if k in ("silo", "hopper"):
        return (shape["x"], shape["bot"]) if side == "out" else (shape["x"], shape["top"])
    if k == "pipe":
        return (shape["x"], shape["y1"]) if side == "out" else (shape["x"], shape["y0"])
    if k in ("box", "truck"):
        s = shape.get(f"{side}_side", "bottom" if side == "out" else "top")
        w, h = shape.get("w", 60), shape.get("h", 30)
        return {"top": (shape["x"], shape["y"] - h / 2), "bottom": (shape["x"], shape["y"] + h / 2),
                "left": (shape["x"] - w / 2, shape["y"]), "right": (shape["x"] + w / 2, shape["y"])}[s]
    return shape["x"], shape["y"]


def bbox(shape):
    k = shape["shape"]
    if k == "noria":
        return shape["x"] - 16, shape["top"] - 14, shape["x"] + 16, shape["bot"] + 14
    if k == "conveyor":
        a, b = sorted((shape["x0"], shape["x1"]))
        return a - 4, shape["y"] - 8, b + 4, shape["y"] + 8
    if k in ("silo", "hopper"):
        w = shape.get("w", 80)
        return shape["x"] - w / 2, shape["top"] - (28 if k == "silo" else 0), shape["x"] + w / 2, shape["bot"]
    if k == "pipe":
        return shape["x"] - 6, shape["y0"], shape["x"] + 6, shape["y1"]
    if k == "point":
        return shape["x"] - 8, shape["y"] - 8, shape["x"] + 8, shape["y"] + 8
    w, h = shape.get("w", 60), shape.get("h", 30)
    return shape["x"] - w / 2, shape["y"] - h / 2, shape["x"] + w / 2, shape["y"] + h / 2


def edge_points(lay, e):
    key = f"{e['from']}->{e['to']}"
    spec = lay["edges"].get(key, {})
    if "pts" in spec:
        return [tuple(p) for p in spec["pts"]]
    a = _port(lay["nodes"][e["from"]], "out", spec.get("from_x"))
    b = _port(lay["nodes"][e["to"]], "in", spec.get("to_x"))
    if abs(a[0] - b[0]) < 1e-6:
        return [a, b]
    y = spec.get("y", (a[1] + b[1]) / 2)
    return [a, (a[0], y), (b[0], y), b]


def alt_points(lay, e):
    """The branch of the side outlets of a silo: layout `alt_pts`, or 22 px beside the main line, joining it
    two thirds of the way down."""
    key = f"{e['from']}->{e['to']}"
    spec = lay["edges"].get(key, {})
    if "alt_pts" in spec:
        return [tuple(p) for p in spec["alt_pts"]]
    (x0, y0), (x1, y1) = edge_points(lay, e)[0], edge_points(lay, e)[-1]
    ym = y0 + (y1 - y0) * 0.72
    return [(x0 + 22, y0), (x0 + 22, ym), (x1, ym)]


def along(pts, t):
    seg = [math.dist(p, q) for p, q in zip(pts, pts[1:])]
    total = sum(seg) or 1.0
    d = t * total
    for (p, q), L in zip(zip(pts, pts[1:]), seg):
        if d <= L or L == seg[-1]:
            k = d / L if L else 0
            return p[0] + (q[0] - p[0]) * k, p[1] + (q[1] - p[1]) * k, (q[0] - p[0], q[1] - p[1])
        d -= L
    return pts[-1][0], pts[-1][1], (1, 0)


def _f(v):
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _label(x, y, text, cls="lbl", anchor="middle"):
    return f'<text class="{cls}" x="{_f(x)}" y="{_f(y)}" text-anchor="{anchor}">{escape(text)}</text>'


def symbol(nid, s, title):
    k = s["shape"]
    out = [f'<g id="n-{escape(nid)}" class="node {k}" data-id="{escape(nid)}"><title>{escape(title)}</title>']
    if k == "noria":
        x, t, b = s["x"], s["top"], s["bot"]
        out += [f'<rect class="body leg" x="{_f(x - 9)}" y="{_f(t)}" width="7" height="{_f(b - t)}"/>',
                f'<rect class="body leg" x="{_f(x + 2)}" y="{_f(t)}" width="7" height="{_f(b - t)}"/>',
                f'<rect class="body head" x="{_f(x - 15)}" y="{_f(t - 14)}" width="30" height="24" rx="10"/>',
                f'<rect class="body boot" x="{_f(x - 15)}" y="{_f(b - 12)}" width="30" height="24" rx="3"/>']
        lx, ly = x + s.get("lbl_dx", 14), t + (b - t) * s.get("lbl_at", 0.42) + s.get("lbl_dy", 0)
        anchor = "start" if s.get("lbl_dx", 14) >= 0 else "end"
    elif k == "conveyor":
        a, b = sorted((s["x0"], s["x1"]))
        y = s["y"]
        d = 1 if s["x1"] > s["x0"] else -1
        hx = s["x1"]
        out += [f'<rect class="body" x="{_f(a)}" y="{_f(y - 6)}" width="{_f(b - a)}" height="12" rx="6"/>',
                f'<path class="dir" d="M{_f(hx - d * 16)},{_f(y - 4)} L{_f(hx - d * 8)},{_f(y)} L{_f(hx - d * 16)},{_f(y + 4)}"/>']
        lx, ly = (a + b) / 2 + s.get("lbl_dx", 0), y - 11 + s.get("lbl_dy", 0)
        anchor = "middle"
        s = dict(s, st_y=s.get("st_y", y + 20 + s.get("lbl_dy", 0)))
    elif k == "silo":
        x, t, b, w = s["x"], s["top"], s["bot"], s.get("w", 80)
        out += [f'<path class="body" d="M{_f(x - w / 2)},{_f(t)} L{_f(x)},{_f(t - 26)} L{_f(x + w / 2)},{_f(t)} '
                f'L{_f(x + w / 2)},{_f(b)} L{_f(x - w / 2)},{_f(b)} Z"/>',
                f'<clipPath id="clip-{escape(nid)}"><rect x="{_f(x - w / 2)}" y="{_f(t)}" width="{_f(w)}" height="{_f(b - t)}"/></clipPath>',
                f'<rect id="lvl-{escape(nid)}" class="level" clip-path="url(#clip-{escape(nid)})" x="{_f(x - w / 2)}" y="{_f(b)}" '
                f'width="{_f(w)}" height="0" data-top="{_f(t)}" data-bot="{_f(b)}"/>']
        lx, ly, anchor = x, t + 24, "middle"
        s = dict(s, st_y=t + 42)
    elif k == "hopper":
        x, t, b, w = s["x"], s["top"], s["bot"], s.get("w", 80)
        out += [f'<path class="body" d="M{_f(x - w / 2)},{_f(t)} L{_f(x + w / 2)},{_f(t)} L{_f(x + 8)},{_f(b)} '
                f'L{_f(x - 8)},{_f(b)} Z"/>',
                f'<clipPath id="clip-{escape(nid)}"><path d="M{_f(x - w / 2)},{_f(t)} L{_f(x + w / 2)},{_f(t)} L{_f(x + 8)},{_f(b)} '
                f'L{_f(x - 8)},{_f(b)} Z"/></clipPath>',
                f'<rect id="lvl-{escape(nid)}" class="level" clip-path="url(#clip-{escape(nid)})" x="{_f(x - w / 2)}" y="{_f(b)}" '
                f'width="{_f(w)}" height="0" data-top="{_f(t)}" data-bot="{_f(b)}"/>']
        lx, ly, anchor = x + s.get("lbl_dx", 0), t - 6 + s.get("lbl_dy", 0), "middle"
    elif k == "pipe":
        out += [f'<rect class="body pipe" x="{_f(s["x"] - 4)}" y="{_f(s["y0"])}" width="8" height="{_f(s["y1"] - s["y0"])}"/>']
        lx, ly, anchor = s["x"] + 10, (s["y0"] + s["y1"]) / 2, "start"
    elif k == "point":
        out += [f'<circle class="body" cx="{_f(s["x"])}" cy="{_f(s["y"])}" r="6"/>']
        lx, ly, anchor = s["x"] + 10, s["y"] - 8, "start"
    elif k == "truck":
        x, y = s["x"], s["y"]
        out += [f'<rect class="body" x="{_f(x - 30)}" y="{_f(y - 12)}" width="40" height="22" rx="2"/>',
                f'<rect class="body" x="{_f(x + 12)}" y="{_f(y - 6)}" width="16" height="16" rx="3"/>',
                f'<circle class="wheel" cx="{_f(x - 20)}" cy="{_f(y + 12)}" r="4"/>',
                f'<circle class="wheel" cx="{_f(x + 18)}" cy="{_f(y + 12)}" r="4"/>']
        lx, ly, anchor = x, y - 18, "middle"
        s = dict(s, st_y=s.get("st_y", y + 28))
    else:
        x, y, w, h = s["x"], s["y"], s.get("w", 60), s.get("h", 30)
        out += [f'<rect class="body" x="{_f(x - w / 2)}" y="{_f(y - h / 2)}" width="{_f(w)}" height="{_f(h)}" rx="3"/>']
        if s.get("level"):
            out += [f'<clipPath id="clip-{escape(nid)}"><rect x="{_f(x - w / 2)}" y="{_f(y - h / 2)}" width="{_f(w)}" height="{_f(h)}"/></clipPath>',
                    f'<rect id="lvl-{escape(nid)}" class="level" clip-path="url(#clip-{escape(nid)})" x="{_f(x - w / 2)}" '
                    f'y="{_f(y + h / 2)}" width="{_f(w)}" height="0" data-top="{_f(y - h / 2)}" data-bot="{_f(y + h / 2)}"/>']
        lx, ly, anchor = x + s.get("lbl_dx", 0), y - h / 2 - 5 + s.get("lbl_dy", 0), "middle"
    name = s.get("label", nid)
    out.append(_label(lx, ly, name, "lbl big" if k == "silo" else "lbl", anchor))
    sx, sy = s.get("st_x", lx), s.get("st_y", ly + 12)
    out.append(f'<text id="st-{escape(nid)}" class="st" x="{_f(sx)}" y="{_f(sy)}" text-anchor="{anchor}"></text>')
    out.append(f'<text id="val-{escape(nid)}" class="val" x="{_f(sx)}" y="{_f(sy + 11)}" text-anchor="{anchor}"></text>')
    out.append("</g>")
    return "".join(out)


def gate_symbol(gid, x, y, direction):
    """Bow-tie valve across the line; `direction` is the line direction at that point."""
    dx, dy = direction
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    px, py = -uy, ux
    a, b = 7.0, 6.0
    p1 = (x - ux * a + px * b, y - uy * a + py * b)
    p2 = (x - ux * a - px * b, y - uy * a - py * b)
    p3 = (x + ux * a + px * b, y + uy * a + py * b)
    p4 = (x + ux * a - px * b, y + uy * a - py * b)
    left = f"M{_f(x)},{_f(y)} L{_f(p1[0])},{_f(p1[1])} L{_f(p2[0])},{_f(p2[1])} Z"
    right = f"M{_f(x)},{_f(y)} L{_f(p3[0])},{_f(p3[1])} L{_f(p4[0])},{_f(p4[1])} Z"
    tx, ty = x + px * 16, y + py * 16
    return (f'<g id="g-{escape(gid)}" class="gate closed" data-id="{escape(gid)}"><title>засувка {escape(gid)}</title>'
            f'<path class="half a" d="{left}"/><path class="half b" d="{right}"/>'
            f'<circle class="hit" cx="{_f(x)}" cy="{_f(y)}" r="11"/>'
            f'<text class="glbl" x="{_f(tx)}" y="{_f(ty + 3)}" text-anchor="middle">{escape(gid)}</text></g>')


def build_svg(graph, lay=None):
    lay = lay or load_layout()
    W, H = lay["size"]
    edges_svg, gates_svg, drawn = [], [], set()
    for e in graph.edges:
        key = f"{e['from']}->{e['to']}"
        pts = edge_points(lay, e)
        d = "M" + " L".join(f"{_f(x)},{_f(y)}" for x, y in pts)
        edges_svg.append(f'<path id="e-{escape(key)}" class="flow" d="{d}"><title>{escape(key)}</title></path>')
        ids = [g for g in e["gates"] + e.get("alt_gates", []) if g not in drawn]
        spec = lay["edges"].get(key, {})
        if e.get("alt_gates"):                    # silo side outlets: a parallel branch that joins the main line
            alt = alt_points(lay, e)
            da = "M" + " L".join(f"{_f(x)},{_f(y)}" for x, y in alt)
            edges_svg.append(f'<path id="e-{escape(key)}~alt" class="flow alt" d="{da}"><title>{escape(key)} (бічні отвори)</title></path>')
        t0 = spec.get("gate_t", 0.5)
        for i, gid in enumerate(ids):
            gt = spec.get("gate_pos", {}).get(gid)
            if gt is not None:
                x, y, dirn = gt[0], gt[1], (1, 0) if len(gt) < 3 else ((1, 0) if gt[2] == "h" else (0, 1))
            else:
                x, y, dirn = along(pts, min(0.95, t0 + 0.18 * i))
            gates_svg.append(gate_symbol(gid, x, y, dirn))
            drawn.add(gid)
    nodes_svg = []
    for n, v in graph.nodes.items():
        s = lay["nodes"][n]
        title = f"{n} — {v['kind']}" + (f" {v.get('model')}" if v.get("model") else "")
        nodes_svg.append(symbol(n, s, title))
    deco = []
    for z in lay.get("zones", []):
        x0, y0, x1, y1 = z["box"]
        deco.append(f'<rect class="zone" x="{_f(x0)}" y="{_f(y0)}" width="{_f(x1 - x0)}" height="{_f(y1 - y0)}" rx="6"/>')
        deco.append(_label(x0 + 8, y0 + 16, z["label"], "zlbl", "start"))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" id="mnemo" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">'
            f'<g class="zones">{"".join(deco)}</g><g class="edges">{"".join(edges_svg)}</g>'
            f'<g class="nodes">{"".join(nodes_svg)}</g><g class="gates">{"".join(gates_svg)}</g></svg>')
