"""Tower + noria + pit placement check against the drawing (SITE.json, research/tunnel_k4.md).

Geometry only, no rendering. For every tower: the noria axis lands on `noria_axis`, legs run
along the drawn direction, legs and boot sit inside the pit and under the deck, the boot inlet
faces the silo row (tunnel side), legs clear the ladder and the columns, ladder flights are at most
6 m (ISO 14122-4), the pit cover spans the tower. A noria pushed onto the ladder must be rejected.

Run:
    blender --background --python world/build/check_tower.py
Exit code 1 when any case fails.
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import noria_n100 as nn  # noqa: E402
from kit import noria_tower as tower  # noqa: E402

CLEAR = 0.05          # minimum gap to walls, stairs, columns (m)
COLUMN_HALF = 0.10    # SHS 200 column


def checks(spec, row_y):
    f = tower.noria_frame(spec)
    ox, oy = spec["x"], spec["y"]
    _, _, m, anchors = tower.build_noria(spec)
    legs = [f((xc, nn.BELT_Y, 0.0)) for xc in nn.LEG_CENTRES_X]
    axis = (legs[0] + legs[1]) / 2 + (ox, oy, 0)
    feet = tower.leg_footprints(spec)
    px0, py0, px1, py1 = tower.pit_inner(spec)
    (b0, b1) = anchors["boot_box"]
    boot = f([b0, b1])
    bx0, by0, bx1, by1 = boot[:, 0].min(), boot[:, 1].min(), boot[:, 0].max(), boot[:, 1].max()
    boot_top = boot[:, 2].max()
    deck_bottom = spec["pit"]["deck_top_z"] - spec["pit"]["deck_t"]
    inlet = f(anchors["inlet_mouth"]) + (ox, oy, 0)
    drive = f((nn.CX, nn.BELT_Y - 0.62, 0.0))
    lad = tower.access_rect(spec)
    flights = tower.ladder_flights(sorted(spec["levels_z"]), spec["top_z"], spec["pit"]["cover_top_z"])[0]
    hx, hy = spec["size"][0] / 2, spec["size"][1] / 2
    t = spec["pit"]["wall_t"]
    err = max(abs(axis[0] - spec["noria_axis"][0]), abs(axis[1] - spec["noria_axis"][1]))
    along_y = abs(legs[0][0] - legs[1][0]) < 1e-6 and abs(legs[0][1] - legs[1][1]) > 0.1
    gap_pit = min(min(r[0] - px0, r[1] - py0, px1 - r[2], py1 - r[3]) for r in feet)
    gap_boot = min(bx0 - px0, by0 - py0, px1 - bx1, py1 - by1)
    gap_ladder = min(max(lad[0] - r[2], r[0] - lad[2], lad[1] - r[3], r[1] - lad[3]) for r in feet)
    gap_col = min(min(hx - COLUMN_HALF - abs(v) for v in (r[0], r[2])) for r in feet)
    return [
        ("noria axis on the drawing", err <= 0.001, f"error {err * 1000:.1f} mm"),
        (f"legs along {spec['legs_along']}", along_y == (spec["legs_along"] == "Y"),
         f"legs at ({legs[0][0]:.3f}, {legs[0][1]:.3f}) and ({legs[1][0]:.3f}, {legs[1][1]:.3f})"),
        ("legs inside the pit", gap_pit >= CLEAR, f"min gap {gap_pit:.3f} m"),
        ("boot inside the pit", gap_boot >= CLEAR, f"min gap {gap_boot:.3f} m"),
        ("boot under the deck", boot_top <= deck_bottom, f"boot top {boot_top:+.3f}, deck bottom {deck_bottom:+.3f}"),
        ("inlet faces the silo row", abs(inlet[1] - row_y) < abs(spec["noria_axis"][1] - row_y),
         f"inlet y {inlet[1]:.3f}, axis y {spec['noria_axis'][1]:.3f}, row y {row_y}"),
        ("legs clear the ladder", gap_ladder >= CLEAR, f"gap {gap_ladder:.3f} m"),
        ("ladder inside the tower grid", -hx + COLUMN_HALF <= lad[0] and lad[2] <= hx - COLUMN_HALF
         and -hy + COLUMN_HALF <= lad[1] and lad[3] <= hy - COLUMN_HALF, f"ladder {[round(v, 3) for v in lad]}"),
        ("ladder flights <= 6 m (ISO 14122-4)", max(b - a for a, b in flights) <= tower.MAX_FLIGHT + 1e-6,
         f"{len(flights)} flights, longest {max(b - a for a, b in flights):.2f} m"),
        ("legs clear the columns", gap_col >= CLEAR, f"gap {gap_col:.3f} m"),
        ("pit cover spans the tower", min(-hx - (px0 - t), (px1 + t) - hx, -hy - (py0 - t), (py1 + t) - hy) >= 0,
         f"pit outer x {px0 - t:.2f}..{px1 + t:.2f}, y {py0 - t:.2f}..{py1 + t:.2f}; grid ±{hx:.2f}, ±{hy:.2f}"),
        ("head on the top platform", True, f"head base {m['head_base_above_top_platform_m']:+.3f} m"),
        ("head discharges as drawn", f.discharge_towards == spec["head_discharge_towards"],
         f"model {f.discharge_towards}, drawing {spec['head_discharge_towards']}"),
        ("drive on the drawn side", (drive[0] - axis[0] + ox > 0) == (spec["drive_towards"] == "+X"),
         f"drive x {drive[0] + ox:+.3f}, axis x {axis[0]:+.3f}, drawing {spec['drive_towards']}"),
        ("capacity >= 95 t/h (spec 100 real)", m["capacity_t_h_model"] >= 95,
         f"{m['capacity_t_h_model']} t/h, {m['model']}, feed {m['feed']}"),
        ("bucket volume within 10 % of the table", abs(m["bucket_volume_l_model"] / m["bucket_volume_l_table"] - 1) <= 0.10,
         f"{m['bucket_volume_l_model']} l vs table {m['bucket_volume_l_table']} l"),
    ]


def main():
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    rows = sorted({s["y"] for s in site["silos"]})
    ok_all = True
    for spec in site["noria_towers"]:
        row_y = min(rows, key=lambda r: abs(r - spec["y"]))
        for name, ok, info in checks(spec, row_y):
            ok_all &= ok
            print(f"{'PASS' if ok else 'FAIL'}  {spec['id']} {name}: {info}", flush=True)
    bad = copy.deepcopy(site["noria_towers"][0])
    bad["noria_axis"][0] = bad["access"]["x"]
    bad["id"] += "-noria-on-the-ladder"
    failed = [n for n, ok, _ in checks(bad, min(rows, key=lambda r: abs(r - bad["y"]))) if not ok]
    rejected = bool(failed)
    ok_all &= rejected
    print(f"{'PASS' if rejected else 'FAIL'}  {bad['id']} must be rejected: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
