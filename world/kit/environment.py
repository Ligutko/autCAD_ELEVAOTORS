"""Phase W1. Environment around the site (designed layer, research/design/environment.md):
ground split into a hard (concrete/asphalt) yard and summer grass, hardened road shoulders cut where a structure stands.

Site frame. Data: SITE.json `designed.environment`; roads come from `designed.site_plan` (kit/site_plan.py).
"""

import numpy as np

from . import common as c
from . import site_plan as spl


def _site():
    from . import receiving as rc
    return rc._site()


def spec(site=None):
    return (site or _site())["designed"]["environment"]


def obstacles(site=None):
    """Plan footprints a ground strip must stop at: the site-plan list plus the tunnels
    (roof +0.6 over the ground) and the exit pavilions."""
    from . import tunnel as tun
    site = site or _site()
    ob = list(spl.footprints(site))
    for t in site.get("tunnels", []):
        ob += [(f"tunnel {t['id']}", "rect", r) for r in tun.footprint(site, t)]
        if "tunnel_exit_pavilion" in site.get("designed", {}):
            _, meas = tun.pavilion(site, t)
            ob.append((f"pavilion {t['id']}", "rect", meas["covers"]))
    shed = site["receiving"]["pit"]["building"]
    ob.append(("pit shed", "rect", (shed["x"][0], shed["y"][0], shed["x"][1], shed["y"][1])))
    return ob


def dist_many(q, ob):
    """Signed distance from points q (..., 2) to the nearest footprint (negative inside)."""
    q = np.asarray(q, float)
    best = np.full(q.shape[:-1], np.inf)
    for _, kind, g in ob:
        if kind == "circle":
            d = np.hypot(q[..., 0] - g[0], q[..., 1] - g[1]) - g[2]
        else:
            x0, y0, x1, y1 = g
            dx = np.maximum.reduce([x0 - q[..., 0], np.zeros(q.shape[:-1]), q[..., 0] - x1])
            dy = np.maximum.reduce([y0 - q[..., 1], np.zeros(q.shape[:-1]), q[..., 1] - y1])
            inside = -np.minimum.reduce([q[..., 0] - x0, x1 - q[..., 0], q[..., 1] - y0, y1 - q[..., 1]])
            d = np.where((dx > 0) | (dy > 0), np.hypot(dx, dy), inside)
        best = np.minimum(best, d)
    return best


def lane_frame(ln, step=0.25):
    """Centreline points, unit normals (left) and half widths of a lane."""
    pts = spl.lane_polyline(ln, step)
    d = np.gradient(pts, axis=0)
    d /= np.linalg.norm(d, axis=1)[:, None]
    nrm = np.column_stack([-d[:, 1], d[:, 0]])
    hw = np.array([spl.lane_width(ln, p[0]) / 2 for p in pts]) if "pts" in ln else np.full(len(pts), ln["w"] / 2)
    return pts, nrm, hw


def shoulder_widths(site, ln, ob=None, step=0.25, march=0.02):
    """Free shoulder width on each side of a lane: the design width, or less where a structure stands
    closer to the road edge. Returns pts, nrm, hw, widths (n, 2) for sides (+left, -right)."""
    ob = obstacles(site) if ob is None else ob
    w = spec(site)["shoulder"]["w"]
    pts, nrm, hw = lane_frame(ln, step)
    ds = np.arange(march, w + 1e-9, march)
    out = np.empty((len(pts), 2))
    for k, side in enumerate((1.0, -1.0)):
        edge = pts + side * nrm * hw[:, None]
        q = edge[:, None, :] + side * nrm[:, None, :] * ds[None, :, None]
        free = dist_many(q, ob) >= 0.0 if ob else np.ones(q.shape[:2], bool)
        blocked = ~free
        first = np.where(blocked.any(axis=1), blocked.argmax(axis=1), len(ds))
        out[:, k] = np.where(first == 0, 0.0, np.where(first < len(ds), ds[np.maximum(first - 1, 0)], w))
    return pts, nrm, hw, out


def _faces_up(v, f):
    return spl.faces_up(v, f)


