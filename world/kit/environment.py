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


# ---------------------------------------------------------------- W1b fence, gates, aprons

_BOX_F = np.array([(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)])


def boxes(lo, hi):
    """Many axis-aligned boxes at once (corner order as common.box): lo, hi (n, 3) -> (verts, faces)."""
    lo, hi = np.asarray(lo, float).reshape(-1, 3), np.asarray(hi, float).reshape(-1, 3)
    sel = np.array([[i, j, k] for i in (0, 1) for j in (0, 1) for k in (0, 1)])       # 8 corners
    v = np.where(sel[None, :, :] == 0, lo[:, None, :], hi[:, None, :]).reshape(-1, 3)
    f = (_BOX_F[None, :, :] + 8 * np.arange(len(lo))[:, None, None]).reshape(-1, 4)
    return v, f


def fence_sides(fe):
    """The four sides of the fence rectangle: {side: (fixed coord, t0, t1, axis of t, outward sign)}."""
    x0, y0, x1, y1 = fe["rect"]
    return {"S": (y0, x0, x1, 0, -1.0), "E": (x1, y0, y1, 1, 1.0), "N": (y1, x0, x1, 0, 1.0), "W": (x0, y0, y1, 1, -1.0)}


def openings(site):
    """Gaps in the fence: [(side, t0, t1, kind, gate dict or None)] — a gate centred on its lane axis, the wicket."""
    fe = spec(site)["fence"]
    sides = fence_sides(fe)
    out = []
    for gt in fe["gates"]:
        ln = spl.lane(spl.spec(site), gt["lane"])
        fixed, _, _, ax, _ = sides[gt["side"]]
        end = min(ln["pts"], key=lambda p: abs(p[1 - ax] - fixed))              # the lane end on this side
        cen = end[ax]
        out.append((gt["side"], cen - gt["clear"] / 2, cen + gt["clear"] / 2, "gate", gt))
    w = fe["wicket"]
    out.append((w["side"], w["c"] - w["w"] / 2, w["c"] + w["w"] / 2, "wicket", None))
    return out


def fence_runs(site):
    """Solid fence stretches between openings: [(side, t0, t1)]."""
    fe = spec(site)["fence"]
    runs = []
    for side, (fixed, t0, t1, ax, sg) in fence_sides(fe).items():
        cuts = sorted((a, b) for s, a, b, *_ in openings(site) if s == side)
        t = t0
        for a, b in cuts:
            if a > t:
                runs.append((side, t, a))
            t = max(t, b)
        if t < t1:
            runs.append((side, t, t1))
    return runs


def _to_world(side, fe, t_lo, t_hi, n_lo, n_hi, z_lo, z_hi):
    """Boxes given along a side (t along it, n outward from the fence line) -> world lo, hi."""
    fixed, _, _, ax, sg = fence_sides(fe)[side]
    t_lo, t_hi, n_lo, n_hi, z_lo, z_hi = np.broadcast_arrays(*(np.asarray(a, float) for a in (t_lo, t_hi, n_lo, n_hi, z_lo, z_hi)))
    a, b = fixed + sg * n_lo, fixed + sg * n_hi
    c_lo, c_hi = np.minimum(a, b), np.maximum(a, b)
    if ax == 0:                                                            # t runs along x, the side is at fixed y
        return np.column_stack([t_lo, c_lo, z_lo]), np.column_stack([t_hi, c_hi, z_hi])
    return np.column_stack([c_lo, t_lo, z_lo]), np.column_stack([c_hi, t_hi, z_hi])


def _mesh_panel(fe, side, t0, t1, n, z0, z1):
    """Welded mesh between t0 and t1 at offset n: vertical wires every mesh[0], horizontal every mesh[1]."""
    wd = fe["wire_d"] / 2
    sx, sz = fe["mesh"]
    tv = np.arange(t0 + sx / 2, t1 - sx / 4, sx)
    zh = np.arange(z0 + sz / 4, z1 + 1e-6, sz)
    lo1, hi1 = _to_world(side, fe, tv - wd, tv + wd, n - wd, n + wd, z0, z1)
    lo2, hi2 = _to_world(side, fe, t0, t1, n - wd, n + wd, zh - wd, zh + wd)
    return np.concatenate([lo1, lo2]), np.concatenate([hi1, hi2])


def fence_height(fe):
    return fe["plinth_h"] + fe["panel_h"]


def gate_leaf(fe, op):
    """Open position of a sliding gate leaf along the fence inside the site: (t0, t1)."""
    side, a, b, _, gt = op
    L = fe["leaf_ratio"] * gt["clear"]
    return (b, b + L) if gt["roll"] > 0 else (a - L, a)


