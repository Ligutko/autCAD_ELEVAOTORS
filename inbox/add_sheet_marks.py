"""Картки висотних відміток, які OCR уже прочитав на аркушах, з рамкою слова.

Беруться лише відмітки зі списку MARKS і лише коли слово в TSV збігається
точно і впевненість OCR не нижча за MIN_CONF. Інакше картка не пишеться,
а відмітка йде у звіт як `not_read`.

Картки: `unverified`, `source.extractor = "add_sheet_marks.py"`.
Запуск з кореня проєкту: python inbox/add_sheet_marks.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INBOX = ROOT / "inbox"
PDF_NAME = "Технологія 06.06.24.pdf"
EXTRACTOR = "add_sheet_marks.py"
MIN_CONF = 80.0

# (аркуш, текст відмітки, subject, claim.name, qualifier, де на аркуші шукати: x-діапазон рамки в px)
MARKS = [
    (4, "-5,100", "H6 (норія 100 т/год)", "pit_bottom_elevation", "дно приямку башмака норії H6, розріз «Напрям транспортування на силоса»", (900, 1500)),
    (4, "-4,700", "H5 (норія 100 т/год)", "pit_bottom_elevation", "дно приямку башмака норії H5, той самий розріз", (2800, 3400)),
    (7, "+29,000", "H6 (норія 100 т/год)", "tower_frame_top_elevation", "верх каркаса вежі H6 на фасаді силосів 3–6", (3000, 3500)),
]


def read_words(page: int) -> list[dict]:
    path = INBOX / "raw" / "ocr" / f"page_{page:02d}.tsv"
    lines = path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    words = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) != len(header):
            continue
        row = dict(zip(header, parts))
        if row["text"].strip():
            left, top = int(row["left"]), int(row["top"])
            words.append(
                {
                    "text": row["text"],
                    "conf": float(row["conf"]),
                    "bbox": [left, top, left + int(row["width"]), top + int(row["height"])],
                }
            )
    return words


def value_m(text: str) -> float:
    return float(text.replace(",", "."))


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    today = date.today().isoformat()
    written, missing = [], []
    for page, text, subject, name, qualifier, (x_lo, x_hi) in MARKS:
        hits = [
            w
            for w in read_words(page)
            if w["text"] == text and w["conf"] >= MIN_CONF and x_lo <= w["bbox"][0] <= x_hi
        ]
        if not hits:
            missing.append({"page": page, "text": text, "subject": subject, "why": "OCR не дав цього слова з потрібною впевненістю"})
            continue
        word = hits[0]
        claim = {"name": name, "value": value_m(text), "unit": "m", "qualifier": qualifier}
        key = "|".join([subject, "dimension", name, PDF_NAME, str(page), EXTRACTOR, text])
        card = {
            "id": "rec_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:8],
            "subject": subject,
            "kind": "dimension",
            "claim": claim,
            "source": {
                "origin": "local",
                "path": PDF_NAME,
                "page": page,
                "quote": text,
                "bbox": word["bbox"],
                "retrieved_at": today,
                "extractor": EXTRACTOR,
            },
            "status": "unverified",
            "conflict_with": [],
            "notes": f"Висотна відмітка з OCR аркуша {page}, впевненість {word['conf']:.0f}. Прив'язка до вузла — за положенням на розрізі, перевірити очима.",
            "seen_in": [],
        }
        path = INBOX / "records" / f"{card['id']}.json"
        if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("status") != "unverified":
            continue
        path.write_text(json.dumps(card, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append({"id": card["id"], "page": page, "text": text, "subject": subject, "bbox": word["bbox"]})
    out = {"date": today, "written": written, "not_read": missing}
    (INBOX / "reports" / "sheet_marks.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for item in written:
        print("MARK", item["id"], item["page"], item["text"], item["subject"])
    for item in missing:
        print("NOT_READ", item["page"], item["text"], item["subject"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