def build_shoulders(site=None, ob=None):
    """Hardened shoulders along every lane, just under the road ribbons: a strip per straight segment (or arc)
    plus a fan on the outer side of each bend (site_plan.corner_joins). Returns (verts, faces), per-lane widths."""
    site = site or _site()
    ob = obstacles(site) if ob is None else ob
    e = spec(site)["shoulder"]
    z_fan = c.ground_z() + e["z_over_ground"]
    level = iter(z_fan + e["z_step"] * (k + 1) for k in range(1000))      # overlapping coplanar strips render black
    w_design = e["w"]
    parts, meas = [], {}
    for ln in spl.spec(site)["lanes"]:
        meas[ln["id"]] = []
        for pc in spl.pieces(ln):
            z = next(level)
            pts, nrm, hw, wid = shoulder_widths(site, pc, ob)
            meas[ln["id"]].append(wid)
            n = len(pts)
            for k, side in enumerate((1.0, -1.0)):
                inner = pts + side * nrm * hw[:, None]
                outer = inner + side * nrm * wid[:, k][:, None]
                v = np.concatenate([np.column_stack([inner, np.full(n, z)]), np.column_stack([outer, np.full(n, z)])])
                f = [(i, i + 1, n + i + 1, n + i) for i in range(n - 1) if wid[i, k] > 0.01 or wid[i + 1, k] > 0.01]
                if f:
                    parts.append((v, _faces_up(v, f)))
    for cp, d1, d2, hw, side in spl.corner_joins(spl.spec(site)):         # outer corner fans, lanes and bends
        q = spl.corner_fill(cp, d1, d2, hw + w_design, side)
        if ob and min(dist_many(np.array(q[1:]), ob)) < 0:                   # a structure in the corner: leave it bare
            continue
        v = np.array([(*p, z_fan) for p in q])
        parts.append((v, _faces_up(v, [(0, 1, 2), (0, 2, 3)])))
    return c.merge_parts(parts), meas


def ground_holes(site):
    """Plan holes in the ground slab: tunnels with their stair wells, noria tower pits, the receiving pit
    and the receiving tower pit (as site.py cut them before W1)."""
    from . import noria_tower as tower
    from . import tunnel as tun
    holes = []
    for t in site.get("tunnels", []):
        holes += tun.footprint(site, t)
    for sp in site["noria_towers"]:
        x0, y0, x1, y1 = tower.pit_inner(sp)
        w = sp["pit"]["wall_t"]
        holes.append((sp["x"] + x0 - w, sp["y"] + y0 - w, sp["x"] + x1 + w, sp["y"] + y1 + w))
    r = site.get("receiving", {})
    if "tower" in r:
        p, w = r["pit"], r["pit"]["wall_t"]
        tp = r["tower"]["pit"]
        holes += [(p["x"][0] - w, p["y"][0] - w, p["x"][1] + w, p["y"][1] + w),
                  (tp["inner_x"][0] - tp["wall_t"], tp["inner_y"][0] - tp["wall_t"], tp["inner_x"][1] + tp["wall_t"], tp["inner_y"][1] + tp["wall_t"])]
    return holes


def ground(site, holes, extent=2000.0, thick=0.2):
    """Ground slab (top at ground_z) split into the yard (hard concrete/asphalt surface) and grass; plan holes left out
    as in tunnel.ground_cells. Returns {"yard": (v, f), "grass": (v, f)}."""
    z1 = c.ground_z()
    z0 = z1 - thick
    rects = spec(site)["yard"]["rects"]
    xs = sorted({-extent, extent} | {h[0] for h in holes} | {h[2] for h in holes} | {r[0] for r in rects} | {r[2] for r in rects})
    ys = sorted({-extent, extent} | {h[1] for h in holes} | {h[3] for h in holes} | {r[1] for r in rects} | {r[3] for r in rects})
    out = {"yard": [], "grass": []}
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            mx, my = (xa + xb) / 2, (ya + yb) / 2
            if any(h[0] <= mx <= h[2] and h[1] <= my <= h[3] for h in holes):
                continue
            key = "yard" if any(r[0] <= mx <= r[2] and r[1] <= my <= r[3] for r in rects) else "grass"
            out[key].append(c.box((xa, ya, z0), (xb, yb, z1)))
    return {k: c.merge_parts(v) for k, v in out.items()}


def top_area(v, f, z):
    """Plan area of the faces lying at height z (the ground top)."""
    a = 0.0
    for block in (f if isinstance(f, list) else [f]):
        p = v[np.asarray(block)]                                          # (n, k, 3)
        top = np.all(np.abs(p[:, :, 2] - z) < 1e-6, axis=1)
        x, y = p[top, :, 0], p[top, :, 1]
        a += float(np.sum(0.5 * np.abs(np.sum(x * np.roll(y, -1, axis=1) - y * np.roll(x, -1, axis=1), axis=1))))
    return a


def build(site=None):
    site = site or _site()
    g = ground(site, ground_holes(site))
    sh, _ = build_shoulders(site)
    return {"ground_yard": ("yard", False, g["yard"]), "ground_grass": ("grass", False, g["grass"]),
            "shoulders": ("shoulder", False, sh)}
