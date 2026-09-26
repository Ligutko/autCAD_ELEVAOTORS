"""K3 check: silo-top galleries and bridges against the drawing and the specification.

Per chain conveyor: length between pulley axes vs the spec (PDF p.8-p.12), slope, casing inside
its gallery or bridge. Per distribution spout: the end lands on its receiving conveyor. Bridge
conveyors and distribution spouts must not run through a tower ladder (the ladder is a judgment:
the process drawing has no tower stairs).

Run:
    blender --background --python world/build/check_gallery.py
Exit code 1 when any case fails.
"""

import copy
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kit import gallery as gal  # noqa: E402
from kit import noria_tower as tower  # noqa: E402

# spec lengths between drive and tail axes (p.8 note 1). T7 and T14: tag not in the OCR text,
# taken by the order of the lines (T7 before T8 on p.8/p.9, T14 after T13 on p.11)
SPEC_LENGTH = {"T7": 30.5, "T8": 39.5, "T10": 29.0, "T11": 26.0, "T12": 37.0, "T14": 23.5, "T15": 39.0}
LENGTH_TOL = 0.10
RECEIVER_Z = (-0.05, 0.35)      # spout end vs casing top: from flush to a 0.35 m inlet hopper


def conveyor_checks(site):
    out = []
    for cid, spec_len in SPEC_LENGTH.items():
        tail, head, _, _ = gal.conveyor_axis(site, cid)
        length = float(np.linalg.norm(head - tail))
        slope = gal.slope_deg(tail, head)
        out.append((f"{cid} length between pulleys = spec", abs(length - spec_len) <= LENGTH_TOL,
                    f"{length:.2f} m vs spec {spec_len} m, slope {slope:+.1f} deg"))
    return out


def _on_receiver(site, cid, p):
    tail, head, w, h = gal.conveyor_axis(site, cid)
    d = head - tail
    t = float(np.clip(np.dot(p - tail, d) / np.dot(d, d), -0.05, 1.05))
    axis = tail + d * t
    lateral = float(np.linalg.norm((p - axis)[:2]))
    dz = p[2] - (axis[2] + h / 2)
    return lateral <= w / 2 + 0.05 and RECEIVER_Z[0] <= dz <= RECEIVER_Z[1] and -0.02 <= t <= 1.02, lateral, dz, t


def spout_checks(site):
    out = []
    for d in site["distribution"]:
        for sp in d["spouts"]:
            cid = sp["to"].split()[0]
            if "head" in sp["to"]:
                continue
            ok, lateral, dz, t = _on_receiver(site, cid, np.array(sp["path"][-1], float))
            src = sp.get("from_conveyor", "head " + d["tower"])
            out.append((f"{d['tower']} spout {src} -> {cid} lands on the conveyor", ok,
                        f"lateral {lateral:.3f} m, above casing top {dz:+.3f} m, along {t:.2f}"))
    return out


def fit_checks(site):
    out = []
    g = site["silo_top_galleries"]
    ya, yb = g["y_rel_row"]
    w = g["conveyor"]["casing_w"]
    out.append(("silo-top conveyor inside the gallery", ya <= -w / 2 and w / 2 <= yb, f"casing ±{w / 2:.3f}, gallery {ya}..{yb}"))
    for b in site["bridges"]:
        for cv in b["conveyors"]:
            half = cv.get("casing_w", 0.40) / 2
            out.append((f"{cv['id']} inside bridge {b['id']}", b["x"][0] <= cv["x"] - half and cv["x"] + half <= b["x"][1],
                        f"x {cv['x']} ±{half}, bridge {b['x']}"))
    for spec in site["noria_towers"]:                        # bridge conveyors and spouts vs the ladder
        lad = tower.access_rect(spec)
        sx0, sy0, sx1, sy1 = lad[0] + spec["x"], lad[1] + spec["y"], lad[2] + spec["x"], lad[3] + spec["y"]
        hits = []
        for b in site["bridges"]:
            for cv in b["conveyors"]:
                tail, head, wc, _ = gal.conveyor_axis(site, cv["id"])
                y_lo, y_hi = sorted((tail[1], head[1]))
                inside_y = y_lo - gal.CONV_END < sy1 and y_hi + gal.CONV_END > sy0
                inside_x = cv["x"] + wc / 2 > sx0 and cv["x"] - wc / 2 < sx1
                if inside_y and inside_x:
                    hits.append(cv["id"])
        g = site["silo_top_galleries"]                   # silo-top conveyors pass through the towers too
        for line in g["lines"]:
            xs = sorted((line["tail_x"], line["head_x"]))
            half = g["conveyor"]["casing_w"] / 2
            if (xs[0] - gal.CONV_END < sx1 and xs[1] + gal.CONV_END > sx0
                    and line["row_y"] + half > sy0 and line["row_y"] - half < sy1):
                hits.append(line["id"])
        for d in site["distribution"]:
            for sp in d["spouts"]:
                pts = np.array(sp["path"], float)
                for a, b in zip(pts, pts[1:]):
                    for k in np.linspace(0, 1, 21):
                        q = a + (b - a) * k
                        if sx0 - 0.15 < q[0] < sx1 + 0.15 and sy0 - 0.15 < q[1] < sy1 + 0.15:
                            hits.append("spout->" + sp["to"])
                            break
        out.append((f"{spec['id']} ladder clear of conveyors and spouts", not hits,
                    f"ladder x {sx0:.2f}..{sx1:.2f}, y {sy0:.2f}..{sy1:.2f}; through it: {sorted(set(hits))}"))
    return out


def main():
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    ok_all = True
    for name, ok, info in conveyor_checks(site) + spout_checks(site) + fit_checks(site):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)
    bad = copy.deepcopy(site)
    bad["silo_top_galleries"]["lines"][0]["head_x"] -= 0.6
    failed = [n for n, ok, _ in conveyor_checks(bad) if not ok]
    ok_all &= bool(failed)
    print(f"{'PASS' if failed else 'FAIL'}  T8 head moved 0.6 m must be rejected: failed {failed}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
