"""Flow distribution under a noria head: splitters (ввід 45°) with rail gates ТЗА-300 and □300 spouts.

Site frame positions from SITE.json `distribution`, read from the drawing centrelines on p.4-p.7
(research/tunnel_k4.md «Розподіл під головою норії»). Spout bodies are not drawn on the sheets:
the □300 section comes from the specification of the inlets (вводи 45°, 300 x 300).
"""

import numpy as np

from . import common as c
from . import steel as st

SPOUT = 0.30
GATE_H = 0.15          # research: rail gate ТЕА-300 body height 150 mm
COLLECTOR = 0.40       # EST: splitter collector box, plan size
MIN_SLOPE_DEG = 45.0   # EST rule of thumb for grain spouts


def _p(xyz, ox, oy):
    return np.array(xyz, dtype=float) - [ox, oy, 0.0]


def segments(path):
    """(start, end) pairs of a spout polyline."""
    pts = [np.array(p, dtype=float) for p in path]
    return list(zip(pts, pts[1:]))


def slope_deg(a, b):
    run = np.linalg.norm((b - a)[:2])
    return 90.0 if run < 1e-6 else float(np.degrees(np.arctan2(abs(b[2] - a[2]), run)))


def build(d, ox=0.0, oy=0.0, outlet=None):
    """Parts in the frame whose origin is (ox, oy). outlet: head outlet in that frame; when given,
    a vertical drop joins it to the first splitter."""
    body, gates, motors, spouts = [], [], [], []
    for k, s in enumerate(d["splitters"]):
        at = _p(s["at"], ox, oy)
        h = COLLECTOR / 2
        body.append(c.box(at - [h, h, 0.25], at + [h, h, 0.0]))
        body.append(c.box(at - [h + 0.04, h + 0.04, 0.0], at + [h + 0.04, h + 0.04, 0.02]))     # inlet flange
        if k == 0 and outlet is not None:
            spouts.append(st.member(np.asarray(outlet, float), at + [0, 0, 0.02], st.shs(SPOUT)))
        for b in s["branches"]:
            bp = _p(b, ox, oy)
            spouts.append(st.member(at - [0, 0, 0.25], bp + [0, 0, GATE_H], st.shs(SPOUT)))
            gates.append(c.box(bp + [-0.25, -0.22, 0.0], bp + [0.25, 0.22, GATE_H]))
            gates.append(c.box(bp + [0.25, -0.07, 0.03], bp + [0.60, 0.07, GATE_H - 0.03]))       # rack housing
            motors.append(st.rod(bp + [0.52, 0.07, GATE_H / 2], bp + [0.52, 0.27, GATE_H / 2], 0.055, 16))
    for sp in d["spouts"]:
        pts = [_p(q, ox, oy) for q in sp["path"]]
        for a, b in zip(pts, pts[1:]):
            spouts.append(st.member(a, b, st.shs(SPOUT)))
        for q in pts[1:-1]:                                        # elbows
            spouts.append(c.box(q - [0.17, 0.17, 0.17], q + [0.17, 0.17, 0.17]))
    parts = {"splitters": body, "gates": gates, "gate_motors": motors, "spouts": spouts}
    return {k: c.merge_parts(v) for k, v in parts.items() if v}
