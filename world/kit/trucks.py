"""Grain road train for the scenes: a DAF XF FT 4x2 tractor (Sleeper Cab, WB 3800) with a Schmitz Cargobull S.KI 24
SG 9.6 AK tipping grain semitrailer, from the makers' public sheets (research/design/trucks/truck_anatomy.md, data
kit/data/truck_grain.json; Grok T12a, the key numbers re-read in the PDFs 2026-09-30). No badges or logos: the shapes
follow the sheet drawings, the paint is ours.

Frame: x forward, y to the left, z up, metres; origin on the ground under the kingpin (the coupling point).

    rig(tip_deg=0.0, load=0.0, variant=0) -> {"parts": {name: mesh}, "dims": {...}}
        tip_deg  body raised about its rear hinge (0 .. TIP_MAX = 44.5, the Schmitz sheet)
        load     grain fill of the body (0..1), drawn only while the body is down
        variant  paint / detail variant (cab colour, tarp side), so a row of trucks is not one clone

Sourced (sheet): WB 3800, VA 1530, AE 990, AC 830, KA 770, cab 2360 x 2500, CH 3020 over the frame, frame top 0.96 /
0.97 m empty and 0.89 / 0.94 laden, RB 790, side member 260, SB 1820, TB 2480, tyres 315/70R22.5; fuel tank 620 l,
620 mm high, LH; trailer R 6600 kingpin -> middle axle, axles 1310 apart, N 2920, BH 2100, L 9790, 49.7 m3, S 1140,
floor 220 over the kingpin plate, HA 3490, width 2550, tyres 385/65R22.5, wheel centres 2040, landing gear 2380 behind
the kingpin, underrun <= 400 over the road, tip 44.5 deg, combi door with two grain hatches.
Analog: tyre diameters 1014 / 1072 mm (Leao ETS100, GITI GSW226). Judgment (EST): everything the sheets do not
dimension - cab section shape and glass, front track, mirrors, bumper and lamps, tank length, hinge, cylinder.
"""

import json
import math
from pathlib import Path

import numpy as np

from . import common as c
from . import steel as st

DATA = json.loads((Path(__file__).resolve().parent / "data" / "truck_grain.json").read_text(encoding="utf-8"))


def _m(group, key):
    return DATA[group][key]["v"] / 1000.0


WB, VA, AE, AC, KA = (_m("tractor", k) for k in ("колісна_база_WB_мм", "передній_звис_VA_мм", "задній_звис_AE_мм",
                                                 "AC_вісь_до_задньої_стінки_кабіни_мм", "KA_шворінь_від_задньої_осі_мм"))
CAB_W, CH = _m("tractor", "ширина_кабіни_мм"), _m("tractor", "CH_від_рами_до_даху_мм")
HV, HA_T = _m("tractor", "рама_перед_HV_порожня_мм"), _m("tractor", "рама_зад_HA_порожня_мм")
HV_L, HA_L = _m("tractor", "рама_перед_HV_з_вантажем_мм"), _m("tractor", "рама_зад_HA_з_вантажем_мм")
ROOF_Z = _m("tractor", "висота_даху_від_землі_без_дефлектора_мм")
RB, SIDE_H = _m("tractor", "ширина_рами_RB_мм"), _m("tractor", "висота_лонжерона_мм")
SB, TB = _m("tractor", "колія_задня_SB_мм"), _m("tractor", "ширина_ззаду_по_шинах_TB_мм")
TANK_L, TANK_H = DATA["tractor"]["паливний_бак_л"]["v"] / 1000.0, _m("tractor", "паливний_бак_висота_мм")
T_TYRE_D, T_TYRE_W = _m("tractor", "діаметр_колеса_мм"), 0.312          # width: Leao ETS100 sheet (analog, in the md)

R_KP, AX_GAP, N_REAR = _m("trailer", "база_R_мм"), _m("trailer", "відстань_між_осями_мм"), _m("trailer", "задній_звис_N_мм")
BH, S_KP = _m("trailer", "висота_борта_BH_мм"), _m("trailer", "висота_сідельного_S_завантажений_горизонт_мм")
FLOOR_KP = DATA["trailer"]["плита_шворня_до_підлоги_мм"]["v"]["es_8255"] / 1000.0     # the drawing sheet (EN print: 200)
HA_TR, TR_W = _m("trailer", "висота_порожнього_без_тенту_HA_мм"), _m("trailer", "зовнішня_ширина_мм")
TR_TRACK = DATA["trailer"]["колія_на_кресленні_мм"]["v"]["ширший"] / 1000.0
_UNL = DATA["trailer"]["креслення_без_підпису_мм"]["v"]
LEG_X = _UNL["між_E_і_R"] / 1000.0          # read on the drawing: kingpin (SL) -> landing gear leg
UNDERRUN_MAX = _UNL["протипідкатний_макс"] / 1000.0
X_TYRE_D, X_TYRE_W = DATA["trailer"]["діаметр_колеса_мм"]["v"][0] / 1000.0, 0.389    # GITI GSW226 (analog)
TIP_MAX = DATA["trailer"]["кут_підйому_град"]["v"]
HK = _m("trailer", "висота_піднятого_без_тенту_HK_мм")
TARP_UP = _m("trailer", "приріст_висоти_від_штори_мм")      # 110: 3600 with the roller tarp - 3490 without
VOLUME = DATA["trailer"]["обєм_м3"]["v"]
L_IN = _m("trailer", "внутрішня_довжина_L_мм")

