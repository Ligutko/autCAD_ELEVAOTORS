"""Silo aeration floor and aeration fans (K5-a) against the drawing: PDF p.2 vectors measured by
inbox/extract_aeration_p2.py (report inbox/reports/aeration_p2.json).

- every drawn channel of every silo has a kit channel with both ends within 5 cm, and the kit has
  no extra channels; channel width as drawn;
- every drawn fan symbol has a kit fan within 5 cm; each collector points at its fan;
- channels vs the tunnel of each row (SITE.json tunnels): over the tunnel void is an error, over the
  tunnel wall is a finding (the drawing reuses one layout for both rows, the row 2 tunnel is mirrored);
- channels clear of the discharge gate openings;
- floor coverage: the largest distance from a floor point to the nearest channel (reported; the
  norm comes with research/silo_equipment.md).

- fans (pad, frame, housing, motor) stay out of the silo foundation plinth.

Broken variants that must fail: branch step 1.6 m instead of 1.4 m, fan radius 13.2 m (the old EST),
fan pushed into the plinth.

Run:
    blender --background --python world/build/check_aeration.py
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

from kit import silo_interior as si  # noqa: E402
from kit import silo_msvu220 as silo  # noqa: E402

REPORT = ROOT.parent / "inbox" / "reports" / "aeration_p2.json"
TOL = 0.05


def kit_state(aer=None):
    """Kit layout and fans for SITE.json silo_aeration (or a modified copy of it)."""
    saved = si.AER
    try:
        if aer is not None:
            si.AER = aer
        segs = [(k, np.asarray(a, float), np.asarray(b, float)) for k, a, b in si.channel_layout()]
        a = si.AER
        fans = [np.array([a["fan_r"] * math.cos(math.radians(d)), a["fan_r"] * math.sin(math.radians(d))]) for d in a["fan_angles_deg"]]
        return segs, fans, a["channel_w"]
    finally:
        si.AER = saved


def _match(drawn, segs):
    """Drawn channels without a kit channel (ends within TOL, either direction) and kit channels left over."""
    left = list(range(len(segs)))
    missing = []
    for ch in drawn:
        p, q = np.array(ch["a"]), np.array(ch["b"])
        hit = None
        for i in left:
            _, a, b = segs[i]
            e = min(max(np.linalg.norm(p - a), np.linalg.norm(q - b)), max(np.linalg.norm(p - b), np.linalg.norm(q - a)))
            if e <= TOL:
                hit = i
                break
        if hit is None:
            missing.append(ch)
        else:
            left.remove(hit)
    return missing, left


def _corners(a, b, w):
    d = (b - a) / np.linalg.norm(b - a)
    n = np.array([-d[1], d[0]]) * w / 2
    return [a + n, a - n, b + n, b - n]


def _seg_dist(p, a, b):
    d = b - a
    t = float(np.clip((p - a) @ d / (d @ d), 0.0, 1.0))
    return float(np.linalg.norm(p - (a + d * t)))


def checks(site, report, aer=None):
    out = []
    segs, fans, width = kit_state(aer)
    for sid, d in sorted(report["silos"].items()):
        drawn = d["channels"]["collectors"] + d["channels"]["branches"]
        missing, extra = _match(drawn, segs)
        out.append((f"{sid} channels = drawing ({len(drawn)} drawn, {len(segs)} in the kit)", not missing and not extra,
                    f"drawn without a kit channel: {len(missing)}, kit channels not drawn: {len(extra)}"
                    + (f"; first missing {missing[0]['a']} -> {missing[0]['b']}" if missing else "")))
        fan_err = max(min(np.linalg.norm(np.array(f["center"]) - k) for k in fans) for f in d["fans"])
        out.append((f"{sid} aeration fans = drawing", len(d["fans"]) == len(fans) and fan_err <= TOL,
                    f"{len(d['fans'])} drawn, largest offset {fan_err:.3f} m"))
        out.append((f"{sid} channel width = drawing", abs(d["width_mean"] - width) <= 0.02, f"kit {width} m, drawn {d['width_mean']} m"))

    a_ = aer or si.AER
    parts = silo.build_fans(a_["fan_r"], a_["fan_angles_deg"])      # the fan geometry the silo kit builds
    # the duct (index 2) passes the plinth through its opening on purpose: check_foundation.py holds it
    v = np.concatenate([np.asarray(p[0], float) for k, p in enumerate(parts) if k != 2])
    low = v[v[:, 2] < -1e-3]                                        # below the plinth top (silo frame z = 0)
    intrude = silo.FOUND_R - float(np.hypot(low[:, 0], low[:, 1]).min())
    out.append(("aeration fans stay out of the foundation plinth", intrude <= 1e-3,
                f"deepest fan point below the plinth top is {intrude:+.3f} m inside the plinth edge R {silo.FOUND_R}"))

    worst = 0.0
    for deg in (aer or si.AER)["fan_angles_deg"]:
        u = np.array([math.cos(math.radians(deg)), math.sin(math.radians(deg))])
        col = next(s for s in segs if s[0] == "collector" and float(((s[2] - s[1]) / np.linalg.norm(s[2] - s[1])) @ u) > 0.999)
        worst = max(worst, si.R_IN - float(np.linalg.norm(col[2])))
    out.append(("each collector runs to the wall at its fan", worst <= 0.5, f"collector end to the inner wall ≤ {worst:.2f} m"))

    # tunnel of each row, silo frame (row axis at y = 0)
    for t in site["tunnels"]:
        y0, y1 = t["inner_y_rel_row"]
        wt = t["wall_t"]
        ys_n = [c[1] for _, a, b in segs for c in _corners(a, b, width) if c[1] > 0]
        ys_s = [c[1] for _, a, b in segs for c in _corners(a, b, width) if c[1] < 0]
        n_gap, s_gap = min(ys_n) - y1, y0 - max(ys_s)
        over_void = n_gap < 0 or s_gap < 0
        out.append((f"{t['id']}: no channel over the tunnel void", not over_void,
                    f"channel edge to the inner face: north {n_gap:.2f} m, south {s_gap:.2f} m"))
        for side, gap in (("north", n_gap), ("south", s_gap)):
            if 0 <= gap < wt:
                out.append((f"{t['id']} {side}: FINDING, not a model error", True,
                            f"channels reach {wt - gap:.2f} m over the {wt} m tunnel wall (edge {gap:.2f} m from the inner face). "
                            f"Sheet 2 uses one channel layout for both rows although this tunnel is mirrored: ask the designer"))

    gate_gap = min(_seg_dist(np.array([x, 0.0]), a, b) - width / 2 - s / 2 * math.sqrt(2)
                   for x, s in zip(si.GATE_OFFSETS, si.GATE_SIZES) for _, a, b in segs)
    out.append(("channels clear of the discharge gate openings", gate_gap > 0, f"closest {gate_gap:.2f} m"))

    # coverage: farthest floor point from a channel edge (floor outside the tunnel band of row 1 (S1, S2))
    g = np.linspace(-si.R_IN, si.R_IN, 221)
    xx, yy = np.meshgrid(g, g)
    pts = np.c_[xx.ravel(), yy.ravel()]
    y0, y1 = site["tunnels"][0]["inner_y_rel_row"]
    keep = (np.hypot(pts[:, 0], pts[:, 1]) < si.R_IN - 0.05) & ((pts[:, 1] > y1) | (pts[:, 1] < y0))
    pts = pts[keep]
    dist = np.full(len(pts), np.inf)
    for _, a, b in segs:
        d = b - a
        tt = np.clip((pts - a) @ d / (d @ d), 0.0, 1.0)
        dist = np.minimum(dist, np.linalg.norm(pts - (a + tt[:, None] * d), axis=1) - width / 2)
    far = pts[np.argmax(dist)]
    out.append(("floor coverage (reported; norm pending research/silo_equipment.md)", True,
                f"farthest floor point from a channel {dist.max():.2f} m at ({far[0]:.1f}, {far[1]:.1f}); "
                f"95 % of the floor within {np.percentile(dist, 95):.2f} m"))
    return out


def main():
    site = json.loads((ROOT / "site" / "SITE.json").read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    ok_all = True
    for name, ok, info in checks(site, report):
        ok_all &= ok
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {info}", flush=True)
    for name, patch in (("branch step 1.6 m instead of 1.4 m", lambda a: a.update(branch_s=[3.1 + 1.6 * k for k in range(6)])),
                        ("fan radius 13.2 m (old EST)", lambda a: a.update(fan_r=13.2)),
                        ("fan pushed into the plinth (radius 11.9 m)", lambda a: a.update(fan_r=11.9))):
        bad = copy.deepcopy(si.AER)
        patch(bad)
        failed = [n for n, ok, _ in checks(site, report, bad) if not ok]
        ok_all &= bool(failed)
        print(f"{'PASS' if failed else 'FAIL'}  broken variant must be rejected — {name}: failed {failed[:3]}{' …' if len(failed) > 3 else ''}", flush=True)
    print("RESULT", "ALL PASS" if ok_all else "FAILED", flush=True)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
