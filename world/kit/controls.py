"""Hands of the plant: what a person touches next to a motor or in the switch room (HERO_DETAIL_SPEC section 2).

Data: world/kit/data/control_posts.json (Grok T8a, vendor sheets in research/design/control_posts/sources/):
- ex_estop_post  R.STAHL 8150 emergency-stop station for dust zone 22 (stainless, one red mushroom, one gland):
                 the only station allowed next to a noria or a conveyor drive in the dust zone;
- pull_cord      Schmersal ZQ 900 rope-pull switch with the red Ø5 rope along a conveyor;
- cabinet        Rittal VX25 800 x 2000 x 600 RAL 7035 (MCC / PLC row in the switch room), optional HMI and lamps;
- signal_column  Schneider XVU Ø60 stack light (not Ex: switch room / outside the dust zone only).

Local frames: floor at z = 0, the part faces -Y (the side a person stands on), X along the face. Metres.
Every function returns {"parts": {name: (verts, faces)}, "dims": {...}}; dims["est"] lists what is estimated.
"""

import json
import math
from pathlib import Path

import numpy as np

from . import common as c
from . import steel as st

DATA = Path(__file__).resolve().parent / "data" / "control_posts.json"

POST_CENTRE_Z = 1.2        # EST: box centre over the floor, inside the 0.6-1.7 m reach band (EN 620 per a secondary
                           # source, analog) and over the EN 60204-1 minimum of 0.6 m
POST_PIPE_R = 0.024        # EST: DN40 stand pipe
MUSHROOM_D = 0.040         # analog: Schneider XB5AS8442 head Ø40 (the STAHL sheet gives no size)
MUSHROOM_H = 0.043         # same sheet
ROPE_Z = 1.0               # EST: rope height over the walkway (EN 620 page not read: NOT_FOUND in the data)
ROPE_R = 0.0025            # data: rope sheath Ø5
ROPE_SUPPORT_MAX = 3.0     # data: supports not farther than 3 m on runs over 10 m
ROPE_MAX = 75.0            # data: at most 75 m per switch
PLINTH = 0.1               # EST: cabinet plinth


def _data():
    return json.loads(DATA.read_text(encoding="utf-8"))


def _mm(*path):
    node = _data()
    for k in path:
        node = node[k]
    return float(node["v"]) / 1000.0


def _mushroom(x, y, z, d=MUSHROOM_D, h=MUSHROOM_H):
    """Red mushroom head on a collar, pointing -Y from a face at y."""
    return c.merge_parts([st.rod((x, y, z), (x, y - h * 0.45, z), 0.0145, 20),
                          st.rod((x, y - h * 0.45, z), (x, y - h, z), d / 2, 28)])


def ex_estop_post(side=-1):
    """R.STAHL 8150 E-stop station on a DN40 stand pipe with a base plate. side: -1 faces -Y, +1 faces +Y."""
    w, h, dp = _mm("зона_22_пост", "ширина_мм"), _mm("зона_22_пост", "висота_мм"), _mm("зона_22_пост", "глибина_мм")
    zc = POST_CENTRE_Z
    parts = {}
    parts["box"] = c.merge_parts([c.box((-w / 2, -dp / 2, zc - h / 2), (w / 2, dp / 2, zc + h / 2)),
                                  c.box((-w / 2 + 0.006, -dp / 2 - 0.004, zc - h / 2 + 0.006), (w / 2 - 0.006, -dp / 2, zc + h / 2 - 0.006))])
    parts["mushroom"] = _mushroom(0.0, -dp / 2 - 0.004, zc + 0.02)
    parts["gland"] = c.merge_parts([st.rod((0.0, 0.0, zc - h / 2), (0.0, 0.0, zc - h / 2 - 0.03), 0.017, 6),        # M25 gland, hex
                                    st.rod((0.0, 0.0, zc - h / 2 - 0.03), (0.0, 0.0, zc - h / 2 - 0.25), 0.007, 10)])  # cable down
    screws = [c.cylinder(0.005, 0.0, 0.003, steps=8, center=(sx, sz)) for sx in (-w / 2 + 0.012, w / 2 - 0.012)
              for sz in (zc - h / 2 + 0.012, zc + h / 2 - 0.012)]
    parts["screws"] = c.merge_parts([(np.column_stack([v[:, 0], -dp / 2 - 0.004 - v[:, 2], v[:, 1]]), f) for v, f in screws])
    back = dp / 2 + 0.03
    parts["stand"] = c.merge_parts([st.rod((0.0, back, 0.0), (0.0, back, zc + h / 2), POST_PIPE_R, 16),
                                    c.box((-0.1, back - 0.1, 0.0), (0.1, back + 0.1, 0.008)),
                                    c.box((-w / 2, dp / 2, zc - 0.03), (w / 2, back, zc + 0.03))])       # bracket
    parts["plate"] = c.box((-0.045, -dp / 2 - 0.002, zc - h / 2 - 0.05), (0.045, -dp / 2, zc - h / 2 - 0.015))   # position tag
    if side > 0:
        parts = {k: (np.asarray(v, float) * (1, -1, 1), [np.asarray(b)[:, ::-1] for b in (f if isinstance(f, list) else [f])])
                 for k, (v, f) in parts.items()}
    return {"parts": parts, "dims": {"box": (w, h, dp), "centre_z": zc, "mushroom_d": MUSHROOM_D,
                                     "est": ["висота центру 1.2 м", "стійка DN40", "грибок Ø40 з аркуша Schneider (analog)"]}}


