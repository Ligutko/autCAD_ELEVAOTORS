"""Phase W1d. Surroundings beyond the fence (designed layer, research/design/environment.md): the public road the
gates open onto with the approaches, crop fields and field shelterbelts of trees.

Site frame. Data: SITE.json `designed.environment.surroundings`. Trees are a few low-poly prototypes placed as
collection instances (positions from `tree_positions`, deterministic).
"""

import math

import numpy as np

from . import common as c
from . import site_plan as spl


def _site():
    from . import receiving as rc
    return rc._site()


def spec(site=None):
    return (site or _site())["designed"]["environment"]["surroundings"]


# ---------------------------------------------------------------- roads

def approach_lanes(site=None):
    """Each gate lane carried on from the fence to the public road's near edge: [(lane id, (x0, y), (x1, y), w)]."""
    site = site or _site()
    su = spec(site)
    sp = spl.spec(site)
    pr = su["public_road"]
    x_edge = pr["x"] - pr["w"] / 2
    out = []
    for lid in su["approach"]["lanes"]:
        ln = spl.lane(sp, lid)
        end = max(ln["pts"], key=lambda p: p[0])                        # the gate end
        out.append((lid, (end[0], end[1]), (x_edge, end[1]), ln["w"]))
    return out


def build_roads(site=None):
    """Public road (asphalt) with shoulders, the approaches (concrete, as the site drives)."""
    site = site or _site()
    su = spec(site)
    pr = su["public_road"]
    g = c.ground_z()
    z = g + site["designed"]["site_plan"]["road_z_over_ground"]
    y0, y1 = pr["y"]
    x0, x1 = pr["x"] - pr["w"] / 2, pr["x"] + pr["w"] / 2
    road = [(np.array([(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]), np.array([(0, 1, 2, 3)]))]
    sh = []
    for xa, xb in ((x0 - pr["shoulder"], x0), (x1, x1 + pr["shoulder"])):
        zz = g + 0.006
        sh.append((np.array([(xa, y0, zz), (xb, y0, zz), (xb, y1, zz), (xa, y1, zz)]), np.array([(0, 1, 2, 3)])))
    app = []
    for k, (_, (xa, ya), (xb, yb), w) in enumerate(approach_lanes(site)):
        zz = z + 0.002 * (k + 1)                                         # own level over the public road where they meet
        app.append((np.array([(xa, ya - w / 2, zz), (xb, yb - w / 2, zz), (xb, yb + w / 2, zz), (xa, ya + w / 2, zz)]),
                    np.array([(0, 1, 2, 3)])))
        zs = g + 0.008 + 0.001 * k
        for s in (-1, 1):                                                 # 1.0 m shoulders along the approaches
            yi, yo = ya + s * w / 2, ya + s * (w / 2 + su["approach"]["shoulder"])
            v = np.array([(xa, yi, zs), (xb, yi, zs), (xb, yo, zs), (xa, yo, zs)])
            sh.append((v, spl.faces_up(v, [(0, 1, 2, 3)])))
    return {"public_road": ("asphalt", False, c.merge_parts(road)), "approaches": ("road", False, c.merge_parts(app)),
            "outer_shoulders": ("shoulder", False, c.merge_parts(sh))}


# ---------------------------------------------------------------- fields

def build_fields(site=None):
    """Crop fields as flat patches just over the grass, one object per crop."""
    site = site or _site()
    g = c.ground_z() + 0.004
    by = {}
    for f in spec(site)["fields"]:
        x0, y0, x1, y1 = f["rect"]
        v = np.array([(x0, y0, g), (x1, y0, g), (x1, y1, g), (x0, y1, g)])
        by.setdefault((f["crop"], f.get("along", "Y")), []).append((v, np.array([(0, 1, 2, 3)])))
    return {f"field_{k}_{a}": (f"crop_{k}_{a}", False, c.merge_parts(v)) for (k, a), v in by.items()}


# ---------------------------------------------------------------- shelterbelts

def tree_positions(site=None):
    """[(x, y, height, prototype index, yaw)] for every tree of every belt: rows parallel to the belt axis,
    jittered, deterministic (seeded by the belt index)."""
    site = site or _site()
    out = []
    for k, b in enumerate(spec(site)["belts"]):
        rng = np.random.default_rng(1000 + k)
        (xa, ya), (xb, yb) = b["pts"]
        L = math.hypot(xb - xa, yb - ya)
        d = np.array([xb - xa, yb - ya]) / L
        n = np.array([-d[1], d[0]])
        rows = b["rows"]
        for r in range(rows):
            off = (r - (rows - 1) / 2) * b["row_gap"]
            for t in np.arange(b["tree_gap"] / 2, L, b["tree_gap"]):
                if rng.random() < b.get("gaps", 0.0):
                    continue                                              # dead or missing trees
                jt = rng.normal(0, b["tree_gap"] * 0.15)
                jn = rng.normal(0, b["row_gap"] * 0.12)
                p = np.array([xa, ya]) + d * (t + jt) + n * (off + jn)
                h = rng.uniform(*b["h"])
                out.append((float(p[0]), float(p[1]), float(h), int(rng.integers(0, 3)), float(rng.uniform(0, 360))))
    return out


def tree_prototype(kind, seed):
    """Broadleaf tree of unit height: tapered trunk branching low (belt trees keep their lower crowns) and a
    clumped, smoothly lobed canopy. Returns (trunk, canopy) parts."""
    rng = np.random.default_rng(seed)
    trunk_h = 0.22 + 0.04 * kind
    a = np.linspace(0, 2 * math.pi, 7, endpoint=False)
    r0, r1 = 0.026, 0.014
    tv = np.concatenate([np.column_stack([r0 * np.cos(a), r0 * np.sin(a), np.zeros(7)]),
                         np.column_stack([r1 * np.cos(a), r1 * np.sin(a), np.full(7, trunk_h + 0.15)])])
    trunk = (tv, [c.grid_faces(2, 7, wrap_cols=True)])
    blobs = []
    cz, crx, crz = trunk_h + 0.42, 0.26 - 0.03 * kind, 0.30          # crown ellipsoid (unit tree height)
    for i in range(34 + 4 * kind):
        u = rng.normal(size=3)
        u /= np.linalg.norm(u)
        rr = rng.uniform(0.35, 1.0) ** 0.5                               # lumps crowd towards the crown surface
        cen = np.array([u[0] * crx * rr, u[1] * crx * rr, cz + u[2] * crz * rr])
        v, f = _ico(1)
        v = v * rng.uniform(0.05, 0.095)
        blobs.append((v + cen, f))
    return trunk, c.merge_parts(blobs)


def _ico(sub):
    """Icosphere (unit radius) with `sub` subdivisions."""
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
         (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
         (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = [np.array(p, float) / np.linalg.norm(p) for p in v]
    for _ in range(sub):
        cache, nf = {}, []

        def mid(i, j):
            key = (min(i, j), max(i, j))
            if key not in cache:
                m = (v[i] + v[j]) / 2
                v.append(m / np.linalg.norm(m))
                cache[key] = len(v) - 1
            return cache[key]
        for a, b, cc in f:
            ab, bc, ca = mid(a, b), mid(b, cc), mid(cc, a)
            nf += [(a, ab, ca), (b, bc, ab), (cc, ca, bc), (ab, bc, ca)]
        f = nf
    return np.array(v), np.array(f)


def build_trees(site, collection, materials):
    """Three prototypes in a hidden collection, one collection instance per tree, scaled to its height."""
    import bpy
    protos = []
    for k in range(3):
        col = bpy.data.collections.new(f"KIT_TREE_{k}")
        (tv, tf), (cv, cf) = tree_prototype(k, 77 + k)
        c.mesh_from_arrays(f"TREE_{k}_TRUNK", tv, tf, materials["bark"], collection=col)
        c.mesh_from_arrays(f"TREE_{k}_CANOPY", cv, cf, materials["leaves"], smooth=True, collection=col)
        protos.append(col)
    n = 0
    for x, y, h, k, yaw in tree_positions(site):
        ob = bpy.data.objects.new(f"TREE.{n:05d}", None)
        ob.instance_type = "COLLECTION"
        ob.instance_collection = protos[k]
        ob.location = (x, y, c.ground_z())
        ob.rotation_euler = (0, 0, math.radians(yaw))
        ob.scale = (h, h, h)
        collection.objects.link(ob)
        n += 1
    return n


def build(site=None):
    site = site or _site()
    out = {}
    out.update(build_roads(site))
    out.update(build_fields(site))
    return out
