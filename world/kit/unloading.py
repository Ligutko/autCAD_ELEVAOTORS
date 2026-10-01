"""A grain tipper unloads into the receiving pit (HERO_DETAIL_SPEC row 3): where the truck stops, how far its body may
tip under the drawn shed, the grain left in the body, the falling stream, the grain in the pit hoppers.

Site frame. The truck (kit/trucks.py) comes in on the pit drive (SITE receiving.pit.drive, direction -X) and stops
with its tractor's front wheels still on the level drive (STOP_MARGIN inside flat_x). Under the shed (eave 7.1 m, PDF
p.4) the body tips only as far as ROOF_CLEAR below the eave allows: the full 44.5 deg of the Schmitz sheet needs the
front axle ~1.1 m down the west ramp (FINDING, check_unloading). The grain physics is quasi-static and sourced
(research/design/pit_unloading/grain_unloading.md, kit/data/grain_bulk.json):
- the grain starts to leave a tipping body at FLOW_START and has left it at FLOW_END (Opanasyuk 2021, table 3, wheat
  15 / 30 deg, a model body without vibration); in between the volume left falls linearly with the angle (EST);
- inside the tipped body the free surface slopes at min(tip, REPOSE) (lab cone of wheat 27.3 deg, same source fig. 5);
- the stream leaves the body's rear lip and falls freely onto the grating; its thickness carries the flow rate;
- the pit hoppers fill level from the bottom (the conveyor T1 under them is not drained here: 100 t/h is ~2 m3 over the
  minute of tipping; the simulator drains the pit).

    stop_x(site) -> bumper x of the stopped truck;  max_tip(site, x_front) -> deg
    state(site, t) -> {"tip", "body_volume", "pit_volume", "flow", ...} at t seconds after the body starts to rise
    build(site, t) -> ({part: mesh}, info)   the truck (tipped), grain in the body, the stream, grain in the pit
"""

import json
import math
from pathlib import Path

import numpy as np

from . import common as c
from . import trucks as tr

GRAIN = json.loads((Path(__file__).resolve().parent / "data" / "grain_bulk.json").read_text(encoding="utf-8"))

STOP_MARGIN = 0.5          # EST: front tyre this far inside the level drive (not on the ramp)
ROOF_CLEAR = 0.30          # EST: body / tarp bows this far under the shed eave at the top of the tip
FLOW_START, FLOW_END = 15.0, 30.0   # Opanasyuk 2021 table 3, wheat: grain starts / has finished leaving the body
REPOSE = 27.3              # Opanasyuk 2021 fig. 5: wheat cone, no vibration (deg)
TIP_RATE = 0.25            # EST deg/s: the body takes ~2 min to the top (no sheet gives the cylinder speed)
HOLD = 20.0                # EST s at the top before the body comes down
LOWER_RATE = 1.0           # EST deg/s down
LOAD = 0.9                 # judgment: the body is filled to 90 % of its top edge
STREAM_V0 = 1.2            # EST m/s: grain leaves the rear lip at this speed, backwards along the floor
STREAM_SEG = 14
STRANDS = 7                # EST: the sheet breaks into strands with gaps (looks like grain, not a board)
DOOR_OPEN = 35.0           # EST deg: the pendulum combi door swung out by the flow (its bottom clears the stream)


def _site():
    from . import receiving as rc
    return rc._site()


def _pit(site):
    return site["receiving"]["pit"]


FRONT_X = tr.rig(0.0)["dims"]["front_x"]


def to_world(v, x_front, y, z):
    """Rig frame -> site frame for a truck facing -X with its bumper at x_front (a half turn: handedness kept)."""
    v = np.asarray(v, float)
    return np.column_stack([x_front - (v[:, 0] - FRONT_X), y - v[:, 1], z + v[:, 2]])


def lane_y(site):
    from . import site_plan as spl
    return spl.lane(spl.spec(site), "in")["pts"][0][1]


def stop_x(site):
    """Bumper x: the front tyre STOP_MARGIN inside the level drive west of the pit (the truck drives -X)."""
    flat0 = _pit(site)["drive"]["flat_x"][0]
    front_axle = flat0 + STOP_MARGIN + tr.T_TYRE_D / 2
    return front_axle - (FRONT_X - tr.TRACTOR_FRONT_X)              # facing -X: the bumper is west of the axle


