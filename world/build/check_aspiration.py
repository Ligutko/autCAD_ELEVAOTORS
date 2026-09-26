"""Aspiration (block E) check. The dust bins are drawn; units and duct routes are a judgment,
so this check holds them to the norms and to the geometry already in the model.

Per system: flange count vs the spec (15 per tunnel belt conveyor), design air from the norms,
duct speeds, ducts inside the tunnels and clear of lamps, cable tray and gate stacks, the riser
clear of gate sleeves and silo foundations. Dust bins clear of silos and towers.
A riser moved onto a silo must be rejected.

Run:
    blender --background --python world/build/check_aspiration.py
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

from kit import aspiration as asp  # noqa: E402
from kit import noria_tower as tower  # noqa: E402
from kit import tunnel as tun  # noqa: E402

SILO_FOUNDATION_R = 11.6        # silo_msvu220 FOUND_R
SPEC_FLANGES_PER_TUNNEL = 15    # PDF p.9, p.11, p.12


def _slope(a, b):
    run = np.linalg.norm((np.array(b) - np.array(a))[:2])
    return 90.0 if run < 1e-6 else math.degrees(math.atan2(abs(b[2] - a[2]), run))


def checks(site):
    out = []
    routes = asp.routes(site, tower, tun)
    tunnels = {t["id"]: t for t in site["tunnels"]}
    for sysd in site["aspiration"]["systems"]:
        r = routes[sysd["id"]]
        out.append((f"{sysd['id']} flanges = spec", r["flanges"] == SPEC_FLANGES_PER_TUNNEL * len(sysd["tunnels"]),
                    f"{r['flanges']} for {sysd['tunnels']}"))
        worst = []
        for dct in r["ducts"]:
            v = asp.speed_ms(dct["air_m3h"], dct["d_mm"])
            for a, b in zip(dct["path"], dct["path"][1:]):
                vmin = asp.V_MIN_VERTICAL if _slope(a, b) >= 60 else asp.V_MIN_SLOPED
                if not vmin <= v <= asp.V_MAX:
                    worst.append(f"{dct['kind']} Ø{dct['d_mm']} {v:.1f} m/s")
        out.append((f"{sysd['id']} duct speeds within the norms", not worst,
                    f"air {r['air_m3h']:.0f} m3/h, main Ø{r['d_main']} {asp.speed_ms(r['air_m3h'], r['d_main']):.1f} m/s, "
                    f"branch Ø{r['d_branch']}, boot Ø{r['d_boot']}; out of range: {sorted(set(worst))}"))
        for tid in sysd["tunnels"]:
            t = tunnels[tid]
            x0, y0, x1, y1, fz, cz = tun.inner_box(site, t)
            yc = t["row_y"] + sysd["collector_y_rel"][tid]
            rad = r["d_main"] / 2000
            zc = site["aspiration"]["collector_z"]
            _, _, lamps = tun.build_services(site, t)
            lamp_y = lamps[0][1]
            wide = y1 if lamp_y > t["row_y"] else y0
            tray_y = wide - 0.12 if wide == y1 else wide + 0.12
            stack_half = max(s for _, s in tun._gate_positions(site, t)) / 2 + 0.06 + 0.25   # body + motor reach
            gaps = {"ceiling": cz - (zc + rad), "wall": min(yc - rad - y0, y1 - (yc + rad)),
                    "lamps": abs(yc - lamp_y) - rad - 0.07, "tray": abs(yc - tray_y) - rad - 0.10,
                    "gate stacks": abs(yc - t["row_y"]) - rad - stack_half}
            out.append((f"{sysd['id']} collector in {tid} clear", min(gaps.values()) >= 0.02,
                        ", ".join(f"{k} {v:.3f}" for k, v in gaps.items())))
        if not sysd["riser_in_pit"]:
            rx, ry = sysd["riser_xy"]
            t = tunnels[sysd["tunnels"][0]]
            sleeve = min(abs(rx - x) - s / 2 for x, s in tun._gate_positions(site, t))
            silo = min(math.hypot(rx - s["x"], ry - s["y"]) for s in site["silos"]) - SILO_FOUNDATION_R
            out.append((f"{sysd['id']} riser clear of sleeves and silo foundations", sleeve >= 0.5 and silo >= 0.2,
                        f"to the nearest sleeve {sleeve:.2f} m, to a silo foundation {silo:.2f} m"))
            main = next(d for d in r["ducts"] if d["kind"] == "main")
            foot = min(math.hypot(p[0] - s["x"], p[1] - s["y"]) for p in main["path"] for s in site["silos"])
            out.append((f"{sysd['id']} main duct clear of the silos", foot - SILO_FOUNDATION_R >= 0.2,
                        f"closest point {foot - SILO_FOUNDATION_R:.2f} m outside a foundation"))
    for b in site["aspiration"]["dust_bins"]:
        cx, cy = b["center"]
        fx, fy = b["frame"]
        silo = min(math.hypot(max(abs(cx - s["x"]) - fx / 2, 0), max(abs(cy - s["y"]) - fy / 2, 0))
                   for s in site["silos"]) - SILO_FOUNDATION_R
        towers = min(max(abs(cx - s["x"]) - fx / 2 - s["size"][0] / 2, abs(cy - s["y"]) - fy / 2 - s["size"][1] / 2)
                     for s in site["noria_towers"])
        out.append((f"dust bin {b['id']} clear of silos and towers", silo >= 0.2 and towers >= 0.2,
                    f"silo foundation {silo:.2f} m, tower {towers:.2f} m"))
    return out


def main():
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    ok_all = True
    for name, ok, info in checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)
    bad = copy.deepcopy(site)
    bad["aspiration"]["systems"][0]["riser_xy"][0] = -38.5
    failed = [n for n, ok, _ in checks(bad) if not ok]
    ok_all &= bool(failed)
    print(f"{'PASS' if failed else 'FAIL'}  riser moved onto silo S1 must be rejected: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