def build_fence(site=None):
    """Posts, plinths and welded mesh panels on every run; sliding gate leaves (rolled back, open) with their
    guide posts; the wicket leaf. Returns {"posts", "plinth", "mesh"}: (verts, faces)."""
    site = site or _site()
    fe = spec(site)["fence"]
    g = c.ground_z()
    ph, top = fe["plinth_h"], fence_height(fe)
    pw, pt = fe["post"]
    posts_lo, posts_hi, pl_lo, pl_hi, me_lo, me_hi = [], [], [], [], [], []

    def post(side, t, size=(pw, pt), h=top + 0.05):
        lo, hi = _to_world(side, fe, t - size[1] / 2, t + size[1] / 2, -size[0] / 2, size[0] / 2, g, g + h)
        posts_lo.append(lo)
        posts_hi.append(hi)

    for side, t0, t1 in fence_runs(site):
        n = max(1, int(np.ceil((t1 - t0) / fe["panel_w"] - 1e-9)))
        ts = np.linspace(t0, t1, n + 1)
        for t in ts:
            post(side, t)
        lo, hi = _to_world(side, fe, ts[:-1] + pt / 2, ts[1:] - pt / 2, -fe["plinth_t"] / 2, fe["plinth_t"] / 2, g, g + ph)
        pl_lo.append(lo)
        pl_hi.append(hi)
        for a, b in zip(ts, ts[1:]):
            lo, hi = _mesh_panel(fe, side, a + pt / 2 + 0.01, b - pt / 2 - 0.01, 0.0, g + ph + 0.02, g + top)
            me_lo.append(lo)
            me_hi.append(hi)
    for op in openings(site):
        side, a, b, kind, gt = op
        for t in (a, b):
            post(side, t, size=(0.1, 0.1), h=top + 0.1)                       # heavier gate posts (judgment)
        if kind == "gate":
            l0, l1 = gate_leaf(fe, op)
            for t in (l0 + 0.3, l1 - 0.3):                                    # roller supports under the open leaf
                lo, hi = _to_world(side, fe, t - 0.1, t + 0.1, -0.45, -0.25, g, g + 0.35)
                posts_lo.append(lo)
                posts_hi.append(hi)
            n = -0.35                                                         # leaf runs just inside the fence line
            frame = [(l0, l1, n - 0.03, n + 0.03, g + 0.35, g + 0.45), (l0, l1, n - 0.03, n + 0.03, g + top - 0.06, g + top),
                     (l0, l0 + 0.06, n - 0.03, n + 0.03, g + 0.35, g + top), (l1 - 0.06, l1, n - 0.03, n + 0.03, g + 0.35, g + top)]
            for fr in frame:
                lo, hi = _to_world(side, fe, *fr)
                posts_lo.append(lo)
                posts_hi.append(hi)
            lo, hi = _mesh_panel(fe, side, l0 + 0.06, l1 - 0.06, n, g + 0.45, g + top - 0.06)
            me_lo.append(lo)
            me_hi.append(hi)
        else:                                                                 # wicket leaf, closed
            lo, hi = _mesh_panel(fe, side, a + 0.06, b - 0.06, 0.0, g + 0.05, g + top - 0.05)
            me_lo.append(lo)
            me_hi.append(hi)
    cat = lambda xs: np.concatenate(xs)
    return {"posts": boxes(cat(posts_lo), cat(posts_hi)), "plinth": boxes(cat(pl_lo), cat(pl_hi)),
            "mesh": boxes(cat(me_lo), cat(me_hi))}


def apron_rects(site=None):
    """Aprons around the structures that stand on grass: each footprint grown by the apron width; overlapping
    ones merged into one pad (a common pad under the fire tanks and the pump house)."""
    site = site or _site()
    a = spec(site)["aprons"]
    sp = spl.spec(site)
    w = a["w"]
    rects = []
    for key in a["for"]:
        if key == "fire_tanks":
            ft = sp["fire_tanks"]
            r = ft["d"] / 2
            rects += [(x - r - w, y - r - w, x + r + w, y + r + w) for x, y in ft["c"]]
        else:
            q = sp["gate"]["kpp"] if key == "kpp" else sp["fire_tanks"]["pump_house"] if key == "pump_house" else sp[key]
            rects.append((q["x"][0] - w, q["y"][0] - w, q["x"][1] + w, q["y"][1] + w))
    merged = True
    while merged:
        merged = False
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                p, q = rects[i], rects[j]
                if p[0] <= q[2] and q[0] <= p[2] and p[1] <= q[3] and q[1] <= p[3]:
                    rects[i] = (min(p[0], q[0]), min(p[1], q[1]), max(p[2], q[2]), max(p[3], q[3]))
                    del rects[j]
                    merged = True
                    break
            if merged:
                break
    return rects


def build_aprons(site=None):
    """Concrete aprons as flat pads just over the ground, under the shoulders and roads they meet."""
    site = site or _site()
    a = spec(site)["aprons"]
    z = c.ground_z() + a["z_over_ground"]
    parts = []
    for x0, y0, x1, y1 in apron_rects(site):                                # merged: pads never overlap each other
        v = np.array([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)])
        parts.append((v, _faces_up(v, [(0, 1, 2, 3)])))
    return c.merge_parts(parts)


def build(site=None):
    site = site or _site()
    g = ground(site, ground_holes(site))
    sh, _ = build_shoulders(site)
    out = {"ground_yard": ("yard", False, g["yard"]), "ground_grass": ("grass", False, g["grass"]),
           "shoulders": ("shoulder", False, sh)}
    e = spec(site)
    if "aprons" in e:
        out["aprons"] = ("yard", False, build_aprons(site))
    if "fence" in e:
        fp = build_fence(site)
        out.update({"fence_posts": ("fence", False, fp["posts"]), "fence_plinth": ("concrete", False, fp["plinth"]),
                    "fence_mesh": ("fence", False, fp["mesh"])})
    return out
