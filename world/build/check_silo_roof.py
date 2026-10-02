"""K1/K5 phase 2B check: silo roof openings, roof fans, hatches and wall doors against the sources
(research/silo_equipment.md §4-5, SITE.json silo_roof / silo_hatches) and against the model.

Roof:
- roof ribs at the stiffener angles (PDF p.6: roof lines match the stiffeners), rafters under ribs;
- vent hole area >= the lowest current source (FAIL), >= the research figure (WARN);
- every roof opening (vents, service holes, hatches, level sensor) sits between two ribs, clear of the
  collar, the eave and the roof ladder, and no two openings overlap;
- roof fans: count = spec, each in a vent of its ring; opposite, outside the gallery band and >= 2 m
  from the roof hatch (WARN, judgment); fan motor under the roof clear of cables and rafters.
Service holes: one per thermometry cable, near its head.
Wall doors: between stiffener flanges, inside one sheet tier; in the site frame the door leaf zone and
the steps cut nothing (real meshes, Blender BVH overlap), the free strip in front is a WARN.

Roof fans on the real component (components.duct_axial_fan, built from the SITE dicts, measured from vertices): impeller
Ø = SITE and in the research range 350-450 mm; tip gap to the casing throat > 0.5 mm (FAIL; WARN outside 0.25-1.5 % D, EST);
motor and bracket under the roof underside and clear of sheet, ribs, rafters and purlins (BVH); finger guard free area
>= 50 % (FAIL; WARN < 70 %, EST; rays along the axis); 0.25 kW = IEC 71, Ø140 and housing 200 mm as SITE; the motor against
the grain at full fill is a FINDING.

Broken variants that must fail: roof fan impeller does not fit the casing, motor 1.1 kW, impeller Ø300, fan raised 0.25 m,
solid guard plate; too few vents, vents not on sector centres, roof hatch on the ladder,
door on a stiffener, door behind the outside ladder, roof ribs off the stiffeners.

Run:
    blender --background --python world/build/check_silo_roof.py
Exit code 1 when any case fails.
"""

import copy
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "build"))

import check_aspiration as ca  # noqa: E402
from kit import aspiration as asp  # noqa: E402
from kit import common as c  # noqa: E402
from kit import noria_tower as tower  # noqa: E402
from kit import silo_interior as si  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402
from kit import tunnel as tun  # noqa: E402

SPEC_ROOF_FANS = 2            # sourced: 2 roof fans 0.25 kW per silo (rec_3d1a15f7)
OPEN_GAP_WARN = 0.3           # judgment: sheet between two roof holes
FAN_HATCH_MIN = 2.0           # judgment (research §4 "для check")
MOTOR_CABLE_WARN = 0.5        # judgment: cable swing under a running fan
EAVE_KEEP = 0.3               # judgment: no hole in the eave angle zone
COLLAR_KEEP = 0.1