def pull_cord(p0, p1, side=-1, mount=(0.0, 0.0, 0.12)):
    """ZQ 900 at p0 (floor-level point at the start of the run), red rope at ROPE_Z to p1, eye supports <= 3 m,
    tension spring and anchor at p1. The switch hangs on a bracket, its reset button faces `side` (Y).
    mount: vector from the rope to the structure the supports are bolted to (default: 0.12 m up)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    w, hmax, dp = _mm("трос_zq900", "ширина_мм"), _mm("трос_zq900", "висота_макс_мм"), _mm("трос_zq900", "план_другий_мм")
    a, b = p0 + (0, 0, ROPE_Z), p1 + (0, 0, ROPE_Z)
    run = float(np.linalg.norm(b - a))
    if run > ROPE_MAX:
        raise ValueError(f"rope {run:.1f} m over the {ROPE_MAX} m of one switch")
    d = (b - a) / run
    n_sup = max(0, math.ceil(run / ROPE_SUPPORT_MAX) - 1)
    parts = {}
    parts["switch"] = c.box(a - (dp / 2, w / 2, hmax * 0.3) - d * 0.05, a + (dp / 2, w / 2, hmax * 0.7) - d * 0.05)
    parts["reset"] = st.rod(a + (0, side * w / 2, hmax * 0.5), a + (0, side * (w / 2 + 0.012), hmax * 0.5), 0.011, 16)
    parts["rope"] = st.rod(a, b, ROPE_R, 8)
    eyes = []
    for k in range(1, n_sup + 1):
        q = a + (b - a) * k / (n_sup + 1)
        eyes.append(st.rod(q, q + np.asarray(mount, float), 0.004, 6))                  # bracket to the structure
        eyes.append(st.rod(q - d * 0.012, q + d * 0.012, 0.007, 8))                     # eye around the rope
    eyes.append(st.rod(b, b + d * 0.2, 0.012, 10))                                     # tension spring
    eyes.append(c.box(b + d * 0.2 - (0.02, 0.04, 0.04), b + d * 0.2 + (0.02, 0.04, 0.04)))  # anchor
    parts["supports"] = c.merge_parts(eyes)
    return {"parts": parts, "dims": {"run": run, "supports": n_sup, "rope_z": ROPE_Z,
                                     "est": ["висота троса 1.0 м (NOT_FOUND у джерелах)"]}}


def cabinet(n=1, hmi=False, lamps=("green", "yellow", "red")):
    """A row of n Rittal VX25 800 x 2000 x 600 on a plinth, doors to -Y, handle, optional HMI and lamps."""
    w, h, dp = _mm("шафа", "rittal_vx25_8807", "ширина_мм"), _mm("шафа", "rittal_vx25_8807", "висота_мм"), \
        _mm("шафа", "rittal_vx25_8807", "глибина_мм")
    body, door, handle, panel, lamp = [], [], [], [], {k: [] for k in ("green", "yellow", "red", "white", "blue")}
    for i in range(n):
        x0 = i * w
        body.append(c.box((x0, 0.0, 0.0), (x0 + w, dp, PLINTH)))
        body.append(c.box((x0 + 0.002, 0.0, PLINTH), (x0 + w - 0.002, dp, PLINTH + h)))
        door.append(c.box((x0 + 0.01, -0.02, PLINTH + 0.01), (x0 + w - 0.01, 0.0, PLINTH + h - 0.01)))
        handle.append(c.box((x0 + w - 0.07, -0.05, PLINTH + 0.95), (x0 + w - 0.045, -0.02, PLINTH + 1.15)))
        if hmi and i == 0:
            hw, hh = (v / 1000.0 for v in _data()["шафа"]["hmi_tp1200_comfort"]["фасад_мм"]["v"])   # Siemens TP1200
            panel.append(c.box((x0 + w / 2 - hw / 2, -0.03, PLINTH + 1.45), (x0 + w / 2 + hw / 2, -0.02, PLINTH + 1.45 + hh)))
        for k, col in enumerate(lamps):
            lx = x0 + w / 2 - 0.08 * (len(lamps) - 1) / 2 + 0.08 * k
            lamp[col].append(st.rod((lx, -0.02, PLINTH + 1.3), (lx, -0.045, PLINTH + 1.3), 0.011, 16))
    parts = {"body": c.merge_parts(body), "doors": c.merge_parts(door), "handles": c.merge_parts(handle)}
    if panel:
        parts["hmi"] = c.merge_parts(panel)
    for col, items in lamp.items():
        if items:
            parts["lamp_" + col] = c.merge_parts(items)
    return {"parts": parts, "dims": {"cabinet": (w, h, dp), "n": n, "plinth": PLINTH, "est": ["цоколь 100 мм"]}}


def signal_column(tiers=("red", "yellow", "green"), buzzer=True):
    """XVU stack light on a wall bracket: base Ø60 x 77, 50 mm per tier, red on top (EN 60204-1 order)."""
    r = _mm("колона_xvu", "база_xvuc21b_діаметр_мм") / 2
    base_h, tier = _mm("колона_xvu", "база_довжина_мм"), _mm("колона_xvu", "світло_xvuc29_довжина_мм")
    parts = {"base": c.merge_parts([c.cylinder(r, 0.0, base_h, steps=24), c.box((-0.04, 0.0, 0.0), (0.04, 0.15, 0.008))])}
    z = base_h
    if buzzer:
        parts["buzzer"] = c.cylinder(r, z, z + 0.04, steps=24)
        z += 0.04
    for col in reversed(tiers):                                 # bottom up: the last tier of the list is lowest
        parts["tier_" + col] = c.cylinder(r * 0.97, z, z + tier, steps=24)
        z += tier
    parts["cap"] = c.cylinder(r, z, z + 0.01, steps=24)
    return {"parts": parts, "dims": {"top": z + 0.01, "order_top_down": list(tiers), "est": ["зумер 40 мм (NOT_FOUND довжина)"]}}
