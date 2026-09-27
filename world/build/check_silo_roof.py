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

Broken variants that must fail: too few vents, vents not on sector centres, roof hatch on the ladder,
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


def checks(site, rib_phase=None):
    return roof_checks(site["silo_roof"], site["silo_hatches"], site["silo_equipment"], rib_phase) + door_checks(site["silo_hatches"])


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

    variants = [("too few vents: 12 + 4", few_vents, None), ("vents not on sector centres", off_sector, None),
                ("roof hatch on the roof ladder", hatch_on_ladder, None), ("door on a stiffener", door_on_stiffener, None),
                ("door behind the outside caged ladder", door_behind_ladder, None), ("roof ribs half a sector off the stiffeners (old kit)", None, 0.0)]
    for name, patch, phase in variants:
        bad = copy.deepcopy(SITE)
        if patch:
            patch(bad)
        failed = [n for n, ok, _ in checks(bad, phase) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
