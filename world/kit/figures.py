"""Phase W1e. Figures for scale (decision 2026-09-24): grain road trains and workers.

Trucks (2026-09-30): the DAF XF FT 4x2 + Schmitz S.KI 24 SG 9.6 AK rig of kit/trucks.py, built to the makers'
sheets (research/design/trucks/truck_anatomy.md); each truck on the list gets its own paint variant and load.
Workers: the Rocketbox avatars of kit/people.py replace the box workers below when the assets are present.

Site frame. Data: SITE.json `designed.environment.scale`: trucks by lane and x (heading along the lane's run),
people by position.
"""

import math

import numpy as np

from . import common as c
from . import site_plan as spl
from . import trucks as tr

LIMIT_LENGTH, LIMIT_WIDTH, LIMIT_HEIGHT = 16.5, 2.55, 4.0    # 96/53/EC Annex I 1.1-1.3 (articulated vehicle)
_RIG = tr.rig(0.0)["dims"]
LENGTH, HEIGHT = _RIG["length"], _RIG["height"]             # the real rig: 14.18 x 3.98 m
WIDTH = 2 * _RIG["half_width_no_mirrors"]
FRONT_X = _RIG["front_x"]                                   # rig frame: the kingpin at 0, the bumper at +4.57
BODY_MID_BACK = FRONT_X - (tr.BODY_REAR_X + tr.BODY_FRONT_TOP) / 2    # bumper -> middle of the body, along the run
LOAD = {"in": 0.9, "out": 0.6}                              # judgment: loaded in, half-loaded while filling under Ш1
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


def build_truck(site, t, tip_deg=0.0, variant=0):
    """{rig part: mesh} of one truck in the site frame: the rig's bumper at t['x_front'], facing the lane's run."""
    x, y, sgn, z = truck_pose(site, t)
    r = tr.rig(tip_deg, load=t.get("load", LOAD.get(t["lane"], 0.0)), variant=variant)
    out = {}
    for k, (v, f) in r["parts"].items():
        v = np.asarray(v, float)
        w = np.column_stack([x + sgn * (v[:, 0] - FRONT_X), y + sgn * v[:, 1], z + v[:, 2]])
        out[k] = (w, f)                                          # a half turn (sgn -1) keeps the handedness
    return out


def part_material(part, variant):
    """Site material key of a rig part (the cab paint by variant)."""
    if part == "tractor_cab":
        return "truck_cab_" + tr.CAB_COLOURS[variant % len(tr.CAB_COLOURS)]
    return "truck_" + part.split("_", 1)[1]


SMOOTH = {"tractor_tyres", "trailer_tyres", "tractor_rims", "trailer_rims", "tractor_tank", "trailer_cylinder", "trailer_tarp"}


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
    for i, t in enumerate(sc["trucks"]):
        for k, v in build_truck(site, t, variant=i).items():
            parts.setdefault((part_material(k, i), k in SMOOTH), []).append(v)
    for p in sc["people"]:
        for k, v in build_person(p).items():
            parts.setdefault(f"person_{k}", []).append(v)
    mat = {"person_legs": "dark", "person_vest": "hivis", "person_skin": "skin", "person_helmet": "hivis"}
    out = {}
    for key, v in parts.items():
        if isinstance(key, tuple):
            m, smooth = key
            out[m] = (m, "quads" if smooth else False, c.merge_parts(v))
        else:
            out[key] = (mat[key], False, c.merge_parts(v))
    return out


def truck_materials(c_):
    """Materials for the rig parts (site.py adds them to its material dict)."""
    m = {f"truck_cab_{name}": c_.mat_painted(f"SITE_TRUCK_CAB_{name.upper()}", col, 0.3, grime=0.15)
         for name, col in zip(tr.CAB_COLOURS, ((0.82, 0.83, 0.84), (0.55, 0.03, 0.02), (0.04, 0.12, 0.35)))}
    m.update({"truck_glass": c_.mat_painted("SITE_TRUCK_GLASS", (0.02, 0.03, 0.04), 0.05, grime=0.0),
              "truck_grille": c_.mat_painted("SITE_TRUCK_GRILLE", (0.03, 0.03, 0.03), 0.4, grime=0.05),
              "truck_trim": c_.mat_painted("SITE_TRUCK_TRIM", (0.08, 0.08, 0.09), 0.5, grime=0.2),
              "truck_lamps": c_.mat_painted("SITE_TRUCK_LAMPS", (0.9, 0.9, 0.85), 0.1, grime=0.0),
              "truck_chassis": c_.mat_painted("SITE_TRUCK_CHASSIS", (0.04, 0.04, 0.04), 0.5, grime=0.4),
              "truck_tank": c_.mat_galvanized("SITE_TRUCK_ALU", age=0.2),
              "truck_tyres": c_.mat_rubber("SITE_TRUCK_TYRES"),
              "truck_rims": c_.mat_painted("SITE_TRUCK_RIMS", (0.62, 0.63, 0.65), 0.35, grime=0.3),
              "truck_fifth_wheel": c_.mat_painted("SITE_TRUCK_FW", (0.05, 0.05, 0.05), 0.6, grime=0.4),
              "truck_body": c_.mat_galvanized("SITE_TRUCK_BODY", age=0.35),
              "truck_body_trim": c_.mat_galvanized("SITE_TRUCK_BODY_TRIM", age=0.55),
              "truck_door": c_.mat_galvanized("SITE_TRUCK_DOOR", age=0.45),
              "truck_tarp": c_.mat_painted("SITE_TRUCK_TARP", (0.10, 0.12, 0.12), 0.8, grime=0.3),
              "truck_grain": c_.mat_painted("SITE_TRUCK_GRAIN", (0.62, 0.46, 0.22), 0.85, grime=0.1),
              "truck_cylinder": c_.mat_painted("SITE_TRUCK_CYL", (0.80, 0.80, 0.82), 0.15, grime=0.05),
              "truck_frame": c_.mat_painted("SITE_TRUCK_FRAME", (0.12, 0.12, 0.13), 0.5, grime=0.35)})
    return m
