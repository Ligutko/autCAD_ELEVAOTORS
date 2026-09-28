"""Phase W1e. Figures for scale (decision 2026-09-24: people only for scale): grain road trains (a 4x2 tractor with a
tipping grain semitrailer) inside the legal envelope of Directive 96/53/EC (16.50 x 2.55 x 4.00 m, rec_e52d1398), wheels
of the МАЗ-5440 tyre 315/80R22.5 (d 1.076 m, izh-maz.ru manual), shapes by judgment; workers 1.75 m in hi-vis vests.

Site frame. Data: SITE.json `designed.environment.scale`: trucks by lane and x (heading along the lane's run),
people by position.
"""

import math

import numpy as np

from . import common as c
from . import site_plan as spl

LENGTH, WIDTH, HEIGHT = 16.5, 2.55, 4.0          # 96/53/EC Annex I 1.1-1.3 (articulated vehicle)
WHEEL_D = 0.0254 * 22.5 + 2 * 0.80 * 0.315       # 315/80R22.5: 1.076 m
TRACTOR_L, CAB_H = 6.0, 3.85                     # judgment: 4x2 tractor under the 4.0 m limit
TRAILER_L, BODY_H = 13.4, 3.6                    # judgment: grain tipper, top of the sides
PERSON_H = 1.75                                  # judgment: adult worker


def _site():
    from . import receiving as rc
    return rc._site()


def spec(site=None):
    return (site or _site())["designed"]["environment"]["scale"]


def truck_pose(site, t):
    """(front x, y, direction +1 / -1 along x, deck z under the wheels) of a truck standing on a lane at t['x_front']."""
    sp = spl.spec(site)
    ln = spl.lane(sp, t["lane"])
    (xa, ya), (xb, yb) = ln["pts"][0], ln["pts"][-1]
    sgn = 1.0 if xb > xa else -1.0                               # the lane's running direction
    z = c.ground_z() + sp["road_z_over_ground"]
    for key in ("scales_in", "scales_out"):
        if sp[key]["lane"] == t["lane"]:
            x0, x1 = sp[key]["x"]
            xr = sorted((t["x_front"], t["x_front"] - sgn * LENGTH))
            if x0 <= xr[0] and xr[1] <= x1:
                z += 0.35                                        # standing on the scales deck
    return t["x_front"], ya, sgn, z


def truck_box(site, t):
    """Plan box and height of a truck: (x0, y0, x1, y1, z0, z1)."""
    x, y, sgn, z = truck_pose(site, t)
    xs = sorted((x, x - sgn * LENGTH))
    return (xs[0], y - WIDTH / 2, xs[1], y + WIDTH / 2, z, z + HEIGHT)