_EDGE = None


def _top_edge():
    """Dense top edge of the body with the tarp bows (the highest line when tipped)."""
    global _EDGE
    if _EDGE is None:
        lx = np.linspace(tr.BODY_REAR_X, tr.BODY_FRONT_TOP, 600)
        _EDGE = np.column_stack([lx, np.zeros_like(lx), np.full_like(lx, tr.HA_TR + tr.TARP_UP)])
    return _EDGE


def top_under_shed(site, x_front, deg):
    """Highest point of the tipped body (with the bows) under the shed roof, site z."""
    p = _pit(site)
    b = p["building"]
    v = to_world(tr._tip(_top_edge(), deg), x_front, 0.0, p["deck_z"])
    m = (v[:, 0] > b["x"][0] - 0.3) & (v[:, 0] < b["x"][1] + 0.3)
    return float(v[m, 2].max()) if m.any() else 0.0


def max_tip(site, x_front):
    """Largest tip (deg, <= the sheet's 44.5) that keeps ROOF_CLEAR under the eave."""
    eave = _pit(site)["building"]["eave_z"] - ROOF_CLEAR
    if top_under_shed(site, x_front, tr.TIP_MAX) <= eave:
        return tr.TIP_MAX
    lo, hi = 0.0, tr.TIP_MAX
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if top_under_shed(site, x_front, mid) <= eave else (lo, mid)
    return lo


def full_tip_stop(site):
    """Bumper x at which the full 44.5 deg fits under the shed (searching west, the front axle onto the ramp)."""
    x = stop_x(site)
    while max_tip(site, x) < tr.TIP_MAX - 1e-6:
        x -= 0.05
    return x


# ------------------------------------------------------------------ grain volumes

BODY_W = 2 * (tr.TR_W / 2 - 0.012 - tr.WALL)          # inside the side panels


def _interior():
    """Side profile of the body interior, rig frame (x, z), counter-clockwise."""
    fb = tr.BODY_FRONT_BOTTOM - tr.WALL * 1.1
    ft = tr.BODY_FRONT_TOP - tr.WALL * 1.1
    zt = tr.HA_TR - 0.01
    fz = lambda z: fb + (ft - fb) * (z - tr.BODY_SIDE_Z0) / (tr.HA_TR - tr.BODY_SIDE_Z0)   # noqa: E731
    return np.array([(tr.BODY_REAR_X, tr.FLOOR_Z), (fz(tr.FLOOR_Z), tr.FLOOR_Z), (fz(zt), zt), (tr.BODY_REAR_X, zt)])


def _area(poly):
    x, z = poly[:, 0], poly[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(z, -1)) - np.dot(z, np.roll(x, -1)))


def _clip(poly, slope, z0):
    """Part of a convex polygon under the line z = z0 + tan(slope) * x."""
    t = math.tan(math.radians(slope))
    f = lambda p: z0 + t * p[0] - p[1]                       # noqa: E731  >= 0 below the line
    out = []
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        fa, fb = f(a), f(b)
        if fa >= 0:
            out.append(a)
        if (fa >= 0) != (fb >= 0):
            out.append(a + (b - a) * fa / (fa - fb))
    return np.array(out) if len(out) >= 3 else np.zeros((0, 2))


def _rot(poly, deg):
    v = np.column_stack([poly[:, 0], np.zeros(len(poly)), poly[:, 1]])
    v = tr._tip(v, deg)
    return v[:, [0, 2]]


def body_capacity():
    return _area(_interior()) * BODY_W


def body_grain(deg, volume):
    """Side polygon (rig frame, tipped) of `volume` m3 of grain in the body tipped by deg: the free surface slopes
    at min(deg, REPOSE) rising to the front."""
    poly = _rot(_interior(), deg)
    if volume <= 1e-6:
        return np.zeros((0, 2))
    slope = min(deg, REPOSE)
    t = math.tan(math.radians(slope))
    lo = (poly[:, 1] - t * poly[:, 0]).min()
    hi = (poly[:, 1] - t * poly[:, 0]).max()
    target = volume / BODY_W
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _area(_clip(poly, slope, mid)) < target else (lo, mid)
    return _clip(poly, slope, hi)


