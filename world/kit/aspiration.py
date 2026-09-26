"""E. Centralized aspiration: dust bins 8.1 / 8.2 (drawn) and two aspiration systems (not drawn).

The drawing has only the dust bins (PDF p.1 «Бункер для пилу», p.3 positions) and, in the spec,
the □350 flanges on the tunnel conveyors (14 inlets + discharge box) and the 350 x 350 branch on
each noria boot. The units and the duct routes are a judgment from the norms (research/tunnel_k4.md
«Аспірація (блок E)»): air per point from «Указания» 1998 app. 22, duct speed >= 18 m/s on sloped
and horizontal runs, >= 12 m/s on verticals, filter RCIE + radial fan on top of each bin.

Routes are computed, not drawn by hand:
- one branch per flange with a damper (open for the working gate, throttled to the closed-point air
  for the others); branches are sized and checked for their open state;
- the tunnel collector is telescopic. Operating states: one conveyor works, `open_points` adjacent
  gates of one silo are open. Each segment is sized for its design flow (the highest over the
  states: the usual network method), so diameters only grow along the flow and the norm holds at
  design load. At partial load (the open gates downstream of a segment) the far segments run slower:
  the check reports those speeds as a finding (dust settling risk), it does not hide them.
  The fan air is the same in every state;
- the discharge-box flange joins the boot duct (norms п.4.5: the discharge box is aspirated through
  the boot); the boot duct rises between the legs («в міжтрубному просторі», spec) and leaves the
  leg zone sideways before it turns;
- the main runs at `main_z` (walkway headroom) and rises to the filter inlet outside the bin frame.
"""

import math

import numpy as np

from . import common as c
from . import steel as st

BIN_GATE_Z = 3.8        # judgment: dust trailer under the gate
HOPPER_H = 2.0          # judgment: hopper 3.0 -> 0.4 m, ~57 deg
BIN_H = 2.5             # judgment: bin prism height
FILTER_D, FILTER_H = 1.7, 3.5   # judgment: RCIE ~21-24 m2 class
FILTER_BASE = 0.8               # judgment: rotary valve and cone under the filter body
FAN_BOX = (1.0, 0.8, 1.1)       # judgment: radial dust fan ~6000 m3/h, 7.5 kW
RISE_OFFSET = 0.35              # riser to the filter runs this far outside the bin frame
LEG_CLEAR = 0.10                # boot duct keeps this gap to the leg casings
DAMPER_FROM_END = 0.35          # damper on each branch, this far before the collector

STD_D = [100, 110, 125, 140, 160, 180, 200, 225, 250, 280, 315, 355, 400, 450, 500]
V_MIN_SLOPED, V_MIN_VERTICAL, V_MAX = 18.0, 12.0, 25.0


# ------------------------------------------------------------------ bins and units

def bin_top_z():
    return BIN_GATE_Z + HOPPER_H + BIN_H


def side_towards(b, y):
    """+1 when y is north of the bin centre, else -1."""
    return 1.0 if y > b["center"][1] else -1.0


def unit_points(b, towards_y):
    """Filter axis, fan position and filter inlet (on the side facing the riser), site frame."""
    cx, cy = b["center"]
    zt = bin_top_z()
    s = side_towards(b, towards_y)
    filt = np.array([cx - 0.5, cy, zt])
    fan = np.array([cx + 0.9, cy, zt])
    inlet = filt + [0, s * FILTER_D / 2, FILTER_BASE + FILTER_H * 0.5]
    return filt, fan, inlet


