"""Tunnel K4 check against the drawing and the specification (SITE.json, research/tunnel_k4.md).

Geometry only, no rendering. Per tunnel: conveyor length between pulley axes equals the spec,
casing stands in the tunnel on its supports and reaches into the pit, gate stacks land on the
casing, both walkways stay open, 14 loading inlets (2 x □400 + 12 x □350) sit under the silo
openings of the K5 kit, the discharge spout reaches the boot inlet steep enough for grain,
the tunnel section fits the pit wall. Two broken variants must be rejected.

Run:
    blender --background --python world/build/check_tunnel.py
Exit code 1 when any case fails.
"""

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import noria_tower as tower  # noqa: E402
from kit import silo_interior as si  # noqa: E402
from kit import tunnel as tun  # noqa: E402

MIN_WALKWAY = 0.5      # EST: hands-on access on both sides of the casing
LENGTH_TOL = 0.05


def checks(site, t):
    cv = t["conveyor"]
    spec = next(s for s in site["noria_towers"] if s["id"] == t["tower"])
    x0, y0, x1, y1, fz, cz = tun.inner_box(site, t)
    px0, py0, px1, py1 = tower.pit_inner(spec)
    px0, px1, py0, py1 = px0 + spec["x"], px1 + spec["x"], py0 + spec["y"], py1 + spec["y"]
    inlet = tun.boot_inlet(site, t)
    _, m = tun.build_conveyor(site, t, inlet)
    gates = tun._gate_positions(site, t)
    silos = {s["id"]: s for s in site["silos"]}
    k5 = sorted(silos[sid]["x"] + off for sid in cv["silos"] for off in si.GATE_OFFSETS)
    far_end = t["end_x"]
    head_end = cv["casing_x"][1] if far_end < 0 else cv["casing_x"][0]
    tail_end = cv["casing_x"][0] if far_end < 0 else cv["casing_x"][1]
    z0, z1 = cv["casing_z"]
    sizes = sorted(round(s * 1000) for _, s in gates)
    sp = m["spout_start"]
    return [
        ("length between pulleys = spec", abs(m["length_between_pulleys_m"] - cv["spec_length_m"]) <= LENGTH_TOL,
         f"{m['length_between_pulleys_m']} m vs spec {cv['spec_length_m']} m"),
        ("tail end inside the tunnel", abs(tail_end - far_end) >= 0.3 and min(x0, x1) <= tail_end <= max(x0, x1),
         f"casing tail {tail_end:+.3f}, tunnel end {far_end:+.3f}"),
        ("head end reaches into the pit", px0 <= head_end <= px1, f"casing head {head_end:+.3f}, pit x {px0:+.3f}..{px1:+.3f}"),
        ("casing on supports above the floor", z0 - fz >= 0.25, f"casing bottom {z0:+.2f}, floor {fz:+.2f}"),
        ("gate spouts land on the casing", abs(site["silo_gates"]["stack_z"]["spout_bottom"] - z1) <= 0.02,
         f"spout bottom {site['silo_gates']['stack_z']['spout_bottom']:+.2f}, casing top {z1:+.2f}"),
        ("walkways on both sides", min(m["walkways_m"]) >= MIN_WALKWAY if "walkways_m" in m else
         min((t["row_y"] - cv["width"] / 2) - y0, y1 - (t["row_y"] + cv["width"] / 2)) >= MIN_WALKWAY,
         f"south {(t['row_y'] - cv['width'] / 2) - y0:.2f} m, north {y1 - (t['row_y'] + cv['width'] / 2):.2f} m"),
        ("14 inlets: 2 x 400 + 12 x 350", sizes == [350] * 12 + [400] * 2, f"{sizes.count(400)} x 400, {sizes.count(350)} x 350"),
        ("inlets under the K5 silo openings", [round(x, 3) for x, _ in gates] == [round(x, 3) for x in k5],
         f"max offset {max(abs(a - b) for (a, _), b in zip(gates, k5)):.3f} m"),
        ("inlets within the casing", all(cv["casing_x"][0] < x < cv["casing_x"][1] for x, _ in gates), ""),
        ("discharge spout reaches the boot inlet", sum((a - b) ** 2 for a, b in zip(m["spout_end"], inlet)) ** 0.5 < 0.01,
         f"inlet {[round(v, 3) for v in inlet]}"),
        (f"spout steep enough for grain (>= {tun.MIN_SPOUT_DEG:.0f} deg)", m["spout_angle_deg"] >= tun.MIN_SPOUT_DEG,
         f"{m['spout_angle_deg']} deg"),
        ("spout starts over the pit", px0 <= sp[0] <= px1 and py0 <= sp[1] <= py1, f"spout start {sp}"),
        ("tunnel section fits the pit wall", py0 - 0.05 <= y0 and y1 <= py1 + 0.05,
         f"tunnel y {y0:.3f}..{y1:.3f}, pit y {py0:.3f}..{py1:.3f}"),
    ]


def main():
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    ok_all = True
    for t in site["tunnels"]:
        for name, ok, info in checks(site, t):
            ok_all &= ok
            print(f"{'PASS' if ok else 'FAIL'}  {t['id']} {name}: {info}", flush=True)

    bad_len = copy.deepcopy(site)
    bad_len["tunnels"][0]["conveyor"]["drive_x"] += 0.5
    bad_gates = copy.deepcopy(site)
    bad_gates["silo_gates"]["offsets_along_row"] = [-9.75, -6.5, -3.25, 0.0, 2.75, 5.5, 8.25]
    for label, s in (("drive pulley moved 0.5 m", bad_len), ("old 2750 gate chain", bad_gates)):
        failed = [n for n, ok, _ in checks(s, s["tunnels"][0]) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  {label} must be rejected: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