def left_fraction(deg):
    """Share of the load still in the body at a tip angle (Opanasyuk start / end angles, linear between: EST)."""
    return float(np.clip((FLOW_END - deg) / (FLOW_END - FLOW_START), 0.0, 1.0))


# ------------------------------------------------------------------ pit hoppers

def hoppers(site):
    """[(top corners 4x2, outlet corners 4x2, z top, z outlet)] of the pit hoppers, as receiving.build_pit_and_shed."""
    from . import receiving as rc
    p = _pit(site)
    r = site["receiving"]
    (x0, x1), (y0, y1) = p["x"], p["y"]
    ys = sorted(oy for _, oy in p["outlets"])
    cuts = [y0] + [(a + b) / 2 for a, b in zip(ys, ys[1:])] + [y1]
    out = []
    for (ox, oy), ya, yb in zip(sorted(p["outlets"], key=lambda o: o[1]), cuts, cuts[1:]):
        zt, zo, h = p["deck_z"] - 0.3, rc.outlet_z(p, oy, r), rc.PIT_OUTLET / 2
        top = np.array([(x0, ya), (x1, ya), (x1, yb), (x0, yb)])
        bot = np.array([(ox - h, oy - h), (ox + h, oy - h), (ox + h, oy + h), (ox - h, oy + h)])
        out.append((top, bot, zt, zo))
    return out


def _section(hp, z):
    top, bot, zt, zo = hp
    f = (z - zo) / (zt - zo)
    return bot + (top - bot) * f


def pit_volume_below(site, z):
    """Grain volume (m3) in all hoppers up to a level z (sections are rectangles: exact by Simpson per hopper)."""
    v = 0.0
    for hp in hoppers(site):
        zo, zt = hp[3], hp[2]
        zz = min(max(z, zo), zt)
        if zz <= zo:
            continue
        a = lambda q: _area(_section(hp, q))              # noqa: E731
        v += (zz - zo) / 6 * (a(zo) + 4 * a((zo + zz) / 2) + a(zz))
    return v


def pit_capacity(site):
    return pit_volume_below(site, max(hp[2] for hp in hoppers(site)))


def pit_level(site, volume):
    """Grain level for a volume in the pit (all hoppers fill alike: the stream falls on their common edge)."""
    hs = hoppers(site)
    lo, hi = min(h[3] for h in hs), max(h[2] for h in hs)
    for _ in range(50):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if pit_volume_below(site, mid) < volume else (lo, mid)
    return hi


# ------------------------------------------------------------------ timeline

def state(site, t, x_front=None, tip_top=None):
    """Quasi-static state t seconds after the body starts to rise (tip_top: force the top angle, for checks)."""
    x_front = stop_x(site) if x_front is None else x_front
    top = max_tip(site, x_front) if tip_top is None else tip_top
    up = top / TIP_RATE
    if t <= up:
        deg = TIP_RATE * t
    elif t <= up + HOLD:
        deg = top
    else:
        deg = max(0.0, top - LOWER_RATE * (t - up - HOLD))
    v0 = LOAD * body_capacity()
    peak = top if t > up else deg                                   # the grain that left does not come back
    left = v0 * left_fraction(peak)
    rate = 0.0
    if t <= up and FLOW_START < deg < FLOW_END:
        rate = v0 * TIP_RATE / (FLOW_END - FLOW_START)              # m3/s while the angle passes the flow band
    return {"t": t, "tip": deg, "tip_top": top, "x_front": x_front, "load_volume": v0, "body_volume": left,
            "pit_volume": v0 - left, "flow": rate}


# ------------------------------------------------------------------ meshes

def _prism(poly, half_w):
    return tr._extrude_y(poly, -half_w, half_w)


