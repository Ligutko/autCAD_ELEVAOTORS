"""Розкладка майданчика з векторного плану, аркуш 2 «Технологія 06.06.24.pdf».

Що робить:
1. Читає векторні шляхи аркуша 2 через PyMuPDF (без OCR, без растру).
2. Знаходить кола силосів: кожне коло на плані намальоване двома синіми
   половинами, бо його перетинає галерея тунелю. Половини зливаються за центром,
   коло підганяється методом найменших квадратів по всіх вершинах.
3. Масштаб лист -> об'єкт бере з відомого радіуса 11000 мм
   (D = 22,0 м: каталог і OCR аркушів 8, 10, 12).
4. Звіряє виміряні відстані між осями з підписаними на аркуші розмірами,
   які OCR уже прочитав разом із рамками (24000, 29000, 12200).
   Незбіг більше 0.5 % -> код виходу 3, картки не пишуться.
5. Пише звіт `inbox/reports/site_plan_p2.md` / `.json` і картки `unverified`.

Картки цього скрипта мають `source.extractor = "extract_plan_p2.py"`.
`parse_local.py` такі картки не видаляє.
Статус `cited` скрипт не ставить ніколи. `FACTS.json` не пише.

Запуск (з кореня проєкту, потрібен pymupdf):
    python inbox/extract_plan_p2.py
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

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
PDF = ROOT / "Технологія 06.06.24.pdf"
PDF_NAME = PDF.name
PAGE_NO = 2
OCR_TSV = INBOX / "raw" / "ocr" / "page_02.tsv"
REPORT_MD = INBOX / "reports" / "site_plan_p2.md"
REPORT_JSON = INBOX / "reports" / "site_plan_p2.json"
RECORDS = INBOX / "records"
EXTRACTOR = "extract_plan_p2.py"

KNOWN_RADIUS_MM = 11000.0
PX_PER_PT = 300.0 / 72.0  # рендер OCR 300 dpi
TOLERANCE_REL = 0.005
BLUE = (0.0, 0.0, 1.0)
RED = (1.0, 0.0, 0.0)

# Номери силосів за схемою аркуша 1 і фасадом аркуша 7:
# верхній ряд 1, 2; нижній ряд 3, 4, 5, 6, зліва направо.
ROW_NUMBERS = {0: (1, 2), 1: (3, 4, 5, 6)}


def fit_circle(points: np.ndarray) -> tuple[float, float, float]:
    x = points[:, 0]
    y = points[:, 1]
    a = np.c_[2.0 * x, 2.0 * y, np.ones(len(x))]
    b = x * x + y * y
    cx, cy, c = np.linalg.lstsq(a, b, rcond=None)[0]
    return float(cx), float(cy), float(math.sqrt(c + cx * cx + cy * cy))


def rotated_points(drawing: dict, matrix: pymupdf.Matrix) -> list[tuple[float, float]]:
    pts = []
    for item in drawing["items"]:
        if item[0] != "l":
            continue
        for point in item[1:3]:
            q = point * matrix
            pts.append((q.x, q.y))
    return pts


def find_silo_circles(page: pymupdf.Page) -> list[dict]:
    matrix = page.rotation_matrix
    halves = []
    for drawing in page.get_drawings():
        rect = drawing["rect"]
        if drawing.get("color") != BLUE or len(drawing["items"]) < 40:
            continue
        # У неповернутій системі півколо: вузьке і високе.
        if not (260.0 < rect.height < 290.0 and 100.0 < rect.width < 140.0):
            continue
        pts = np.array(rotated_points(drawing, matrix))
        halves.append({"points": pts, "fit": fit_circle(pts)})
    circles: list[dict] = []
    for half in halves:
        cx, cy, _ = half["fit"]
        for circle in circles:
            if abs(circle["cx"] - cx) < 3.0 and abs(circle["cy"] - cy) < 3.0:
                circle["parts"].append(half)
                break
        else:
            circles.append({"cx": cx, "cy": cy, "parts": [half]})
    result = []
    for circle in circles:
        pts = np.vstack([part["points"] for part in circle["parts"]])
        cx, cy, radius = fit_circle(pts)
        residual = float(np.abs(np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - radius).max())
        result.append(
            {
                "cx_pt": cx,
                "cy_pt": cy,
                "radius_pt": radius,
                "halves": len(circle["parts"]),
                "vertices": int(len(pts)),
                "max_residual_pt": residual,
            }
        )
    return result


def find_tower_outlines(page: pymupdf.Page, silos: list[dict], factor: float) -> list[dict]:
    """Червоні замкнені прямокутники між силосами, 4..6 м у плані."""
    matrix = page.rotation_matrix
    found = []
    for drawing in page.get_drawings():
        if drawing.get("color") != RED or len(drawing["items"]) < 8:
            continue
        rect = drawing["rect"] * matrix
        w_mm = rect.width * factor
        h_mm = rect.height * factor
        if not (4000.0 < w_mm < 6000.0 and 4000.0 < h_mm < 6000.0):
            continue
        cx = (rect.x0 + rect.x1) / 2.0
        cy = (rect.y0 + rect.y1) / 2.0
        near = sorted(silos, key=lambda s: math.hypot(s["cx_pt"] - cx, s["cy_pt"] - cy))
        if math.hypot(near[0]["cx_pt"] - cx, near[0]["cy_pt"] - cy) * factor > 20000.0:
            continue
        key = (round(cx, 1), round(cy, 1))
        if any((round(f["cx_pt"], 1), round(f["cy_pt"], 1)) == key for f in found):
            continue
        found.append(
            {
                "cx_pt": cx,
                "cy_pt": cy,
                "width_mm": w_mm,
                "depth_mm": h_mm,
                "items": len(drawing["items"]),
            }
        )
    return found


def read_ocr_words() -> list[dict]:
    words = []
    lines = OCR_TSV.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) != len(header):
            continue
        row = dict(zip(header, parts))
        if not row["text"].strip():
            continue
        words.append(
            {
                "text": row["text"],
                "bbox": [
                    int(row["left"]),
                    int(row["top"]),
                    int(row["left"]) + int(row["width"]),
                    int(row["top"]) + int(row["height"]),
                ],
                "conf": float(row["conf"]),
            }
        )
    return words


def ocr_hits(words: list[dict], text: str) -> list[dict]:
    return [w for w in words if w["text"] == text and w["conf"] >= 90.0]


def card_id(key: str) -> str:
    return "rec_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:8]


def make_card(subject, kind, claim, quote, bbox, notes, today):
    key = "|".join(
        [
            subject,
            kind,
            str(claim.get("name", claim.get("sheet"))),
            PDF_NAME,
            str(PAGE_NO),
            EXTRACTOR,
            json.dumps(claim, ensure_ascii=False, sort_keys=True),
        ]
    )
    return {
        "id": card_id(key),
        "subject": subject,
        "kind": kind,
        "claim": claim,
        "source": {
            "origin": "local",
            "path": PDF_NAME,
            "page": PAGE_NO,
            "quote": quote,
            "bbox": bbox,
            "retrieved_at": today,
            "extractor": EXTRACTOR,
        },
        "status": "unverified",
        "conflict_with": [],
        "notes": notes,
        "seen_in": [],
    }


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    today = date.today().isoformat()
    doc = pymupdf.open(PDF)
    if doc.page_count != 12:
        print(f"PLAN_FAIL сторінок {doc.page_count}, очікується 12")
        return 2
    page = doc[PAGE_NO - 1]
    silos = find_silo_circles(page)
    if len(silos) != 6:
        print(f"PLAN_FAIL знайдено кіл силосів: {len(silos)}, очікується 6")
        return 3

    mean_radius_pt = sum(s["radius_pt"] for s in silos) / len(silos)
    factor = KNOWN_RADIUS_MM / mean_radius_pt  # мм об'єкта на 1 pt листа

    # Ряди: групуємо за вертикаллю на повернутій сторінці.
    rows: list[list[dict]] = []
    for s in sorted(silos, key=lambda s: (s["cy_pt"], s["cx_pt"])):
        for row in rows:
            if abs(row[0]["cy_pt"] - s["cy_pt"]) < 5.0:
                row.append(s)
                break
        else:
            rows.append([s])
    rows.sort(key=lambda r: r[0]["cy_pt"])
    if [len(r) for r in rows] != [2, 4]:
        print(f"PLAN_FAIL ряди {[len(r) for r in rows]}, очікується [2, 4]")
        return 3
    for index, row in enumerate(rows):
        row.sort(key=lambda s: s["cx_pt"])
        for silo, number in zip(row, ROW_NUMBERS[index]):
            silo["number"] = number

    by_no = {s["number"]: s for s in silos}
    origin = by_no[3]

    def to_site(cx_pt: float, cy_pt: float) -> tuple[float, float]:
        # X уздовж ряду праворуч, Y від нижнього ряду до верхнього, метри.
        return (
            (cx_pt - origin["cx_pt"]) * factor / 1000.0 + 0.0,
            -(cy_pt - origin["cy_pt"]) * factor / 1000.0 + 0.0,
        )

    def dist_mm(a: int, b: int, axis: str) -> float:
        key = "cx_pt" if axis == "x" else "cy_pt"
        return abs(by_no[a][key] - by_no[b][key]) * factor

    words = read_ocr_words()
    checks = []
    for label, a, b, axis, text in (
        ("вісь 3 - вісь 4, нижній ряд", 3, 4, "x", "24000"),
        ("вісь 5 - вісь 6, нижній ряд", 5, 6, "x", "24000"),
        ("вісь 1 - вісь 2, верхній ряд", 1, 2, "x", "24000"),
        ("вісь 4 - вісь 5, через вежу", 4, 5, "x", "29000"),
        ("вісь 3 - вісь 1, між рядами", 3, 1, "y", "25500"),
    ):
        measured = dist_mm(a, b, axis)
        annotated = float(text)
        hits = ocr_hits(words, text)
        # Рамка того підпису, що найближчий до середини проміжку між осями.
        mid_x = (by_no[a]["cx_pt"] + by_no[b]["cx_pt"]) / 2.0 * PX_PER_PT
        mid_y = (by_no[a]["cy_pt"] + by_no[b]["cy_pt"]) / 2.0 * PX_PER_PT
        hits.sort(
            key=lambda w: math.hypot(
                (w["bbox"][0] + w["bbox"][2]) / 2.0 - mid_x,
                (w["bbox"][1] + w["bbox"][3]) / 2.0 - mid_y,
            )
        )
        rel = abs(measured - annotated) / annotated
        checks.append(
            {
                "what": label,
                "annotated_mm": annotated,
                "measured_mm": round(measured, 1),
                "rel_error": round(rel, 5),
                "ocr_bbox": hits[0]["bbox"] if hits else None,
                "ocr_hits": len(hits),
                "ok": rel <= TOLERANCE_REL,
            }
        )
    failed = [c for c in checks if not c["ok"]]

    towers = find_tower_outlines(page, silos, factor)
    tower_rows = []
    for tower in sorted(towers, key=lambda t: t["cy_pt"]):
        x_m, y_m = to_site(tower["cx_pt"], tower["cy_pt"])
        tower_rows.append(
            {
                "center_m": [round(x_m, 3) + 0.0, round(y_m, 3) + 0.0],
                "outline_w_m": round(tower["width_mm"] / 1000.0, 3),
                "outline_d_m": round(tower["depth_mm"] / 1000.0, 3),
            }
        )

    silo_rows = []
    for number in sorted(by_no):
        s = by_no[number]
        x_m, y_m = to_site(s["cx_pt"], s["cy_pt"])
        silo_rows.append(
            {
                "number": number,
                "center_m": [round(x_m, 3) + 0.0, round(y_m, 3) + 0.0],
                "radius_m": round(s["radius_pt"] * factor / 1000.0, 4),
                "halves": s["halves"],
                "vertices": s["vertices"],
                "max_residual_mm": round(s["max_residual_pt"] * factor, 1),
            }
        )

    report = {
        "pdf": PDF_NAME,
        "page": PAGE_NO,
        "method": "PyMuPDF get_drawings, rotation_matrix, least-squares circle fit",
        "pymupdf": pymupdf.__version__,
        "scale": {
            "sheet_unit": "pt",
            "world_unit": "mm",
            "factor_mm_per_pt": round(factor, 4),
            "from": "mean fitted radius of 6 silo wall circles = 11000 mm",
            "mean_radius_pt": round(mean_radius_pt, 4),
        },
        "frame": "X along silo rows to the right, Y from lower row to upper row, origin = axis of silo 3, metres",
        "silos": silo_rows,
        "tower_outlines": tower_rows,
        "checks": checks,
        "pass": not failed,
        "status": "unverified",
        "not_extracted": [
            "elevation of silo base (+0,600 on sheets 4, 5, 7) is not a plan dimension",
            "aeration duct pattern inside circles",
            "aeration fan symbols around each silo",
            "tunnel bands through silo axes",
            "receiving area at the top of the sheet",
        ],
    }

    if failed:
        REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("PLAN_FAIL " + "; ".join(f"{c['what']}: {c['measured_mm']} vs {c['annotated_mm']}" for c in failed))
        return 3

    subject_site = "Зерновий комплекс"
    cards = []
    first_24000 = next((c for c in checks if c["annotated_mm"] == 24000.0), None)
    cards.append(
        make_card(
            subject_site,
            "scale",
            {"sheet": 2, "sheet_unit": "pt", "world_unit": "mm", "factor": round(factor, 4)},
            "24000",
            first_24000["ocr_bbox"] if first_24000 else None,
            "Масштаб з векторного плану: середній радіус 6 кіл стіни силоса = 11000 мм. "
            "Перевірено на підписаних розмірах аркуша: "
            + ", ".join(f"{c['annotated_mm']:.0f} мм -> {c['measured_mm']:.0f} мм" for c in checks)
            + ". Цитата — підпис розміру, з яким звірено масштаб.",
            today,
        )
    )
    cards.append(
        make_card(
            subject_site,
            "count",
            {"name": "silos_on_plan", "value": 6, "unit": "pcs"},
            "R11000",
            None,
            "Шість кіл стіни силоса на плані аркуша 2 (2 у верхньому ряду, 4 у нижньому). "
            "Каталог має quantity 2 для силоса, це інше поле. Рядок R11000 OCR не прочитав, рамки немає.",
            today,
        )
    )
    for check in checks:
        name = {
            "вісь 3 - вісь 4, нижній ряд": "axis_spacing_row_3_4",
            "вісь 5 - вісь 6, нижній ряд": "axis_spacing_row_5_6",
            "вісь 1 - вісь 2, верхній ряд": "axis_spacing_row_1_2",
            "вісь 4 - вісь 5, через вежу": "axis_spacing_4_5_across_tower",
            "вісь 3 - вісь 1, між рядами": "axis_spacing_between_rows",
        }[check["what"]]
        vertical_note = (
            " Підпис 25500 повернутий вертикально, OCR його не прочитав: число виміряне з вектора через картку масштабу."
            if check["ocr_bbox"] is None
            else ""
        )
        cards.append(
            make_card(
                subject_site,
                "dimension",
                {
                    "name": name,
                    "value": check["annotated_mm"],
                    "unit": "mm",
                    "qualifier": f"{check['what']}; виміряно з вектора {check['measured_mm']:.0f} мм",
                },
                f"{check['annotated_mm']:.0f}",
                check["ocr_bbox"],
                "Підписаний розмір плану аркуша 2, звірений з вектором." + vertical_note,
                today,
            )
        )

    RECORDS.mkdir(parents=True, exist_ok=True)
    written = 0
    for card in cards:
        path = RECORDS / f"{card['id']}.json"
        if path.exists():
            prev = json.loads(path.read_text(encoding="utf-8"))
            if prev.get("status") != "unverified":
                # Рішення людини не перезаписуємо.
                continue
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written += 1
    report["cards"] = [c["id"] for c in cards]
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# План майданчика. Аркуш 2, вектор",
        "",
        f"Дата: {today}. Скрипт: `inbox/{EXTRACTOR}`. Статус усіх карток: `unverified`. `FACTS.json` не створювався.",
        "",
        "Числа зняті з векторних ліній PDF, не з растру і не з DXF. OCR тут лише дає рамку підпису розміру.",
        "",
        "## Масштаб",
        "",
        f"Середній радіус шести кіл стіни силоса на аркуші: {mean_radius_pt:.3f} pt.",
        f"Відомий радіус 11000 мм (D = 22,0 м). Масштаб: **1 pt = {factor:.2f} мм** об'єкта.",
        "",
        "## Звірка з підписаними розмірами",
        "",
        "| Що | Підпис на аркуші, мм | Виміряно з вектора, мм | Похибка | OCR-рамка |",
        "|---|---|---|---|---|",
    ]
    for c in checks:
        md.append(
            f"| {c['what']} | {c['annotated_mm']:.0f} | {c['measured_mm']:.0f} | {c['rel_error'] * 100:.2f} % | "
            + (f"{c['ocr_bbox']}" if c["ocr_bbox"] else "немає, підпис вертикальний")
            + " |"
        )
    md += [
        "",
        "Усі п'ять відстаней сходяться в межах 0.5 %. Масштаб узгоджений з кресленням, а не підігнаний під одне число.",
        "",
        "## Осі силосів",
        "",
        "Система: X уздовж рядів праворуч, Y від нижнього ряду до верхнього, початок — вісь силоса 3. Метри.",
        "",
        "| Силос | X, м | Y, м | R, м | Макс. відхилення кола, мм |",
        "|---|---|---|---|---|",
    ]
    for s in silo_rows:
        md.append(
            f"| {s['number']} | {s['center_m'][0]:.3f} | {s['center_m'][1]:.3f} | {s['radius_m']:.4f} | {s['max_residual_mm']:.0f} |"
        )
    md += [
        "",
        "## Контури біля веж норій",
        "",
        "Червоні замкнені прямокутники 4–6 м поруч із силосами. На аркуші 4 шахта вежі має розмір 4400, тож ці контури ширші за шахту: це, найімовірніше, приямок/фундамент. Тип контуру не встановлений.",
        "",
        "| Центр X, м | Центр Y, м | Ширина, м | Глибина, м |",
        "|---|---|---|---|",
    ]
    for t in tower_rows:
        md.append(f"| {t['center_m'][0]:.3f} | {t['center_m'][1]:.3f} | {t['outline_w_m']:.3f} | {t['outline_d_m']:.3f} |")
    md += [
        "",
        "## Картки",
        "",
        f"Записано або оновлено: {written}. Id: " + ", ".join(f"`{c['id']}`" for c in cards) + ".",
        "",
        "## Що з аркуша 2 ще не знято",
        "",
    ]
    md += [f"- {item}" for item in report["not_extracted"]]
    md.append("")
    REPORT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"PLAN_PASS factor={factor:.4f} mm/pt cards={len(cards)} written={written}")
    for s in silo_rows:
        print("SILO", s["number"], s["center_m"], s["radius_m"])
    for t in tower_rows:
        print("TOWER_OUTLINE", t)
    return 0


if __name__ == "__main__":
    sys.exit(main())
