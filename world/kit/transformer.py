"""Oil-filled hermetic power transformer TMG-630/10/0.4 (МЭТЗ ім. Козлова), corrugated tank, no conservator (C7b).

Dimensions are the catalogue ones, research/design/ktp/NOTES.md:
  mitek_tmg_characteristics.pdf PDF page 4 (printed 9), figure and table «ТМГ мощностью 630 кВ·А», mm:
    L 1590, B 1000, H 1415, H1 1085, A 820, A1 820, A2 230, A3 135, A4 135, b 170, b1 170, the figure's 94 (floor to tank bottom);
  PDF page 2 (printed 7), table ТМГ-630/10-У1: no-load 1100 W, short-circuit 7900 W, uk 5.5 %, oil 394 kg, total 1690 kg.
Everything the catalogue does not letter is EST (fin depth and pitch, bushing sheds, roller size, lugs, gauges), marked below.

Local frame, metres: origin on the floor (roller contact plane) in the middle of the plan, X along the length L, Y across the
width B (the HV row of three bushings at +Y, the LV row of four at -Y), Z up. Rollers at (±A/2, ±A1/2).

    oil_transformer(kva=630, faults=None) -> {"parts": {name: (verts, faces)}, "dims": {...}}
"""

import math

import numpy as np

from . import common as c
from . import steel as st

CAT = {630: {"L": 1.590, "B": 1.000, "H": 1.415, "H1": 1.085, "A": 0.820, "A1": 0.820, "A2": 0.230, "A3": 0.135, "A4": 0.135,
             "b": 0.170, "b1": 0.170, "under": 0.094, "mass_kg": 1690.0, "oil_kg": 394.0, "p0_w": 1100.0, "pk_w": 7900.0, "uk_pct": 5.5}}
SRC = "МЭТЗ ТМГ, каталог (mitek.spb.ru/files/tmg_1351065965.pdf) стор. PDF 4 (друк. 9) і PDF 2 (друк. 7)"

FIN_PITCH = 0.050          # EST: corrugation pitch (the figure shows ~22 folds over 1.2 m)
FIN_T = 0.003              # EST: corrugated sheet 1.0-1.5 mm, drawn thicker so it reads at 5 m
FIN_Z = (0.130, 1.040)     # EST: corrugated height, between the base frame and the cover
CORE_X, CORE_Y = 0.600, 0.300   # EST: tank core half-sizes the fins stand on (fins reach L / 2 and B / 2)
COVER_T = 0.015
WHEEL_R = 0.045            # EST: transport roller Ø90 (the catalogue draws 94 mm under the tank)
WHEEL_W = 0.040
GAP = 0.0005


def _members(path, z0, z1, t):
    """Thin vertical panels along a polyline in plan (x, y), thickness t, from z0 to z1."""
    prof = np.array([(-t / 2, z0), (t / 2, z0), (t / 2, z1), (-t / 2, z1)])
    return [st.member((a[0], a[1], 0.0), (b[0], b[1], 0.0), prof) for a, b in zip(path, path[1:])]


def _accordion(a0, a1, root, tip, pitch, along_x):
    """Zig-zag fold line between `root` and `tip` from a0 to a1; along_x False: the line runs along Y, folds across X."""
    n = max(2, int(round((a1 - a0) / (pitch / 2.0))))
    pts = []
    for k in range(n + 1):
        s = a0 + (a1 - a0) * k / n
        r = tip if k % 2 else root
        pts.append((s, r) if along_x else (r, s))
    return pts


def _stack(x, y, z0, radii, heights):
    """Revolved porcelain-like stack: cylinders of the given radii and heights from z0 up."""
    parts, z = [], z0
    for r, h in zip(radii, heights):
        parts.append(c.cylinder(r, z, z + h, steps=20, center=(x, y)))
        z += h
    return parts, z