def stream(deg, rate, x_front, y, z_deck, z_land):
    """Falling sheet from the rear lip of the tipped body down to z_land: (verts, faces) site frame, or None."""
    if rate <= 0:
        return None
    lip = tr._tip(np.array([[tr.BODY_REAR_X, 0.0, tr.FLOOR_Z]]), deg)[0]
    a = math.radians(deg)
    v = STREAM_V0 * np.array([-math.cos(a), -math.sin(a)])           # down the floor, out of the rear
    w = BODY_W * 0.85
    th = max(rate / (w * 0.7 * STREAM_V0), 0.02)                      # sheet thickness from the flow rate (70 % filled)
    g = 9.80665
    z0 = lip[2] + z_deck
    disc = v[1] ** 2 + 2 * g * (z0 - z_land)
    t_end = (v[1] + math.sqrt(max(disc, 0.0))) / g
    rng = np.random.default_rng(7)
    edges = np.sort(rng.uniform(-0.5, 0.5, 2 * STRANDS)) * w          # strands with gaps, fixed seed: stable frames
    parts = []
    for k0 in range(STRANDS):
        ya, yb = edges[2 * k0], edges[2 * k0 + 1]
        if yb - ya < 0.04:
            continue
        rows = []
        for k in range(STREAM_SEG + 1):
            s_ = t_end * k / STREAM_SEG
            x = lip[0] + v[0] * s_
            z = lip[2] + v[1] * s_ - 0.5 * g * s_ * s_
            pinch = 1.0 - 0.3 * k / STREAM_SEG                        # strands thin as they speed up (EST)
            ym, hw_ = (ya + yb) / 2, (yb - ya) / 2 * pinch
            for yy in (ym - hw_, ym + hw_):
                for dz in (0.0, -th * pinch):
                    rows.append((x, yy, z + dz))
        loc = np.array(rows)
        n = STREAM_SEG + 1
        f = []
        for k in range(n - 1):
            a0, b0 = 4 * k, 4 * (k + 1)
            f += [(a0 + 0, a0 + 2, b0 + 2, b0 + 0), (a0 + 1, b0 + 1, b0 + 3, a0 + 3),
                  (a0 + 0, b0 + 0, b0 + 1, a0 + 1), (a0 + 2, a0 + 3, b0 + 3, b0 + 2)]
        parts.append((to_world(loc, x_front, y, z_deck), np.array(f)))
    return c.merge_parts(parts)


def pit_grain(site, volume):
    """Level grain surface in each hopper (a thin slab), or None when empty."""
    if volume <= 1e-6:
        return None, None
    z = pit_level(site, volume)
    out = []
    for hp in hoppers(site):
        if z <= hp[3]:
            continue
        sec = _section(hp, min(z, hp[2]))
        lo = _section(hp, max(min(z, hp[2]) - 0.04, hp[3]))
        zz = min(z, hp[2])
        v = np.vstack([np.column_stack([sec, np.full(4, zz)]), np.column_stack([lo, np.full(4, zz - 0.04)])])
        out.append((v, np.array([(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)])))
    return c.merge_parts(out), z


def build(site=None, t=None, variant=0, x_front=None, tip_top=None):
    """The unloading at time t (default: mid-flow). Returns ({part: mesh}, info); rig parts keep the rig names."""
    site = site or _site()
    p = _pit(site)
    x_front, y, z = (stop_x(site) if x_front is None else x_front), lane_y(site), p["deck_z"]
    if t is None:
        t = ((FLOW_START + FLOW_END) / 2) / TIP_RATE
    s = state(site, t, x_front, tip_top)
    rig = tr.rig(s["tip"], load=0.0, variant=variant, door_open=DOOR_OPEN if s["flow"] > 0 else None)
    parts = {k: (to_world(v, x_front, y, z), f) for k, (v, f) in rig["parts"].items()}
    gpoly = body_grain(s["tip"], s["body_volume"])
    if len(gpoly):
        v, f = _prism(gpoly, BODY_W / 2 - 0.005)
        parts["grain_body"] = (to_world(v, x_front, y, z), f)
    mesh, level = pit_grain(site, s["pit_volume"])
    if mesh is not None:
        parts["grain_pit"] = mesh
    st_ = stream(s["tip"], s["flow"], x_front, y, z, z)            # it lands on the grating and passes through
    if st_ is not None:
        parts["grain_stream"] = st_
    s.update({"pit_level": level, "y": y, "deck_z": z})
    return parts, s
