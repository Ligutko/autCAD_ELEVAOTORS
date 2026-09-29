"""Control center, stage 1: the geometry numbers the simulator needs, taken from the kits the model is built from.

The simulator is plain Python (no bpy), the kits import bpy, so the numbers are derived once here and written to
`world/sim/geometry.json`. `check_live.py` re-derives them in Blender and fails if the file no longer matches the
model (a kit changed, the file was edited by hand).

Run:
    blender --background --python world/sim/derive_geometry.py            # writes world/sim/geometry.json
    blender --background --python world/sim/derive_geometry.py -- --print # prints, writes nothing

Per mover:
  conveyor  run_m: tail -> head of the casing centreline (routes.conveyor_axis, drying.conv_axis for T3 / T5,
            SITE receiving x span for the plan conveyors T2 / T4 / T6, their z is 0.0 on the drawing: basis judgment).
  noria     lift_m: boot axis -> head axis (tower norias: noria_n100.BeltPath heights through routes.tower_noria_points;
            H1-H4 boxes: boot centre -> head centre, receiving.noria_boxes).
Silo: inner radius, wall height, repose angle, floor z (silo_interior / silo_msvu220), the volume of the grain heap
at fill = 1 as build_grain draws it (cylinder to the wall top + repose cone), compared with the spec volume.
"""

import json
import math
import sys
from pathlib import Path

import bpy  # noqa: F401,I001  the kits need bpy loaded first

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import drying as dr  # noqa: E402
from kit import process as pr  # noqa: E402
from kit import routes as R  # noqa: E402
from kit import silo_interior as si  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402

OUT = ROOT / "sim" / "geometry.json"


def _r(v, n=3):
    return round(float(v), n)


def derive(site=None):
    g = pr.Graph(site)
    site = g.site
    movers = {}
    for n, v in sorted(g.nodes.items()):
        if v["kind"] not in pr.MOVERS:
            continue
        if v["kind"] == "noria":
            if any(t["id"] == n for t in site["noria_towers"]):
                _, _, _, meta = R.tower_noria_points(site, n)
                movers[n] = {"kind": "noria", "lift_m": _r(meta["z_head"] - meta["z_boot"]),
                             "z_boot": _r(meta["z_boot"]), "z_head": _r(meta["z_head"]),
                             "basis": "derived", "src": "routes.tower_noria_points (noria_n100.BeltPath)"}
            else:
                pts, _, _ = R.receiving_noria_points(site, n)
                movers[n] = {"kind": "noria", "lift_m": _r(pts[1][2] - pts[0][2]),
                             "z_boot": _r(pts[0][2]), "z_head": _r(pts[1][2]),
                             "basis": "derived", "src": "routes.receiving_noria_points (receiving.noria_boxes centres)"}
            continue
        if n in ("T3", "T5"):
            a, b = dr.conv_axis(n, site)
            src, basis = "drying.conv_axis (SITE designed.drying_geom)", "designed"
        else:
            try:
                a, b, _, _ = R.conveyor_axis(site, n)
                src, basis = "routes.conveyor_axis", "derived"
            except KeyError:
                cv = next(c for c in site["receiving"]["conveyors"] if c["id"] == n)
                xa, xb = cv["x"]
                a, b = (xa, cv["y"], cv["z"]), (xb, cv["y"], cv["z"])
                src, basis = "SITE receiving.conveyors x span (plan conveyor, z not on the drawing)", "judgment"
        movers[n] = {"kind": v["kind"], "run_m": _r(math.dist(a, b)), "basis": basis, "src": src}

    r_in, h_wall, rep = si.R_IN, silo.WALL_TOP, si.REPOSE
    cone = math.pi * r_in ** 2 * r_in * math.tan(rep) / 3
    heap_full = math.pi * r_in ** 2 * h_wall + cone
    spec_v = next(n["volume_m3"] for n in site["process"]["nodes"] if n["id"] == "S1")
    silo_geom = {
        "r_in_m": _r(r_in, 4), "wall_top_m": _r(h_wall, 4), "repose_deg": _r(math.degrees(rep), 2),
        "floor_z": _r(silo.FLOOR_Z), "cone_m3": _r(cone, 1), "heap_full_m3": _r(heap_full, 1),
        "spec_volume_m3": spec_v, "heap_vs_spec_pct": _r(100 * (heap_full / spec_v - 1), 2),
        "src": "silo_interior.R_IN / REPOSE (STD 25-28 deg), silo_msvu220.WALL_TOP (LUB 13 x 1.152), "
               "heap as silo_interior.build_grain draws it",
    }
    return {"generated_by": "world/sim/derive_geometry.py", "movers": movers, "silo": silo_geom}


def main():
    data = derive()
    text = json.dumps(data, ensure_ascii=False, indent=1)
    if "--print" in sys.argv:
        print(text)
        return
    OUT.write_text(text + "\n", encoding="utf-8")
    print("wrote", OUT, len(data["movers"]), "movers", flush=True)


if __name__ == "__main__":
    main()