def oil_transformer(kva=630, faults=None):
    if kva not in CAT:
        raise ValueError("only 630 kVA is tabulated")
    f = faults or {}
    d = CAT[kva]
    L, B, H1, A, A1 = d["L"], d["B"], d["H1"], d["A"], d["A1"]
    zb = d["under"]                       # tank bottom over the floor (catalogue figure: 94)
    ztop = H1 - COVER_T                   # tank wall top; the cover plate sits on it up to H1
    parts = {}

    # ---------------- tank core, cover, base frame
    parts["tank"] = c.box((-CORE_X, -CORE_Y, zb), (CORE_X, CORE_Y, ztop))
    parts["cover"] = c.box((-CORE_X - 0.06, -CORE_Y - 0.04, ztop), (CORE_X + 0.06, CORE_Y + 0.04, H1))
    base = [c.box((-CORE_X - 0.02, sy * (CORE_Y + 0.02) - 0.03, zb - 0.04), (CORE_X + 0.02, sy * (CORE_Y + 0.02) + 0.03, zb)) for sy in (-1, 1)]
    parts["base"] = c.merge_parts(base)

    # ---------------- corrugated fins: long sides (±Y) and ends (±X)
    fins = []
    for sy in (-1, 1):
        pts = _accordion(-CORE_X + 0.02, CORE_X - 0.02, sy * CORE_Y, sy * (B / 2 - 0.010), FIN_PITCH, True)
        fins += _members(pts, *FIN_Z, FIN_T)
    for sx in (-1, 1):
        pts = _accordion(-CORE_Y + 0.02, CORE_Y - 0.02, sx * CORE_X, sx * (L / 2 - 0.010), FIN_PITCH, False)
        fins += _members(pts, *FIN_Z, FIN_T)
    parts["fins"] = c.merge_parts(fins)

    # ---------------- bushings: HV (10 kV) at +b, LV (0.4 kV) at -b1
    a2 = float(f.get("a2", d["A2"]))                             # broken variant: HV phases closer together
    hv_x = (-a2, 0.0, a2)
    hv_y = d["b"]
    hv_h = float(f.get("hv_h", 0.0))                          # broken variant: HV porcelain taller
    hv_porc, hv_metal, hv_top = [], [], []
    for x in hv_x:
        base_f = c.cylinder(0.065, H1, H1 + 0.018, steps=24, center=(x, hv_y))
        stack, z = _stack(x, hv_y, H1 + 0.018, [0.036, 0.062, 0.036, 0.062, 0.036, 0.062, 0.036],
                          [0.060, 0.012, 0.035, 0.012, 0.035, 0.012, 0.030 + hv_h])             # EST: three sheds on a 10 kV post
        cap = c.cylinder(0.030, z, z + 0.022, steps=16, center=(x, hv_y))
        stud = c.cylinder(0.011, z + 0.022, z + 0.062, steps=12, center=(x, hv_y))
        hv_metal += [base_f, cap, stud]
        hv_porc += stack
        hv_top.append((x, hv_y, z + 0.062))
    parts["hv_porcelain"] = c.merge_parts(hv_porc)
    lv_x = tuple(-d["A3"] + k * d["A3"] for k in range(4))   # c, b, a, o: A3, A3, A4 pitch (A4 = A3 = 135)
    lv_y = -d["b1"]
    lv_porc, lv_top = [], []
    for x in lv_x:
        base_f = c.cylinder(0.045, H1, H1 + 0.015, steps=20, center=(x, lv_y))
        stack, z = _stack(x, lv_y, H1 + 0.015, [0.028, 0.044, 0.028], [0.050, 0.010, 0.030])   # EST
        stud = c.cylinder(0.0135, z, z + 0.075, steps=12, center=(x, lv_y))                       # M27 stud (TMG21 table A.3, d = M27)
        nut = st.rod((x, lv_y, z + 0.030), (x, lv_y, z + 0.052), 0.0245, 6)
        hv_metal += [base_f, stud, nut]
        lv_porc += stack
        lv_top.append((x, lv_y, z + 0.075))
    parts["lv_porcelain"] = c.merge_parts(lv_porc)

    # ---------------- cover fittings (positions read from the catalogue plan, EST sizes)
    tap = [c.cylinder(0.035, H1, H1 + 0.045, steps=20, center=(0.040, 0.0)),
           st.member((0.040, 0.0, H1 + 0.045), (0.040, 0.0, H1 + 0.070), st.flat(0.022, 0.022)),
           st.member((0.0, 0.0, H1 + 0.088), (0.080, 0.0, H1 + 0.088), st.flat(0.018, 0.016))]      # tap-changer knob with a lever
    gauge = [c.cylinder(0.030, H1, H1 + 0.060, steps=16, center=(-0.62, 0.0)), c.cylinder(0.022, H1 + 0.060, H1 + 0.066, steps=16, center=(-0.62, 0.0))]
    filler = [c.cylinder(0.040, H1, H1 + 0.090, steps=20, center=(-0.46, 0.0)), c.cylinder(0.050, H1 + 0.090, H1 + 0.108, steps=20, center=(-0.46, 0.0))]
    valve = [c.cylinder(0.026, H1, H1 + 0.050, steps=16, center=(0.38, 0.0)), c.cylinder(0.034, H1 + 0.050, H1 + 0.062, steps=16, center=(0.38, 0.0))]
    # dial thermometer on the cover over the thermometer pocket: a pocket, a bracket and a round dial
    pocket = [c.cylinder(0.011, H1, H1 + 0.075, steps=12, center=(-0.58, 0.115))]
    dial = [st.rod((-0.58, 0.115, H1 + 0.075), (-0.58, 0.115, H1 + 0.140), 0.008, 8),
            st.rod((-0.58, 0.115 - 0.030, H1 + 0.175), (-0.58, 0.115 + 0.010, H1 + 0.175), 0.050, 24)]
    parts["tap"] = c.merge_parts(tap)
    parts["gauge"] = c.merge_parts(gauge + filler + valve)
    parts["thermo"] = c.merge_parts(pocket + dial)
    lugs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lugs.append(c.box((sx * (CORE_X + 0.03) - 0.025, sy * (CORE_Y + 0.025) - 0.006, H1), (sx * (CORE_X + 0.03) + 0.025, sy * (CORE_Y + 0.025) + 0.006, H1 + 0.045)))
    parts["lugs"] = c.merge_parts(lugs)
    parts["bushing_metal"] = c.merge_parts(hv_metal)

    # ---------------- nameplate on the LV-side fin tips, drain plug, earthing clamp
    parts["nameplate"] = c.merge_parts([c.box((-0.11, -B / 2 + 0.0005, 0.62), (0.11, -B / 2 + 0.0035, 0.74)),
                                        c.box((-0.11, -B / 2 + 0.0035, 0.64), (-0.09, -B / 2 + 0.010, 0.72)),
                                        c.box((0.09, -B / 2 + 0.0035, 0.64), (0.11, -B / 2 + 0.010, 0.72))])      # on two spacers off the fin tips
    drain = [st.rod((CORE_X, CORE_Y - 0.04, zb + 0.05), (CORE_X + 0.032, CORE_Y - 0.04, zb + 0.05), 0.012, 8)]
    # earthing lug on the base beam end (outside the end fins, which stop at |y| = 0.28), a bolt leads out of it
    earth_pt = (-CORE_X - 0.115, 0.32, zb - 0.020)
    earth = [c.box((-CORE_X - 0.095, 0.29, zb - 0.035), (-CORE_X - 0.02, 0.35, zb - 0.005)),
             st.rod((-CORE_X - 0.095, 0.32, zb - 0.020), earth_pt, 0.006, 8)]
    parts["earth"] = c.merge_parts(drain + earth)

    # ---------------- four transport rollers, swivel brackets; wheel bottom on the floor
    rollers = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * A / 2, sy * A1 / 2
            rollers.append(st.rod((cx, cy - WHEEL_W / 2, WHEEL_R), (cx, cy + WHEEL_W / 2, WHEEL_R), WHEEL_R, 20))
            for yy in (cy - WHEEL_W / 2 - 0.012, cy + WHEEL_W / 2 + 0.004):
                rollers.append(c.box((cx - 0.030, yy, WHEEL_R * 0.55), (cx + 0.030, yy + 0.008, zb)))
            rollers.append(c.box((cx - 0.030, cy - WHEEL_W / 2 - 0.012, zb - 0.01), (cx + 0.030, cy + WHEEL_W / 2 + 0.012, zb)))
    parts["rollers"] = c.merge_parts(rollers)

    allv = np.concatenate([np.asarray(v, float).reshape(-1, 3) for v, _ in parts.values()])
    dims = {"kva": kva, "L": float(allv[:, 0].max() - allv[:, 0].min()), "B": float(allv[:, 1].max() - allv[:, 1].min()),
            "H": float(allv[:, 2].max()), "H1": H1, "cat": dict(d), "src": SRC,
            "bbox": {"min": allv.min(0).tolist(), "max": allv.max(0).tolist()},
            "hv": [list(map(float, p)) for p in hv_top], "lv": [list(map(float, p)) for p in lv_top],
            "rollers": [(sx * A / 2, sy * A1 / 2) for sx in (-1, 1) for sy in (-1, 1)], "wheel_r": WHEEL_R,
            "floor_z": float(allv[:, 2].min()), "mass_kg": d["mass_kg"], "oil_kg": d["oil_kg"], "loss_w": d["p0_w"] + d["pk_w"],
            "lv_row_y": lv_y, "hv_row_y": hv_y, "fins": len(fins), "earth_pt": earth_pt,
            "est": ["шаг і глибина гофрів 50 мм / до габариту B, L", "порцелянові юбки вводів ВН і НН", "ролики Ø90 мм", "вушка, маслоуказатель, клапан, терморозетка"]}
    return {"parts": parts, "dims": dims}


MATERIALS = {"tank": "trafo", "cover": "trafo", "base": "trafo", "fins": "trafo", "lugs": "trafo", "hv_porcelain": "porcelain",
             "lv_porcelain": "porcelain", "bushing_metal": "galv", "tap": "dark", "gauge": "dark", "thermo": "dark",
             "nameplate": "white", "earth": "galv", "rollers": "dark"}