def build_truck(site, t):
    x, y, sgn, z = truck_pose(site, t)
    parts = {"cab": [], "glass": [], "trailer": [], "tarp": [], "wheels": [], "chassis": []}
    L = lambda a, b: sorted((x - sgn * a, x - sgn * b))
    hw = WIDTH / 2
    r = WHEEL_D / 2
    # tractor: cab over the front axle with a raked windscreen and a roof fairing, bumper, chassis
    X = lambda a: x - sgn * a                                    # distance back from the front bumper
    zs = [z + 1.1, z + 2.35, z + 3.35, z + CAB_H]
    prof = [(0.05, zs[0]), (0.0, zs[1]), (0.25, zs[2]), (0.55, zs[2] + 0.05), (1.3, zs[3]), (2.3, zs[3]), (2.3, zs[0])]
    n = len(prof)
    v = np.array([(X(a), y + s * hw, zz) for s in (-1, 1) for a, zz in prof])
    f = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))] + [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    parts["cab"].append((v, [np.array([q]) for q in f]))
    wv = np.array([(X(0.02), y + s * (hw - 0.12), zz) for s, zz in ((-1, zs[1] + 0.1), (1, zs[1] + 0.1), (1, zs[2] - 0.08), (-1, zs[2] - 0.08))])
    wv[2:, 0] = X(0.23)
    parts["glass"].append((wv, np.array([(0, 1, 2, 3)])))        # windscreen on the raked face
    for s in (-1, 1):                                            # side windows
        xa, xb = L(0.35, 1.2)
        parts["glass"].append(c.box((xa, y + s * hw - 0.01, zs[1] + 0.15), (xb, y + s * hw + 0.01, zs[2] - 0.1)))
    xa, xb = L(-0.1, 0.2)
    parts["chassis"].append(c.box((xa, y - hw + 0.05, z + 0.45), (xb, y + hw - 0.05, z + 1.05)))   # bumper
    xa, xb = L(0.0, TRACTOR_L)
    parts["chassis"].append(c.box((xa, y - 0.5, z + 0.8), (xb, y + 0.5, z + 1.2)))
    # trailer: kingpin over the tractor's rear axle, tipping body with ribs
    t0 = TRACTOR_L - 1.6
    xa, xb = L(t0, t0 + TRAILER_L)
    parts["chassis"].append(c.box((xa, y - 1.0, z + 1.1), (xb, y + 1.0, z + 1.4)))
    parts["trailer"].append(c.box((xa, y - hw, z + 1.4), (xb, y + hw, z + BODY_H)))
    for k in range(9):
        xr = t0 + 0.4 + k * (TRAILER_L - 0.8) / 8
        xa2, xb2 = L(xr, xr + 0.08)
        for s in (-1, 1):
            parts["chassis"].append(c.box((xa2, y + s * hw - (0.03 if s > 0 else 0), z + 1.4), (xb2, y + s * hw + (0.03 if s < 0 else 0), z + BODY_H)))
    xa, xb = L(t0 + 0.1, t0 + TRAILER_L - 0.1)
    parts["tarp"].append(c.box((xa, y - hw + 0.05, z + BODY_H), (xb, y + hw - 0.05, z + BODY_H + 0.05)))
    # wheels: tractor front + drive, trailer triple axle
    axles = [1.4, TRACTOR_L - 1.9] + [t0 + TRAILER_L - k for k in (1.3, 2.61, 3.92)]
    for ax in axles:
        xc = x - sgn * ax
        for s in (-1, 1):
            yc = y + s * (hw - 0.3)
            v, f = c.cylinder(r, -0.15, 0.15, steps=20)
            v = v[:, [0, 2, 1]]                                     # axis along y
            v = v + np.array([xc, yc, z + r])
            parts["wheels"].append((v, f))
    return {k: c.merge_parts(v) for k, v in parts.items() if v}


def build_person(p):
    """Worker: legs, torso in a hi-vis vest, head with a helmet."""
    x, y, _ = p
    g = c.ground_z()
    h = PERSON_H
    body = {"legs": [c.box((x - 0.17, y - 0.1, g), (x + 0.17, y + 0.1, g + 0.47 * h))],
            "vest": [c.box((x - 0.21, y - 0.13, g + 0.47 * h), (x + 0.21, y + 0.13, g + 0.8 * h))],
            "skin": [c.cylinder(0.1, g + 0.83 * h, g + 0.93 * h, steps=12, center=(x, y))],
            "helmet": [c.cylinder(0.13, g + 0.93 * h, g + h, steps=12, center=(x, y))]}
    return {k: c.merge_parts(v) for k, v in body.items()}


def build(site=None):
    site = site or _site()
    sc = spec(site)
    parts = {}
    for t in sc["trucks"]:
        for k, v in build_truck(site, t).items():
            parts.setdefault(f"truck_{k}", []).append(v)
    for p in sc["people"]:
        for k, v in build_person(p).items():
            parts.setdefault(f"person_{k}", []).append(v)
    mat = {"truck_cab": "truck_cab", "truck_glass": "dark", "truck_trailer": "galv_old", "truck_tarp": "tarp", "truck_wheels": "rubber",
           "truck_chassis": "dark", "person_legs": "dark", "person_vest": "hivis", "person_skin": "skin", "person_helmet": "hivis"}
    return {k: (mat[k], False, c.merge_parts(v)) for k, v in parts.items()}