def _caged_ladder(x, y, out, z0, z1, max_flight):
    """Caged ladder on a bin face (ISO 14122-4): flights <= max_flight, alternating +-0.35 m along X,
    rest platform between flights. out: +1/-1, the side of the face the cage stands on (Y)."""
    k = max(1, math.ceil((z1 - z0) / max_flight - 1e-9))
    stiles, rungs, cage, rest, rails, toes = [], [], [], [], [], []
    for i in range(k):
        za, zb = z0 + (z1 - z0) * i / k, z0 + (z1 - z0) * (i + 1) / k
        xl = x + (0.35 if i % 2 else -0.35)
        yl = y + out * 0.2
        for sx in (xl - 0.25, xl + 0.25):
            stiles.append(st.member((sx, yl, za), (sx, yl, zb + 1.1), st.flat(0.06, 0.012)))
        for z in np.arange(za + 0.3, zb + 1e-6, 0.3):
            rungs.append(st.rod((xl - 0.25, yl, z), (xl + 0.25, yl, z), 0.012, 8))
        for z in np.arange(za + 2.2, zb + 1.0, 0.9):
            ring = [(xl - 0.35, yl), (xl - 0.35, yl + out * 0.7), (xl + 0.35, yl + out * 0.7), (xl + 0.35, yl)]
            for (ax, ay), (bx, by) in zip(ring, ring[1:]):
                cage.append(st.member((ax, ay, z), (bx, by, z), st.flat(0.05, 0.006)))
        for cxx in (xl - 0.35, xl, xl + 0.35):
            cage.append(st.member((cxx, yl + out * 0.7, za + 2.2), (cxx, yl + out * 0.7, zb + 1.0), st.flat(0.05, 0.006)))
        if i < k - 1:
            ya, yb = sorted((y, y + out * 0.9))
            rest.append(st.grating_panel(x - 0.8, ya, x + 0.8, yb, zb))
            tube, toe = st.guard_rail([(x - 0.75, y), (x - 0.75, y + out * 0.85), (x + 0.75, y + out * 0.85), (x + 0.75, y)], zb)
            rails.append(tube)
            toes.append(toe)
    return stiles, rungs, cage, rest, rails, toes


