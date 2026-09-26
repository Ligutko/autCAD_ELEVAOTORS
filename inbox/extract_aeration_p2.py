"""Аерація підлоги силосів і вентилятори аерації з векторного аркуша 2 «Технологія 06.06.24.pdf».

Що робить:
1. Кола силосів і масштаб — як у extract_plan_p2.py (R 11000 мм). Масштаб звіряється з відстанями
   між осями силосів у SITE.json (24.0 / 29.0 / 25.5 м). Незбіг більше 0.5 % -> код виходу 3.
2. Канали аерації: червоні лінії товщиною 0.48 pt усередині кола. Кожен канал намальований
   прямокутником; дві довгі паралельні сторони на відстані ширини каналу дають вісь каналу.
   Канал уздовж напрямку на вентилятор — колектор, решта — відгалуження.
3. Вентилятори: сині чотирикутники (символ) біля стіни. Центр, радіус від осі силоса, кут.
4. Параметри схеми для кожного силоса: ширина каналу, початок і кінець колектора, положення
   відгалужень уздовж колектора, межі (стіна, вертикальна вісь, смуга тунелю).
   Перевірка узгодженості: схема однакова в усіх 6 силосах (кількість каналів, крок, радіуси).
   Розбіжність понад 3 см -> код виходу 4, картки не пишуться.
5. Пише `inbox/reports/aeration_p2.json` / `.md` і картки `unverified`.

Система координат силоса: вісь силоса в (0, 0), +X на схід (праворуч на аркуші), +Y на північ.
Статус `cited` скрипт не ставить ніколи. `FACTS.json` не пише.

Запуск (з кореня проєкту, потрібен pymupdf):
    python inbox/extract_aeration_p2.py
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_plan_p2 as ep  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
SITE = ROOT / "world" / "site" / "SITE.json"
REPORT_JSON = INBOX / "reports" / "aeration_p2.json"
REPORT_MD = INBOX / "reports" / "aeration_p2.md"
RECORDS = INBOX / "records"
EXTRACTOR = "extract_aeration_p2.py"

RED = (1.0, 0.0, 0.0)
BLUE = (0.0, 0.0, 1.0)
CHANNEL_LINE_W = 0.48          # pt, stroke of the channel outlines on this sheet
PAIR_GAP = (0.18, 0.40)        # m, channel width window for pairing two long sides
MIN_SIDE = 0.8                 # m, shorter strokes are channel ends
CONSISTENT = 0.03              # m, allowed spread of a parameter across the 6 silos
SCALE_TOL = 0.005


def _dir_angle(a, b):
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0


def pair_channels(segs):
    """Two long parallel strokes at channel-width distance with overlapping extents -> one channel axis."""
    longs = [(np.array(a), np.array(b)) for a, b in segs if math.dist(a, b) >= MIN_SIDE]
    used, channels, width = set(), [], []
    for i, (a1, b1) in enumerate(longs):
        if i in used:
            continue
        u = (b1 - a1) / np.linalg.norm(b1 - a1)
        n = np.array([-u[1], u[0]])
        best = None
        for j, (a2, b2) in enumerate(longs):
            if j <= i or j in used:
                continue
            if abs((_dir_angle(a1, b1) - _dir_angle(a2, b2) + 90) % 180 - 90) > 1.0:
                continue
            gap = abs(float((a2 - a1) @ n))
            if not PAIR_GAP[0] <= gap <= PAIR_GAP[1]:
                continue
            s1 = sorted([0.0, float((b1 - a1) @ u)])
            s2 = sorted([float((a2 - a1) @ u), float((b2 - a1) @ u)])
            overlap = min(s1[1], s2[1]) - max(s1[0], s2[0])
            if overlap < 0.8 * min(s1[1] - s1[0], s2[1] - s2[0]):
                continue
            if best is None or gap < best[1]:
                best = (j, gap, s2)
        if best is None:
            continue
        j, gap, s2 = best
        used |= {i, j}
        a2, b2 = longs[j]
        mid_off = float(((a2 - a1) @ n)) / 2.0
        s1 = sorted([0.0, float((b1 - a1) @ u)])
        t0, t1 = (s1[0] + s2[0]) / 2.0, (s1[1] + s2[1]) / 2.0
        p0 = a1 + u * t0 + n * mid_off
        p1 = a1 + u * t1 + n * mid_off
        if np.linalg.norm(p0) > np.linalg.norm(p1):          # axis runs outwards from the silo centre
            p0, p1 = p1, p0
        channels.append({"a": [round(float(v), 3) for v in p0], "b": [round(float(v), 3) for v in p1],
                         "width": round(gap, 3), "length": round(float(np.linalg.norm(p1 - p0)), 3)})
        width.append(gap)
    return channels, len(longs) - 2 * len(channels)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    today = date.today().isoformat()
    site = json.loads(SITE.read_text(encoding="utf-8"))
    doc = pymupdf.open(ep.PDF)
    page = doc[ep.PAGE_NO - 1]
    m = page.rotation_matrix
    silos = ep.find_silo_circles(page)
    if len(silos) != 6:
        print(f"AER_FAIL кіл силосів {len(silos)}, очікується 6")
        return 3
    factor = ep.KNOWN_RADIUS_MM / (sum(s["radius_pt"] for s in silos) / len(silos)) / 1000.0   # m per pt
    rows = sorted({round(s["cy_pt"] / 5.0) for s in silos})
    for s in silos:
        s["row"] = rows.index(round(s["cy_pt"] / 5.0))
    number = 1
    for r in range(len(rows)):
        for s in sorted([s for s in silos if s["row"] == r], key=lambda s: s["cx_pt"]):
            s["id"] = f"S{number}"
            number += 1
    by_id = {s["id"]: s for s in silos}

    # scale against SITE.json axis distances
    site_silos = {s["id"]: s for s in site["silos"]}
    scale = []
    for a, b in (("S1", "S2"), ("S3", "S4"), ("S5", "S6"), ("S4", "S5"), ("S1", "S3")):
        meas = math.hypot(by_id[a]["cx_pt"] - by_id[b]["cx_pt"], by_id[a]["cy_pt"] - by_id[b]["cy_pt"]) * factor
        ref = math.hypot(site_silos[a]["x"] - site_silos[b]["x"], site_silos[a]["y"] - site_silos[b]["y"])
        scale.append({"pair": f"{a}-{b}", "measured_m": round(meas, 3), "site_m": ref, "rel": round(abs(meas - ref) / ref, 5)})
    if any(c["rel"] > SCALE_TOL for c in scale):
        print("AER_FAIL масштаб", scale)
        return 3

    drawings = page.get_drawings()
    per_silo = {}
    for sid, s in sorted(by_id.items()):
        cx, cy = s["cx_pt"], s["cy_pt"]

        def loc(p):
            q = p * m
            return ((q.x - cx) * factor, -(q.y - cy) * factor)

        segs, fans = [], []
        for d in drawings:
            if d.get("color") == RED and round(d.get("width") or 0, 2) == CHANNEL_LINE_W:
                for it in d["items"]:
                    if it[0] == "l":
                        a, b = loc(it[1]), loc(it[2])
                        if max(math.hypot(*a), math.hypot(*b)) < 11.5:
                            segs.append((a, b))
            elif d.get("color") == BLUE and any(it[0] == "qu" for it in d["items"]):
                q = np.array([loc(p) for it in d["items"] if it[0] == "qu" for p in (it[1].ul, it[1].ur, it[1].lr, it[1].ll)])
                c = q.mean(axis=0)
                r = float(np.hypot(*c))
                ang = math.degrees(math.atan2(c[1], c[0])) % 360
                if 11.0 < r < 14.0 and 40.0 <= ang % 90.0 <= 50.0:          # diagonal fans; other blue symbols (towers) are not
                    side = float(np.linalg.norm(q[1] - q[0]))
                    fans.append({"center": [round(float(c[0]), 3), round(float(c[1]), 3)], "r": round(r, 3),
                                 "angle_deg": round(math.degrees(math.atan2(c[1], c[0])) % 360, 2),
                                 "symbol_side_m": round(side, 3)})
        channels, unpaired = pair_channels(segs)
        fan_dirs = [math.radians(f["angle_deg"]) for f in fans]
        collectors, branches = [], []
        for ch in channels:
            a, b = np.array(ch["a"]), np.array(ch["b"])
            u = (b - a) / np.linalg.norm(b - a)
            on_ray = any(abs(math.cos(t) * u[1] - math.sin(t) * u[0]) < 0.02 and
                         abs(math.cos(t) * a[1] - math.sin(t) * a[0]) < 0.1 for t in fan_dirs)
            (collectors if on_ray else branches).append(ch)
        # branch positions: where the branch line crosses its collector ray, measured from the silo axis
        params = {"collectors": [], "branch_s": []}
        for col in collectors:
            a, b = np.array(col["a"]), np.array(col["b"])
            u = (b - a) / np.linalg.norm(b - a)
            n = np.array([-u[1], u[0]])
            ts = []
            for br in branches:
                p, q = np.array(br["a"]), np.array(br["b"])
                mid = (p + q) / 2
                if np.sign(mid[0]) != np.sign(a[0] + b[0]) or np.sign(mid[1]) != np.sign(a[1] + b[1]):
                    continue
                w = (q - p) / np.linalg.norm(q - p)
                if abs(float(w @ u)) > 0.02:
                    continue
                s_ = float((p @ u))                                   # a is on the ray, so p@u is the distance from the axis
                if not any(abs(s_ - x) < 0.05 for x in ts):
                    ts.append(round(s_, 3))
            params["collectors"].append({"r0": round(float(np.linalg.norm(a)), 3), "r1": round(float(np.linalg.norm(b)), 3),
                                         "angle_deg": round(math.degrees(math.atan2(u[1], u[0])) % 360, 2),
                                         "hemisphere": "n" if a[1] + b[1] > 0 else "s",
                                         "branches": sum(1 for br in branches if abs(float(((np.array(br["b"]) - np.array(br["a"])) / br["length"]) @ u)) < 0.02
                                                         and np.sign((br["a"][0] + br["b"][0])) == np.sign(a[0] + b[0])
                                                         and np.sign((br["a"][1] + br["b"][1])) == np.sign(a[1] + b[1]))})
            params["branch_s"].append((("n" if a[1] + b[1] > 0 else "s"), sorted(ts)))
        ends = [np.array(br[k]) for br in branches for k in ("a", "b")]
        params["wall_r_max"] = round(max(float(np.linalg.norm(e)) for e in ends), 3)
        corners = []                                   # branch ends at the wall: the outer corner of the rectangle
        for br in branches:
            a_, b_ = np.array(br["a"]), np.array(br["b"])
            e = b_ if np.linalg.norm(b_) > np.linalg.norm(a_) else a_
            dv = (b_ - a_) / np.linalg.norm(b_ - a_)
            nv = np.array([-dv[1], dv[0]]) * br["width"] / 2
            if abs(e[0]) > 0.7 and abs(e[1]) > 1.9:    # not an end at the vertical axis or at the tunnel band
                corners.append(max(float(np.linalg.norm(e + nv)), float(np.linalg.norm(e - nv))))
        params["corner_r"] = round(float(np.mean(corners)), 3)
        params["corner_r_spread"] = round(max(corners) - min(corners), 3)
        params["axis_clear_min"] = round(min(abs(e[0]) for e in ends), 3)
        north = [e[1] for e in ends if e[1] > 0]
        south = [e[1] for e in ends if e[1] < 0]
        params["tunnel_edge_n"] = round(min(north), 3) if north else None
        params["tunnel_edge_s"] = round(max(south), 3) if south else None
        per_silo[sid] = {"row": s["row"], "fans": sorted(fans, key=lambda f: f["angle_deg"]), "channels": {"collectors": collectors, "branches": branches},
                         "counts": {"collectors": len(collectors), "branches": len(branches), "fans": len(fans), "unpaired_long_strokes": unpaired},
                         "width_mean": round(float(np.mean([c["width"] for c in channels])), 3) if channels else None,
                         "params": params}

    # consistency across silos
    issues = []

    def spread(values, what):
        v = [x for x in values if x is not None]
        if v and max(v) - min(v) > CONSISTENT:
            issues.append(f"{what}: {min(v)}..{max(v)}")
        return round(float(np.mean(v)), 3) if v else None

    counts = {sid: d["counts"] for sid, d in per_silo.items()}
    if len({json.dumps(c, sort_keys=True) for c in counts.values()}) != 1:
        issues.append(f"кількості різні: {counts}")
    summary = {
        "fan_r": spread([f["r"] for d in per_silo.values() for f in d["fans"]], "радіус вентиляторів"),
        "fan_angles_deg": sorted({round(f["angle_deg"] % 90, 1) for d in per_silo.values() for f in d["fans"]}),
        "channel_w": spread([d["width_mean"] for d in per_silo.values()], "ширина каналу"),
        "collector_r0": {h: spread([c["r0"] for d in per_silo.values() for c in d["params"]["collectors"] if c["hemisphere"] == h],
                                   f"початок колектора ({h})") for h in ("n", "s")},
        "branches_per_quadrant": {h: sorted({c["branches"] for d in per_silo.values() for c in d["params"]["collectors"] if c["hemisphere"] == h})
                                  for h in ("n", "s")},
        "collector_r1": spread([c["r1"] for d in per_silo.values() for c in d["params"]["collectors"]], "кінець колектора"),
        "branch_s": {h: [spread([ts[i] for d in per_silo.values() for hh, ts in d["params"]["branch_s"] if hh == h and i < len(ts)],
                                f"відгалуження {h}{i}")
                         for i in range(max(len(ts) for d in per_silo.values() for hh, ts in d["params"]["branch_s"] if hh == h))]
                     for h in ("n", "s")},
        "wall_r_max": spread([d["params"]["wall_r_max"] for d in per_silo.values()], "кінці біля стіни"),
        "corner_r": spread([d["params"]["corner_r"] for d in per_silo.values()], "зовнішній кут відгалуження біля стіни"),
        "axis_clear_min": spread([d["params"]["axis_clear_min"] for d in per_silo.values()], "зазор біля осі"),
        "tunnel_edge_by_row": {r: {"n": spread([d["params"]["tunnel_edge_n"] for d in per_silo.values() if d["row"] == r], f"ряд {r} північ"),
                                   "s": spread([d["params"]["tunnel_edge_s"] for d in per_silo.values() if d["row"] == r], f"ряд {r} південь")}
                               for r in (0, 1)},
        "counts_per_silo": next(iter(counts.values())),
    }
    report = {"source": f"{ep.PDF_NAME}, аркуш 2", "extractor": EXTRACTOR, "date": today, "m_per_pt": round(factor, 6),
              "scale_checks": scale, "consistency_issues": issues, "summary": summary, "silos": per_silo}
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if issues:
        print("AER_FAIL схема різна між силосами:", issues)
        return 4

    subject = "МСВУ 220.13.В12, аерація підлоги (аркуш 2)"
    claims = [
        ("channels_per_silo", summary["counts_per_silo"]["collectors"] + summary["counts_per_silo"]["branches"], "шт",
         f"{summary['counts_per_silo']['collectors']} колектори + {summary['counts_per_silo']['branches']} відгалужень"),
        ("channel_width", summary["channel_w"], "m", "ширина каналу між довгими сторонами прямокутника"),
        ("collector_start_r", summary["collector_r0"], "m", "початок колектора від осі силоса (n — північні, s — південні чверті)"),
        ("branches_per_quadrant", summary["branches_per_quadrant"], "шт", "відгалужень на чверть (n / s)"),
        ("collector_end_r", summary["collector_r1"], "m", "кінець колектора біля стіни"),
        ("branch_positions_s", summary["branch_s"], "m", "перетин осі відгалуження з променем колектора, від осі силоса (n / s)"),
        ("branch_end_r_max", summary["wall_r_max"], "m", "найдальший кінець осі відгалуження від осі силоса"),
        ("branch_corner_r", summary["corner_r"], "m", "зовнішній кут прямокутника відгалуження біля стіни лежить на цьому радіусі"),
        ("branch_axis_clear", summary["axis_clear_min"], "m", "кінці відгалужень біля вертикальної осі силоса"),
        ("aeration_fan_r", summary["fan_r"], "m", "центр символу вентилятора від осі силоса"),
        ("aeration_fan_angles", summary["fan_angles_deg"], "deg mod 90", "кут символу вентилятора від осі X (схід)"),
    ]
    written = 0
    for name, value, unit, qual in claims:
        card = ep.make_card(subject, "dimension", {"name": name, "value": value, "unit": unit, "qualifier": qual},
                            f"вектори аркуша 2: {qual}", None, "Заміряно скриптом по векторах; масштаб з R 11000, звірено з осями силосів.", today)
        card["source"]["extractor"] = EXTRACTOR
        card["basis"] = "sourced"
        card["id"] = ep.card_id(EXTRACTOR + name + json.dumps(value))
        (RECORDS / f"{card['id']}.json").write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1

    md = ["# Аерація підлоги і вентилятори з аркуша 2", "",
          f"Скрипт `inbox/{EXTRACTOR}`, {today}. Масштаб {factor:.5f} м/pt, звірено з осями силосів: "
          + ", ".join(f"{c['pair']} {c['measured_m']} / {c['site_m']}" for c in scale) + ".", "",
          "Схема однакова в усіх 6 силосах (розкид параметрів ≤ 3 см).", "",
          "| Параметр | Значення |", "|---|---|"]
    for name, value, unit, qual in claims:
        md.append(f"| {qual} | {value} {unit} |")
    md += ["", "Смуга тунелю по рядах (кінці відгалужень біля тунелю, y від осі силоса):", ""]
    for r, v in summary["tunnel_edge_by_row"].items():
        md.append(f"- ряд {r}: північ {v['n']}, південь {v['s']}")
    md += ["", f"Карток записано: {written} (`unverified`)."]
    REPORT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    print(f"AER_OK карток {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
