"""Measure the grain-packet motion on the PIXELS of the screenshots of build/live_probe.py (plain Python, not Blender).

    python world/build/live_motion_shots.py <probe_dir> [--selftest]

live_probe.py writes, per camera, two screenshots ~0.3 s apart (motion_<scenario>_<cam>_a/b.png) and gui_probe.json with
the overlay time of each frame and the projected image pixels of every moving path (one per 5 cm of arc). Here the
packets (core colour of live_motion.LOOK) are read along that pixel path in both frames; the shift of the pattern between
the frames, found by correlating the two profiles over one packet spacing, must be v * dt for the speed v of the mover
(the source speed: 2.87 / 2.40 m/s norias, 2.4 belts, 0.675 chains, 2.0 EST edges) within TOL_M.
--selftest feeds broken variants that must fail: the same frame twice (nothing moved), speeds halved, speeds from the
wrong mover. The trip proof (`--at` run): the pixel coverage of H5's path by packets must be high while H5 runs and
~zero once it has tripped.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

TOL_M = 0.15            # the shift may be off by this much along the path (frame time is known to ~10 ms = 3 cm at 2.87 m/s)
COLOR_TOL = 28          # per channel, against the core colour of the overlay
MIN_ARC_M = 8.0         # paths shorter than ~3 packet spacings say little about a shift (few packets, foreshortened)
MIN_HITS = 30           # samples of the path on packet pixels in frame A (1.5 m of packets), else the path is not seen there


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.int16)


def profile(img, px, core, frame=None):
    """(valid, hit) per sample: valid = the pixel is inside the image and inside the camera frame (outside it the viewport
    darkens the picture: passepartout); hit = a pixel of the packet colour within +-1 px."""
    h, w, _ = img.shape
    valid = np.zeros(len(px), bool)
    hit = np.zeros(len(px), bool)
    c = np.array(core, dtype=np.int16)
    x0, y0, x1, y1 = (frame[0] + 3, frame[1] + 3, frame[2] - 3, frame[3] - 3) if frame else (1, 1, w - 2, h - 2)
    for i, q in enumerate(px):
        if q is None:
            continue
        x, y = int(round(q[0])), int(round(q[1]))
        if 1 <= x < w - 1 and 1 <= y < h - 1 and x0 <= x <= x1 and y0 <= y <= y1:
            valid[i] = True
            win = img[y - 1:y + 2, x - 1:x + 2].reshape(-1, 3)
            hit[i] = bool((np.abs(win - c).max(axis=1) <= COLOR_TOL).any())
    return valid, hit


def best_lag(a, b, va, vb, step, spacing):
    """Lag (m, 0 <= lag < spacing) that best maps the packets of frame A onto frame B, and the score at every lag."""
    n = int(round(spacing / step))
    scores = []
    for k in range(n):
        m = min(len(a), len(b)) - k
        sel = va[:m] & vb[k:k + m]
        x, y = a[:m][sel], b[k:k + m][sel]
        scores.append(float((x & y).sum() / max(1.0, np.sqrt(x.sum() * y.sum()))))
    scores = np.array(scores)
    return float(scores.argmax() * step), scores


def circ(d, spacing):
    return (d + spacing / 2) % spacing - spacing / 2


def measure_pair(pair, root, speeds=None, same_frame=False, cams=None):
    """Rows (owner, expected lag, found lag, speed in px, ok) of one pair of screenshots."""
    a = load(root / pair["png_a"])
    b = a if same_frame else load(root / pair["png_b"])
    dt = pair["t_b"] - pair["t_a"]
    sp = pair["spacing_m"]
    rows = []
    for owner, o in pair["owners"].items():
        if o["length_m"] < MIN_ARC_M:
            continue
        step = o["step_m"]
        va, ha = profile(a, o["px"], pair["core_rgb"], pair.get("frame"))
        vb, hb = profile(b, o["px"], pair["core_rgb"], pair.get("frame"))
        if int((va & ha).sum()) < MIN_HITS:
            continue
        v = (speeds or {}).get(owner, o["v"])
        lag_exp = (v * dt) % sp
        lag, scores = best_lag(ha, hb, va, vb, step, sp)
        k_exp = int(round(lag_exp / step)) % len(scores)
        err = circ(lag - lag_exp, sp)
        moved = scores[k_exp] > scores[0] + 0.1 if lag_exp > 0.3 else True
        ok = abs(err) <= TOL_M and scores[k_exp] >= 0.8 * scores.max() and moved
        rows.append((owner, o["v"], dt, lag_exp, lag, (lag / dt) if dt else 0.0, ok, float(scores[k_exp]), float(scores[0])))
    return rows


def report(title, rows_by_cam, expect_ok=True):
    bad = 0
    print(title)
    for cam, rows in rows_by_cam.items():
        for owner, v, dt, lag_exp, lag, v_px, ok, s_exp, s0 in rows:
            print(f"   {cam:<11} {owner:<20} v {v:5.3f} m/s  dt {dt:.3f} s  shift expected {lag_exp:.2f} m, found {lag:.2f} m "
                  f"(pattern speed {v_px:.2f} m/s)  corr at expected {s_exp:.2f} / at 0 {s0:.2f}  {'OK' if ok else 'OFF'}")
            bad += (not ok)
    n = sum(len(r) for r in rows_by_cam.values())
    return n, bad


def coverage(row, root, core):
    img = load(root / row["png"])
    px = row["paths"]["H5"]["px"]
    valid, hit = profile(img, px, core, row.get("frame"))
    return float((valid & hit).sum() / max(1, valid.sum())), int(valid.sum())


def trip_rows(at, root, core, invert=False, quiet=False):
    """The pixels along H5's path in the frames of the `--at` run: high packet coverage while H5 runs, ~none once it tripped."""
    good_all, seen = True, set()
    rows = []
    for row in at:
        cov, n = coverage(row, root, core)
        running = row["H5"] == "run" and not any(a.startswith("H5.") and a.endswith(":trip") for a in row["alarms"])
        moving = "H5" in row["moving"]
        expect = (not running) if invert else running
        good = ((cov >= 0.15) if expect else (cov <= 0.02)) and (moving == expect)
        good_all &= good
        seen.add(running)
        rows.append((row, cov, running, good))
        if not quiet:
            print(f"   sim t {row['sim_t']:.0f} s: H5 {row['H5']}, load {row['H5_load_t_h']} t/h, alarms {row['alarms']}, moving in the scene {moving}; "
                  f"packets on {100 * cov:.1f} % of its {n} path pixels in the frame -> {'OK' if good else 'OFF'}")
    both = seen == {True, False}
    if not quiet:
        print(f"   {'PASS' if both else 'FAIL'}  both states seen (running and stopped)")
    return rows, good_all and both