def build_bin(b, riser_y, max_flight=6.0):
    """Dust bin on four legs: prism, hopper, gate ТЗА-400 underneath, roof rail and a caged ladder on
    the face away from the incoming main. Low bracing only on the long faces, so a trailer can drive
    in through the short faces under the gate."""
    cx, cy = b["center"]
    fx, fy = b["frame"]
    s = b["bin"][0] / 2
    z0, z1, z2 = BIN_GATE_Z, BIN_GATE_Z + HOPPER_H, bin_top_z()
    frame, shell, gate = [], [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            frame.append(st.member((cx + sx * fx / 2, cy + sy * fy / 2, 0.0), (cx + sx * fx / 2, cy + sy * fy / 2, z1), st.SHS_150))
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for (ax, ay), (bx, by) in zip(corners, corners[1:] + corners[:1]):
        frame.append(st.member((cx + ax * fx / 2, cy + ay * fy / 2, z1 - 0.1), (cx + bx * fx / 2, cy + by * fy / 2, z1 - 0.1), st.shs(0.12)))
        if ay == by:                                               # long faces (along X)
            frame.append(st.member((cx + ax * fx / 2, cy + ay * fy / 2, 1.2), (cx + bx * fx / 2, cy + by * fy / 2, 1.2), st.shs(0.12)))
            frame.append(st.member((cx + ax * fx / 2, cy + ay * fy / 2, 1.2), (cx + bx * fx / 2, cy + by * fy / 2, z1 - 0.1), st.L75))
    shell.append(c.box((cx - s, cy - s, z1), (cx + s, cy + s, z2)))
    g = 0.2
    v = np.array([(cx - s, cy - s, z1), (cx + s, cy - s, z1), (cx + s, cy + s, z1), (cx - s, cy + s, z1),
                  (cx - g, cy - g, z0), (cx + g, cy - g, z0), (cx + g, cy + g, z0), (cx - g, cy + g, z0)])
    f = np.array([(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)])
    shell.append((v, f))
    gate.append(c.box((cx - 0.3, cy - 0.28, z0 - 0.25), (cx + 0.3, cy + 0.28, z0)))
    gate.append(c.box((cx + 0.3, cy - 0.07, z0 - 0.2), (cx + 0.75, cy + 0.07, z0 - 0.05)))
    away = -side_towards(b, riser_y)                              # ladder face: away from the main
    lx = cx + 0.5
    stiles, rungs, cage, rest, rails, toes = _caged_ladder(lx, cy + away * fy / 2, away, 0.0, z2, max_flight)
    k = max(1, math.ceil(z2 / max_flight - 1e-9))
    x_top = lx + (0.35 if (k - 1) % 2 else -0.35)                 # the last flight comes out here
    yl, yo, e = cy + away * (s - 0.05), cy - away * (s - 0.05), s - 0.05
    ring = [(x_top + 0.4, yl), (cx + e, yl), (cx + e, yo), (cx - e, yo), (cx - e, yl), (x_top - 0.4, yl)]
    tube, toe = st.guard_rail(ring, z2)                           # open at the ladder exit
    rails.append(tube)
    toes.append(toe)
    return {"bin_frame": c.merge_parts(frame), "bin_shell": c.merge_parts(shell), "bin_gate": c.merge_parts(gate),
            "ladder": c.merge_parts(stiles + cage), "ladder_rungs": c.merge_parts(rungs),
            "bin_rest": c.merge_parts(rest) if rest else None, "bin_rails": c.merge_parts(rails), "bin_toes": c.merge_parts(toes)}


def build_unit(b, riser_y):
    """RCIE filter with rotary valve into the bin, radial fan with motor and stack."""
    filt, fan, _ = unit_points(b, riser_y)
    parts = {"filter": [], "fan": [], "fan_motor": []}
    parts["filter"].append(st.rod(filt + [0, 0, FILTER_BASE], filt + [0, 0, FILTER_BASE + FILTER_H], FILTER_D / 2, 32))
    parts["filter"].append(st.rod(filt + [0, 0, 0.05], filt + [0, 0, FILTER_BASE], 0.25, 16))        # cone -> valve
    parts["filter"].append(st.rod(filt + [0, 0, FILTER_BASE + FILTER_H], filt + [0, 0, FILTER_BASE + FILTER_H + 0.4], 0.3, 16))
    fx, fy, fz = FAN_BOX
    parts["fan"].append(c.box(tuple(fan - [fx / 2, fy / 2, 0.0]), tuple(fan + [fx / 2, fy / 2, fz])))
    parts["fan"].append(st.rod(fan + [0, 0, fz], fan + [0, 0, fz + 2.2], 0.22, 20))           # stack
    parts["fan"].append(st.member(filt + [0, 0, FILTER_BASE + FILTER_H + 0.4], fan + [0, 0, fz * 0.7], st.shs(0.30)))
    parts["fan_motor"].append(st.rod(fan + [fx / 2, 0, 0.45], fan + [fx / 2 + 0.55, 0, 0.45], 0.16, 20))
    return {k: c.merge_parts(v) for k, v in parts.items()}


# ------------------------------------------------------------------ ducts

def duct(path, d_mm):
    pts = [np.array(p, dtype=float) for p in path]
    r = d_mm / 2000
    parts = [st.rod(a, b, r, 16) for a, b in zip(pts, pts[1:])]
    parts += [st.rod(p - [0, 0, r], p + [0, 0, r], r * 1.05, 16) for p in pts[1:-1]]      # elbows
    return parts


def damper(path, d_mm):
    """Butterfly damper body and lever on a branch, DAMPER_FROM_END before the collector."""
    a, b = np.array(path[-2], float), np.array(path[-1], float)
    u = (b - a) / np.linalg.norm(b - a)
    p = b - u * DAMPER_FROM_END
    r = d_mm / 2000
    lever = np.cross(u, [1.0, 0.0, 0.0])
    lever = lever / (np.linalg.norm(lever) or 1.0)
    return [st.rod(p - u * 0.04, p + u * 0.04, r * 1.3, 16),
            st.rod(p + lever * r * 1.3, p + lever * (r * 1.3 + 0.12), 0.012, 6)]


def speed_ms(air_m3h, d_mm):
    return air_m3h / 3600 / (math.pi * (d_mm / 2000) ** 2)


def pick_d(air_m3h, v_min=V_MIN_SLOPED):
    """Largest standard diameter that still keeps the design flow at or above v_min."""
    ok = [d for d in STD_D if speed_ms(air_m3h, d) >= v_min]
    return max(ok) if ok else STD_D[0]


def _tunnel_flanges(site, t, tun):
    """(x, z_top, kind) of the 15 aspiration flanges on a tunnel conveyor: 14 inlets + discharge box."""
    cv = t["conveyor"]
    z1 = cv["casing_z"][1]
    east = cv["drive_x"] > cv["tail_x"]
    pts = [(xg + 0.55, z1 + 0.12, "inlet") for xg, _ in tun._gate_positions(site, t)]
    pts.append((cv["drive_x"] + (0.55 if east else -0.55), z1 + 0.25, "discharge"))
    return pts


def design_air(site, sysd, tun):
    """Fan design air of a system: boot + open loading points + closed points (norms, app. 22), with reserve.
    The same in every operating state: one conveyor works, `open_points` gates are open."""
    a = site["aspiration"]
    n = sum(len(_tunnel_flanges(site, t, tun)) for t in site["tunnels"] if t["id"] in sysd["tunnels"])
    q = sysd["boot_air_m3h"] + a["open_points"] * a["open_point_m3h"] + (n - a["open_points"]) * a["closed_point_m3h"]
    return q * (1 + a["reserve"]), n


def _inlet_key(tid, x):
    return tid, round(x, 4)


def operating_states(site, sysd, tun):
    """[(working tunnel, {open inlet keys})]: one conveyor works and `open_points` adjacent gates
    of one silo are open (unloading one silo)."""
    a = site["aspiration"]
    n = a["open_points"]
    silos = {s["id"]: s for s in site["silos"]}
    offs = sorted(site["silo_gates"]["offsets_along_row"])
    out = []
    for t in [t for t in site["tunnels"] if t["id"] in sysd["tunnels"]]:
        for sid in t["conveyor"]["silos"]:
            xs = [silos[sid]["x"] + o + 0.55 for o in offs]
            for i in range(len(xs) - n + 1):
                out.append((t["id"], {_inlet_key(t["id"], x) for x in xs[i:i + n]}))
    return out


def _arm_ducts(arm, states, q_open, q_closed):
    """Telescopic collector along X for one arm. Segment flow in a state = base + point flows upstream.
    Diameter from the design flow of the segment (the highest over the operating states, the usual
    network method), so diameters only grow along the flow. Runs of equal diameter merge.
    air_m3h = lowest design flow on the run (for the norm), air_max_m3h = highest,
    dusty_min_m3h = lowest flow that still carries dust in some state (partial load, reported)."""
    pts = arm["points"]                                   # [(key, x)] in flow order
    xs = [arm["x_start"]] + [x for _, x in pts] + [arm["x_end"]]
    y, z = arm["y"], arm["z"]
    out = []
    for j in range(len(xs) - 1):
        xa, xb = xs[j], xs[j + 1]
        if abs(xb - xa) < 1e-6:
            continue
        up = [k for k, _ in pts[:j]]
        flows, dusty = [], []
        for _, opened in states:
            q = arm["base"] + sum(q_open if k in opened else q_closed for k in up)
            flows.append(q)
            if arm["base_dusty"] or any(k in opened for k in up):
                dusty.append(q)
        q_design = max(flows)
        q_dusty = min(dusty) if dusty else q_design
        d = pick_d(q_design)
        if out and out[-1]["d_mm"] == d:
            out[-1]["path"][-1] = (xb, y, z)
            out[-1]["air_m3h"] = min(out[-1]["air_m3h"], q_design)
            out[-1]["air_max_m3h"] = max(out[-1]["air_max_m3h"], q_design)
            out[-1]["dusty_min_m3h"] = min(out[-1]["dusty_min_m3h"], q_dusty)
        else:
            out.append({"kind": "collector", "path": [(xa, y, z), (xb, y, z)], "d_mm": d, "air_m3h": q_design,
                        "air_max_m3h": q_design, "dusty_min_m3h": q_dusty})
    return out


def leg_zone(site_spec, tower):
    """Plan rectangle of both noria legs in the site frame."""
    rects = tower.leg_footprints(site_spec)
    x0, y0, x1, y1 = tower._bbox(rects)
    return x0 + site_spec["x"], y0 + site_spec["y"], x1 + site_spec["x"], y1 + site_spec["y"]


def routes(site, tower, tun):
    """Every duct of every system as {"path", "d_mm", "air_m3h", "air_max_m3h", "kind"} in the site frame.

    A riser in a tunnel (riser_in_pit false) splits that tunnel's collector into a far arm and a pit
    arm; the boot duct feeds the pit arm at the pit face. A riser in the pit (riser_in_pit true) takes
    one arm per tunnel across the pit and the boot duct at `boot_duct_z` from the side."""
    a = site["aspiration"]
    k = 1.0 + a["reserve"]
    q_open, q_closed = a["open_point_m3h"] * k, a["closed_point_m3h"] * k
    zc, zr = a["collector_z"], a["main_z"]
    bins = {b["id"]: b for b in a["dust_bins"]}
    out = {}
    for sysd in a["systems"]:
        air, n_flanges = design_air(site, sysd, tun)
        states = operating_states(site, sysd, tun)
        tl = [t for t in site["tunnels"] if t["id"] in sysd["tunnels"]]
        spec = next(s for s in site["noria_towers"] if s["id"] == sysd["tower"])
        rx, ry = sysd["riser_xy"]
        in_pit = sysd["riser_in_pit"]
        bdz = sysd["boot_duct_z"]
        q_boot = sysd["boot_air_m3h"] * k
        d_branch = pick_d(q_open)
        d_main = pick_d(air)

        # boot duct geometry first: branches may land on it
        nx, ny = spec["noria_axis"]
        _, _, _, anchors = tower.build_noria(spec)
        boot_top = tower.noria_frame(spec)(anchors["boot_box"][1])[2]
        lx0, _, lx1, _ = leg_zone(spec, tower)
        if in_pit:
            x_t, y_t = rx, ry
        else:
            x_t, y_t = tun.pit_face_x(site, tl[0]), tl[0]["row_y"] + sysd["collector_y_rel"][tl[0]["id"]]
        boot_extra = sum(q_closed for t in tl for *_, kind in _tunnel_flanges(site, t, tun)
                         if kind == "discharge" and not in_pit)
        d_boot = pick_d(q_boot)
        r_boot = d_boot / 2000
        sx = -1.0 if x_t < nx else 1.0
        x_out = (lx0 if sx < 0 else lx1) + sx * (LEG_CLEAR + r_boot)      # first turn: just clear of the legs
        path = [(nx, ny, boot_top + 0.05), (nx, ny, bdz), (x_out, ny, bdz), (x_out, y_t, bdz), (x_t, y_t, bdz)]
        if not in_pit:
            path.append((x_t, y_t, zc))
        path = [p for i, p in enumerate(path) if i == 0 or np.linalg.norm(np.subtract(p, path[i - 1])) > 1e-6]
        ducts = [{"kind": "boot", "d_mm": d_boot, "air_m3h": q_boot, "air_max_m3h": q_boot + boot_extra, "path": path}]

        for t in tl:
            yc = t["row_y"] + sysd["collector_y_rel"][t["id"]]
            xp = tun.pit_face_x(site, t)
            far_pts, pit_pts = [], []
            for x, zf, kind in _tunnel_flanges(site, t, tun):
                if kind == "discharge" and not in_pit:           # aspirated through the boot duct (п.4.5)
                    lo, hi = sorted((x_t, x_out))
                    x_land = min(max(x, lo + r_boot), hi - r_boot - d_branch / 2000)
                    ducts.append({"kind": "branch", "path": [(x, t["row_y"], zf), (x_land, y_t, bdz)], "d_mm": d_branch,
                                  "air_m3h": q_open, "air_max_m3h": q_open})
                    continue
                ducts.append({"kind": "branch", "path": [(x, t["row_y"], zf), (x, yc, zc)], "d_mm": d_branch,
                              "air_m3h": q_open, "air_max_m3h": q_open})
                key = _inlet_key(t["id"], x) if kind == "inlet" else (t["id"], "discharge")
                if in_pit or (x - rx) * (t["end_x"] - rx) > 0:
                    far_pts.append((key, x))
                else:
                    pit_pts.append((key, x))
            far_pts.sort(key=lambda p: -abs(p[1] - rx))
            if far_pts:
                ducts += _arm_ducts({"points": far_pts, "x_start": far_pts[0][1], "x_end": rx, "y": yc, "z": zc,
                                     "base": 0.0, "base_dusty": False}, states, q_open, q_closed)
            if not in_pit:
                pit_pts.sort(key=lambda p: abs(p[1] - xp))
                ducts += _arm_ducts({"points": pit_pts, "x_start": xp, "x_end": rx, "y": yc, "z": zc,
                                     "base": q_boot + boot_extra, "base_dusty": True}, states, q_open, q_closed)

        # riser and main: up to main_z, towards the bin, up outside the bin frame, into the filter inlet
        b = bins[sysd["unit_at"]]
        _, _, inlet = unit_points(b, ry)
        s = side_towards(b, ry)
        stop = b["center"][1] + s * (b["frame"][1] / 2 + RISE_OFFSET)
        z0 = zc
        if in_pit:                                            # below the boot entry only the collectors flow
            ducts.append({"kind": "riser", "d_mm": d_main, "air_m3h": air - q_boot, "air_max_m3h": air - q_boot,
                          "path": [(rx, ry, zc), (rx, ry, bdz)]})
            z0 = bdz
        path = [(rx, ry, z0), (rx, ry, zr), (rx, stop, zr), (inlet[0], stop, zr), (inlet[0], stop, inlet[2]), tuple(inlet)]
        path = [p for i, p in enumerate(path) if i == 0 or np.linalg.norm(np.subtract(p, path[i - 1])) > 1e-6]
        ducts.append({"kind": "main", "d_mm": d_main, "air_m3h": air, "air_max_m3h": air, "path": path})
        out[sysd["id"]] = {"air_m3h": air, "flanges": n_flanges, "d_branch": d_branch, "d_main": d_main,
                           "d_boot": d_boot, "ducts": ducts, "states": len(states)}
    return out


def riser_holes(site, tun):
    """Roof holes {tunnel id: [(x, half, y)]} and pit cover holes {tower id: [(x0, y0, x1, y1)]}, site frame."""
    a = site.get("aspiration")
    roof, cover = {}, {}
    if not a:
        return roof, cover
    for sysd in a["systems"]:
        rx, ry = sysd["riser_xy"]
        half = pick_d(design_air(site, sysd, tun)[0]) / 2000 + 0.05
        if sysd["riser_in_pit"]:
            cover.setdefault(sysd["tower"], []).append((rx - half, ry - half, rx + half, ry + half))
        else:
            tid = next(t["id"] for t in site["tunnels"] if t["id"] in sysd["tunnels"]
                       and min(t["end_x"], tun.pit_face_x(site, t)) <= rx <= max(t["end_x"], tun.pit_face_x(site, t)))
            roof.setdefault(tid, []).append((rx, half, ry))
    return roof, cover


def build_system_ducts(route):
    parts, dampers = [], []
    for dct in route["ducts"]:
        parts += duct(dct["path"], dct["d_mm"])
        if dct["kind"] == "branch":
            dampers += damper(dct["path"], dct["d_mm"])
    return {"ducts": c.merge_parts(parts), "dampers": c.merge_parts(dampers)}


# ------------------------------------------------------------------ scene

def build(site, tower, tun, systems=None, collection=None, materials=None):
    """Dust bins, units and ducts of the chosen systems (all by default) as Blender objects.
    Returns (objs, measure)."""
    m = materials or {}
    galv = m.get("galv") or c.mat_galvanized("ASP_GALV", age=0.4, spangle_scale=60.0)
    galv_old = m.get("galv_old") or c.mat_galvanized("ASP_GALV_OLD", age=0.6, spangle_scale=50.0)
    grating = m.get("grating") or st.mat_grating("ASP_GRATING")
    yellow = m.get("yellow") or c.mat_painted("ASP_RAIL_YELLOW", (0.80, 0.55, 0.03), 0.45)
    dark = m.get("dark") or c.mat_painted("ASP_DARK", (0.20, 0.23, 0.24), 0.4)
    motor = m.get("motor") or c.mat_painted("ASP_MOTOR_BLUE", (0.05, 0.16, 0.35), 0.35)
    red = m.get("red") or c.mat_painted("ASP_GATE_RED", (0.55, 0.06, 0.04), 0.45, grime=0.3)
    filt = c.mat_painted("ASP_FILTER", (0.80, 0.81, 0.80), 0.4, grime=0.35)
    fan_paint = c.mat_painted("ASP_FAN", (0.42, 0.45, 0.46), 0.35, grime=0.35)
    look = {"bin_frame": (galv, False), "bin_shell": (galv_old, False), "bin_gate": (red, False),
            "ladder": (galv, False), "ladder_rungs": (galv, "quads"), "bin_rest": (grating, False),
            "bin_rails": (yellow, "quads"), "bin_toes": (yellow, False), "filter": (filt, "quads"),
            "fan": (fan_paint, False), "fan_motor": (motor, "quads"), "ducts": (galv, "quads"),
            "dampers": (dark, "quads")}
    a = site["aspiration"]
    bins = {b["id"]: b for b in a["dust_bins"]}
    all_routes = routes(site, tower, tun)
    objs, measure = {}, {}
    for sysd in a["systems"]:
        if systems is not None and sysd["id"] not in systems:
            continue
        b = bins[sysd["unit_at"]]
        ry = sysd["riser_xy"][1]
        r = all_routes[sysd["id"]]
        parts = {**build_bin(b, ry), **build_unit(b, ry), **build_system_ducts(r)}
        for key, data in parts.items():
            if data is None:
                continue
            mat, smooth = look[key]
            name = f"ASP_{sysd['id']}_{key.upper()}"
            objs[name] = c.mesh_from_arrays(name, *data, mat, smooth=smooth, collection=collection)
        measure[sysd["id"]] = {
            "serves": [sysd["tower"] + " boot"] + sysd["tunnels"], "unit_at": b["id"],
            "air_m3h": round(r["air_m3h"]), "flanges": r["flanges"], "operating_states": r["states"],
            "main_mm": r["d_main"], "branch_mm": r["d_branch"], "boot_mm": r["d_boot"],
            "collector_mm": sorted({d["d_mm"] for d in r["ducts"] if d["kind"] == "collector"}),
            "main_speed_ms": round(speed_ms(r["air_m3h"], r["d_main"]), 1),
            "riser_xy": sysd["riser_xy"], "riser_in_pit": sysd["riser_in_pit"],
            "bin_top_z": bin_top_z(), "status": "judgment (see SITE.json aspiration.status)",
        }
    return objs, measure
