"""E. Centralized aspiration: dust bins 8.1 / 8.2 (drawn) and two aspiration systems (not drawn).

The drawing has only the dust bins (PDF p.1 «Бункер для пилу», p.3 positions) and, in the spec,
the □350 flanges on the tunnel conveyors and the 350 x 350 branch on each noria boot. The units and
the duct routes are a judgment from the norms (research/tunnel_k4.md «Аспірація (блок E)»):
air per point from «Указания» 1998 app. 22, duct speed 12-20 m/s, filter RCIE + radial fan on
top of each bin. Everything that is a judgment is marked in SITE.json `aspiration.status`.
"""

import math

import numpy as np

from . import common as c
from . import steel as st

BIN_GATE_Z = 3.8        # judgment: dust truck under the gate
HOPPER_H = 2.0          # judgment: hopper 3.0 -> 0.4 m, ~57 deg
BIN_H = 2.5             # judgment: bin prism height
FILTER_D, FILTER_H = 1.7, 3.5   # judgment: RCIE ~21-24 m2 class
FAN_BOX = (1.0, 0.8, 1.1)      # judgment: radial dust fan ~6000 m3/h, 7.5 kW


def bin_top_z():
    return BIN_GATE_Z + HOPPER_H + BIN_H


def build_bin(b):
    """Dust bin on four legs: prism, hopper, gate ТЗА-400 underneath, roof, ladder-side platform."""
    cx, cy = b["center"]
    fx, fy = b["frame"]
    s = b["bin"][0] / 2
    z0, z1, z2 = BIN_GATE_Z, BIN_GATE_Z + HOPPER_H, bin_top_z()
    frame, shell, gate = [], [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            frame.append(st.member((cx + sx * fx / 2, cy + sy * fy / 2, 0.0), (cx + sx * fx / 2, cy + sy * fy / 2, z1), st.SHS_150))
    for z in (z1 - 0.1, 1.2):
        for (ax, ay), (bx, by) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            frame.append(st.member((cx + ax * fx / 2, cy + ay * fy / 2, z), (cx + bx * fx / 2, cy + by * fy / 2, z), st.shs(0.12)))
    shell.append(c.box((cx - s, cy - s, z1), (cx + s, cy + s, z2)))
    g = 0.2
    v = np.array([(cx - s, cy - s, z1), (cx + s, cy - s, z1), (cx + s, cy + s, z1), (cx - s, cy + s, z1),
                  (cx - g, cy - g, z0), (cx + g, cy - g, z0), (cx + g, cy + g, z0), (cx - g, cy + g, z0)])
    f = np.array([(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)])
    shell.append((v, f))
    gate.append(c.box((cx - 0.3, cy - 0.28, z0 - 0.25), (cx + 0.3, cy + 0.28, z0)))
    gate.append(c.box((cx + 0.3, cy - 0.07, z0 - 0.2), (cx + 0.75, cy + 0.07, z0 - 0.05)))
    return {"bin_frame": c.merge_parts(frame), "bin_shell": c.merge_parts(shell), "bin_gate": c.merge_parts(gate)}


def unit_points(b):
    """Filter inlet, filter axis and fan position on top of a bin (site frame)."""
    cx, cy = b["center"]
    zt = bin_top_z()
    filt = np.array([cx - 0.5, cy, zt])
    fan = np.array([cx + 0.9, cy, zt])
    inlet = filt + [0, -FILTER_D / 2, FILTER_H * 0.7]
    return filt, fan, inlet


def build_unit(b):
    """RCIE filter with rotary valve into the bin, radial fan with motor and stack."""
    filt, fan, _ = unit_points(b)
    parts = {"filter": [], "fan": [], "fan_motor": []}
    parts["filter"].append(st.rod(filt + [0, 0, 0.8], filt + [0, 0, 0.8 + FILTER_H], FILTER_D / 2, 32))
    parts["filter"].append(st.rod(filt + [0, 0, 0.05], filt + [0, 0, 0.8], 0.25, 16))        # cone -> valve
    parts["filter"].append(st.rod(filt + [0, 0, 0.8 + FILTER_H], filt + [0, 0, 1.2 + FILTER_H], 0.3, 16))
    fx, fy, fz = FAN_BOX
    parts["fan"].append(c.box(tuple(fan - [fx / 2, fy / 2, 0.0]), tuple(fan + [fx / 2, fy / 2, fz])))
    parts["fan"].append(st.rod(fan + [0, 0, fz], fan + [0, 0, fz + 2.2], 0.22, 20))           # stack
    parts["fan"].append(st.member(filt + [0, 0, 1.2 + FILTER_H], fan + [0, 0, fz * 0.7], st.shs(0.30)))
    parts["fan_motor"].append(st.rod(fan + [fx / 2, 0, 0.45], fan + [fx / 2 + 0.55, 0, 0.45], 0.16, 20))
    return {k: c.merge_parts(v) for k, v in parts.items()}


def duct(path, d_mm):
    pts = [np.array(p, dtype=float) for p in path]
    r = d_mm / 2000
    parts = [st.rod(a, b, r, 16) for a, b in zip(pts, pts[1:])]
    parts += [st.rod(p - [0, 0, r], p + [0, 0, r], r * 1.05, 16) for p in pts[1:-1]]      # elbows
    return parts


def speed_ms(air_m3h, d_mm):
    return air_m3h / 3600 / (math.pi * (d_mm / 2000) ** 2)


# ------------------------------------------------------------------ routes (computed, not hand-drawn)

STD_D = [100, 110, 125, 140, 160, 180, 200, 225, 250, 280, 315, 355, 400, 450, 500]
V_MIN_SLOPED, V_MIN_VERTICAL, V_MAX = 18.0, 12.0, 25.0


def pick_d(air_m3h, v_min=V_MIN_SLOPED):
    """Largest standard diameter that still keeps the design flow at or above v_min."""
    ok = [d for d in STD_D if speed_ms(air_m3h, d) >= v_min]
    return max(ok) if ok else STD_D[0]


def _tunnel_flanges(site, t, tun):
    """(x, z_top) of the 15 aspiration flanges on a tunnel conveyor (14 inlets + discharge box)."""
    cv = t["conveyor"]
    z1 = cv["casing_z"][1]
    east = cv["drive_x"] > cv["tail_x"]
    pts = [(xg + 0.55, z1 + 0.12) for xg, _ in tun._gate_positions(site, t)]
    pts.append((cv["drive_x"] + (0.55 if east else -0.55), z1 + 0.25))
    return pts


def design_air(site, sysd, tun):
    """Design air flow of a system: boot + open loading points + closed points (norms, app. 22)."""
    a = site["aspiration"]
    n = sum(len(tun._gate_positions(site, t)) + 1 for t in site["tunnels"] if t["id"] in sysd["tunnels"])
    q = sysd["boot_air_m3h"] + a["open_points"] * a["open_point_m3h"] + (n - a["open_points"]) * a["closed_point_m3h"]
    return q * (1 + a["reserve"]), n


def routes(site, tower, tun):
    """Every duct of every system as {"path", "d_mm", "air_m3h", "kind"} in the site frame."""
    a = site["aspiration"]
    bins = {b["id"]: b for b in a["dust_bins"]}
    out = {}
    for sysd in a["systems"]:
        air, n_flanges = design_air(site, sysd, tun)
        d_branch = pick_d(a["open_point_m3h"])
        d_main = pick_d(air)
        ducts = []
        spec = next(s for s in site["noria_towers"] if s["id"] == sysd["tower"])
        _, _, _, anchors = tower.build_noria(spec)
        boot = tower.noria_frame(spec)(anchors["boot_box"][1]) + [spec["x"], spec["y"], 0.0]
        nx, ny = spec["noria_axis"]
        rx, ry = sysd["riser_xy"]
        zc = a["collector_z"]
        for t in [t for t in site["tunnels"] if t["id"] in sysd["tunnels"]]:
            yc = t["row_y"] + sysd["collector_y_rel"][t["id"]]
            for xa, zf in _tunnel_flanges(site, t, tun):
                ducts.append({"kind": "branch", "path": [(xa, t["row_y"], zf), (xa, yc, zc)], "d_mm": d_branch,
                              "air_m3h": a["open_point_m3h"]})
            xs = [x for x, _ in _tunnel_flanges(site, t, tun)]
            x_far = min(xs) - 0.3 if t["end_x"] < 0 else max(xs) + 0.3
            x_pit = tun.pit_face_x(site, t)
            x_to = rx if min(x_far, x_pit) <= rx <= max(x_far, x_pit) else x_pit
            ducts.append({"kind": "collector", "path": [(x_far, yc, zc), (x_to, yc, zc)], "d_mm": d_main, "air_m3h": air})
            if x_to != x_pit:
                ducts.append({"kind": "collector", "path": [(x_pit, yc, zc), (x_to, yc, zc)], "d_mm": d_main, "air_m3h": air})
        d_boot = pick_d(sysd["boot_air_m3h"])
        ducts.append({"kind": "boot", "d_mm": d_boot, "air_m3h": sysd["boot_air_m3h"],
                      "path": [(nx, ny, boot[2] + 0.05), (nx, ny, a["pit_duct_z"]), (rx, ry, a["pit_duct_z"])]
                      if sysd["riser_in_pit"] else
                      [(nx, ny, boot[2] + 0.05), (nx, ny, a["pit_duct_z"]),
                       (tun.pit_face_x(site, next(t for t in site["tunnels"] if t["id"] in sysd["tunnels"])), ry, a["pit_duct_z"]),
                       (tun.pit_face_x(site, next(t for t in site["tunnels"] if t["id"] in sysd["tunnels"])), ry, zc)]})
        if sysd["riser_in_pit"]:                      # collectors from both sides meet the riser across the pit
            for t in [t for t in site["tunnels"] if t["id"] in sysd["tunnels"]]:
                ducts.append({"kind": "collector", "d_mm": d_main, "air_m3h": air,
                              "path": [(tun.pit_face_x(site, t), ry, zc), (rx, ry, zc)]})
        b = bins[sysd["unit_at"]]
        _, _, inlet = unit_points(b)
        zr = a["main_z"]
        z_start = a["pit_duct_z"] if sysd["riser_in_pit"] else zc
        sgn = 1.0 if inlet[1] > ry else -1.0
        stop = inlet[1] - sgn * 1.2                   # rise outside the bin frame, then into the filter inlet
        path = [(rx, ry, z_start), (rx, ry, zr), (inlet[0], ry, zr), (inlet[0], stop, zr),
                (inlet[0], stop, inlet[2]), tuple(inlet)]
        path = [p for k, p in enumerate(path) if k == 0 or np.linalg.norm(np.subtract(p, path[k - 1])) > 1e-6]
        ducts.append({"kind": "main", "d_mm": d_main, "air_m3h": air, "path": path})
        out[sysd["id"]] = {"air_m3h": air, "flanges": n_flanges, "d_branch": d_branch, "d_main": d_main,
                           "d_boot": d_boot, "ducts": ducts}
    return out


def build_system_ducts(route):
    parts = []
    for dct in route["ducts"]:
        parts += duct(dct["path"], dct["d_mm"])
    return {"ducts": c.merge_parts(parts)}