def _poly(o, n=16):
    """Plan outline of a roof opening: rectangle (w across the slope, l along it) or n-gon for round ones."""
    u = np.array([math.cos(math.radians(o["deg"])), math.sin(math.radians(o["deg"]))])
    t = np.array([-u[1], u[0]])
    p = np.array([o["x"], o["y"]])
    if o.get("round"):
        a = np.linspace(0, 2 * math.pi, n, endpoint=False)
        return [tuple(p + o["w"] / 2 * (math.cos(k) * u + math.sin(k) * t)) for k in a]
    return [tuple(p + s * o["w"] / 2 * t + q * o["l"] / 2 * u) for s, q in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


def _ladder_strip():
    u = np.array([math.cos(math.radians(silo.LADDER_ANGLE)), math.sin(math.radians(silo.LADDER_ANGLE))])
    t = np.array([-u[1], u[0]])
    r0, r1 = silo.roof_ladder_span()
    h = silo.ROOF_LADDER_HALF
    return [tuple(u * r0 - t * h), tuple(u * r1 - t * h), tuple(u * r1 + t * h), tuple(u * r0 + t * h)]


def roof_checks(roof, hatches, eq, rib_phase=None):
    out = []
    ops = silo.roof_openings(roof, hatches, eq)
    ribs = silo.rib_angles(rib_phase)
    stiff = np.degrees(silo.stiffener_angles()) % 360
    d_rib = max(min(abs((r - s + 180) % 360 - 180) for s in stiff) for r in ribs)
    out.append(("roof ribs at the stiffener angles (PDF p.6)", d_rib < 1e-6, f"worst {d_rib:.3f} deg"))
    d_raf = max(min(abs((a - r + 180) % 360 - 180) for r in ribs) for a in si.rafter_angles())
    out.append(("rafters under roof ribs", d_raf < 1e-6, f"worst {d_raf:.3f} deg"))

    vents = [o for o in ops if o["kind"] in ("vent", "fan_vent")]
    area = sum(math.pi * (o["w"] / 2) ** 2 for o in vents)
    v = roof["vents"]
    out.append((f"vent hole area >= {v['area_min_m2']} m2 (lowest current source)", area >= v["area_min_m2"],
                f"{len(vents)} × Ø{v['hole_d_m'] * 1000:.0f} = {area:.2f} m2"))
    out.append((f"vent hole area >= {v['area_required_m2']} m2 (research, WARN)", True,
                f"{area:.2f} m2" + ("" if area >= v["area_required_m2"] else " — WARN: below the research figure")))

    on_rib = [f"{o['id']} {g:.3f}" for o in ops if (g := silo.rib_clearance(o["r"], o["deg"], o["w"], o["l"], rib_phase)) < 0]
    out.append(("every roof opening sits between two ribs", not on_rib, f"on a rib (clearance m): {on_rib[:6]}"))
    edge = [o["id"] for o in ops if o["r"] - o["l"] / 2 < silo.COLLAR_R + COLLAR_KEEP or o["r"] + o["l"] / 2 > silo.R - EAVE_KEEP]
    out.append(("roof openings clear of the collar and the eave", not edge, f"outside: {edge}"))
    strip = _ladder_strip()
    lad = [o["id"] for o in ops if ca.poly_dist(_poly(o), strip) <= 0.0]
    out.append(("roof openings clear of the roof ladder", not lad, f"on the ladder: {lad}"))
    clash, tight = [], []
    polys = [(o, _poly(o)) for o in ops]
    for i, (a, pa) in enumerate(polys):
        for b, pb in polys[i + 1:]:
            g = ca.poly_dist(pa, pb)
            if g <= 0.0:
                clash.append(f"{a['id']}×{b['id']}")
            elif g < OPEN_GAP_WARN:
                tight.append(f"{a['id']}×{b['id']} {g:.2f}")
    out.append(("no two roof openings overlap", not clash, f"{len(ops)} openings; overlapping: {clash[:6]}"))
    out.append((f"roof openings >= {OPEN_GAP_WARN} m apart (WARN, judgment)", True,
                ("WARN: " + ", ".join(tight[:6])) if tight else "all apart"))

    fans = [o for o in ops if o["kind"] == "fan_vent"]
    f = roof["fans"]
    out.append(("roof fans = spec", len(fans) == SPEC_ROOF_FANS, f"{len(fans)} vs {SPEC_ROOF_FANS} (rec_3d1a15f7)"))
    ring = f["ring"]
    miss = [d for d in f["near_deg"] if not any(o["ring"] == ring and abs((o["deg"] - d + 180) % 360 - 180) <= 180 / silo.ROOF_RIBS + 1e-9
                                                for o in fans)]
    out.append(("each roof fan sits in a vent of its ring", not miss, f"no vent within half a sector of {miss}"))
    notes = []
    if len(fans) == 2 and abs(abs((fans[0]["deg"] - fans[1]["deg"] + 180) % 360 - 180) - 180) > 5:
        notes.append("not opposite")
    band = SITE["silo_top_galleries"]["y_rel_row"]
    notes += [f"{o['id']} under the gallery" for o in fans if band[0] - o["w"] / 2 - 0.3 <= o["y"] <= band[1] + o["w"] / 2 + 0.3]
    hatch = next(o for o in ops if o["kind"] == "roof_access")
    notes += [f"{o['id']} {math.hypot(o['x'] - hatch['x'], o['y'] - hatch['y']):.2f} m from the hatch" for o in fans
              if math.hypot(o["x"] - hatch["x"], o["y"] - hatch["y"]) < FAN_HATCH_MIN]
    out.append(("roof fans opposite, outside the gallery band, >= 2 m from the hatch (WARN, judgment)", True,
                ("WARN: " + ", ".join(notes)) if notes else "yes"))

    mr = f["motor_below_roof"]["d_m"] / 2
    cab = si.cable_positions(eq["thermo"]["rings"])
    gaps = [(math.hypot(o["x"] - x, o["y"] - y) - mr - si.CABLE_R, o["id"]) for o in fans for x, y, _ in cab]
    g, gid = min(gaps)
    out.append(("roof fan motors clear of the thermometry cables", g > 0.0,
                f"closest {g:.2f} m ({gid})" + (f" — WARN: < {MOTOR_CABLE_WARN} m" if g < MOTOR_CABLE_WARN else "")))
    raf = min(o["r"] * math.sin(math.radians(min(abs((o["deg"] - a + 180) % 360 - 180) for a in si.rafter_angles())))
              - mr - si.RAFTER_HALF for o in fans)
    out.append(("roof fan motors clear of the rafters", raf > 0.0, f"closest {raf:.2f} m"))

    holes = [o for o in ops if o["kind"] == "service_hole"]
    far = [f"{o['id']} {o['offset']:.2f}" for o in holes if o["offset"] > hatches["thermo_service_holes"]["max_offset_m"]]
    out.append(("one service hole per cable, near its head", len(holes) == len(cab) and not far,
                f"{len(holes)} holes for {len(cab)} cables; too far: {far}"))
    return out


# ---- roof fan on a real component (C7a): geometry of the fans built from the (patched) SITE dicts, silo frame.
FAN_D_RANGE = (0.35, 0.45)    # research §4: impeller ≈ 400 mm (350-450), rec_894d3a4a
FAN_KW = 0.25                 # sourced: 0.25 kW (rec_d26b642f)
FAN_FRAME = "71"              # 0.25 kW -> IEC 71 (iec_motor_frames.json: WEG W22 p.46), literal
FAN_TOL_D = 0.005             # impeller Ø ± 5 mm
FAN_GAP_MIN = 0.0005          # FAIL: tip gap <= 0.5 mm, a touching blade (physical limit)
FAN_GAP_BAND = (0.001, 0.006)  # WARN: 0.25-1.5 % D, own recommendation (EST)
FAN_OPEN_FAIL = 0.5           # FAIL: free area of the finger guard < 50 % (a solid plate is 0)
FAN_OPEN_WARN = 0.7           # WARN: own recommendation (EST)
FAN_MOTOR_D_TOL = 0.05        # motor Ø within 5 % of SITE motor_below_roof.d_m
FAN_MOTOR_L_TOL = 0.01        # motor housing length within 10 mm of SITE motor_below_roof.l_m
FAN_BURY_CLEAR = 0.3          # judgment: grain surface kept this far under the motor nose (FINDING only)
_ROOF_BVH = None


def _roof_bvh():
    """BVH of the unbroken roof sheet with ribs, and of the rafters and purlins, silo frame (cached)."""
    global _ROOF_BVH
    if _ROOF_BVH is None:
        sheet, _ = silo.build_roof()
        raf, rings = si.build_roof_structure()
        _ROOF_BVH = (ca._bvh(sheet), ca._bvh(raf), ca._bvh(rings))
    return _ROOF_BVH


def open_fraction(grille, r_max, step=0.01):
    """Share of rays along -Z through the circle r_max (about the guard axis) that miss the guard wires (BVH ray_cast)."""
    from mathutils import Vector
    v = np.asarray(grille[0], float).reshape(-1, 3)
    cx, cy = 0.5 * (v[:, 0].min() + v[:, 0].max()), 0.5 * (v[:, 1].min() + v[:, 1].max())
    tree = ca._bvh(grille)
    zt = float(v[:, 2].max()) + 0.05
    hit = tot = 0
    for dx in np.arange(-r_max, r_max + 1e-9, step):
        for dy in np.arange(-r_max, r_max + 1e-9, step):
            if dx * dx + dy * dy > r_max * r_max:
                continue
            tot += 1
            if tree.ray_cast(Vector((cx + dx, cy + dy, zt)), Vector((0.0, 0.0, -1.0)))[0] is not None:
                hit += 1
    return 1.0 - hit / max(tot, 1)


def fan_checks(roof, hatches, eq, faults=None, fan_dz=0.0):
    """Roof fans built from `roof` (SITE silo_roof dict, may be patched): impeller Ø, tip gap, motor under the roof,
    finger guard, power and frame. Each fan is built on its own, measured from the vertices."""
    out = []
    ops = silo.roof_openings(roof, hatches, eq)
    fans = [o for o in ops if o["kind"] == "fan_vent"]
    f, v = roof["fans"], roof["vents"]
    rn = v["hole_d_m"] / 2
    rows = {k: [] for k in ("dia", "gap", "under", "grille", "power")}
    info = {k: [] for k in rows}
    warn = []
    sheet, raf, rings = _roof_bvh()
    for o in fans:
        try:
            _, fan = silo.build_roof_vents([o], spec=roof, detail="lod", faults=faults, fan_dz=fan_dz)
        except ValueError as e:                                    # the impeller does not fit the casing
            rows["gap"].append(f"{o['id']}: {e}")
            continue
        cx, cy = o["x"], o["y"]
        imp = np.asarray(fan["impeller"][0], float).reshape(-1, 3)
        r_tip = float(np.hypot(imp[:, 0] - cx, imp[:, 1] - cy).max())
        d_tip = 2 * r_tip
        info["dia"].append(f"{o['id']} Ø{d_tip * 1000:.1f}")
        if abs(d_tip - f["impeller_d_m"]) > FAN_TOL_D or not FAN_D_RANGE[0] <= f["impeller_d_m"] <= FAN_D_RANGE[1]:
            rows["dia"].append(f"{o['id']} Ø{d_tip * 1000:.1f} vs SITE {f['impeller_d_m'] * 1000:.0f}, research {FAN_D_RANGE[0] * 1000:.0f}-{FAN_D_RANGE[1] * 1000:.0f}")
        cas = np.asarray(fan["casing"][0], float).reshape(-1, 3)
        rr = np.hypot(cas[:, 0] - cx, cas[:, 1] - cy)
        r_min = float(rr.min())
        ring = cas[np.abs(rr - r_min) < 1e-7]
        n_seg = max(3, len(np.unique(np.round(np.arctan2(ring[:, 1] - cy, ring[:, 0] - cx), 6))))
        gap = r_min * float(np.cos(np.pi / n_seg)) - r_tip
        info["gap"].append(f"{o['id']} {gap * 1000:.2f} mm")
        if gap <= FAN_GAP_MIN:
            rows["gap"].append(f"{o['id']} {gap * 1000:.2f} mm")
        if not FAN_GAP_BAND[0] <= gap <= FAN_GAP_BAND[1]:
            warn.append(f"{o['id']} gap {gap * 1000:.2f} mm outside {FAN_GAP_BAND[0] * 1000:.0f}-{FAN_GAP_BAND[1] * 1000:.0f} mm")
        # motor and bracket: under the roof sheet (axis underside) and clear of sheet, ribs, rafters, purlins (BVH)
        mb = c.merge_parts([fan["motor"], fan["bracket"]])
        z_top = float(np.asarray(mb[0], float)[:, 2].max())
        z_under = si.roof_underside_z(o["r"])
        hits = [n for n, t in (("roof sheet", sheet), ("rafters", raf), ("purlins", rings)) if t is not None and ca._bvh(mb).overlap(t)]
        info["under"].append(f"{o['id']} top {z_top:.3f} vs sheet underside {z_under:.3f}")
        if z_top > z_under or hits:
            rows["under"].append(f"{o['id']} top {z_top:.3f} > underside {z_under:.3f}" if z_top > z_under else f"{o['id']} touches {hits}")
        opn = open_fraction(fan["grille"], rn - 0.01)
        info["grille"].append(f"{o['id']} free {opn:.0%}")
        if opn < FAN_OPEN_FAIL:
            rows["grille"].append(f"{o['id']} free {opn:.0%}")
        elif opn < FAN_OPEN_WARN:
            warn.append(f"{o['id']} guard free {opn:.0%} < {FAN_OPEN_WARN:.0%}")
        dm = fan["dims"]
        info["power"].append(f"{o['id']} {f['kw']} kW frame {dm['motor_frame']} Ø{dm['motor_dia'] * 1000:.0f} housing {dm['motor_housing_len'] * 1000:.0f} mm")
        if (abs(f["kw"] - FAN_KW) > 1e-9 or dm["motor_frame"] != FAN_FRAME
                or abs(dm["motor_dia"] - f["motor_below_roof"]["d_m"]) > FAN_MOTOR_D_TOL * f["motor_below_roof"]["d_m"]
                or abs(dm["motor_housing_len"] - f["motor_below_roof"]["l_m"]) > FAN_MOTOR_L_TOL):
            rows["power"].append(f"{o['id']} {f['kw']} kW frame {dm['motor_frame']} Ø{dm['motor_dia'] * 1000:.0f} housing {dm['motor_housing_len'] * 1000:.0f} mm")
    out.append(("roof fan impeller Ø = SITE and inside the research range 350-450 mm (from vertices)", not rows["dia"],
                f"tolerance 5 mm; {info['dia']}; {rows['dia'] or 'ok'}"))
    out.append(("roof fan tip gap to the casing throat > 0.5 mm (no touching)", not rows["gap"], f"{info['gap']}; {rows['gap'] or 'ok'}"))
    out.append(("roof fan motor under the roof and clear of sheet, ribs, rafters, purlins (BVH)", not rows["under"],
                f"{info['under']}; {rows['under'] or 'ok'}"))
    out.append((f"roof fan finger guard free area >= {FAN_OPEN_FAIL:.0%} (rays along the axis)", not rows["grille"], f"{info['grille']}; {rows['grille'] or 'ok'}"))
    out.append((f"roof fan {FAN_KW} kW = IEC {FAN_FRAME}, Ø and housing length as SITE motor_below_roof", not rows["power"],
                f"{info['power']}; {rows['power'] or 'ok'}"))
    out.append((f"roof fans in the model = SPEC {SPEC_ROOF_FANS}", len(fans) == SPEC_ROOF_FANS, f"{len(fans)} fan vents"))
    out.append(("roof fan tip gap / guard free area in the recommended band (WARN, EST)", True,
                ("WARN: " + "; ".join(warn)) if warn else "in the band"))
    if fans and not rows["gap"]:
        o = fans[0]
        h = fan["dims"]
        z_nose = silo.roof_fan_shoulder_z(o["r"], rn) + h["z_nose"]
        z_heap = silo.WALL_TOP + (si.R_IN - o["r"]) * math.tan(si.REPOSE)
        h_max = z_nose - FAN_BURY_CLEAR - (si.R_IN - o["r"]) * math.tan(si.REPOSE)
        out.append(("roof fan motor and the grain: FINDING, not a model error", True,
                    f"at fill to the wall top (peak 27 deg) the heap at r {o['r']} m stands {z_heap:.2f} m, the motor nose hangs at {z_nose:.2f} m: "
                    f"{'submerged by ' + format(z_heap - z_nose, '.2f') + ' m' if z_heap > z_nose else 'clear'}; to keep {FAN_BURY_CLEAR} m under the nose, "
                    f"the grain at the wall must stay below {h_max:.2f} m ({h_max / silo.WALL_TOP:.0%} of the wall height)"))
    return out


def door_checks(hatches):
    out = []
    flange = max(abs(s) for _, s in silo.OMEGA)
    stiff = np.degrees(silo.stiffener_angles()) % 360
    bad_st, bad_tier = [], []
    for d in hatches["wall_doors"]:
        half = math.degrees((d["w_m"] / 2 + d["frame_w_m"]) / silo.R)
        free = min(abs((d["angle_deg"] - s + 180) % 360 - 180) for s in stiff) - math.degrees(flange / silo.R)
        if half > free:
            bad_st.append(f"ring {d['ring']} at {d['angle_deg']}: needs {half:.2f} deg, free {free:.2f}")
        z0, z1 = (d["ring"] - 1) * silo.RING_H, d["ring"] * silo.RING_H
        if d["sill_z_m"] - d["frame_w_m"] < z0 + 0.05 or d["sill_z_m"] + d["h_m"] + d["frame_w_m"] > z1 - 0.05:
            bad_tier.append(f"ring {d['ring']} {d['sill_z_m']:.2f}..{d['sill_z_m'] + d['h_m']:.2f} vs tier {z0:.2f}..{z1:.2f}")
    out.append(("wall doors between stiffener flanges", not bad_st, f"{bad_st}"))
    out.append(("wall doors inside one sheet tier (no lap seam through the frame)", not bad_tier, f"{bad_tier}"))

    obs = _site_obstacles()
    hits, strip = [], []
    for s in SITE["silos"]:
        off = np.array([s["x"], s["y"], s["z"]])
        own = {f"{s['id']} wall"}
        for d in hatches["wall_doors"]:
            leaf, front, steps = silo.door_zones(d, HATCH_CLEAR)
            for name, data, sink in (("leaf", leaf, hits), ("steps", steps, hits), ("front strip", front, strip)):
                if data is None:
                    continue
                bvh = ca._bvh(data, off)
                sink.extend(f"{s['id']} ring {d['ring']} {name} x {k}" for k, b in obs.items() if k not in own and bvh.overlap(b))
    out.append(("door leaf zones and steps cut nothing (real meshes)", not hits, f"clashes: {sorted(set(hits))[:8]}"))
    out.append((f"{HATCH_CLEAR} m free strip in front of every door (WARN, judgment)", True,
                ("WARN: " + ", ".join(sorted(set(strip))[:8])) if strip else "free"))
    return out


_OBS = None


def _site_obstacles():
    """{name: BVH} in the site frame: tunnels, towers, dust bins (check_aspiration), aspiration ducts,
    and per silo a wall proxy, its aeration fans and its outside ladder."""
    global _OBS
    if _OBS is not None:
        return _OBS
    obs = ca.obstacles(SITE, *asp.riser_holes(SITE, tun))
    for sid, r in asp.routes(SITE, tower, tun).items():
        for k, dct in enumerate(r["ducts"]):
            obs[f"aspiration {sid} {dct['kind']} {k}"] = ca._bvh(c.merge_parts(asp.duct(dct["path"], dct["d_mm"])))
    fans = c.merge_parts(list(silo.build_fans()))
    ladder = silo.build_ladder()
    wall = c.cylinder(silo.R + 0.1, 0.0, silo.WALL_TOP, steps=96)
    for s in SITE["silos"]:
        off = np.array([s["x"], s["y"], s["z"]])
        obs[f"{s['id']} wall"] = ca._bvh(wall, off)
        obs[f"{s['id']} fans"] = ca._bvh(fans, off)
        obs[f"{s['id']} outside ladder"] = ca._bvh(ladder, off)
    _OBS = {k: v for k, v in obs.items() if v is not None}
    return _OBS


SITE = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
HATCH_CLEAR = SITE["silo_hatches"]["door_front_clear_m"]


def checks(site, rib_phase=None, fan_faults=None, fan_dz=0.0):
    return (roof_checks(site["silo_roof"], site["silo_hatches"], site["silo_equipment"], rib_phase) + door_checks(site["silo_hatches"])
            + fan_checks(site["silo_roof"], site["silo_hatches"], site["silo_equipment"], fan_faults, fan_dz))


def main():
    ok_all = True
    for name, ok, info in checks(SITE):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)

    def few_vents(s):
        s["silo_roof"]["vents"]["rings"][1]["n"] = 4

    def off_sector(s):
        s["silo_roof"]["vents"]["snap"] = "none"
        s["silo_roof"]["vents"]["rings"][0]["a0_deg"] = 2.25       # first vent on a rib line

    def hatch_on_ladder(s):
        s["silo_hatches"]["roof_access"]["angle_deg"] = silo.LADDER_ANGLE

    def door_on_stiffener(s):
        s["silo_hatches"]["wall_doors"][0]["angle_deg"] = 191.25

    def door_behind_ladder(s):
        s["silo_hatches"]["wall_doors"][0]["angle_deg"] = 265.5      # mid-sector, 0.43 m from the caged ladder axis

    def fan_tight(s):
        s["silo_roof"]["vents"]["hole_d_m"] = 0.4114           # impeller 0.400 + 5 mm tip gap no longer fits the 3 mm sheet casing

    def fan_big_motor(s):
        s["silo_roof"]["fans"]["kw"] = 1.1                       # IEC 90S instead of the 0.25 kW IEC 71

    def fan_small_impeller(s):
        s["silo_roof"]["fans"]["impeller_d_m"] = 0.30            # below the research range 350-450 mm

    variants = [("too few vents: 12 + 4", few_vents, None), ("vents not on sector centres", off_sector, None),
                ("roof hatch on the roof ladder", hatch_on_ladder, None), ("door on a stiffener", door_on_stiffener, None),
                ("door behind the outside caged ladder", door_behind_ladder, None), ("roof ribs half a sector off the stiffeners (old kit)", None, 0.0),
                ("roof fan impeller does not fit the casing throat", fan_tight, None),
                ("roof fan motor 1.1 kW (IEC 90S) instead of 0.25 kW", fan_big_motor, None),
                ("roof fan impeller Ø300, below the research range", fan_small_impeller, None),
                ("roof fan raised 0.25 m: motor above the roof underside", None, None, {"fan_dz": 0.25}),
                ("roof fan guard is a solid plate", None, None, {"fan_faults": {"grille": "plate"}})]
    for name, patch, phase, *extra in variants:
        bad = copy.deepcopy(SITE)
        if patch:
            patch(bad)
        failed = [n for n, ok, _ in checks(bad, phase, **(extra[0] if extra else {})) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