# ---- judgment (EST): not dimensioned on the sheets
FRONT_TRACK = 2.05          # EST: front tyre centres (the sheet prints "255" with no unit); tyres inside the cab width
FW_H = 0.19                 # sheet text "150+40 mm" JOST JSK37C over the frame: plate top = 0.95 + 0.19 = 1.14 = S
CAB_Z0 = 1.15               # EST: cab shell bottom behind the arches (steps below it)
ARCH_R = 0.64               # EST: front wheel arch radius
BODY_FRONT_BOTTOM = 0.30    # drawing p.4 (scaled by R): body front wall foot 0.30 m ahead of the kingpin
BODY_FRONT_TOP = 0.69       # the top edge 0.69 m ahead: the wall leans forward
BODY_SIDE_Z0 = 1.25         # drawing: side panel skirt, 0.1 m under the floor
HINGE = (-9.30, 1.28)       # EST: tipping hinge at the rear under the body (x, z)
WALL = 0.04                 # EST: aluminium body wall with its stiffening, drawn solid
MIRROR_OUT = 0.24           # EST: mirror heads out of the cab side (outside the 2.55 m, allowed for mirrors)
CYL_STAGES = 5              # EST: 5-stage front telescopic cylinder (Hyva FE class), Ø 0.21 .. 0.11 m
CAB_COLOURS = ("white", "red", "blue")

TRACTOR_REAR_X = -KA                         # rear (drive) axle
TRACTOR_FRONT_X = TRACTOR_REAR_X + WB        # front axle
BUMPER_X = TRACTOR_FRONT_X + VA
CAB_REAR_X = TRACTOR_FRONT_X - AC
FRAME_END_X = TRACTOR_REAR_X - AE
TRAILER_AXLES = [-(R_KP - AX_GAP), -R_KP, -(R_KP + AX_GAP)]
TRAILER_REAR_X = -(R_KP + N_REAR)
BODY_REAR_X = TRAILER_REAR_X + 0.14          # combi door frame behind the body
FLOOR_Z = S_KP + FLOOR_KP
FRAME_TOP = (HA_T + HA_L) / 2 - 0.005       # rear, between empty 0.97 and laden 0.94: the plate top lands at S 1.14


# ------------------------------------------------------------------ primitives

def _revolve(profile, centre, steps=32):
    """Surface of revolution about the Y axis through `centre`: profile [(r, y_offset)] (closed by caps at both ends)."""
    a = np.linspace(0, 2 * math.pi, steps, endpoint=False)
    rows = []
    for r, dy in profile:
        rows.append(np.column_stack([centre[0] + r * np.cos(a), np.full(steps, centre[1] + dy), centre[2] + r * np.sin(a)]))
    v = np.concatenate(rows)
    f = [c.grid_faces(len(profile), steps, wrap_cols=True)]
    if profile[0][0] > 1e-6:
        f.append(np.arange(steps)[None, :])
    if profile[-1][0] > 1e-6:
        f.append(np.arange((len(profile) - 1) * steps, len(profile) * steps)[::-1][None, :])
    return v, f


