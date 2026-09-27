"""Приймальна частина (верхній блок аркуша 2) і її висоти (аркуші 3, 4).

Фаза 4. Рішення людини 2026-09-27: блок, найімовірніше, існуючий; моделюємо
спрощено + детально стики з новою чергою.

Що робить:
1. Аркуш 2 (план ±0.000): масштаб з 6 кіл силосів R 11000 (як extract_plan_p2.py),
   самоперевірка 24000 / 29000 / 25500 (<= 0.5 %, інакше код виходу 3, карток немає).
2. Переводить вектори верхнього блоку в систему SITE.json:
   X = X_плану(від осі силоса 3) - 38.5, Y = Y_плану; метри.
3. Знаходить: старі силоси «2», «3» (кола, кільце анкерів R 4690, кількість анкерів),
   яму (1) з навісом і проїздом, вежу (4) з норіями H1-H4, конвеєри T1, T2, T4, T6,
   будівлю «4» (6), естакаду 2300/4000/2300 x 4800. Кожен підписаний розмір
   звіряється з довжиною чорної розмірної лінії.
4. Аркуш 4 (розріз по Y через вежі): відмітки за масштабом 56.022 мм/pt
   від -1,900 і -5,100 (rec_e768e3ac), перевірка на +33,000 / +9,200.
5. Пише кропи в inbox/raw/pdf_crops/p02_recv_*.png, p04_recv_*.png, p03_recv_*.png,
   звіт inbox/reports/receiving_p2.json і картки unverified.

Картки мають source.extractor = "extract_receiving_p2.py". cited не ставиться ніколи.

Запуск з кореня проєкту:
    python inbox/extract_receiving_p2.py
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_plan_p2 import find_silo_circles, fit_circle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "Технологія 06.06.24.pdf"
PDF_NAME = PDF.name
CROPS = ROOT / "inbox" / "raw" / "pdf_crops"
RECORDS = ROOT / "inbox" / "records"
REPORT_JSON = ROOT / "inbox" / "reports" / "receiving_p2.json"
EXTRACTOR = "extract_receiving_p2.py"
KNOWN_RADIUS_MM = 11000.0
TOL = 0.005

COLORS = {
    (1.0, 0.0, 0.0): "red",
    (0.0, 0.0, 1.0): "blue",
    (0.0, 0.0, 0.0): "black",
    (1.0, 0.0, 1.0): "magenta",
    (0.87, 0.43, 0.0): "orange",
    (0.0, 1.0, 0.0): "green",
}


def cname(c):
    if c is None:
        return None
    return COLORS.get(tuple(round(v, 2) for v in c), str(c))


class Sheet2:
    """План аркуша 2 у координатах SITE."""

    def __init__(self, doc):
        self.page = doc[1]
        self.M = self.page.rotation_matrix
        silos = find_silo_circles(self.page)
        if len(silos) != 6:
            raise SystemExit(f"RECV_FAIL кіл силосів {len(silos)}, очікується 6")
        self.silos = silos
        self.r_pt = sum(s["radius_pt"] for s in silos) / 6
        self.f = KNOWN_RADIUS_MM / self.r_pt  # мм/pt
        top = min(s["cy_pt"] for s in silos)
        lower = sorted([s for s in silos if s["cy_pt"] > top + 50], key=lambda s: s["cx_pt"])
        upper = sorted([s for s in silos if s["cy_pt"] <= top + 50], key=lambda s: s["cx_pt"])
        if len(lower) != 4 or len(upper) != 2:
            raise SystemExit("RECV_FAIL ряди силосів не 2 + 4")
        self.lower, self.upper = lower, upper
        self.o = lower[0]  # силос 3 = SITE (-38.5, 0)
        self.drawings = self.page.get_drawings()

    def site(self, p):
        return (
            (p.x - self.o["cx_pt"]) * self.f / 1000 - 38.5,
            -(p.y - self.o["cy_pt"]) * self.f / 1000,
        )

    def to_pt(self, X, Y):
        return (self.o["cx_pt"] + (X + 38.5) * 1000 / self.f, self.o["cy_pt"] - Y * 1000 / self.f)

    def bbox_pt(self, X0, Y0, X1, Y1):
        a = self.to_pt(X0, Y1)
        b = self.to_pt(X1, Y0)
        return [round(a[0], 1), round(a[1], 1), round(b[0], 1), round(b[1], 1)]

    def checks(self):
        f = self.f
        L, U = self.lower, self.upper
        out = []
        for what, a, b, key, ann in (
            ("вісь 3 - вісь 4", L[0], L[1], "cx_pt", 24000),
            ("вісь 5 - вісь 6", L[2], L[3], "cx_pt", 24000),
            ("вісь 1 - вісь 2", U[0], U[1], "cx_pt", 24000),
            ("вісь 4 - вісь 5 через вежу", L[1], L[2], "cx_pt", 29000),
            ("вісь 3 - вісь 1 між рядами", L[0], U[0], "cy_pt", 25500),
        ):
            m = abs(a[key] - b[key]) * f
            out.append({"what": what, "annotated_mm": ann, "measured_mm": round(m, 1),
                        "rel": round(abs(m - ann) / ann, 5), "ok": abs(m - ann) / ann <= TOL})
        return out

    def items(self, d):
        M = self.M
        for it in d["items"]:
            if it[0] == "l":
                yield "l", [self.site(it[1] * M), self.site(it[2] * M)]
            elif it[0] == "c":
                yield "c", [self.site(q * M) for q in it[1:5]]
            elif it[0] in ("re", "qu"):
                q = (it[1].quad if it[0] == "re" else it[1]) * M
                yield "q", [self.site(q.ul), self.site(q.ur), self.site(q.lr), self.site(q.ll)]

    def in_box(self, X0, Y0, X1, Y1):
        for d in self.drawings:
            r = d["rect"] * self.M
            a = self.site(pymupdf.Point(r.x0, r.y1))
            b = self.site(pymupdf.Point(r.x1, r.y0))
            if a[0] >= X0 and b[0] <= X1 and a[1] >= Y0 and b[1] <= Y1:
                yield d, (a[0], a[1], b[0], b[1])

    def lines(self, color, X0, Y0, X1, Y1, lmin=0.0, lmax=1e9):
        out = []
        for d, _ in self.in_box(X0 - 60, Y0 - 60, X1 + 60, Y1 + 60):
            if color != "any" and cname(d.get("color")) != color:
                continue
            for k, ps in self.items(d):
                if k != "l":
                    continue
                (a, b), (c, e) = ps
                L = math.hypot(c - a, e - b)
                if lmin <= L <= lmax and X0 <= min(a, c) and max(a, c) <= X1 and Y0 <= min(b, e) and max(b, e) <= Y1:
                    out.append((a, b, c, e, L))
        return out

    def quads(self, color, X0, Y0, X1, Y1, smin, smax):
        out = set()
        for d, _ in self.in_box(X0, Y0, X1, Y1):
            if cname(d.get("color")) != color:
                continue
            for k, ps in self.items(d):
                if k != "q":
                    continue
                xs = [p[0] for p in ps]
                ys = [p[1] for p in ps]
                w, h = max(xs) - min(xs), max(ys) - min(ys)
                if smin <= max(w, h) <= smax:
                    out.add((round((max(xs) + min(xs)) / 2, 3), round((max(ys) + min(ys)) / 2, 3), round(w, 3), round(h, 3)))
        return sorted(out, key=lambda t: (t[1], t[0]))

    def small_symbols(self, color, X0, Y0, X1, Y1, smin, smax):
        out = []
        for d, b in self.in_box(X0, Y0, X1, Y1):
            if cname(d.get("color")) != color:
                continue
            w, h = b[2] - b[0], b[3] - b[1]
            if smin <= w <= smax and smin <= h <= smax:
                out.append((round((b[0] + b[2]) / 2, 3), round((b[1] + b[3]) / 2, 3), round(w, 3), round(h, 3)))
        return out

    def circles(self, color, X0, Y0, X1, Y1, rmin, rmax):
        out = []
        for d, _ in self.in_box(X0, Y0, X1, Y1):
            if cname(d.get("color")) != color or len(d["items"]) < 12:
                continue
            pts = np.array([p for _, ps in self.items(d) for p in ps])
            cx, cy, r = fit_circle(pts)
            res = float(np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - r).max())
            if res < 0.05 and rmin <= r <= rmax:
                out.append((round(cx, 3), round(cy, 3), round(r, 4), round(res, 4)))
        return out

    def ring_fit(self, cx, cy, color, fill, rmin, rmax):
        pts = []
        for d, _ in self.in_box(cx - 5.4, cy - 5.4, cx + 5.4, cy + 5.4):
            if cname(d.get("color")) != color or cname(d.get("fill")) != fill:
                continue
            P = np.array([p for _, ps in self.items(d) for p in ps])
            r = np.hypot(P[:, 0] - cx, P[:, 1] - cy)
            if r.min() > rmin and r.max() < rmax:
                pts.append(P)
        P = np.vstack(pts)
        return fit_circle(P), len(pts)

    def anchors(self, cx, cy):
        """Чорні заливки (анкерні опори) на кільці 4.45-4.90 м, кластери за кутом."""
        angs = []
        for d, b in self.in_box(cx - 5.4, cy - 5.4, cx + 5.4, cy + 5.4):
            if cname(d.get("fill")) != "black":
                continue
            mx, my = (b[0] + b[2]) / 2 - cx, (b[1] + b[3]) / 2 - cy
            if 4.45 <= math.hypot(mx, my) <= 4.90 and max(b[2] - b[0], b[3] - b[1]) < 0.45:
                angs.append(math.degrees(math.atan2(my, mx)) % 360)
        angs.sort()
        clusters = []
        for a in angs:
            if clusters and a - clusters[-1][-1] < 4.0:
                clusters[-1].append(a)
            else:
                clusters.append([a])
        if len(clusters) > 1 and clusters[0][0] + 360 - clusters[-1][-1] < 4.0:
            clusters[0] = clusters.pop() + clusters[0]
        # опора складається з >= 4 залитих частин; поодинокі заливки — стрілки й текст
        centres = sorted((sum(c) / len(c)) % 360 for c in clusters if len(c) >= 4)
        return centres

    def dim(self, value_mm, X0, Y0, X1, Y1):
        """Чорна розмірна лінія довжиною value_mm (±0.6 %) у вікні; повертає кінці."""
        best = None
        for a, b, c, e, L in self.lines("black", X0, Y0, X1, Y1, 0.2, 40):
            if not (abs(a - c) < 0.01 or abs(b - e) < 0.01):
                continue
            err = abs(L * 1000 - value_mm)
            if err <= max(0.006 * value_mm, 12) and (best is None or err < best[0]):
                best = (err, (round(a, 3), round(b, 3)), (round(c, 3), round(e, 3)), round(L * 1000))
        return best

    def crop(self, name, X0, Y0, X1, Y1, dpi):
        a = self.to_pt(X0, Y1)
        b = self.to_pt(X1, Y0)
        pix = self.page.get_pixmap(dpi=dpi, clip=pymupdf.Rect(a[0], a[1], b[0], b[1]))
        pix.save(CROPS / name)
        return f"inbox/raw/pdf_crops/{name}"


def card_id(key: str) -> str:
    return "rec_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]


CARDS: list[dict] = []


def card(subject, name, value, unit, qualifier, page, bbox, crop, basis, notes, quote="", kind="dimension"):
    claim = {"name": name, "value": value, "unit": unit, "qualifier": qualifier}
    key = "|".join([subject, kind, name, PDF_NAME, str(page), EXTRACTOR])
    CARDS.append({
        "id": card_id(key),
        "subject": subject,
        "kind": kind,
        "claim": claim,
        "source": {"origin": "local", "path": PDF_NAME, "page": page, "bbox": bbox, "quote": quote,
                   "crop": crop, "retrieved_at": date.today().isoformat(), "extractor": EXTRACTOR},
        "basis": basis,
        "status": "unverified",
        "conflict_with": [],
        "notes": notes + " Координати SITE: X на схід від осі веж H5/H6, Y на північ від осі ряду 3-6, z — відмітки. bbox — повернена сторінка, pt.",
        "seen_in": [],
    })


def r3(v):
    return round(v + 0.0, 3)


def sheet2(doc, rep):
    s = Sheet2(doc)
    checks = s.checks()
    rep["sheet2"] = {"factor_mm_per_pt": round(s.f, 4), "checks": checks}
    if not all(c["ok"] for c in checks):
        print("RECV_FAIL масштаб: " + "; ".join(f"{c['what']} {c['measured_mm']}" for c in checks if not c["ok"]))
        raise SystemExit(3)

    CROPS.mkdir(parents=True, exist_ok=True)
    cr_all = s.crop("p02_recv_block_200dpi.png", -24.5, 41.0, 16.0, 69.5, 200)
    cr_pit = s.crop("p02_recv_pit_300dpi.png", -22.0, 58.5, 15.0, 69.0, 300)
    cr_tower = s.crop("p02_recv_tower_600dpi.png", -3.0, 49.5, 5.5, 60.5, 600)
    cr_silo = s.crop("p02_recv_silo2_400dpi.png", -13.5, 48.0, -2.5, 59.5, 400)
    cr_est = s.crop("p02_recv_estakada_400dpi.png", -7.5, 41.0, 4.5, 51.6, 400)
    cr_b4 = s.crop("p02_recv_bld4_500dpi.png", 4.0, 48.5, 12.5, 59.0, 500)

    # --- розміри з підписами: розмірна лінія має відповідну довжину -----------
    dims = {}
    for label, v, box in (
        ("4350_w", 4350, (-4, 68, 2, 69)), ("4350_e", 4350, (0.5, 68, 6, 69)),
        ("6700", 6700, (9, 59, 10.5, 68)), ("3750", 3750, (-10, 59, -9, 68)), ("2950", 2950, (-10, 59, -9, 68)),
        ("6000_pit", 6000, (-2, 60, -1.7, 67)), ("4000_pit_w", 4000, (-3, 61.9, 1.2, 62.1)),
        ("4000_pit_e", 4000, (1.0, 61.9, 5.2, 62.1)), ("2000_hopper", 2000, (2.9, 62, 3.1, 65)),
        ("3200", 3200, (-3, 60.9, 0.4, 61.0)), ("800", 800, (0.2, 59.4, 1.2, 59.6)), ("1050", 1050, (1.0, 59.4, 2.2, 59.6)),
        ("3000", 3000, (-1.9, 57.5, -1.7, 60.7)), ("6150", 6150, (-8.3, 58, -1.9, 58.1)),
        ("6200", 6200, (-2.1, 50.4, 4.3, 50.6)), ("6000_tower", 6000, (4.8, 51, 5.0, 57.5)),
        ("2200", 2200, (-2.9, 55, -2.7, 57.5)), ("1600_w", 1600, (-0.6, 56.3, 1.2, 56.5)), ("1600_e", 1600, (1.0, 56.3, 2.8, 56.5)),
        ("1500_axis", 1500, (0.3, 53.6, 0.5, 55.3)), ("1100", 1100, (1.2, 51.3, 1.3, 52.6)), ("1400", 1400, (2.4, 51.5, 4.0, 51.6)),
        ("4000_boots", 4000, (-1.0, 49.9, 3.2, 50.0)), ("4150", 4150, (4.1, 58.5, 8.5, 58.7)), ("1300", 1300, (6.9, 53.8, 7.1, 55.3)),
        ("550", 550, (-10.7, 53.3, -10.5, 54.1)), ("12000", 12000, (-20.3, 47.1, -8.0, 47.2)),
        ("3500", 3500, (-2.7, 47.8, -2.6, 51.5)), ("4800", 4800, (-6.8, 43, -6.7, 48)),
        ("2300_w", 2300, (-5.9, 41.7, -3.4, 41.8)), ("4000_est", 4000, (-3.6, 41.7, 0.6, 41.8)), ("2300_e", 2300, (0.4, 41.7, 2.9, 41.8)),
        ("1500_est", 1500, (-3.6, 51.9, -1.9, 52.1)),
    ):
        hit = s.dim(v, *box)
        dims[label] = {"annotated_mm": v, "line": None if hit is None else {"from": hit[1], "to": hit[2], "measured_mm": hit[3]}}
    rep["sheet2"]["dims"] = dims
    missing = [k for k, d in dims.items() if d["line"] is None]
    if missing:
        print("RECV_WARN не знайдено розмірних ліній:", missing)

    # --- старі силоси «3» (захід) і «2» (схід) ---------------------------------
    walls = s.circles("red", -26, 47, -2, 60, 3.5, 5.5)
    centres = sorted({(c[0], c[1]) for c in walls if c[2] > 5.0})
    old = []
    for cx, cy in centres:
        rs = sorted(c[2] for c in walls if abs(c[0] - cx) < 0.05 and abs(c[1] - cy) < 0.05)
        (ax, ay, ar), n = s.ring_fit(cx, cy, "black", None, 4.45, 4.95)
        anc = s.anchors(cx, cy)
        old.append({"centre": [r3(cx), r3(cy)], "radii_red": rs, "anchor_ring_r": round(ar, 4),
                    "anchor_ring_centre": [r3(ax), r3(ay)], "anchors": len(anc),
                    "anchor_angles": [round(a, 1) for a in anc]})
    rep["old_silos"] = old
    if len(old) != 2:
        raise SystemExit(f"RECV_FAIL старих силосів {len(old)}")
    s3, s2 = old[0], old[1]
    card("Існуючий силос «3» (приймальна частина)", "centre", s3["centre"], "m",
         "центр кола силоса «3», план ±0.000", 2, s.bbox_pt(-25.5, 48.3, -14.8, 59.1), cr_all, "derived",
         f"Коло стіни підігнане МНК по вершинах червоних кіл, R {s3['radii_red']}. Відстань між «3» і «2» 12000 підписана "
         f"(розмірна лінія {dims['12000']['line']['measured_mm'] if dims['12000']['line'] else '—'} мм). Тип силоса не підписаний.")
    card("Існуючий силос «2» (приймальна частина)", "centre", s2["centre"], "m",
         "центр кола силоса «2», план ±0.000", 2, s.bbox_pt(-13.5, 48.3, -2.8, 59.1), cr_silo, "derived",
         f"Червоні кола R {s2['radii_red']}. Від осі силоса «2» до західної лінії колон вежі 6150 підписано "
         f"(лінія {dims['6150']['line']['measured_mm'] if dims['6150']['line'] else '—'} мм).", quote="6150")
    card("Існуючі силоси «2», «3»", "wall_and_plinth_radii",
         {"wall_r_m": [min(s3["radii_red"]), sorted(s3["radii_red"])[1]], "plinth_outer_r_m": max(s3["radii_red"])}, "m",
         "два близькі червоні кола (стіна, товщина лінії ≈30 мм) і зовнішнє коло фундаменту", 2,
         s.bbox_pt(-13.5, 48.3, -2.8, 59.1), cr_silo, "derived",
         "Стіна R 4.26/4.29 (D ≈ 8.55 м), зовнішнє коло R 5.09 (D ≈ 10.18 м) — найімовірніше край фундаментного кільця. Підписаний лише R4690 (кільце анкерів).")
    card("Існуючі силоси «2», «3»", "anchor_ring_radius", 4690, "mm",
         "R4690 — радіус штрих-пунктирного кола, на якому стоять анкерні опори", 2,
         s.bbox_pt(-13.5, 48.3, -2.8, 59.1), cr_silo, "sourced",
         f"Підпис R4690 (двічі, на обох силосах). Вектор: «3» R {s3['anchor_ring_r']}, «2» R {s2['anchor_ring_r']} (чорне штрих-пунктирне коло). "
         "Кільце анкерів ЗОВНІ стіни (R 4.29) на 0.40 м.", quote="R4690")
    card("Існуючі силоси «2», «3»", "anchor_count", {"3": s3["anchors"], "2": s2["anchors"]}, "pcs",
         "чорні анкерні опори з 4 пурпуровими точками на кільці R4690", 2,
         s.bbox_pt(-13.5, 48.3, -2.8, 59.1), cr_silo, "derived",
         f"Кластери чорних заливок на r 4.45-4.90 м за кутом. Кути «2»: {s2['anchor_angles']}. Крок ≈18°. "
         "Кожна опора — чорний восьмикутник ≈0.25 м з 4 пурпуровими точками (болти). Звірено з кропом очима.")

    # --- яма (1), навіс, проїзд ---------------------------------------------------
    pitl = s.lines("magenta", -4, 60, 6, 67, 5.5, 8.5)
    xs = [v for a, b, c, e, L in pitl for v in (a, c)]
    ys = [v for a, b, c, e, L in pitl for v in (b, e)]
    pit = {"x": [r3(min(xs)), r3(max(xs))], "y": [r3(min(ys)), r3(max(ys))]}
    pit["centre"] = [r3((min(xs) + max(xs)) / 2), r3((min(ys) + max(ys)) / 2)]
    rep["pit"] = pit
    cols = []
    for a, b, c, e, L in s.lines("red", -4, 59.5, 6.5, 68, 0.235, 0.245):
        if abs(a - c) < 0.01:
            cols.append((a, (b + e) / 2))
    # колона = квадрат 0.24: пара вертикальних сторін; центр — середнє пари
    groups: list[list[float]] = []
    for x in sorted(x for x, _ in cols):
        if groups and x - groups[-1][-1] < 0.5:
            groups[-1].append(x)
        else:
            groups.append([x])
    canopy_x = [r3((min(g) + max(g)) / 2) for g in groups]
    canopy_y = [r3(float(np.mean([y for _, y in cols if y < 62]))), r3(float(np.mean([y for _, y in cols if y > 66])))]
    rep["canopy_columns"] = {"x": canopy_x, "y_rows": canopy_y}
    walls_b = s.lines("red", -3.6, 60.0, 5.8, 67.3, 7.0, 11.3)
    rep["pit_building_walls"] = sorted({(r3(a), r3(b), r3(c), r3(e)) for a, b, c, e, L in walls_b})
    road = s.lines("red", -21.0, 60.9, 13.8, 65.6, 4.5, 4.7)
    road_x = sorted({r3(a) for a, b, c, e, L in road if abs(a - c) < 0.01})
    edge = sorted({r3(b) for a, b, c, e, L in s.lines("red", -21.0, 60.9, 13.8, 65.6, 6.0, 12) if abs(b - e) < 0.01})
    rep["road"] = {"x_breaks": road_x, "edges_y": edge}
    pads = s.quads("red", -7, 59, 9, 68, 1.1, 1.3)
    rep["pads_1200"] = pads
    hop = s.lines("black", 0.9, 62.4, 1.3, 64.9, 0.25, 0.4)

    card("Завальна яма (1)", "pit_outline", {"x": pit["x"], "y": pit["y"], "centre": pit["centre"]}, "m",
         "яма в плані (пурпуровий контур), 4000 + 4000 × 6000, дно -5.000", 2, s.bbox_pt(-3, 60.5, 5.2, 66.8), cr_pit, "derived",
         f"Розміри підписані: 4000+4000 (лінії {dims['4000_pit_w']['line']}, {dims['4000_pit_e']['line']}), 6000 ({dims['6000_pit']['line']}). "
         "Центр ями по X збігається з віссю вежі (X 1.10) і віссю T1.", quote="4000 4000 6000 -5,000")
    card("Завальна яма (1)", "hopper_outlets", {"x": pit["centre"][0], "y": [62.656, 64.651], "spacing_mm": 2000}, "m",
         "дві лійки ями з випусками на T1, між ними 2000", 2, s.bbox_pt(-0.5, 62, 3.2, 65.2), cr_pit, "derived",
         f"Пірамідальні лінії від кутів ями сходяться до двох випусків; підпис 2000 (лінія {dims['2000_hopper']['line']}). "
         "На розрізі арк. 4 під ними засувки 6.24 і 6.25.", quote="2000")
    card("Завальна яма (1)", "canopy_columns", {"x": canopy_x, "y_rows": canopy_y}, "m",
         "6 колон навісу/будівлі ями: 3 × 2 ряди, 4350 + 4350 × 6700", 2, s.bbox_pt(-3.6, 60, 5.8, 67.3), cr_pit, "derived",
         f"Колони — червоні квадрати 0.24 м. 4350 ({dims['4350_w']['line']}), 4350 ({dims['4350_e']['line']}), 6700 ({dims['6700']['line']}). "
         f"Стіни будівлі ями (червоний контур) {rep['pit_building_walls']}.", quote="4350 4350 6700")
    card("Завальна яма (1)", "drive_through", {"edges_y": edge, "x_breaks": road_x, "axis_y": 63.25,
                                               "direction": "зі сходу на захід (-X)", "slope_label": "1:10 на ділянці X -20.90…-12.90",
                                               "deck_z": 0.100}, "m",
         "проїзд через яму: смуга 4.60 м, вісь Y 63.25, ухил 1:10, відмітка +0.100, напрям «Напрямок проїзду» ←", 2,
         s.bbox_pt(-21, 59.5, 14, 67.5), cr_pit, "derived",
         "Вісь проїзду: від ряду колон 3750 / 2950 (підписано) → Y 63.25, на 0.40 південніше центру ями (63.65). Бордюри 0.20 (лінії 61.15, 65.35). "
         "Злам покриття на X -12.90; західна ділянка -20.90…-12.90 (8.0 м) підписана «1:10»; східна 5.70…13.70 теж 8.0 м, без підпису ухилу. "
         "Стрілка «Напрямок проїзду» ← на сході: машини заїжджають зі сходу. Перепад +0.100 → земля -0.45 = 0.55 м (арк. 4 «550»), при 1:10 це 5.5 м, а ділянка 8.0 м.",
         quote="1:10 +0,100 Напрямок проїзду 3750 2950")
    card("Завальна яма (1)", "outer_posts", [[p[0], p[1]] for p in pads], "m",
         "4 опори з фундаментом 1.2 × 1.2 і стійкою 0.6 × 0.6 на кінцях будівлі ями, на рядах колон", 2,
         s.bbox_pt(-7, 59.5, 9, 68), cr_pit, "derived",
         "Призначення не підписане (можливо, стійки огородження/відбійників або порталу). Від крайніх колон навісу 2.65-2.70 м назовні.")

    # --- вежа (4), норії H1-H4, приямок ---------------------------------------------
    tcols = s.small_symbols("red", -2.5, 51, 4.5, 58, 0.18, 0.21)
    tx = sorted({round(c[0], 3) for c in tcols})
    ty = sorted({round(c[1], 3) for c in tcols})
    tower = {"cols_x": tx, "cols_y": ty, "centre": [r3(sum(tx) / 2), r3(sum(ty) / 2)],
             "size": [r3(tx[-1] - tx[0]), r3(ty[-1] - ty[0])]}
    rep["tower"] = tower
    boots = s.quads("red", -1.5, 51.8, 4, 56.5, 0.75, 1.25)
    rep["boot_pits"] = boots
    names = {}
    for b in boots:
        if b[1] > 54:
            names[{-1: "H4", 0: "H4", 1: "H1", 2: "H1", 3: "H2"}.get(int(round(b[0] + 0.5)), "?")] = b
        else:
            names["H3"] = b
    rep["norias_plan"] = names
    card("Приймальна вежа (4)", "column_grid", tower, "m",
         "сітка 4 колон вежі 6200 × 6000 (червоні квадрати 0.20 м)", 2, s.bbox_pt(-2.3, 50.4, 5.0, 58.2), cr_tower, "derived",
         f"6200 ({dims['6200']['line']}), 6000 ({dims['6000_tower']['line']}). У SITE.json receiving.tower_H1_H4 x 1.1, y 54.8 (EST): "
         f"X збігається, Y на {round(54.8 - tower['centre'][1], 2)} м північніше за креслення.", quote="6200 6000")
    card("Приймальна вежа (4)", "pit_walls", {"inner": {"x": [-1.748, 3.949], "y": [51.406, 57.151]},
                                              "outer": {"x": [-2.256, 4.448], "y": [50.897, 57.649]}, "floor_z": -5.8}, "m",
         "приямок вежі: внутрішні і зовнішні грані стін, дно -5.800", 2, s.bbox_pt(-2.3, 50.8, 4.5, 57.7), cr_tower, "derived",
         "Червоні прямокутники 5.697 × 5.745 (у світлі) і 6.704 × 6.752 (зовні), стіни ≈0.50. Ланцюг арк. 4 1100 + 2700 + 1950 = 5750 = ширина у світлі по Y. "
         "Підпис -5,800 на плані.", quote="-5,800")
    card("Приймальна вежа (4)", "noria_axes_plan",
         {k: [v[0], v[1]] for k, v in names.items()}, "m",
         "центри приямків башмаків H1-H4 (червоні прямокутники) = осі норій у плані", 2,
         s.bbox_pt(-1.5, 51.8, 4, 56.5), cr_tower, "derived",
         f"H4, H1, H2 в один ряд на Y 55.20 з кроком 1600 + 1600 ({dims['1600_w']['line']}, {dims['1600_e']['line']}); ряд на 2200 від північних колон "
         f"({dims['2200']['line']}) і на 1500 від осі старих силосів ({dims['1500_axis']['line']}). H3 окремо: 1100 від південних колон ({dims['1100']['line']}), "
         f"1400 до східної стіни приямку ({dims['1400']['line']}); труби H3 розставлені вздовж X, H1/H2/H4 — вздовж Y. Приямки башмаків: {boots}.",
         quote="1600 1600 2200 1100 1400")

    # --- конвеєри T1, T2, T4, T6 ---------------------------------------------------------
    conv = {
        "T1": {"axis_x": 1.097, "y": [55.904, 66.147], "width": 0.489,
               "note": "з ями на південь у приямок вежі, під ухилом 9° (арк. 4)"},
        "T2": {"axis_y": 53.976, "x": [-9.852, 2.444], "width": 0.402,
               "note": "від середини силоса «2» на схід у вежу; «Самоплив з транспортера T2 на норію H2» (арк. 4)"},
        "T6": {"axis_y": 53.425, "x": [-21.697, 0.497], "width": 0.393,
               "note": "від силоса «3» через силос «2» у вежу"},
        "T4": {"axis_y": 53.899, "x": [2.645, 11.239], "width": 0.288,
               "note": "з вежі на схід через будівлю «4» (6)"},
    }
    rep["conveyors_plan"] = conv
    for cid, c in conv.items():
        card(f"Конвеєр {cid} (приймальна частина)", "plan_extent", c, "m",
             "синій кожух у плані ±0.000: вісь і кінці", 2,
             s.bbox_pt(-22, 53, 12, 54.3) if cid != "T1" else s.bbox_pt(0.7, 55.8, 1.5, 66.3),
             cr_all, "derived",
             ("Між осями T6 і T2 підписано 550 (" + str(dims["550"]["line"]) + "). " if cid in ("T2", "T6") else "")
             + ("Вісь T4 на 1300 південніше ряду норій (" + str(dims["1300"]["line"]) + "). " if cid == "T4" else "")
             + ("T1 іде по осі ями й вежі X 1.10; прохід між ямою і вежею: стіни каналу X 0.295 і 2.146 (800 + 1050), довжина 3000 від зовнішньої стіни приямку до ями. "
                if cid == "T1" else "")
             + "Тип конвеєра не підписаний; специфікація нової черги його не містить (існуючий).",
             quote=cid)

    # --- будівля «4» (6) і естакада Ш1 ---------------------------------------------------
    card("Будівля «4» (позначка (6))", "outline", {"outer": {"x": [5.081, 11.622], "y": [49.353, 57.947]},
                                                  "inner_blue": {"x": [5.465, 11.229], "y": [50.063, 57.563]},
                                                  "axis_x": 8.347, "support_rows_y": [52.8, 55.0]}, "m",
         "червоний зовнішній контур 6.54 × 8.59, синій внутрішній 5.76 × 7.50, відмітка ±0.000", 2,
         s.bbox_pt(4.9, 49.2, 11.8, 58.1), cr_b4, "derived",
         f"4150 від східної лінії колон вежі до осі будівлі ({dims['4150']['line']}). Всередині 2 ряди опор (Y ≈52.8 і ≈55.0, 2.2 м), по кінцях заштриховані "
         "червоні вузли, між ними малі квадрати на X ≈7.7 і 9.0. Призначення будівлі не підписане. Колон каркаса у звичному вигляді (квадрати) немає.",
         quote="4150 ±0,000")
    est_cols = s.quads("red", -7, 42, 4, 49, 0.55, 0.65)
    est_strips = s.quads("red", -7, 42, 4, 49, 9.0, 10.0)
    rep["estakada"] = {"columns": est_cols, "strips": est_strips}
    card("Естакада бункера Ш1 і сепаратора", "column_grid",
         {"cols_x": sorted({c[0] for c in est_cols}), "rows_y": sorted({c[1] for c in est_cols}),
          "col_size": 0.6, "strip_footings": [[s_[0], s_[1], s_[2], s_[3]] for s_ in est_strips]}, "m",
         "8 колон 0.6 × 0.6: 2300 / 4000 / 2300 × 4800, стрічкові фундаменти 9.6 × 1.0; під нею проїзд ← (на захід)", 2,
         s.bbox_pt(-7, 41.5, 4, 49), cr_est, "derived",
         f"2300 ({dims['2300_w']['line']}), 4000 ({dims['4000_est']['line']}), 2300 ({dims['2300_e']['line']}), 4800 ({dims['4800']['line']}); "
         f"3500 до південної лінії колон вежі ({dims['3500']['line']}); 1500 між лініями X -3.50 і -2.00 ({dims['1500_est']['line']}). "
         "Що це Ш1 з сепаратором 5 — з розрізу арк. 4 (ширина 4800 і розрив 3500 до вежі збігаються).",
         quote="2300 4000 2300 4800 3500")
    return s


class Section:
    """Розріз аркуша 4 або 5 (вид уздовж X, горизонталь = Y SITE).

    Масштаб 56.022 мм/pt (rec_e768e3ac). Y прив'язано до двох ліній колон приймальної
    вежі (подвійні червоні вертикалі, центри Y 51.401 і 57.405 з плану арк. 2),
    z — до лінії відмітки +33,000; перевірка на +9,200, ±0,000, -5,800.
    """

    K = 0.056022

    def __init__(self, doc, page_no):
        self.page = doc[page_no - 1]
        self.no = page_no
        self.M = self.page.rotation_matrix
        self.raw = []
        for d in self.page.get_drawings():
            r = d["rect"] * self.M
            if r.x1 < 1080 or r.x0 > 1620 or r.y1 < 180 or r.y0 > 1010:
                continue
            self.raw.append((d, r))
        verts = sorted({round(x0, 2) for x0, y0, x1, y1, c in self.segs("red") if abs(x0 - x1) < 0.05
                        and abs(y1 - y0) * self.K > 30 and 1250 < x0 < 1380})
        if len(verts) != 4:
            raise SystemExit(f"RECV_FAIL арк. {page_no}: ліній колон вежі {verts}")
        self.xs, self.xn = (verts[0] + verts[1]) / 2, (verts[2] + verts[3]) / 2
        span = (self.xn - self.xs) * self.K
        marks = sorted(y0 for x0, y0, x1, y1, c in self.segs("black")
                       if abs(y0 - y1) < 0.05 and 23.0 < abs(x1 - x0) < 24.2 and 1370 < min(x0, x1) < 1380)
        self.y33 = marks[0]
        self.marks = marks
        self.check = {"tower_span_mm": round(span * 1000), "tower_span_plan_mm": 6004}

    def segs(self, color):
        for d, r in self.raw:
            if color != "any" and cname(d.get("color")) != color:
                continue
            for it in d["items"]:
                if it[0] == "l":
                    a, b = it[1] * self.M, it[2] * self.M
                    yield a.x, a.y, b.x, b.y, cname(d.get("color"))

    def Y(self, x):
        return 51.401 + (x - self.xs) * self.K

    def z(self, y):
        return 33.0 - (y - self.y33) * self.K

    def boxes(self, color, Y0, z0, Y1, z1, nmin=20):
        out = []
        for d, r in self.raw:
            if cname(d.get("color")) != color or len(d["items"]) < nmin:
                continue
            a, b = self.Y(r.x0), self.Y(r.x1)
            lo, hi = self.z(r.y1), self.z(r.y0)
            if a >= Y0 and b <= Y1 and lo >= z0 and hi <= z1:
                out.append((a, b, lo, hi))
        if not out:
            return None
        return [r3(min(o[0] for o in out)), r3(max(o[1] for o in out)), r3(min(o[2] for o in out)), r3(max(o[3] for o in out))]

    def hlines(self, color, Y0, Y1, z0, z1, lmin):
        out = set()
        for x0, y0, x1, y1, c in self.segs(color):
            if abs(y0 - y1) < 0.05 and abs(x1 - x0) * self.K >= lmin:
                a, b = sorted((self.Y(x0), self.Y(x1)))
                # лінія майданчика перекриває вежу між колонами (Y0..Y1 — внутрішня смуга)
                if a <= Y0 and b >= Y1 and z0 <= self.z(y0) <= z1:
                    out.add((r3(self.z(y0)), r3(a), r3(b)))
        return sorted(out)

    def crop(self, name, Y0, z0, Y1, z1, dpi):
        x0 = self.xs + (Y0 - 51.401) / self.K
        x1 = self.xs + (Y1 - 51.401) / self.K
        ya = self.y33 + (33.0 - z1) / self.K
        yb = self.y33 + (33.0 - z0) / self.K
        self.page.get_pixmap(dpi=dpi, clip=pymupdf.Rect(x0, ya, x1, yb)).save(CROPS / name)
        return f"inbox/raw/pdf_crops/{name}"

    def bbox(self, Y0, z0, Y1, z1):
        return [round(self.xs + (Y0 - 51.401) / self.K, 1), round(self.y33 + (33.0 - z1) / self.K, 1),
                round(self.xs + (Y1 - 51.401) / self.K, 1), round(self.y33 + (33.0 - z0) / self.K, 1)]


def sheets345(doc, rep):
    s4 = Section(doc, 4)
    s5 = Section(doc, 5)
    lv = s4.hlines("red", 51.60, 57.00, -7, 35, 5.3)
    levels = sorted({l[0] for l in lv})
    rep["sheet4"] = {"tower_span_mm": s4.check, "marks_y": s4.marks[:12], "tower_red_levels": levels}
    # звірка відміток
    need = {"+30.000": 30.0, "+26.800": 26.8, "+24.400": 24.4, "+22.000": 22.0, "+19.400": 19.4,
            "+9.200": 9.2, "±0.000": 0.0, "-2.400": -2.4, "-5.800": -5.8}
    found = {k: min(levels, key=lambda z: abs(z - v)) for k, v in need.items()}
    rep["sheet4"]["levels_vs_labels"] = {k: {"label": v, "line": found[k], "err_mm": round((found[k] - v) * 1000)} for k, v in need.items()}
    bad = [k for k, v in need.items() if abs(found[k] - v) > 0.02]
    if bad:
        print("RECV_WARN відмітки арк. 4 не збігаються з лініями:", bad)
    cr_tower = s4.crop("p04_recv_tower_250dpi.png", 45.5, 18.0, 58.5, 36.5, 250)
    cr_low = s4.crop("p04_recv_low_220dpi.png", 41.5, -7.5, 68.5, 18.5, 220)
    cr_t10 = s5.crop("p05_recv_T10_400dpi.png", 50.5, 18.5, 57.8, 28.5, 400)

    card("Приймальна вежа (4)", "tower_levels",
         {"roof_z": 33.0, "roof_rails_z": [33.6, 34.2], "platforms_z": [30.0, 26.8, 24.4, 22.0, 19.4, 9.2, 0.0],
          "pit_floor_z": [-2.4, -5.8], "slab_t_m": 0.2, "frame_top_z": 33.0},
         "m", "відмітки майданчиків вежі в розрізі (червоні лінії на всю ширину 5.8 м між колонами)", 4,
         s4.bbox(51.0, -6.5, 57.8, 34.5), cr_tower, "derived",
         f"Підписані відмітки +33,000, +30,000, +26,800, +24,400, +22,000, +19,400, +9,200, ±0,000, -2,400, -5,800. "
         f"Червоні лінії: {rep['sheet4']['levels_vs_labels']}. Низ кожного майданчика на 0.2 м нижче; поручні +0.6 і +1.2 "
         "(над +33.0: 33.60, 34.20 — дах вежі з огородженням). Знак «+19,400» намальований на 0.19 м вище за лінію майданчика (19.59), "
         f"лінія — рівно 19.400. Ширина вежі між осями колон у розрізі {s4.check['tower_span_mm']} мм (план 6004). "
         "Висота вежі +33.0 підтверджена; голови H1 і H3 стоять над дахом.",
         quote="+33,000 +30,000 +26,800 +24,400 +22,000 +19,400 +9,200")

    heads = {
        "H1": s4.boxes("blue", 53.5, 33.5, 56.5, 36.5),
        "H3": s4.boxes("blue", 51.8, 33.3, 53.2, 36.0, 15),
        "H4": s4.boxes("blue", 53.5, 27.0, 56.5, 29.8),
        "H2": s4.boxes("blue", 53.5, 22.5, 56.5, 25.2),
    }
    tubes = sorted({r3(s4.Y(x0)) for x0, y0, x1, y1, c in s4.segs("blue")
                    if abs(x0 - x1) < 0.05 and abs(y1 - y0) * s4.K > 30})
    boot_top = min(s4.z(max(y0, y1)) for x0, y0, x1, y1, c in s4.segs("blue")
                   if abs(x0 - x1) < 0.05 and abs(y1 - y0) * s4.K > 30)
    rep["sheet4"]["heads"] = heads
    rep["sheet4"]["tube_lines_Y"] = tubes
    rep["sheet4"]["boot_top_z"] = r3(boot_top)
    card("Норії H1-H4 (існуючі)", "heads_and_tubes_section",
         {"heads_bbox_Y_z": heads, "tubes_Y": tubes, "boot_top_z": r3(boot_top),
          "tube_len_est_m": {k: r3(v[2] - boot_top) for k, v in heads.items() if v}},
         "m", "голови норій у розрізі: [Y від, Y до, z низ, z верх]; лінії труб; верх башмаків", 4,
         s4.bbox(51.5, -6.0, 57.0, 36.5), cr_tower, "derived",
         "H1 — над дахом вежі (+33), H3 — поряд над дахом, H4 — на майданчику +26.8, H2 — на +22.0. H1, H2, H4 намальовані тим самим блоком голови "
         "(≈2.35 × 2.0 м), H3 — менший. Труби H1/H2/H4 у розрізі збігаються (ряд уздовж X): пари ліній Y 54.59/54.91 і 55.49/55.81 → вісь Y 55.20, "
         "між трубами 0.90, труба ≈0.32. H3: Y 52.27…52.74 (труби вздовж X, накладаються) → вісь 52.50. Довжина труби = від верху башмака до низу голови — "
         "оцінка з блоків креслення, не з паспорта. Продуктивність кожної 100 т/год — арк. 1.", quote="H1 H2 H3 H4")

    sep = s4.boxes("blue", 44.0, 9.8, 47.0, 13.5, 4)
    card("Сепаратор 5 і бункер Ш1 (очисна вежа)", "levels",
         {"estakada_cols_Y": [43.105, 47.905], "floor_z": 9.2, "floor_extends_to_tower_Y": [42.98, 57.30],
          "bunker_Sh1": {"Y": [43.19, 47.81], "box_z": [7.0, 9.2], "outlet_z": 4.66, "outlet_Y": 45.50},
          "separator_bbox_Y_z": sep, "separator_room": {"Y": [42.98, 48.02], "walls_z": [9.2, 16.1], "roof_z": 16.29,
                                                        "roof_raised_part": {"Y": [45.21, 48.02], "top_z": 17.49}},
          "ladder": {"Y": [48.35, 49.09], "z": [11.94, 17.29]}, "truck_clear_under_outlet_m": 4.66 + 0.45},
         "m", "очисна вежа на естакаді 2300/4000/2300 × 4800: бункер Ш1 під підлогою +9.2, сепаратор 5 на +9.2, приміщення до +16.3", 4,
         s4.bbox(42.5, -0.6, 49.5, 17.8), cr_low, "derived",
         "Підписано +9,200, +16,300, 9200, 5930, 4800, 3500, Ш1, 5. Фундаменти колон естакади в розрізі на Y 42.81…43.41 і 47.61…48.21 → осі 43.105 / 47.905, "
         "точно як у плані арк. 2 (перевірка прив'язки Y). Бункер: прямокутна частина +7.0…+9.2, лійка до випуску ≈+4.66 із засувкою 6.21; під ним проїзд "
         "машини (габарит машини в розрізі до +3.55). Самоплив 6.20 з лійки Ш1 іде під 40° у приямок вежі (Y 46.1, z 4.7 → Y 52.3, z -0.5). "
         "Сепаратор живиться самопливом 45° від вежі (Y 52.33, z 23.32 → Y 47.27, z 18.26), засувки 6.18 / 6.19 на +16.3. "
         "Тип і модель сепаратора не підписані.", quote="Ш1 5 +9,200 +16,300 9200 5930")

    pit_bld = {"columns_Y": [60.17, 67.19], "columns_z": [0.335, 7.104], "roof_box": {"Y": [59.92, 67.38], "z": [7.104, 10.103]},
               "deck_z": 0.106, "plinth_z": 0.335, "pit_floor_z": -4.99, "pit_slab_under_z": -5.393,
               "pit_Y_inner": [60.648, 66.652]}
    card("Завальна яма (1)", "section_levels", pit_bld, "m",
         "будівля ями в розрізі: колони до +7.10, дах-ферма +7.10…+10.10, проїзд +0.100, дно ями -5.000", 4,
         s4.bbox(57.0, -6.5, 68.5, 10.5), cr_low, "derived",
         "Підписано +0,100, 550 (проїзд над землею: 0.100 − (−0.45) = 0.55 ✓ до ground_z), -5,000, 6000, 3500, 2000 / 2000, 400, T1, 6.24, 6.25. "
         "Лінія дна -4.990, низ плити -5.393. Покрівля намальована прямокутником 3.0 м заввишки (ферма або шатро), форма даху не показана. "
         "Бічні ригелі стін на +1.13 / 2.53 / 3.93 / 5.33 / 6.59 — стіни, найімовірніше, обшиті (профлист); не підписано.",
         quote="+0,100 550 -5,000")

    t1 = [(s4.Y(x0), s4.z(y0), s4.Y(x1), s4.z(y1)) for x0, y0, x1, y1, c in s4.segs("blue")
          if abs(x1 - x0) > 1 and abs(y1 - y0) > 1 and 7.5 < math.degrees(math.atan2(abs(y1 - y0), abs(x1 - x0))) < 10
          and 55 < s4.Y(min(x0, x1)) < 66 and math.hypot(x1 - x0, y1 - y0) * s4.K > 5]
    ang = [math.degrees(math.atan2(abs(b[3] - b[1]), abs(b[2] - b[0]))) for b in t1]
    rep["sheet4"]["T1_casing"] = t1
    card("Конвеєр T1 (яма → вежа)", "incline",
         {"casing_lines": [[r3(v) for v in l] for l in t1], "angle_deg": round(sum(ang) / len(ang), 2) if ang else None,
          "label_deg": 9, "low_end_Y": 65.2, "high_end_Y": 56.0},
         "m", "похилий T1 від лійок ями (Y 62.65 / 64.65) вгору на південь до башмаків у приямку вежі", 4,
         s4.bbox(55.5, -5.5, 66.0, -2.5), cr_low, "derived",
         "Підпис «9°». Кожух ≈0.5 м; нижній кінець під північною лійкою на ≈-4.8, верхній над віссю ряду норій на ≈-3.2…-2.9 (верх башмаків -3.83). "
         "Дві засувки 6.24 і 6.25 під лійками ями (2000 між ними). Тип T1 не підписаний.", quote="9° T1 6.24 6.25")

    # --- стики: T7 (арк. 4) і T10 (арк. 5) --------------------------------------------------
    def marks_y(sec, lo, hi):
        ys = sorted({r3(sec.Y(x0)) for x0, y0, x1, y1, c in sec.segs("(1.0, 1.0, 0.0)")
                     if abs(x0 - x1) < 0.02 and 0.09 < abs(y1 - y0) * sec.K < 0.25 and lo < sec.Y(x0) < hi
                     and 25.7 <= sec.z(min(y0, y1)) and sec.z(max(y0, y1)) <= 26.5})
        return ys
    t7_axis = [(s4.Y(x0), s4.z(y0), s4.Y(x1), s4.z(y1)) for x0, y0, x1, y1, c in s4.segs("(1.0, 1.0, 0.0)")
               if abs(y0 - y1) * s4.K < 0.05 and abs(x1 - x0) * s4.K > 0.5 and 24 < s4.Y(x0) < 56.5]
    p = np.array([[a, b] for a, b, c, d in t7_axis] + [[c, d] for a, b, c, d in t7_axis])
    slope, icpt = np.polyfit(p[:, 0], p[:, 1], 1)
    t7_marks = marks_y(s4, 51.0, 56.5)
    t10_axis = sorted({r3(s5.z(y0)) for x0, y0, x1, y1, c in s5.segs("(1.0, 1.0, 0.0)")
                       if abs(y0 - y1) < 0.05 and abs(x1 - x0) * s5.K > 0.5 and 24 < s5.Y(x0) < 55})
    t10_marks = marks_y(s5, 51.0, 56.5)
    rep["joints"] = {"T7": {"axis_z_at": {"Y55.36": r3(slope * 55.36 + icpt), "Y24.87": r3(slope * 24.87 + icpt)},
                            "slope_deg": round(math.degrees(math.atan(abs(slope))), 2), "yellow_marks_Y": t7_marks},
                     "T10": {"axis_z": t10_axis, "yellow_marks_Y": t10_marks}}
    card("Стик T7 з приймальною вежею", "T7_in_receiving_tower",
         {"x": -1.052, "tail_pulley_Y": 55.36, "axis_z_at_tail": r3(slope * 55.36 + icpt),
          "inlets_Y": [52.37, 53.36, 54.01], "inlets_chain_mm": [1000, 642, 1358], "slope_deg": round(math.degrees(math.atan(abs(slope))), 2),
          "casing_plan_x": [-1.25, -0.854], "casing_north_end_Y": 55.571},
         "m", "T7 (новий, ТЦС-320, 30.5 м) заходить у вежу на +26.0: хвіст і 3 точки завантаження всередині існуючої вежі", 4,
         s4.bbox(51.0, 24.5, 56.5, 28.0), cr_tower, "derived",
         f"Жовта вісь T7 (арк. 4): z = {slope:.5f}·Y + {icpt:.3f}; мітки барабанів і входів на Y {t7_marks}. Ланцюг 1000 / 642 / 1358 підписаний "
         "(від першого входу до хвостового барабана: 52.37 → 53.37 → 54.01 → 55.37). План арк. 3 «+24,400, +25,600»: кожух X -1.25…-0.854 до Y 55.57. "
         "Специфікація арк. 8: T7 «три точки завантаження, встановлений під кутом 2°» — на кресленні ≈1.6°. Джерела входів за арк. 1: H1 (засувка 6.1), "
         "H3 (ввід 7, засувка 6.3), H4 (ввід 7, засувка 6.5). Які саме патрубки вежі йдуть на котрий вхід, з розрізу однозначно не видно.",
         quote="1000 642 1358")
    card("Стик T10 з приймальною вежею", "T10_in_receiving_tower",
         {"x": -0.152, "head_pulley_Y": 53.946, "axis_z": t10_axis, "casing_z": [25.773, 26.271],
          "outlet_intermediate": {"Y": 51.869, "z_from": 25.8, "to": "врізка в самопливну трубу 45° на очисну вежу ≈(Y 51.9, z 22.9)"},
          "outlet_head": {"Y": 53.865, "to": "ввід одинарний 7: 6.9 → T5 (вхід ≈Y 53.70, z 22.0), 6.10 → T3 (вхід ≈Y 53.90, z 19.4…20.8)"},
          "drive": "праве (арк. 9), мотор-редуктор у вежі на сході від кожуха (план арк. 3)", "casing_plan_x": [-0.35, 0.047]},
         "m", "T10 (новий, ТЦС-320, 29.0 м) закінчується у вежі на +26.0 приводною головкою; 2 точки розвантаження", 5,
         s5.bbox(50.5, 19.0, 57.0, 27.0), cr_t10, "derived",
         f"Жовта вісь T10 горизонтальна z {t10_axis}; мітки на Y {t10_marks}. Лійки під кожухом на Y 51.87 і 53.87 (помаранчеві осі вниз). "
         "2300 і 2500 від південних колон вежі підписані біля кінців спусків на T5 (+22) і T3 (+19.4): Y 53.70 і 53.90. "
         "Арк. 1: «Врізка в самопливну трубу подачі зерна на очисну вежу (сепаратор або бункер чистого зерна)», «На транспортер поз. Т5 (силоси волог. зерна)», "
         "«На транспортер поз. Т3 (завантаження сушарки)». T3 і T5 — існуючі конвеєри, у цьому PDF є лише їх кінці.",
         quote="Врізка в самопливну трубу подачі зерна на очисну вежу")

    # --- арк. 3: плани вежі на +24.4 / +25.6 / +26.8 -----------------------------------------------
    cr3 = CROPS / "p03_recv_plans_500dpi.png"
    p3 = doc[2]
    p3.get_pixmap(dpi=500, clip=pymupdf.Rect(806, 72, 950, 253)).save(cr3)
    p3.get_pixmap(dpi=500, clip=pymupdf.Rect(1076, 72, 1215, 259)).save(CROPS / "p03_recv_plan_268_500dpi.png")
    card("Приймальна вежа (4)", "upper_plans_sheet3",
         {"plan_24400_25600": {"west_part": {"x": [-2.002, 1.799], "z": 24.4}, "east_part": {"x": [1.799, 4.203], "z": 22.0},
                                "east_bay": {"x": [4.203, 5.203], "y": [54.009, 57.405], "z": 22.0},
                                "gallery_walls_x": [-2.002, 0.799], "gallery_end_Y": 51.406, "gallery_z": 25.6,
                                "stairs_Y": [49.69, 50.29], "stairs_x": [[-1.994, -1.30], [0.105, 0.799]]},
          "plan_25600_26800": {"platform": {"x": [-1.998, 4.199], "y": [51.406, 57.405], "z": 26.8},
                               "landing_red": {"x": [-2.998, 0.795], "y": [50.605, 54.009]},
                               "west_bay": {"x": [-2.998, -1.998], "y": [54.009, 57.405]}},
          "H2_drive_towards": "+X (схід, мотор за колоною в еркері 1000 × 3400)", "H4_drive_towards": "-X (захід, у еркері 1000)"},
         "m", "плани вежі на арк. 3 (у масштабі 68.855 мм/pt, прив'язані до колон 6200 × 6000)", 3,
         [806, 72, 1215, 259], "inbox/raw/pdf_crops/p03_recv_plans_500dpi.png", "derived",
         "Підписи: «План на відм. +24,400 м, +25,600 м» (3800 | 2400, 6000, 3400, 1650, 1000, 1100, 6200, 950 | 900 | 950, 2800, +24,400, +22,000, +25,600) і "
         "«План на відм. +25,600 м, +26,800 м» (6200, 6000, 1500, 1600, 2200, 1000, 1650, 1100, 800, +26,800). Колони вежі на арк. 3: 90.06 × 87.12 pt → 6201 × 5999 мм. "
         "Галерея +25.6 закінчується на південній лінії колон (Y 51.406); по обидва боки від конвеєрів біля торця — сходові марші (≈0.7 м) униз на +24.4 і вгору на +26.8 "
         "(майданчик 800 на південь від колон). Кольори: нові конструкції пурпурові, майданчик 800 / еркер 1000 на +26.8 — червоні (як існуючі на арк. 2); що це означає, не підписано.",
         quote="План на відм. +24,400 м, +25,600 м")


FLOW_EDGES = [
    # звідки, куди, т/год (None — не підписано), позначка, аркуш, basis
    ("H1", "T7 (вхід 1)", 100, "засувка 6.1", 1, "sourced"),
    ("H3", "ввід одинарний 7 (H3)", 100, "поз. 7", 1, "sourced"),
    ("ввід одинарний 7 (H3)", "T7 (вхід 2)", 100, "засувка 6.3 (похила гілка)", 1, "sourced"),
    ("ввід одинарний 7 (H3)", "існуючий маршрут H3", 100, "засувка 6.2 (пряма гілка)", 1, "derived"),
    ("H4", "ввід одинарний 7 (H4)", 100, "поз. 7", 1, "sourced"),
    ("ввід одинарний 7 (H4)", "T7 (вхід 3)", 100, "засувка 6.5 (похила гілка)", 1, "sourced"),
    ("ввід одинарний 7 (H4)", "існуючий маршрут H4", 100, "засувка 6.4 (пряма гілка)", 1, "derived"),
    ("T7", "T8 (силоси 1, 2)", 100, "проміжна засувка T7", 1, "sourced"),
    ("T7", "T11 (міст до H6)", 100, "голова T7 над хвостом T11 у H5", 1, "sourced"),
    ("H5", "T10", 100, "ввід тройний 10, центральна гілка", 1, "sourced"),
    ("T14", "T10", 100, "голова T14 над хвостом T10 у H5", 1, "sourced"),
    ("T10", "самопливна труба на очисну вежу (сепаратор 5 або Ш1)", 100,
     "проміжна засувка T10: «Врізка в самопливну трубу подачі зерна на очисну вежу (сепаратор або бункер чистого зерна)»", 1, "sourced"),
    ("T10", "ввід одинарний 7 (T10)", 100, "голова T10", 1, "sourced"),
    ("ввід одинарний 7 (T10)", "T5 (силоси вологого зерна)", 100, "засувка 6.9: «На транспортер поз. Т5 (силоси волог. зерна)»", 1, "sourced"),
    ("ввід одинарний 7 (T10)", "T3 (завантаження сушарки)", 100, "засувка 6.10: «На транспортер поз. Т3 (завантаження сушарки)»", 1, "sourced"),
    ("Завальна яма (1)", "T1", None, "засувки 6.24, 6.25 під двома лійками", 4, "derived"),
    ("T1", "башмак H1 (вісь T1 X 1.10 = вісь H1)", None, "T1, 9°", 4, "derived"),
    ("T2", "H2", None, "«Самоплив з транспортера T2 на норію H2»", 4, "sourced"),
    ("силоси «2», «3»", "T6 / T2", None, "T6, T2 під силосами на ±0.000 (план)", 2, "derived"),
    ("«1» (вузол на +30.6…+31.8)", "самопливна труба 45° → сепаратор 5", None, "6.16; труба Y 52.33 z 23.32 → Y 47.27 z 18.26; 6.18 / 6.19", 4, "derived"),
    ("сепаратор 5", "бункер Ш1", None, "5, Ш1", 4, "derived"),
    ("бункер Ш1", "автотранспорт під естакадою", None, "засувка 6.21, «Напрямок проїзду»", 4, "derived"),
    ("бункер Ш1", "приямок вежі (норія)", None, "засувка 6.20, самоплив 40°", 4, "derived"),
    ("вежа", "будівля «4» (6)", None, "T4", 2, "derived"),
]


def flows(rep):
    rep["flow_edges"] = [dict(zip(("from", "to", "t_h", "mark", "sheet", "basis"), e)) for e in FLOW_EDGES]
    card("Граф потоків: стик старої і нової черги", "flow_edges_new_old", rep["flow_edges"], "t/h",
         "ребра «звідки → куди, т/год, позначка» для приймальної частини і стиків (арк. 1 — схема, арк. 2, 4 — план і розріз)", 1,
         None, "inbox/raw/pdf_crops/overview_p01.png", "derived",
         "Арк. 1: H1, H3, H4 намальовані зеленим пунктиром (існуючі), нові ввідні 7 і засувки 6.1-6.10 — синім. H2 на арк. 1 немає. "
         "Усі нові ребра підписані «100 т/год»; для ребер старого блоку (T1, T2, T6, T4, сепаратор, Ш1) продуктивність у PDF не вказана. "
         "Пряма/похила гілка вводу 7 визначена за символами засувок (похила — хрест на 45°, пряма — «_|»), це прочитання схеми, не підпис.",
         quote="Врізка в самопливну трубу подачі зерна на очисну вежу (сепаратор або бункер чистого зерна); На транспортер поз. Т5 (силоси волог. зерна); На транспортер поз. Т3 (завантаження сушарки)")
    card("Засувки 6.x на аркушах 4-5", "gate_numbering_conflict",
         {"sheet1_spec": "6.1 H1; 6.2/6.3 ввід 7 H3; 6.4/6.5 ввід 7 H4; 6.6-6.8 ввід 10 H5; 6.9/6.10 ввід 7 T10 (спец. арк. 9: 6.1-6.10, 10 шт.)",
          "sheet4_5_labels": "6.1, 6.2 біля голови H1; 6.4, 6.6 під вузлом «1»; 6.10, 6.22, 6.23 у приямку вежі; 6.16, 6.18-6.21, 6.24, 6.25 — поза специфікацією"},
         None, "нумерація засувок у розрізах 4-5 не збігається зі схемою арк. 1 і специфікацією", 4,
         None, "inbox/raw/pdf_crops/p04_recv_tower_250dpi.png", "sourced",
         "Позиції 6.16-6.25 у специфікації (арк. 8-12) відсутні: це, найімовірніше, засувки існуючого комплексу (узгоджується з рішенням «блок існуючий»). "
         "6.6 на арк. 1 стоїть на вводі тройному H5, а на арк. 4 — у приймальній вежі; 6.10 на арк. 1 — на T10, на арк. 4 — у приямку. Питання проєктанту.",
         kind="conflict")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    doc = pymupdf.open(PDF)
    rep = {"pdf": PDF_NAME, "extractor": EXTRACTOR, "frame": "SITE.json: X схід від осі веж H5/H6, Y північ від осі ряду 3-6, м"}
    sheet2(doc, rep)
    sheets345(doc, rep)
    flows(rep)
    RECORDS.mkdir(parents=True, exist_ok=True)
    written = 0
    for c in CARDS:
        path = RECORDS / f"{c['id']}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") != "unverified":
            continue
        path.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1
    rep["cards"] = [c["id"] for c in CARDS]
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.write_text(json.dumps(rep, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"RECV_PASS factor={rep['sheet2']['factor_mm_per_pt']} cards={len(CARDS)} written={written}")
    for c in rep["sheet2"]["checks"]:
        print("CHECK", c["what"], c["measured_mm"], c["rel"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
