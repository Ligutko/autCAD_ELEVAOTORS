"""Flow distribution check: noria head outlet vs the drawing, splitters, spout slopes, gate counts.

The head outlet in the model is built from the kit (noria axis, rotation, boot and tube heights,
outlet offsets), so its match with the drawn outlet checks that whole chain. Spout ends on the
silo-top and bridge conveyors are reported only: the galleries (K3) are not aligned to the drawing yet.

Run:
    blender --background --python world/build/check_distribution.py
Exit code 1 when any case fails.
"""

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import distribution as dist  # noqa: E402
from kit import noria_tower as tower  # noqa: E402

OUTLET_TOL = 0.10
# spec rail gates ТЗА-300 near each head: stage 2 (p.11) lists 5 and all are at H6; stage 1 (p.9)
# lists 10, of which the drawing shows 3 at H5 (the rest are at the receiving tower, not modelled)
DRAWN_GATES = {"H5": 3, "H6": 5}


def checks(site, d):
    spec = next(s for s in site["noria_towers"] if s["id"] == d["tower"])
    _, _, _, anchors = tower.build_noria(spec)
    outlet = tower.noria_frame(spec)(anchors["outlet"]) + [spec["x"], spec["y"], 0.0]
    drawn = np.array(d["head_outlet"])
    first = np.array(d["splitters"][0]["at"])
    branches = [np.array(b) for s in d["splitters"] for b in s["branches"]]
    slopes = [(sp["to"], dist.slope_deg(a, b)) for sp in d["spouts"] for a, b in dist.segments(sp["path"])
              if np.linalg.norm((b - a)[:2]) > 0.05]
    worst = min(slopes, key=lambda s: s[1])
    orphan = [sp["to"] for sp in d["spouts"] if "from_conveyor" not in sp and "head" not in sp["to"]
              and min(np.linalg.norm(np.array(sp["path"][0]) - b) for b in branches) > 0.01]
    gates = sum(len(s["branches"]) for s in d["splitters"])
    return [
        ("head outlet matches the drawing", np.linalg.norm(outlet - drawn) <= OUTLET_TOL,
         f"model {np.round(outlet, 3).tolist()}, drawing {drawn.tolist()}, off {np.linalg.norm(outlet - drawn):.3f} m"),
        ("first splitter right under the outlet", np.linalg.norm((first - outlet)[:2]) <= OUTLET_TOL and 0 <= outlet[2] - first[2] <= 0.6,
         f"plan off {np.linalg.norm((first - outlet)[:2]):.3f} m, drop {outlet[2] - first[2]:.3f} m"),
        (f"all spout slopes >= {dist.MIN_SLOPE_DEG:.0f} deg", worst[1] >= dist.MIN_SLOPE_DEG,
         f"flattest {worst[1]:.1f} deg (to {worst[0]}); all: " + ", ".join(f"{a} {s:.0f}" for a, s in slopes)),
        ("head spouts start on a splitter branch", not orphan, f"orphans {orphan}"),
        ("gates as drawn / spec", gates == DRAWN_GATES[d["tower"]], f"{gates} gates, expected {DRAWN_GATES[d['tower']]}"),
    ]


def main():
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    ok_all = True
    for d in site["distribution"]:
        for name, ok, info in checks(site, d):
            ok_all &= ok
            print(f"{'PASS' if ok else 'FAIL'}  {d['tower']} {name}: {info}", flush=True)
        for sp in d["spouts"]:
            print(f"INFO  {d['tower']} spout to {sp['to']} ends at {sp['path'][-1]} (receiver not checked until K3)", flush=True)
    bad = copy.deepcopy(site)
    bad["distribution"][0]["spouts"][1]["path"][-1][2] = 28.4        # T11 spout made ~30 deg
    failed = [n for n, ok, _ in checks(bad, bad["distribution"][0]) if not ok]
    ok_all &= bool(failed)
    print(f"{'PASS' if failed else 'FAIL'}  flat spout must be rejected: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