def _rrect(x0, x1, y0, y1, r, n=4):
    """Rounded rectangle outline in plan (counter-clockwise)."""
    r = min(r, (x1 - x0) / 2 - 1e-4, (y1 - y0) / 2 - 1e-4)
    pts = []
    for cx, cy, a0 in ((x1 - r, y1 - r, 0.0), (x0 + r, y1 - r, 90.0), (x0 + r, y0 + r, 180.0), (x1 - r, y0 + r, 270.0)):
        for k in range(n + 1):
            a = math.radians(a0 + 90.0 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return np.array(pts)


def _stack(sections):
    """Loft of horizontal outlines [(z, outline Nx2)] (same N), capped: a cab shell built by height."""
    n = len(sections[0][1])
    v = np.concatenate([np.column_stack([o, np.full(n, z)]) for z, o in sections])
    f = [c.grid_faces(len(sections), n, wrap_cols=True)[:, ::-1], np.arange(n)[::-1][None, :],
         np.arange((len(sections) - 1) * n, len(sections) * n)[None, :]]
    return v, f


def _loft_x(stations, n=4):
    """Loft along X of rounded sections [(x, half width, z0, z1, top radius)] (flat bottom), capped."""
    rings = []
    for x, hw, z0, z1, r in stations:
        r = min(r, hw - 1e-3, (z1 - z0) - 1e-3)
        ring = [(-hw, z0), (hw, z0)]
        for cy, a0 in ((hw - r, 0.0), (-hw + r, 90.0)):
            for k in range(n + 1):
                a = math.radians(a0 + 90.0 * k / n)
                ring.append((cy + r * math.cos(a), z1 - r + r * math.sin(a)))
        rings.append(np.array([(x, y, z) for y, z in ring]))
    m = len(rings[0])
    v = np.concatenate(rings)
    f = [c.grid_faces(len(rings), m, wrap_cols=True), np.arange(m)[None, :], np.arange((len(rings) - 1) * m, len(rings) * m)[::-1][None, :]]
    return v, f


def _extrude_y(outline_xz, y0, y1):
    """Prism of a convex XZ outline between y0 and y1."""
    o = np.asarray(outline_xz, float)
    n = len(o)
    v = np.concatenate([np.column_stack([o[:, 0], np.full(n, y0), o[:, 1]]), np.column_stack([o[:, 0], np.full(n, y1), o[:, 1]])])
    f = [c.grid_faces(2, n, wrap_cols=True), np.arange(n)[None, :], np.arange(n, 2 * n)[::-1][None, :]]
    return v, f


def _quad(p0, p1, p2, p3):
    return np.array([p0, p1, p2, p3], float), np.array([(0, 1, 2, 3)])


# ------------------------------------------------------------------ wheels

def _tyre(centre, d, w, rim_d=0.5715, steps=36):
    """Tyre about Y: tread with rounded shoulders, sidewalls down to the 22.5 in rim."""
    ro, ri, hw = d / 2, rim_d / 2 + 0.01, w / 2
    prof = [(ri, -hw * 0.92), (ro - 0.05, -hw), (ro - 0.012, -hw * 0.9), (ro, -hw * 0.7), (ro, hw * 0.7),
            (ro - 0.012, hw * 0.9), (ro - 0.05, hw), (ri, hw * 0.92)]
    return _revolve(prof, centre, steps)


def _rim(centre, outward, rim_d=0.5715, w=0.30, dished=0.06, steps=32):
    """Steel/alu disc wheel seen from `outward` (+1 / -1 along Y): rim flange, dished disc, hub, 10 nuts."""
    ro = rim_d / 2
    s = outward
    out = [_revolve([(ro + 0.012, s * w / 2), (ro, s * w / 2 * 0.95), (ro, -s * w / 2 * 0.95), (ro + 0.012, -s * w / 2)], centre, steps)]
    out.append(_revolve([(ro, s * (w / 2 - 0.03)), (0.19, s * (w / 2 - dished)), (0.11, s * (w / 2 - dished - 0.02)), (0.0, s * (w / 2 - dished - 0.02))], centre, steps))
    out.append(_revolve([(0.075, s * (w / 2 - dished - 0.01)), (0.07, s * (w / 2 - dished + 0.07)), (0.0, s * (w / 2 - dished + 0.08))], centre, 16))
    for k in range(10):                                        # M22 nuts on the 335 mm pitch circle
        a = 2 * math.pi * k / 10
        p = np.array(centre) + (0.1675 * math.cos(a), s * (w / 2 - dished + 0.005), 0.1675 * math.sin(a))
        out.append(st.rod(p, p + (0, s * 0.03, 0), 0.016, 6))
    return c.merge_parts(out)


def _wheel_set(x, z, y_centre, d, w, dual, side):
    """Tyres and rims of one wheel station (single or dual) on one side (side +1 left / -1 right)."""
    tyres, rims = [], []
    offs = (-(w / 2 + 0.02), w / 2 + 0.02) if dual else (0.0,)
    for k, o in enumerate(offs):
        cy = y_centre + o
        tyres.append(_tyre((x, cy, z), d, w))
        if not dual or (k == 1 if side > 0 else k == 0):       # the outer rim of a dual pair shows its face
            rims.append(_rim((x, cy, z), side, w=w * 0.95))
        else:
            rims.append(_revolve([(0.2857, -w / 2 * 0.9), (0.2857, w / 2 * 0.9)], (x, cy, z), 24))
    return tyres, rims


# ------------------------------------------------------------------ tractor

def _cab_front_x(z):
    """Front face of the cab at height z: grille nearly upright, windscreen raked back (DAF XF side view)."""
    pts = [(CAB_Z0, BUMPER_X - 0.06), (1.95, BUMPER_X - 0.09), (3.10, BUMPER_X - 0.40), (3.42, BUMPER_X - 0.62)]
    for (za, xa), (zb, xb) in zip(pts, pts[1:]):
        if z <= zb:
            return xa + (xb - xa) * (z - za) / (zb - za)
    return pts[-1][1]


def tractor(variant=0):
    """DAF XF FT 4x2 Sleeper Cab, WB 3800: cab, chassis, fifth wheel, tank, wheels. Returns {part: mesh}."""
    P = {k: [] for k in ("cab", "glass", "grille", "trim", "lamps", "chassis", "tank", "tyres", "rims", "fifth_wheel")}
    hw = CAB_W / 2
    roof_rear = ROOF_Z                                              # 3.98 = HV + CH: closed hatch, no deflector
    # cab: horizontal outlines stacked up to the roof front edge, then the sleeper roof rising to the rear
    secs = []
    for z, shrink, r in ((CAB_Z0, 0.0, 0.16), (1.95, 0.0, 0.20), (2.6, 0.01, 0.22), (3.10, 0.03, 0.24), (3.42, 0.10, 0.30)):
        secs.append((z, _rrect(CAB_REAR_X, _cab_front_x(z), -hw + shrink, hw - shrink, r)))
    P["cab"].append(_stack(secs))
    xf_roof = _cab_front_x(3.42)
    P["cab"].append(_loft_x([(CAB_REAR_X + 0.02, hw - 0.12, 3.40, roof_rear, 0.35), (CAB_REAR_X + 0.6, hw - 0.12, 3.40, roof_rear - 0.01, 0.35),
                             (xf_roof - 0.35, hw - 0.14, 3.40, 3.62, 0.25), (xf_roof - 0.02, hw - 0.16, 3.40, 3.44, 0.03)]))
    # glass: windscreen on the raked face, door windows, a sleeper window
    zg0, zg1 = 1.98, 3.06
    xa, xb = _cab_front_x(zg0) + 0.008, _cab_front_x(zg1) + 0.008
    P["glass"].append(_quad((xa, -hw + 0.14, zg0), (xa, hw - 0.14, zg0), (xb, hw - 0.16, zg1), (xb, -hw + 0.16, zg1)))
    for s in (-1, 1):
        y = s * (hw + 0.004)
        x_front = lambda z: _cab_front_x(z) - 0.14                   # noqa: E731  A-pillar
        pts = [(CAB_REAR_X + 1.05, 2.02), (x_front(2.02), 2.02), (x_front(2.95), 2.95), (CAB_REAR_X + 1.05, 2.95)]
        if s < 0:
            pts = pts[::-1]
        P["glass"].append((np.array([(px, y, pz) for px, pz in pts]), np.array([(0, 1, 2, 3)])))
        for xs in (CAB_REAR_X + 1.0, _cab_front_x(1.3) - 0.05):      # door seams
            P["trim"].append(c.box((xs - 0.004, y - 0.004, CAB_Z0 + 0.05), (xs + 0.004, y + 0.004, 2.98)))
        P["trim"].append(c.box((CAB_REAR_X + 1.12, y - s * 0.0, 1.62), (CAB_REAR_X + 1.30, y + s * 0.018, 1.66)))   # handle
    # front: grille, lower grille, bumper, lamps
    for z0, z1, inset in ((1.25, 1.90, 0.20), (0.62, 1.02, 0.30)):
        xg = _cab_front_x(1.5) + 0.006 if z0 > 1.1 else BUMPER_X - 0.055
        P["grille"].append(c.box((xg - 0.01, -hw + inset, z0), (xg + 0.006, hw - inset, z1)))
        for k in range(1, 7 if z0 > 1.1 else 4):
            zz = z0 + (z1 - z0) * k / (7 if z0 > 1.1 else 4)
            P["trim"].append(c.box((xg, -hw + inset + 0.03, zz - 0.012), (xg + 0.012, hw - inset - 0.03, zz + 0.012)))
    nose = [(CAB_Z0, _rrect(TRACTOR_FRONT_X + ARCH_R + 0.02, BUMPER_X - 0.06, -hw, hw, 0.16)),
            (0.42, _rrect(TRACTOR_FRONT_X + ARCH_R + 0.02, BUMPER_X - 0.02, -hw + 0.04, hw - 0.04, 0.14))]
    P["cab"].append(_stack(nose[::-1]))
    P["trim"].append(c.box((BUMPER_X - 0.24, -hw + 0.06, 0.34), (BUMPER_X + 0.005, hw - 0.06, 0.58)))           # bumper
    for s in (-1, 1):
        y0, y1 = sorted((s * (hw - 0.10), s * (hw - 0.52)))
        P["lamps"].append(c.box((BUMPER_X - 0.07, y0, 0.66), (BUMPER_X - 0.008, y1, 0.80)))                     # headlamps
        P["lamps"].append(c.box((BUMPER_X - 0.07, y0 + 0.04 * s, 0.84), (BUMPER_X - 0.02, y1 - 0.2 * s, 0.86)))  # DRL strip
    # arches, steps, mirrors
    for s in (-1, 1):
        a = np.linspace(0.0, math.pi, 17)
        ring = [(TRACTOR_FRONT_X + ARCH_R * math.cos(t), T_TYRE_D / 2 + ARCH_R * math.sin(t)) for t in a]
        inner = [(TRACTOR_FRONT_X + (ARCH_R - 0.07) * math.cos(t), T_TYRE_D / 2 + (ARCH_R - 0.07) * math.sin(t)) for t in a[::-1]]
        o = np.array(ring + inner)
        y0, y1 = sorted((s * (hw - 0.30), s * hw))
        n = len(o)
        v = np.concatenate([np.column_stack([o[:, 0], np.full(n, y0), o[:, 1]]), np.column_stack([o[:, 0], np.full(n, y1), o[:, 1]])])
        f = [c.grid_faces(2, n, wrap_cols=True)] + [np.array([(i, i + 1, n - 2 - i, n - 1 - i) for i in range(len(ring) - 1)]),
                                                     np.array([(n + i, n + n - 1 - i, n + n - 2 - i, n + i + 1) for i in range(len(ring) - 1)])]
        P["trim"].append((v, f))
        xs0, xs1 = CAB_REAR_X + 0.02, TRACTOR_FRONT_X - ARCH_R - 0.02
        yo = s * (hw - 0.02)
        P["trim"].append(c.box((xs0, min(yo, s * (hw - 0.34)), 0.40), (xs1, max(yo, s * (hw - 0.34)), CAB_Z0)))       # step box
        for k, zt in enumerate((0.45, 0.80)):                                                                           # treads
            yt = s * (hw - 0.02 - 0.06 * k)
            P["chassis"].append(c.box((xs0 + 0.02, min(yt, yt + s * 0.02), zt), (xs1 - 0.02, max(yt, yt + s * 0.02) + 0.0, zt + 0.03)))
        arm0 = np.array([_cab_front_x(2.9) - 0.12, s * hw, 2.92])
        arm1 = arm0 + (-0.05, s * MIRROR_OUT, 0.06)
        P["trim"].append(st.rod(arm0, arm1, 0.018, 8))
        P["trim"].append(st.rod(arm0 - (0, 0, 0.55), arm1 - (0, 0, 0.55), 0.015, 8))
        mx = arm1[0] - 0.03
        P["trim"].append(c.box((mx - 0.06, min(arm1[1], arm1[1] + s * 0.02), 2.30), (mx + 0.03, max(arm1[1], arm1[1] + s * 0.02) + 0.0, 2.98)))
        P["glass"].append(c.box((mx - 0.07, min(arm1[1] - s * 0.11, arm1[1]), 2.34), (mx - 0.06, max(arm1[1] - s * 0.11, arm1[1]), 2.94)))
    # chassis: two side members, cross members, rear light bar, mudguards, catwalk
    z_top = FRAME_TOP
    for s in (-1, 1):
        y0, y1 = sorted((s * RB / 2, s * (RB / 2 - 0.08)))
        P["chassis"].append(c.box((FRAME_END_X, y0, z_top - SIDE_H), (TRACTOR_FRONT_X + 0.9, y1, z_top)))
    for x in (FRAME_END_X + 0.05, TRACTOR_REAR_X, TRACTOR_REAR_X + 1.3, 1.2, CAB_REAR_X + 0.4):
        P["chassis"].append(c.box((x - 0.05, -RB / 2 + 0.08, z_top - SIDE_H + 0.03), (x + 0.05, RB / 2 - 0.08, z_top - 0.03)))
    P["chassis"].append(c.box((FRAME_END_X, -hw + 0.1, 0.62), (FRAME_END_X + 0.06, hw - 0.1, 0.74)))       # light bar
    for s in (-1, 1):
        y0, y1 = sorted((s * (hw - 0.14), s * (hw - 0.34)))
        P["lamps"].append(c.box((FRAME_END_X - 0.012, y0, 0.63), (FRAME_END_X, y1, 0.73)))
    P["chassis"].append(c.box((CAB_REAR_X - 0.62, -0.45, z_top), (CAB_REAR_X - 0.02, 0.45, z_top + 0.03)))       # catwalk
    rr = T_TYRE_D / 2 + 0.07
    for s in (-1, 1):
        a = np.linspace(math.radians(15), math.radians(165), 13)
        prof = [(TRACTOR_REAR_X + rr * math.cos(t), T_TYRE_D / 2 + rr * math.sin(t)) for t in a]
        y0, y1 = sorted((s * (SB / 2 - T_TYRE_W - 0.06), s * (TB / 2 + 0.02)))
        for (xa, za), (xb, zb) in zip(prof, prof[1:]):
            P["trim"].append(_quad((xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)))
            P["trim"].append(_quad((xa, y1, za), (xb, y1, zb), (xb, y0, zb), (xa, y0, za)))
    # fuel tank LH (620 l, 620 mm high, D section), battery box and AdBlue RH
    tank_len = TANK_L / (TANK_H * 0.70 * 0.92)                      # EST: 0.70 m deep D section, 92 % fill of the box
    xt1 = CAB_REAR_X - 0.08
    P["tank"].append(_loft_x([(xt1 - tank_len, 0.35, 0.0, TANK_H, 0.12), (xt1, 0.35, 0.0, TANK_H, 0.12)]))
    P["tank"][-1] = (P["tank"][-1][0] + (0, RB / 2 + 0.36, z_top - SIDE_H - 0.18), P["tank"][-1][1])
    for xb in (xt1 - tank_len + 0.15, xt1 - 0.15):
        P["chassis"].append(c.box((xb - 0.03, RB / 2, z_top - SIDE_H - 0.20), (xb + 0.03, RB / 2 + 0.72, z_top - SIDE_H - 0.17)))
    P["chassis"].append(c.box((CAB_REAR_X - 0.95, -RB / 2 - 0.55, z_top - SIDE_H - 0.30), (CAB_REAR_X - 0.1, -RB / 2, z_top - SIDE_H + 0.18)))
    P["tank"].append(st.rod((CAB_REAR_X - 1.55, -RB / 2 - 0.25, z_top - SIDE_H - 0.02), (CAB_REAR_X - 1.0, -RB / 2 - 0.25, z_top - SIDE_H - 0.02), 0.2, 20))
    # fifth wheel JOST JSK37C: mounting plate, saddle with the V slot, top at S
    P["fifth_wheel"].append(c.box((-0.30, -RB / 2, z_top), (0.30, RB / 2, z_top + 0.10)))
    saddle = [(0.46, 0.0), (0.40, 0.30), (0.0, 0.43), (-0.40, 0.30), (-0.46, 0.0), (-0.40, -0.30), (0.0, -0.43), (0.40, -0.30)]
    o = np.array(saddle)
    n = len(o)
    zs0, zs1 = z_top + 0.12, z_top + FW_H
    v = np.concatenate([np.column_stack([o, np.full(n, zs0)]), np.column_stack([o, np.full(n, zs1)])])
    P["fifth_wheel"].append((v, [c.grid_faces(2, n, wrap_cols=True)[:, ::-1], np.arange(n)[::-1][None, :], np.arange(n, 2 * n)[None, :]]))
    # wheels: single front, dual rear
    for s in (-1, 1):
        t, r = _wheel_set(TRACTOR_FRONT_X, T_TYRE_D / 2, s * FRONT_TRACK / 2, T_TYRE_D, T_TYRE_W, False, s)
        P["tyres"] += t
        P["rims"] += r
        t, r = _wheel_set(TRACTOR_REAR_X, T_TYRE_D / 2, s * SB / 2, T_TYRE_D, T_TYRE_W, True, s)
        P["tyres"] += t
        P["rims"] += r
    for x in (TRACTOR_FRONT_X, TRACTOR_REAR_X):
        P["chassis"].append(st.rod((x, -SB / 2 + 0.1, T_TYRE_D / 2), (x, SB / 2 - 0.1, T_TYRE_D / 2), 0.07, 12))
    P["chassis"].append(c.box((TRACTOR_REAR_X - 0.25, -0.30, T_TYRE_D / 2 - 0.2), (TRACTOR_REAR_X + 0.25, 0.30, T_TYRE_D / 2 + 0.2)))   # diff
    return {k: c.merge_parts(v) for k, v in P.items() if v}


# ------------------------------------------------------------------ trailer

def _tip(v, deg):
    """Rotate verts about the hinge line (along Y) so the body front rises by deg."""
    if not deg:
        return v
    a = math.radians(deg)
    v = np.asarray(v, float).copy()
    dx, dz = v[:, 0] - HINGE[0], v[:, 2] - HINGE[1]
    v[:, 0] = HINGE[0] + dx * math.cos(a) - dz * math.sin(a)
    v[:, 2] = HINGE[1] + dx * math.sin(a) + dz * math.cos(a)
    return v


def body_corner_top_front(deg):
    """The top front edge point of the body at a tip angle (the highest point when tipped)."""
    return _tip(np.array([[BODY_FRONT_TOP, 0.0, HA_TR]]), deg)[0]


def trailer(tip_deg=0.0, load=0.0, variant=0, door_open=None):
    """Schmitz S.KI 24 SG 9.6 AK: chassis with gooseneck, three axles, the tipping body, cylinder, combi door."""
    P = {k: [] for k in ("body", "body_trim", "tarp", "grain", "cylinder", "frame", "tyres", "rims", "trim", "lamps", "door")}
    hw = TR_W / 2
    top = HA_TR
    # body (tipping): side walls, front wall leaning forward, floor, top rails, rolled tarp, ladder
    side = [(BODY_FRONT_BOTTOM, BODY_SIDE_Z0), (BODY_REAR_X, BODY_SIDE_Z0), (BODY_REAR_X, top), (BODY_FRONT_TOP, top)]
    body = []
    panel = hw - 0.012                                          # the chords stand 12 mm proud of the side panel
    for s in (-1, 1):
        y0, y1 = sorted((s * panel, s * (panel - WALL)))
        body.append(_extrude_y(side, y0, y1))
    fw = [(BODY_FRONT_BOTTOM, BODY_SIDE_Z0), (BODY_FRONT_TOP, top), (BODY_FRONT_TOP - WALL * 1.1, top), (BODY_FRONT_BOTTOM - WALL * 1.1, BODY_SIDE_Z0)]
    body.append(_extrude_y(fw, -hw + WALL, hw - WALL))
    body.append(c.box((BODY_REAR_X, -hw + WALL, BODY_SIDE_Z0), (BODY_FRONT_BOTTOM - WALL, hw - WALL, FLOOR_Z)))      # floor
    trim = []
    for s in (-1, 1):
        y0, y1 = sorted((s * hw, s * (panel - WALL - 0.03)))
        trim.append(st.member((BODY_REAR_X, s * (hw - 0.035), top - 0.05), (BODY_FRONT_TOP, s * (hw - 0.035), top - 0.05),
                              np.array([(-0.035, -0.06), (0.035, -0.06), (0.035, 0.05), (-0.035, 0.05)])))                   # top chord
        trim.append(c.box((BODY_REAR_X, y0, BODY_SIDE_Z0 - 0.02), (BODY_FRONT_BOTTOM, y1, BODY_SIDE_Z0 + 0.10)))      # bottom chord
        for k in range(1, 4):                                   # shallow horizontal swages of the side panel
            z = BODY_SIDE_Z0 + (top - BODY_SIDE_Z0) * k / 4
            yy = s * (panel + 0.004)
            trim.append(c.box((BODY_REAR_X + 0.15, min(yy, yy - s * 0.01), z - 0.012), (BODY_FRONT_TOP - 0.3 - (top - z) * 0.18, max(yy, yy - s * 0.01), z + 0.012)))
    tarp_side = 1 if variant % 2 == 0 else -1                   # the roller tarp rolled up on one side edge
    # roller tarp (the sheet: 3490 without, 3600 with it): bows over the open top, the tarp rolled up on one side
    tarp = [st.rod((BODY_REAR_X + 0.05, tarp_side * (hw - 0.09), top + 0.04), (BODY_FRONT_TOP - 0.05, tarp_side * (hw - 0.09), top + 0.04), 0.06, 14)]
    for k in range(6):
        x = BODY_REAR_X + 0.4 + k * (BODY_FRONT_TOP - BODY_REAR_X - 0.8) / 5
        tarp.append(st.rod((x, -hw + 0.05, top), (x, -hw + 0.05, top + TARP_UP - 0.012), 0.012, 6))
        tarp.append(st.rod((x, hw - 0.05, top), (x, hw - 0.05, top + TARP_UP - 0.012), 0.012, 6))
        tarp.append(st.rod((x, -hw + 0.05, top + TARP_UP - 0.012), (x, hw - 0.05, top + TARP_UP - 0.012), 0.012, 6))
    ladder_x = BODY_FRONT_TOP + 0.04
    for y in (-0.22, 0.22):                                     # front ladder to the top edge
        trim.append(st.rod((BODY_FRONT_BOTTOM + 0.30 * (1.9 - BODY_SIDE_Z0) / (top - BODY_SIDE_Z0) + 0.06, y, 1.9), (ladder_x, y, top - 0.02), 0.016, 8))
    for k in range(6):
        z = 2.05 + k * 0.28
        fx = BODY_FRONT_BOTTOM + (BODY_FRONT_TOP - BODY_FRONT_BOTTOM) * (z - BODY_SIDE_Z0) / (top - BODY_SIDE_Z0) + 0.06
        trim.append(st.rod((fx, -0.22, z), (fx, 0.22, z), 0.013, 6))
    grain = []
    if load > 0 and tip_deg <= 0:
        zg = FLOOR_Z + (top - 0.05 - FLOOR_Z) * min(load, 1.0)
        xg1 = BODY_FRONT_BOTTOM + (BODY_FRONT_TOP - BODY_FRONT_BOTTOM) * (zg - BODY_SIDE_Z0) / (top - BODY_SIDE_Z0) - WALL * 1.2
        gx = np.linspace(BODY_REAR_X + 0.01, xg1, 13)
        gy = np.linspace(-hw + WALL + 0.005, hw - WALL - 0.005, 7)
        mound = 0.12 * load
        vv = np.array([(x, y, zg + mound * (1 - (2 * (y / hw)) ** 2 / 4) * math.sin(math.pi * (x - gx[0]) / (gx[-1] - gx[0]))) for x in gx for y in gy])
        grain.append((vv, c.grid_faces(len(gx), len(gy))[:, ::-1]))
    door = []                                                   # combi door: pendulum frame, two leaves, two grain hatches
    dz0, dz1 = BODY_SIDE_Z0 + 0.02, top - 0.02
    door.append(c.box((-0.10, -hw + 0.01, dz0), (0.0, hw - 0.01, dz1)))
    door.append(c.box((-0.12, -0.02, dz0), (-0.10, 0.02, dz1)))
    for s in (-1, 1):
        y0, y1 = sorted((s * 0.18, s * 0.62))
        door.append(c.box((-0.13, y0, dz0 + 0.12), (-0.10, y1, dz0 + 0.62)))                     # grain hatch
        door.append(c.box((-0.16, min(s * 0.40, s * 0.44), dz0 + 0.62), (-0.10, max(s * 0.40, s * 0.44), dz0 + 0.68)))   # lever
        for zz in (dz0 + 0.3, dz1 - 0.3):
            door.append(c.box((-0.14, min(s * (hw - 0.3), s * (hw - 0.06)), zz - 0.04), (-0.10, max(s * (hw - 0.3), s * (hw - 0.06)), zz + 0.04)))
    # door hangs from the top rear hinge: at a tip it stays plumb (pendulum), swung out of the body end
    hinge_top = np.array([[BODY_REAR_X, 0.0, dz1]])
    ht = _tip(hinge_top, tip_deg)[0]
    th = math.radians(door_open if door_open is not None else (0.0 if tip_deg <= 0 else 4.0))   # grain pushes it out
    ct, sn = math.cos(th), math.sin(th)
    for v, f in door:
        v = np.asarray(v, float).copy()
        dx, dz = v[:, 0].copy(), v[:, 2] - dz1                     # about the top hinge, plumb when shut
        v[:, 0] = ht[0] + dx * ct + dz * sn
        v[:, 2] = ht[2] - dx * sn + dz * ct
        P["door"].append((v, f))
    for key, items in (("body", body), ("body_trim", trim), ("tarp", tarp), ("grain", grain)):
        for v, f in items:
            P[key].append((_tip(v, tip_deg), f))
    # chassis: gooseneck plate, two side members stepping down behind the tractor, cross members, hinge brackets
    z_fr0, z_fr1 = S_KP, BODY_SIDE_Z0 - 0.01
    for s in (-1, 1):
        y0, y1 = sorted((s * 0.45, s * 0.53))
        P["frame"].append(_extrude_y([(1.20, z_fr0), (-2.2, z_fr0), (-2.6, 0.92), (TRAILER_REAR_X, 0.92), (TRAILER_REAR_X, z_fr1),
                                      (1.20, z_fr1)], y0, y1))
    P["frame"].append(c.box((-0.9, -0.53, z_fr0), (1.2, 0.53, z_fr0 + 0.02)))                    # kingpin plate
    P["frame"].append(st.rod((0.0, 0.0, z_fr0), (0.0, 0.0, z_fr0 - 0.08), 0.045, 12))           # 2 in kingpin
    for x in np.arange(-3.0, TRAILER_REAR_X + 0.3, -0.75):
        P["frame"].append(c.box((x - 0.04, -0.45, 1.05), (x + 0.04, 0.45, z_fr1)))
    for s in (-1, 1):
        P["frame"].append(c.box((HINGE[0] - 0.12, s * 0.40 - 0.03, HINGE[1] - 0.12), (HINGE[0] + 0.12, s * 0.40 + 0.03, HINGE[1] + 0.02)))
    P["frame"].append(c.box((0.7, -hw + 0.1, 1.30), (1.35, hw - 0.1, 1.33)))                     # front platform on the frame
    # landing gear 2380 behind the kingpin, raised (coupled)
    for s in (-1, 1):
        P["frame"].append(c.box((-LEG_X - 0.07, s * 0.62 - 0.07, 0.45), (-LEG_X + 0.07, s * 0.62 + 0.07, 1.0)))
        P["frame"].append(c.box((-LEG_X - 0.05, s * 0.62 - 0.05, 0.28), (-LEG_X + 0.05, s * 0.62 + 0.05, 0.45)))
        P["frame"].append(c.box((-LEG_X - 0.15, s * 0.62 - 0.12, 0.25), (-LEG_X + 0.15, s * 0.62 + 0.12, 0.28)))
    P["frame"].append(st.rod((-LEG_X, -0.62, 0.8), (-LEG_X, 0.62, 0.8), 0.025, 8))
    P["trim"].append(c.box((-LEG_X - 0.03, hw - 0.35, 0.72), (-LEG_X + 0.03, hw - 0.12, 0.76)))  # crank
    # tool box, air tanks
    P["trim"].append(c.box((-4.35, -hw + 0.10, 0.62), (-3.25, -hw + 0.62, 1.02)))
    P["frame"].append(st.rod((-3.1, 0.25, 0.80), (-4.4, 0.25, 0.80), 0.13, 16))
    # axles: beams, air bags, trailing arms, wheels 385/65R22.5 singles, mudguards over the group
    zx = X_TYRE_D / 2
    for x in TRAILER_AXLES:
        P["frame"].append(st.rod((x, -TR_TRACK / 2 + 0.2, zx), (x, TR_TRACK / 2 - 0.2, zx), 0.065, 12))
        for s in (-1, 1):
            P["frame"].append(c.box((x + 0.02, s * 0.49 - 0.06, zx - 0.08), (x + 0.75, s * 0.49 + 0.06, zx + 0.04)))   # arm
            P["frame"].append(c.cylinder(0.14, zx + 0.05, 0.91, steps=16, center=(x - 0.25, s * 0.49)))            # air bag
            t, r = _wheel_set(x, zx, s * TR_TRACK / 2, X_TYRE_D, X_TYRE_W, False, s)
            P["tyres"] += t
            P["rims"] += r
    rr = X_TYRE_D / 2 + 0.06
    for s in (-1, 1):
        y0, y1 = sorted((s * (TR_TRACK / 2 - X_TYRE_W / 2 - 0.03), s * (hw - 0.02)))
        prof = []
        for x in TRAILER_AXLES[::-1]:
            prof += [(x + rr * math.cos(t), zx + rr * math.sin(t)) for t in np.linspace(math.radians(20), math.radians(160), 9)]
        for (xa, za), (xb, zb) in zip(prof, prof[1:]):
            P["trim"].append(_quad((xa, y0, za), (xb, y0, zb), (xb, y1, zb), (xa, y1, za)))
            P["trim"].append(_quad((xa, y1, za), (xb, y1, zb), (xb, y0, zb), (xa, y0, za)))
    # rear: underrun bar (bottom <= 400 over the road), lamps, marker lamps
    ux = TRAILER_REAR_X + 0.02
    P["trim"].append(c.box((ux - 0.10, -hw + 0.12, UNDERRUN_MAX - 0.02), (ux, hw - 0.12, UNDERRUN_MAX + 0.12)))
    for s in (-1, 1):
        P["trim"].append(c.box((ux - 0.06, s * 0.8 - 0.04, UNDERRUN_MAX + 0.12), (ux - 0.02, s * 0.8 + 0.04, 0.95)))
        y0, y1 = sorted((s * (hw - 0.14), s * (hw - 0.60)))
        P["lamps"].append(c.box((ux - 0.115, y0, UNDERRUN_MAX + 0.02), (ux - 0.10, y1, UNDERRUN_MAX + 0.11)))
    # front telescopic cylinder: base on the gooseneck, head on the front wall high up
    base = np.array([BODY_FRONT_BOTTOM + 0.55, 0.0, S_KP + 0.10])
    head0 = np.array([[BODY_FRONT_TOP - 0.02 + 0.16, 0.0, top - 0.55]])
    head = _tip(head0, tip_deg)[0]
    L = float(np.linalg.norm(head - base))
    d = (head - base) / L
    seg = max(L / CYL_STAGES, 0.0)
    for k in range(CYL_STAGES):
        r = 0.105 - 0.019 * k
        a0 = base + d * (k * seg * 0.96 if L > 2.2 else k * 0.02)
        a1 = a0 + d * (seg * 1.04 if L > 2.2 else L - k * 0.02)
        P["cylinder"].append(st.rod(a0, a1, r, 20))
    P["cylinder"].append(c.box(tuple(base - (0.12, 0.2, 0.08)), tuple(base + (0.12, 0.2, 0.0))))
    return {k: c.merge_parts(v) for k, v in P.items() if v}


# ------------------------------------------------------------------ the rig

def rig(tip_deg=0.0, load=0.0, variant=0, door_open=None):
    """Tractor + trailer coupled at the kingpin. Parts keep their names; 'cab' carries the variant colour."""
    if not 0.0 <= tip_deg <= TIP_MAX + 1e-9:
        raise ValueError(f"tip {tip_deg} deg outside 0..{TIP_MAX}")
    parts = {f"tractor_{k}": v for k, v in tractor(variant).items()}
    parts.update({f"trailer_{k}": v for k, v in trailer(tip_deg, load, variant, door_open).items()})
    v_all = np.concatenate([np.asarray(v, float) for v, _ in parts.values()])
    dims = {"front_x": float(v_all[:, 0].max()), "rear_x": float(v_all[:, 0].min()), "half_width_no_mirrors": TR_W / 2,
            "width_with_mirrors": float(v_all[:, 1].max() - v_all[:, 1].min()), "height": float(v_all[:, 2].max()),
            "cab_colour": CAB_COLOURS[variant % len(CAB_COLOURS)], "tip_deg": tip_deg,
            "top_front_tipped": body_corner_top_front(tip_deg).tolist()}
    dims["length"] = dims["front_x"] - dims["rear_x"]
    return {"parts": parts, "dims": dims}
