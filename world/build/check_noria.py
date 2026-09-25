"""Noria height check: the spec tubes must fit both towers, swapped tubes must be rejected.

The pit and top-platform elevations come from the drawing sections, the tube lengths from the
specification (PDF p.8, p.10). The elevator is stacked bottom-up from the pit, so the head landing
on the top platform is an independent cross-check of the two sources.

Run:
    blender --background --python world/build/check_noria.py
Exit code 1 when any case fails.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import noria_n100 as nn  # noqa: E402


def run(tower, tube_mm, expect_ok):
    try:
        _, _, m, _ = nn.build(tower["top_z"], tower["pit_z"], tube_mm / 1000, tower["noria_model"], tower["feed"])
        ok = True
        info = (f"tube {m['leg_length_m']} m, head axis +{m['head_pulley_z_m']}, "
                f"head base {m['head_base_above_top_platform_m']:+.3f} m vs top +{tower['top_z']}")
    except ValueError as e:
        ok, info = False, str(e)
    passed = ok == expect_ok
    print(f"{'PASS' if passed else 'FAIL'}  {tower['id']} tube {tube_mm} "
          f"({'must fit' if expect_ok else 'must be rejected'}): {info}", flush=True)
    return passed


def main():
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    towers = site["noria_towers"]
    results = [run(t, t["tube_mm"], True) for t in towers]
    tubes = [t["tube_mm"] for t in towers]
    for t, other in zip(towers, tubes[::-1]):
        if other != t["tube_mm"]:
            results.append(run(t, other, False))
    print("RESULT", "ALL PASS" if all(results) else f"{results.count(False)} FAILED", flush=True)
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