def main():
    root = Path(sys.argv[1])
    d = json.loads((root / "gui_probe.json").read_text(encoding="utf-8"))
    ok_all = True
    pairs = d.get("motion_pairs", [])
    if pairs:
        rows = {p["cam"]: measure_pair(p, root) for p in pairs}
        n, bad = report("shift of the packet pattern between two screenshots of one camera, on the pixels:", rows)
        tested = {c: len(r) for c, r in rows.items()}
        print(f"   {n} paths measured per camera {tested} (0 = no moving path of this scenario inside that camera frame), {bad} off")
        ok_all &= n > 0 and bad == 0
        if "--selftest" in sys.argv:
            print("broken variants (each must give OFF):")
            same = {p["cam"]: measure_pair(p, root, same_frame=True) for p in pairs}
            n1, bad1 = report("  the same frame twice, nothing moved", same)
            half = {p["cam"]: measure_pair(p, root, speeds={k: v["v"] * 0.5 for k, v in p["owners"].items()}) for p in pairs}
            n2, bad2 = report("  expected speeds halved", half)
            shifted = {p["cam"]: measure_pair(p, root, speeds={k: 2.87 if abs(v["v"] - 2.87) > 0.01 else 0.675 for k, v in p["owners"].items()})
                       for p in pairs}
            n3, bad3 = report("  every mover taken as H5 (2.87) or a chain (0.675)", shifted)
            for name, n_, bad_ in (("same frame", n1, bad1), ("speeds halved", n2, bad2), ("speeds swapped", n3, bad3)):
                good = bad_ > 0 and bad_ >= 0.5 * n_
                print(f"   {'PASS' if good else 'FAIL'}  broken variant '{name}': {bad_} of {n_} paths rejected")
                ok_all &= good
    if d.get("at"):
        core = pairs[0]["core_rgb"] if pairs else [255, 224, 107]
        print("trip proof (CAM_DRYING, the pixels along H5's path inside the camera frame):")
        rows, good_all = trip_rows(d["at"], root, core)
        ok_all &= good_all
        if "--selftest" in sys.argv:
            _, good_inv = trip_rows(d["at"], root, core, invert=True, quiet=True)
            print(f"   {'PASS' if not good_inv else 'FAIL'}  broken variant 'expected states swapped (stopped where it runs)': "
                  f"{'rejected' if not good_inv else 'accepted'}")
            ok_all &= not good_inv
    print("RESULT", "ALL PASS" if ok_all else "FAILED")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
