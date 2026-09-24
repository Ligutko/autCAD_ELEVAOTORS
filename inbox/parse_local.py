"""SLICE-1. Локальний розбір PDF і каталогу в картки зі статусом unverified.

Скрипт не ходить у мережу, не відкриває Blender і не пише FACTS.json чи SITE.json.
Повторний запуск не дублює картки: ідентифікатор рахується з ключа твердження.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

INBOX = Path(__file__).resolve().parent
ROOT = INBOX.parent

PDF_NAME = "Технологія 06.06.24.pdf"
CATALOG_NAME = "Plant3D_Equipment_Catalog.json"
PRD_NAME = "PRD_3D_PIPELINE.md"

SETTINGS_ID = "slice1-oem1-psm11-fallback6-tessdata_fast-v1"
RENDER_DPI = 300
EXPECTED_PAGES = 12

CATALOG_NOTE = "каталог, зібраний раніше зі специфікації PDF"
MM_NOTE = (
    " У файлі значення {raw} записане в міліметрах; "
    "у картці метри, як у розділі 6 PRD."
)

HOMO = str.maketrans(
    {
        "A": "А",
        "a": "а",
        "B": "В",
        "b": "в",
        "C": "С",
        "c": "с",
        "E": "Е",
        "e": "е",
        "H": "Н",
        "K": "К",
        "M": "М",
        "m": "м",
        "N": "Н",
        "n": "н",
        "O": "О",
        "o": "о",
        "P": "Р",
        "p": "р",
        "T": "Т",
        "U": "У",
        "u": "у",
        "X": "Х",
        "x": "х",
        "Y": "У",
        "y": "у",
        "I": "І",
    }
)

SUBJECT_OF_TAG = {
    "МСВУ 220.13.В12": "МСВУ 220.13.В12",
    "Норія Н-100": "Н-100",
    "Т7 (У13-ТЦС-320)": "У13-ТЦС-320",
    "Конвеєр радіально-поворотний": "Конвеєр радіально-поворотний",
    "Вентилятор системи аерації": "Вентилятор системи аерації",
    "Даховий вентилятор": "Даховий вентилятор",
    "У13-ТЭА-400": "У13-ТЭА-400",
    "У13-ТЭА-350": "У13-ТЭА-350",
    "У13-ТЭР-400": "У13-ТЭР-400",
    "У13-ТЭР-350": "У13-ТЭР-350",
    "У13-УН175": "У13-УН175",
    "Естакада надсилосна": "Естакада надсилосна",
}

NODE_OF = {
    "МСВУ 220.13.В12": "silo_flat_or_hopper",
    "Н-100": "bucket_elevator",
    "У13-УН175": "bucket_elevator",
    "У13-ТЦС-320": "chain_conveyor",
    "Конвеєр радіально-поворотний": "radial_conveyor",
    "Вентилятор системи аерації": "aeration_fan",
    "Даховий вентилятор": "roof_fan",
    "У13-ТЭА-400": "gate_electric",
    "У13-ТЭА-350": "gate_electric",
    "У13-ТЭР-400": "gate_manual",
    "У13-ТЭР-350": "gate_manual",
    "Естакада надсилосна": "gallery",
}

SKIP_KEYS = {"tag", "description", "material", "notes"}
MM_TO_M = {"diameter", "height", "length"}

FIELD_SPEC = {
    "diameter": ("dimension", "diameter", "m"),
    "height": ("dimension", "height", "m"),
    "length": ("dimension", "length", "m"),
    "width": ("dimension", "width", "mm"),
    "volume": ("capacity", "volume", "m3"),
    "capacity": ("capacity", "capacity", "t/h"),
    "power": ("power", "power", "kW"),
    "quantity": ("count", "quantity", "pcs"),
}

QUALIFIER = {
    ("МСВУ 220.13.В12", "diameter"): "зовнішній діаметр корпусу",
    ("МСВУ 220.13.В12", "height"): "висота корпусу",
    ("МСВУ 220.13.В12", "volume"): "об'єм зберігання",
    ("МСВУ 220.13.В12", "quantity"): "кількість силосів",
    ("Н-100", "height"): "висота норії",
    ("Н-100", "capacity"): "продуктивність норії",
    ("Н-100", "power"): "потужність приводу",
    ("У13-ТЦС-320", "length"): "довжина транспортера",
    ("У13-ТЦС-320", "width"): "ширина короба",
    ("У13-ТЦС-320", "capacity"): "продуктивність транспортера",
    ("Естакада надсилосна", "length"): "довжина естакади",
    ("Конвеєр радіально-поворотний", "power"): "потужність приводу",
}

GENERIC_QUALIFIER = {
    "diameter": "діаметр",
    "height": "висота",
    "length": "довжина",
    "width": "ширина",
    "volume": "об'єм",
    "capacity": "продуктивність",
    "power": "потужність",
    "quantity": "кількість",
    "opening_side_a": "сторона отвору",
    "opening_side_b": "сторона отвору",
    "total_storage_capacity": "сумарний об'єм зберігання",
    "total_silos": "кількість силосів у підсумку каталогу",
    "total_power": "сумарна потужність за файлом каталогу",
}

TOTAL_SPEC = {
    "total_storage_capacity_m3": ("capacity", "total_storage_capacity", "m3"),
    "total_silos": ("count", "total_silos", "pcs"),
    "total_power_kW": ("power", "total_power", "kW"),
}

# Поля з колонки «чого бракує». Ім'я збігається з claim.name, якщо OCR його закриє.
GAP_FIELDS = {
    "silo_flat_or_hopper": [
        ("bottom_type", "Тип днища (плоске чи конус) не названий у картках."),
        ("cone_angle", "Кут конуса, якщо днище конічне, не названий у картках."),
        ("corrugation_pitch", "Крок гофри не названий у картках."),
        ("sheet_thickness", "Товщина листа не названа у картках."),
        ("bolt_pattern", "Болтове поле не назване у картках."),
        ("roof_slope", "Ухил даху не названий у картках."),
        ("belt_count", "Кількість поясів не названа у картках."),
    ],
    "bucket_elevator": [
        ("head", "Голова норії без розміру в картках."),
        ("boot", "Башмак норії без розміру в картках."),
        ("shaft_section", "Переріз шахти норії не названий у картках."),
        ("bucket_pitch", "Крок ковшів не названий у картках."),
    ],
    "chain_conveyor": [
        ("box_height", "Висота короба транспортера не названа у картках."),
        ("gallery_position", "Місце транспортера на естакаді не назване у картках."),
    ],
    "radial_conveyor": [
        ("boom_length", "Довжина стріли радіального конвеєра не названа у картках."),
        ("service_radius", "Радіус обслуговування радіального конвеєра не названий у картках."),
    ],
    "aeration_fan": [
        ("ducts", "Канали аерації не названі у картках."),
        ("grate", "Решітка аерації не названа у картках."),
        ("mount_point", "Точка посадки вентилятора аерації не названа у картках."),
    ],
    "roof_fan": [
        ("diameter", "Діаметр дахового вентилятора не названий у картках."),
        ("roof_location", "Місце дахового вентилятора на даху не назване у картках."),
    ],
    "gate_electric": [
        ("body", "Корпус засувки з електроприводом не названий у картках."),
        ("route_fit", "Як засувка сідає на трасу, не названо у картках."),
    ],
    "gate_manual": [
        ("body", "Корпус ручної засувки не названий у картках."),
        ("route_fit", "Як ручна засувка сідає на трасу, не названо у картках."),
    ],
    "gallery": [
        ("section", "Переріз естакади не названий у картках."),
        ("underside_elevation", "Відмітка низу естакади не названа у картках."),
    ],
}

ABSENT_NODES = [
    (
        "receiving_pit",
        "Приймальна яма",
        "presence",
        "У каталозі вузла немає. Не вигадувати яму, доки OCR цього PDF не покаже вузол.",
    ),
    (
        "separator",
        "Сепаратор",
        "presence",
        "У каталозі вузла немає. Не вигадувати сепаратор, доки OCR цього PDF не покаже вузол.",
    ),
    (
        "dryer",
        "Сушарка",
        "presence",
        "У каталозі вузла немає. Не вигадувати сушарку, доки OCR цього PDF не покаже вузол.",
    ),
    (
        "belt_conveyor",
        "Стрічковий конвеєр",
        "presence",
        "Окремого тега немає. Не вигадувати стрічковий конвеєр, доки OCR цього PDF не покаже вузол.",
    ),
    (
        "ladder_platform",
        "Драбина і майданчик",
        "passport_or_visible_node",
        "Потрібен паспорт або видимий вузол на листі. Зараз картки немає.",
    ),
    (
        "explosion_panel",
        "Вибухорозрядна панель",
        "passport_or_norm_size",
        "Потрібен паспорт або пункт норми з розміром. Зараз картки немає.",
    ),
    (
        "thermometry",
        "Термометрія",
        "passport_or_visible_node",
        "Потрібен паспорт або видимий вузол на листі. Зараз картки немає.",
    ),
    (
        "aeration_floor",
        "Підлога аерації",
        "channel_layout",
        "Розкладки каналів немає. У каталозі є лише вентилятори. Не вигадувати підлогу.",
    ),
]

REQUIRED_CATALOG = [
    ("МСВУ 220.13.В12", "dimension", "diameter", "22", "m"),
    ("МСВУ 220.13.В12", "dimension", "height", "21.422", "m"),
    ("МСВУ 220.13.В12", "capacity", "volume", "6381", "m3"),
    ("МСВУ 220.13.В12", "count", "quantity", "2", "pcs"),
    ("Н-100", "capacity", "capacity", "100", "t/h"),
    ("Н-100", "dimension", "height", "33", "m"),
    ("Н-100", "power", "power", "22", "kW"),
    ("У13-УН175", "power", "power", "22", "kW"),
    ("У13-ТЦС-320", "capacity", "capacity", "100", "t/h"),
    ("У13-ТЦС-320", "dimension", "length", "30.5", "m"),
    ("У13-ТЦС-320", "dimension", "width", "320", "mm"),
    ("У13-ТЦС-320", "power", "power", "11", "kW"),
    ("Конвеєр радіально-поворотний", "power", "power", "19.6", "kW"),
    ("Вентилятор системи аерації", "power", "power", "11", "kW"),
    ("Вентилятор системи аерації", "count", "quantity", "4", "pcs"),
    ("Даховий вентилятор", "power", "power", "0.25", "kW"),
    ("Даховий вентилятор", "count", "quantity", "2", "pcs"),
    ("У13-ТЭА-400", "dimension", "opening_side_a", "400", "mm"),
    ("У13-ТЭА-400", "dimension", "opening_side_b", "400", "mm"),
    ("У13-ТЭА-400", "power", "power", "0.18", "kW"),
    ("У13-ТЭА-350", "dimension", "opening_side_a", "350", "mm"),
    ("У13-ТЭА-350", "power", "power", "0.18", "kW"),
    ("У13-ТЭР-400", "dimension", "opening_side_a", "400", "mm"),
    ("У13-ТЭР-350", "dimension", "opening_side_a", "350", "mm"),
    ("Естакада надсилосна", "dimension", "length", "24", "m"),
    ("Зерновий комплекс", "capacity", "total_storage_capacity", "12762", "m3"),
    ("Зерновий комплекс", "count", "total_silos", "2", "pcs"),
    ("Зерновий комплекс", "power", "total_power", "88.73", "kW"),
]

TAG_SPECS = [
    (
        "МСВУ 220.13.В12",
        "silo_flat_or_hopper",
        re.compile(r"МСВУ[\s\-\._]*220[\s\-\._]*13[\s\-\._]*В[\s\-\._]*12", re.IGNORECASE),
        False,
    ),
    (
        "У13-ТЦС-320",
        "chain_conveyor",
        re.compile(r"У13[\s\-\._]*ТЦС[\s\-\._]*320", re.IGNORECASE),
        False,
    ),
    (
        "У13-УН175",
        "bucket_elevator",
        re.compile(r"У13[\s\-\._]*УН[\s\-\._]*175", re.IGNORECASE),
        False,
    ),
    (
        "У13-ТЭА",
        "gate_electric",
        re.compile(r"У13[\s\-\._]*Т[ЭЕЄЗ3]А(?:[\s\-\._]*(400|350))?", re.IGNORECASE),
        True,
    ),
    (
        "У13-ТЭР",
        "gate_manual",
        re.compile(r"У13[\s\-\._]*Т[ЭЕЄЗ3]Р(?:[\s\-\._]*(400|350))?", re.IGNORECASE),
        True,
    ),
    (
        "Н-100",
        "bucket_elevator",
        re.compile(r"(?<![0-9А-ЯІЇЄҐ])Н-100(?!\d)"),
        False,
    ),
]

# Пробіл у зібраному рядку — це межа слова Tesseract, не роздільник тисяч.
# Інакше «Н-100 100» злипається в одне число 100100.
NUM_RE = re.compile(r"(?<!\d)(\d+(?:[.,]\d+)?)(?!\d)")
HINTS = [
    ("diameter", re.compile(r"діаметр|диаметр|Ø|∅|(?<![A-Za-zА-Яа-я])[DД]\s*=", re.IGNORECASE)),
    ("height", re.compile(r"висот|высот|нтруб|(?<![A-Za-zА-Яа-я])[HН]\s*=", re.IGNORECASE)),
    ("volume", re.compile(r"(?<![A-Za-zА-Яа-я])V\s*=", re.IGNORECASE)),
    ("length", re.compile(r"довжин|длин[аы]", re.IGNORECASE)),
    ("width", re.compile(r"ширин", re.IGNORECASE)),
    ("sheet_thickness", re.compile(r"товщин|толщин", re.IGNORECASE)),
    ("corrugation_pitch", re.compile(r"гофр", re.IGNORECASE)),
    ("cone_angle", re.compile(r"(?<!\w)кут(?!\w)|угол", re.IGNORECASE)),
    ("belt_count", re.compile(r"пояс", re.IGNORECASE)),
    ("head", re.compile(r"голов[аіы](?!\w)", re.IGNORECASE)),
    ("boot", re.compile(r"башмак", re.IGNORECASE)),
    ("bucket_pitch", re.compile(r"ковш", re.IGNORECASE)),
    ("shaft_section", re.compile(r"шахт", re.IGNORECASE)),
    ("box_height", re.compile(r"короб", re.IGNORECASE)),
    ("boom_length", re.compile(r"стріл|стрел", re.IGNORECASE)),
    ("service_radius", re.compile(r"радіус|радиус", re.IGNORECASE)),
    ("ducts", re.compile(r"канал", re.IGNORECASE)),
    ("grate", re.compile(r"решіт|решет", re.IGNORECASE)),
    ("bolt_pattern", re.compile(r"болт", re.IGNORECASE)),
    ("roof_slope", re.compile(r"ухил\s+дах|уклон\s+крыш", re.IGNORECASE)),
]
DIMENSION_HINTS = {name for name, _ in HINTS}

UNIT_EXACT = {
    "мм": "mm",
    "mm": "mm",
    "м3": "m3",
    "мз": "m3",
    "m3": "m3",
    "тон/год": "t/h",
    "квт": "kW",
    "kw": "kW",
    "т/год": "t/h",
    "т/ч": "t/h",
    "т/h": "t/h",
    "шт": "pcs",
    "pcs": "pcs",
    "м": "m",
    "m": "m",
    "град": "deg",
    "°": "deg",
}

UNIT_UA = {
    "m": "м",
    "mm": "мм",
    "sheet_mm": "мм листа",
    "m3": "м³",
    "t/h": "т/год",
    "kW": "кВт",
    "pcs": "шт",
    "deg": "°",
}

BINDING_RULE = (
    "Число з одиницею прив’язується до тега, якщо воно в тому самому рядку, "
    "у рядку безпосередньо над тегом (так зібрана специфікація) або в кількох "
    "наступних рядках до початку іншого обладнання. На сторінці з кількома тегами "
    "число без свого тега лишається в unbound_numbers."
)


class Word:
    __slots__ = ("text", "conf", "x0", "y0", "x1", "y1", "block", "par", "line")

    def __init__(self, text, conf, x0, y0, x1, y1, block, par, line):
        self.text = text
        self.conf = conf
        self.x0 = x0
        self.y0 = y0
        self.x1 = x1
        self.y1 = y1
        self.block = block
        self.par = par
        self.line = line


class Line:
    __slots__ = ("words", "text", "block", "bbox", "spans")

    def __init__(self, words, text, block, bbox, spans):
        self.words = words
        self.text = text
        self.block = block
        self.bbox = bbox
        self.spans = spans


def ensure_venv() -> None:
    venv_py = INBOX / ".venv" / "Scripts" / "python.exe"
    if not venv_py.is_file():
        sys.stderr.write(
            "Немає inbox/.venv. Створіть його командою "
            "py -3.13 -m venv inbox\\.venv і поставте pymupdf.\n"
        )
        raise SystemExit(1)
    if Path(sys.executable).resolve() != venv_py.resolve():
        # os.execv на Windows ріже шлях по пробілу в «autocad project».
        completed = subprocess.run([str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]])
        raise SystemExit(completed.returncode)


def dec(raw) -> Decimal:
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, int) and not isinstance(raw, bool):
        return Decimal(raw)
    return Decimal(str(raw))


def canonical_value(value) -> str:
    s = format(dec(value), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s or "0"


def json_num(value: Decimal):
    s = canonical_value(value)
    if "." not in s:
        return int(s)
    return Decimal(s)


def _convert(obj):
    if isinstance(obj, Decimal):
        s = canonical_value(obj)
        return {"__decimal__": s}
    if isinstance(obj, dict):
        return {k: _convert(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert(v) for v in obj]
    return obj


def dumps(obj) -> str:
    text = json.dumps(_convert(obj), ensure_ascii=False, indent=2)
    text = re.sub(
        r'\{\s*"__decimal__":\s*"(-?\d+(?:\.\d+)?)"\s*\}',
        r"\1",
        text,
    )
    if "__decimal__" in text:
        raise RuntimeError("не вдалося записати десяткове число в JSON")
    return text + "\n"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_block(origin, path, page, quote, bbox, retrieved_at) -> dict:
    return {
        "origin": origin,
        "path": path,
        "page": page,
        "quote": quote,
        "bbox": bbox,
        "retrieved_at": retrieved_at,
    }


def make_card(subject, kind, claim, source, notes) -> dict:
    return {
        "subject": subject,
        "kind": kind,
        "claim": claim,
        "source": source,
        "status": "unverified",
        "conflict_with": [],
        "notes": notes,
        "seen_in": [],
    }


def card_key(card: dict) -> str:
    claim = card["claim"]
    kind = card["kind"]
    if kind == "gap":
        ident, unit, value = claim["field"], "", ""
    elif kind == "node":
        ident = claim["node_type"]
        unit = ""
        value = "1" if claim["present"] else "0"
    else:
        ident = claim["name"]
        unit = claim.get("unit", "")
        value = canonical_value(claim["value"])
    page = card["source"]["page"]
    page_s = "null" if page is None else str(page)
    return "\n".join(
        [
            card["subject"],
            kind,
            ident,
            unit,
            value,
            card["source"]["origin"],
            card["source"]["path"],
            page_s,
        ]
    )


def add_card(store: dict, card: dict) -> None:
    if card["status"] != "unverified":
        raise RuntimeError("парсер пише лише статус unverified")
    key = card_key(card)
    prev = store.get(key)
    if prev is None:
        store[key] = card
        return
    prev["seen_in"].append(
        {
            "path": card["source"]["path"],
            "page": card["source"]["page"],
            "quote": card["source"]["quote"],
        }
    )


def make_id(key: str, used: dict) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    for size in (8, 12, 16, 24, 32, 64):
        cand = "rec_" + digest[:size]
        prev = used.get(cand)
        if prev is None or prev == key:
            used[cand] = key
            return cand
    raise RuntimeError("не вдалося зібрати унікальний id картки")


def assign_ids(store: dict) -> list:
    used = {}
    cards = []
    for key, card in sorted(store.items(), key=lambda item: item[0]):
        card["id"] = make_id(key, used)
        card["seen_in"] = sorted(
            card["seen_in"],
            key=lambda item: (item["path"], str(item["page"]), item["quote"]),
        )
        cards.append(card)
    return cards


def apply_conflicts(cards: list) -> None:
    groups = defaultdict(list)
    for card in cards:
        if card["kind"] not in {"dimension", "power", "capacity", "count"}:
            continue
        groups[(card["subject"], card["kind"], card["claim"]["name"])].append(card)
    for group in groups.values():
        signatures = {(canonical_value(c["claim"]["value"]), c["claim"]["unit"]) for c in group}
        if len(signatures) < 2:
            continue
        ids = sorted(c["id"] for c in group)
        for card in group:
            card["conflict_with"] = [item for item in ids if item != card["id"]]


def qualifier_for(subject: str, name: str) -> str:
    return QUALIFIER.get((subject, name)) or GENERIC_QUALIFIER.get(name, name)


def catalog_cards(catalog: dict, retrieved_at: str) -> list:
    cards = []
    equipment = catalog.get("equipment") or {}
    for items in equipment.values():
        if not isinstance(items, list):
            continue
        for item in items:
            tag = item.get("tag")
            if tag not in SUBJECT_OF_TAG:
                raise RuntimeError(f"невідомий тег каталогу: {tag}")
            subject = SUBJECT_OF_TAG[tag]
            node_type = NODE_OF[subject]
            cards.append(
                make_card(
                    subject,
                    "node",
                    {"node_type": node_type, "present": True},
                    source_block(
                        "local",
                        CATALOG_NAME,
                        None,
                        f'"tag": "{tag}"',
                        None,
                        retrieved_at,
                    ),
                    CATALOG_NOTE,
                )
            )
            for key, raw in item.items():
                if key in SKIP_KEYS:
                    continue
                if key == "size":
                    cards.extend(opening_cards(subject, str(raw), retrieved_at))
                    continue
                if key not in FIELD_SPEC:
                    raise RuntimeError(f"невідоме числове поле каталогу: {tag}.{key}")
                kind, name, unit = FIELD_SPEC[key]
                value = dec(raw)
                notes = CATALOG_NOTE
                if key in MM_TO_M:
                    value = value / Decimal(1000)
                    notes = CATALOG_NOTE + MM_NOTE.format(raw=raw)
                cards.append(
                    make_card(
                        subject,
                        kind,
                        {
                            "name": name,
                            "value": json_num(value),
                            "unit": unit,
                            "qualifier": qualifier_for(subject, name),
                        },
                        source_block(
                            "local",
                            CATALOG_NAME,
                            None,
                            f'"{key}": {json.dumps(raw, ensure_ascii=False)}',
                            None,
                            retrieved_at,
                        ),
                        notes,
                    )
                )
    totals = catalog.get("totals") or {}
    for key, raw in totals.items():
        if key not in TOTAL_SPEC:
            raise RuntimeError(f"невідомий підсумок каталогу: {key}")
        kind, name, unit = TOTAL_SPEC[key]
        cards.append(
            make_card(
                "Зерновий комплекс",
                kind,
                {
                    "name": name,
                    "value": json_num(dec(raw)),
                    "unit": unit,
                    "qualifier": qualifier_for("Зерновий комплекс", name),
                },
                source_block(
                    "local",
                    CATALOG_NAME,
                    None,
                    f'"{key}": {json.dumps(raw, ensure_ascii=False)}',
                    None,
                    retrieved_at,
                ),
                CATALOG_NOTE,
            )
        )
    return cards


def opening_cards(subject: str, raw: str, retrieved_at: str) -> list:
    match = re.fullmatch(r"(\d+)\s*[xх×X]\s*(\d+)", raw.strip())
    if not match:
        raise RuntimeError(f"незрозумілий розмір отвору в каталозі: {subject} {raw}")
    cards = []
    for name, side in (("opening_side_a", match.group(1)), ("opening_side_b", match.group(2))):
        cards.append(
            make_card(
                subject,
                "dimension",
                {
                    "name": name,
                    "value": json_num(dec(side)),
                    "unit": "mm",
                    "qualifier": f"сторона отвору {raw}",
                },
                source_block(
                    "local",
                    CATALOG_NAME,
                    None,
                    f'"size": "{raw}"',
                    None,
                    retrieved_at,
                ),
                CATALOG_NOTE,
            )
        )
    return cards


def assert_required(cards: list) -> None:
    index = {
        (c["subject"], c["kind"], c["claim"].get("name"), c["claim"].get("unit"), canonical_value(c["claim"]["value"]))
        for c in cards
        if c["kind"] in {"dimension", "power", "capacity", "count"} and c["source"]["path"] == CATALOG_NAME
    }
    missing = []
    for subject, kind, name, value, unit in REQUIRED_CATALOG:
        if (subject, kind, name, unit, value) not in index:
            missing.append(f"{subject} {name}={value} {unit}")
    if missing:
        raise RuntimeError("у картках каталогу немає чисел розділу 6: " + "; ".join(missing))


def parse_tsv(text: str) -> list:
    rows = []
    for index, raw in enumerate(text.splitlines()):
        if index == 0 and raw.startswith("level"):
            continue
        parts = raw.split("\t")
        if len(parts) < 12:
            continue
        try:
            level = int(parts[0])
        except ValueError:
            continue
        if level != 5:
            continue
        token = parts[11]
        if not token.strip():
            continue
        try:
            conf = float(parts[10])
        except ValueError:
            conf = -1.0
        if conf < 0:
            continue
        try:
            left = int(float(parts[6]))
            top = int(float(parts[7]))
            width = int(float(parts[8]))
            height = int(float(parts[9]))
            block = int(parts[2])
            par = int(parts[3])
            line_no = int(parts[4])
        except ValueError:
            continue
        rows.append(
            Word(token, conf, left, top, left + width, top + height, block, par, line_no)
        )
    groups = {}
    order = []
    for word in rows:
        key = (word.block, word.par, word.line)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(word)
    lines = []
    for key in order:
        words = sorted(groups[key], key=lambda item: (item.x0, item.y0))
        lines.append(make_line(words))
    return lines


def make_line(words: list) -> Line:
    parts = []
    spans = []
    cursor = 0
    for word in words:
        if parts:
            cursor += 1
        start = cursor
        parts.append(word.text)
        cursor += len(word.text)
        spans.append((start, cursor))
    text = " ".join(parts)
    bbox = [
        min(word.x0 for word in words),
        min(word.y0 for word in words),
        max(word.x1 for word in words),
        max(word.y1 for word in words),
    ]
    return Line(words, text, words[0].block, bbox, spans)


def find_tags(line: Line) -> list:
    homo = line.text.translate(HOMO)
    found = []
    for base, node_type, pattern, is_gate in TAG_SPECS:
        for match in pattern.finditer(homo):
            size = match.group(1) if is_gate and match.lastindex else None
            subject = base
            if is_gate:
                if size in {"400", "350"}:
                    subject = f"{base}-{size}"
                else:
                    window = homo[match.end() : match.end() + 24]
                    near = re.search(r"(?<!\d)(400|350)(?!\d)", window)
                    if near:
                        subject = f"{base}-{near.group(1)}"
            found.append(
                {
                    "subject": subject,
                    "node_type": node_type,
                    "start": match.start(),
                    "end": match.end(),
                }
            )
    found.sort(key=lambda item: (item["start"], -(item["end"] - item["start"])))
    accepted = []
    for tag in found:
        if any(not (tag["end"] <= prev["start"] or tag["start"] >= prev["end"]) for prev in accepted):
            continue
        accepted.append(tag)
    return accepted


def classify_unit(text: str):
    token = text.strip().lower().strip(".,;:").replace(" ", "").replace("³", "3").replace("^", "")
    return UNIT_EXACT.get(token)


def parse_number(token: str):
    cleaned = token.replace("\u00a0", "").replace(" ", "").replace(",", ".")
    if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
        return None
    if len(cleaned.split(".")[0]) > 8:
        return None
    return dec(cleaned)


def hint_near(text: str, start: int, end: int):
    best = None
    best_dist = 10**9
    for name, pattern in HINTS:
        for match in pattern.finditer(text):
            if match.end() <= start:
                dist = start - match.end()
            elif match.start() >= end:
                dist = match.start() - end
            else:
                dist = 0
            if dist < best_dist:
                best_dist = dist
                best = name
    if best_dist > 30:
        return None
    return best


def field_for(unit: str, line_text: str, value: Decimal, start: int = 0, end: int = 0) -> tuple[str, str]:
    hint = hint_near(line_text, start, end)
    if unit == "kW":
        return "power", "power"
    if unit == "t/h":
        return "capacity", "capacity"
    if unit == "m3":
        return "volume", "capacity"
    if unit == "pcs":
        return "quantity", "count"
    if unit == "deg" and hint == "cone_angle":
        return "cone_angle", "dimension"
    if hint in DIMENSION_HINTS and hint not in {"cone_angle", "volume"} and unit in {"m", "mm", "sheet_mm"}:
        return hint, "dimension"
    token = canonical_value(value).replace(".", "_")
    return f"ocr_{unit}_{token}", "dimension"


def numbers_on_line(line: Line) -> list:
    found = []
    for match in NUM_RE.finditer(line.text):
        raw = match.group(1)
        # «0, 18 кВт» OCR розриває десяткову кому. Друга частина не є окремим числом.
        prefix = line.text[max(0, match.start() - 6) : match.start()]
        if re.search(r"\d,\s*$", prefix):
            continue
        value = parse_number(raw)
        if value is None:
            found.append({"raw": raw, "value": None, "start": match.start(), "end": match.end()})
            continue
        word_indexes = [
            index
            for index, (start, end) in enumerate(line.spans)
            if not (end <= match.start() or start >= match.end())
        ]
        unit = None
        if word_indexes:
            last = word_indexes[-1]
            # Число й одиниця іноді злиплі: «22м», «11кВт».
            stuck = line.words[last].text[match.end() - line.spans[last][0] :]
            if stuck:
                unit = classify_unit(stuck.strip("\"'«»"))
            if unit is None:
                following = [
                    word.text
                    for word in line.words[last + 1 : last + 5]
                    if not re.fullmatch(r"[\W_]+", word.text, flags=re.UNICODE)
                ]
                for take in (1, 2, 3):
                    if take > len(following):
                        break
                    unit = classify_unit("".join(following[:take]))
                    if unit:
                        break
        conf = min((line.words[index].conf for index in word_indexes), default=0.0)
        found.append(
            {
                "raw": raw,
                "value": value,
                "start": match.start(),
                "end": match.end(),
                "unit": unit,
                "conf": conf,
                "words": word_indexes,
            }
        )
    return found


def overlaps_tag(start: int, end: int, tags: list) -> bool:
    return any(not (end <= tag["start"] or start >= tag["end"]) for tag in tags)


def nearest_tag(start: int, tags: list):
    if not tags:
        return None
    if len(tags) == 1:
        return tags[0]
    left = [tag for tag in tags if tag["end"] <= start]
    if left:
        return min(left, key=lambda tag: start - tag["end"])
    return min(tags, key=lambda tag: abs(tag["start"] - start))


NEW_ROW = re.compile(
    r"конвеєр|вентилятор|засувк|норі[яі]|транспортер|естакада|силос\s+для",
    re.IGNORECASE,
)
KEEP_FORWARD = re.compile(
    r"кВт|т/год|т/ч|тон/год|[НH]\s*=|[DД]\s*=|V\s*=|нтруб|мз|м³|м3",
    re.IGNORECASE,
)
OPENING_RE = re.compile(r"(?<!\d)(\d{3})\s*[xх×X]\s*(\d{3})(?!\d)")


def line_starts_new_row(line: Line) -> bool:
    if NEW_ROW.search(line.text):
        return True
    return NEW_ROW.search(line.text.translate(HOMO)) is not None


def bind_page(page: int, lines: list, retrieved_at: str) -> tuple:
    cards = []
    unbound = []
    rejected = []
    hits = []
    no_unit = 0
    consumed = set()

    def remember_tag(line: Line, tag: dict) -> None:
        hits.append(
            {
                "page": page,
                "subject": tag["subject"],
                "node_type": tag["node_type"],
                "quote": line.text,
                "bbox": line.bbox,
            }
        )
        cards.append(
            make_card(
                tag["subject"],
                "node",
                {"node_type": tag["node_type"], "present": True},
                source_block("local", PDF_NAME, page, line.text, line.bbox, retrieved_at),
                "тег знайдено OCR на цій сторінці",
            )
        )

    for index, line in enumerate(lines):
        tags = find_tags(line)
        if not tags:
            continue
        for tag in tags:
            remember_tag(line, tag)
        bound_any = False
        if len(tags) == 1 and index > 0 and (index - 1) not in consumed and not find_tags(lines[index - 1]):
            before = len(cards)
            _bind_line_numbers(
                page,
                lines[index - 1],
                tags,
                cards,
                unbound,
                rejected,
                retrieved_at,
                allow_bare=False,
                same_line=False,
            )
            consumed.add(index - 1)
            bound_any = len(cards) > before
        if len(tags) == 1:
            steps = 0
            cursor = index + 1
            while cursor < len(lines) and steps < 6:
                nxt = lines[cursor]
                if find_tags(nxt):
                    break
                is_new = line_starts_new_row(nxt)
                if is_new and bound_any:
                    break
                take = bool(KEEP_FORWARD.search(nxt.text)) or (is_new and not bound_any)
                if take:
                    before = len(cards)
                    _bind_line_numbers(
                        page,
                        nxt,
                        tags,
                        cards,
                        unbound,
                        rejected,
                        retrieved_at,
                        allow_bare=False,
                        same_line=False,
                    )
                    consumed.add(cursor)
                    if len(cards) > before:
                        bound_any = True
                if is_new:
                    break
                cursor += 1
                steps += 1
        _bind_line_numbers(page, line, tags, cards, unbound, rejected, retrieved_at, allow_bare=True)
        consumed.add(index)

    for index, line in enumerate(lines):
        if index in consumed:
            continue
        for number in numbers_on_line(line):
            if number["value"] is None:
                rejected.append(
                    {
                        "page": page,
                        "text": number["raw"],
                        "reason": "not_a_number",
                        "line": line.text[:240],
                    }
                )
                continue
            if number.get("unit"):
                unbound.append(
                    {
                        "page": page,
                        "text": number["raw"],
                        "unit": number["unit"],
                        "reason": "no_subject",
                        "line": line.text[:240],
                    }
                )
            else:
                no_unit += 1
    return cards, unbound, rejected, hits, no_unit


def _bind_line_numbers(
    page, line, tags, cards, unbound, rejected, retrieved_at, allow_bare: bool, same_line: bool = True
) -> None:
    covered_spans = []
    if len(tags) == 1 and tags[0]["subject"].startswith(("У13-ТЭА", "У13-ТЭР")):
        for match in OPENING_RE.finditer(line.text):
            if same_line and overlaps_tag(match.start(), match.end(), tags):
                continue
            covered_spans.append((match.start(), match.end()))
            raw = match.group(0)
            for name, side in (("opening_side_a", match.group(1)), ("opening_side_b", match.group(2))):
                cards.append(
                    make_card(
                        tags[0]["subject"],
                        "dimension",
                        {
                            "name": name,
                            "value": json_num(dec(side)),
                            "unit": "mm",
                            "qualifier": f"сторона отвору {raw}",
                        },
                        source_block("local", PDF_NAME, page, line.text, line.bbox, retrieved_at),
                        "число з OCR у рядку з відомим тегом",
                    )
                )
    numbers = []
    for number in numbers_on_line(line):
        if same_line and overlaps_tag(number["start"], number["end"], tags):
            continue
        if any(not (number["end"] <= start or number["start"] >= end) for start, end in covered_spans):
            continue
        numbers.append(number)
    bare = [number for number in numbers if number["value"] is not None and not number.get("unit")]
    crowded = allow_bare and len(bare) > 4
    for number in numbers:
        if number["value"] is None:
            rejected.append(
                {
                    "page": page,
                    "text": number["raw"],
                    "reason": "not_a_number",
                    "line": line.text[:240],
                }
            )
            continue
        value = number["value"]
        unit = number.get("unit")
        if value == 0:
            rejected.append(
                {"page": page, "text": number["raw"], "reason": "not_a_number", "line": line.text[:240]}
            )
            continue
        if unit is None and not allow_bare:
            if value >= 100:
                unbound.append(
                    {
                        "page": page,
                        "text": number["raw"],
                        "unit": None,
                        "reason": "no_unit",
                        "line": line.text[:240],
                    }
                )
            continue
        if unit is None and crowded:
            unbound.append(
                {
                    "page": page,
                    "text": number["raw"],
                    "unit": None,
                    "reason": "crowded_line",
                    "line": line.text[:240],
                }
            )
            continue
        if unit is None:
            if number["conf"] < 45 or value < 10:
                continue
            if value == value.to_integral() and Decimal(1990) <= value <= Decimal(2035):
                rejected.append(
                    {
                        "page": page,
                        "text": number["raw"],
                        "reason": "not_a_number",
                        "line": line.text[:240],
                    }
                )
                continue
            unit = "sheet_mm"
        elif number["conf"] < 20:
            rejected.append(
                {
                    "page": page,
                    "text": number["raw"],
                    "reason": "not_a_number",
                    "line": line.text[:240],
                }
            )
            continue
        tag = nearest_tag(number["start"], tags)
        if tag is None:
            unbound.append(
                {
                    "page": page,
                    "text": number["raw"],
                    "unit": unit,
                    "reason": "no_subject",
                    "line": line.text[:240],
                }
            )
            continue
        name, kind = field_for(unit, line.text, value, number["start"], number["end"])
        qual = qualifier_for(tag["subject"], name)
        if name.startswith("ocr_"):
            qual = "число в рядку з тегом; назву поля з тексту не витягнуто"
        cards.append(
            make_card(
                tag["subject"],
                kind,
                {
                    "name": name,
                    "value": json_num(value),
                    "unit": unit,
                    "qualifier": qual,
                },
                source_block("local", PDF_NAME, page, line.text, line.bbox, retrieved_at),
                "число з OCR у рядку з відомим тегом",
            )
        )


def covered_fields(cards: list) -> set:
    found = set()
    for card in cards:
        if card["kind"] in {"dimension", "power", "capacity", "count"}:
            found.add((card["subject"], card["claim"]["name"]))
    return found


def gap_cards(cards: list, retrieved_at: str) -> list:
    covered = covered_fields(cards)
    gaps = []
    subjects_by_node = defaultdict(list)
    for subject, node_type in NODE_OF.items():
        subjects_by_node[node_type].append(subject)
    for node_type, fields in GAP_FIELDS.items():
        subjects = subjects_by_node.get(node_type) or []
        for subject in subjects:
            for field, why in fields:
                if (subject, field) in covered:
                    continue
                gaps.append(
                    make_card(
                        subject,
                        "gap",
                        {"field": field, "why_needed": why},
                        source_block(
                            "local",
                            PRD_NAME,
                            None,
                            why,
                            None,
                            retrieved_at,
                        ),
                        "дірка словника: картки з цим полем немає",
                    )
                )
    for node_type, subject, field, why in ABSENT_NODES:
        if (subject, field) in covered:
            continue
        gaps.append(
            make_card(
                subject,
                "gap",
                {"field": field, "why_needed": why, "node_type": node_type},
                source_block("local", PRD_NAME, None, why, None, retrieved_at),
                "вузла немає в каталозі; геометрію не вигадувати",
            )
        )
    if not any(card["kind"] == "scale" for card in cards):
        why = (
            "Окремої картки масштабу немає. Довжини з листа без одиниці лишаються "
            "в sheet_mm, координати DXF у метри об'єкта не переводяться."
        )
        gaps.append(
            make_card(
                "Креслення",
                "gap",
                {"field": "scale", "why_needed": why},
                source_block("local", PRD_NAME, None, why, None, retrieved_at),
                "масштабу листа в картках немає",
            )
        )
    return gaps


def claim_label(card: dict) -> str:
    claim = card["claim"]
    if card["kind"] == "node":
        state = "є в джерелі" if claim["present"] else "немає"
        return f"{claim['node_type']}: {state}"
    if card["kind"] == "gap":
        return f"{claim['field']}: {claim['why_needed']}"
    unit = UNIT_UA.get(claim["unit"], claim["unit"])
    name = GENERIC_QUALIFIER.get(claim["name"], claim.get("qualifier") or claim["name"])
    return f"{name}: {canonical_value(claim['value'])} {unit}"


def render_gaps_md(cards: list, log: dict) -> str:
    catalog = [c for c in cards if c["source"]["path"] == CATALOG_NAME and c["kind"] != "node"]
    nodes = [c for c in cards if c["kind"] == "node" and c["source"]["path"] == CATALOG_NAME]
    ocr_cards = [c for c in cards if c["source"]["path"] == PDF_NAME and c["kind"] != "node"]
    ocr_nodes = [c for c in cards if c["source"]["path"] == PDF_NAME and c["kind"] == "node"]
    gaps = [c for c in cards if c["kind"] == "gap"]
    lines = [
        "# Дірки SLICE-1",
        "",
        f"Дата: {log['generated_at']}",
        f"PDF: `{PDF_NAME}`, сторінок: {log['pdf']['page_count']}",
        f"OCR: {log['ocr']['version']}",
        f"Мови: {', '.join(log['ocr']['langs'])}",
        "",
        "Усі картки мають статус `unverified`. Скрипт не створює `FACTS.json` і `SITE.json`.",
        "",
        "## Підсумок",
        "",
        f"- Карток разом: {len(cards)}",
        f"- З каталогу, числові: {len(catalog)}",
        f"- З каталогу, вузли: {len(nodes)}",
        f"- З OCR, числові: {len(ocr_cards)}",
        f"- З OCR, теги без прив'язки до нового числа: {len(ocr_nodes)}",
        f"- Дірок: {len(gaps)}",
        f"- Чисел з одиницею без тега: {len(log['unbound_numbers'])}",
        f"- Чисел без одиниці і без тега (лише лічильник): {log['unbound_no_unit_count']}",
        f"- Відхилених токенів: {len(log['rejected_tokens'])}",
        "",
        BINDING_RULE,
        "",
        "## Що знайшли в каталозі",
        "",
        "Це числа з `Plant3D_Equipment_Catalog.json`. Вони ще не затверджені.",
        "",
    ]
    by_subject = defaultdict(list)
    for card in catalog:
        by_subject[card["subject"]].append(card)
    for subject in sorted(by_subject):
        bits = [claim_label(card) for card in by_subject[subject]]
        lines.append(f"- **{subject}.** " + "; ".join(bits))
    lines.extend(["", "## Що знайшов OCR", ""])
    if not log["tag_hits"] and not ocr_cards:
        lines.append("Жоден відомий тег не зійшовся з числом. Каталожні картки від цього не зникають.")
    else:
        hit_pages = defaultdict(list)
        for hit in log["tag_hits"]:
            hit_pages[hit["page"]].append(hit["subject"])
        if hit_pages:
            lines.append("Теги на сторінках:")
            lines.append("")
            for page in sorted(hit_pages):
                subjects = sorted(set(hit_pages[page]))
                lines.append(f"- сторінка {page}: " + ", ".join(subjects))
            lines.append("")
        if ocr_cards:
            lines.append("Числа, прив'язані до тега:")
            lines.append("")
            for card in ocr_cards:
                page = card["source"]["page"]
                lines.append(
                    f"- сторінка {page}, **{card['subject']}.** {claim_label(card)}. "
                    f"Цитата: «{card['source']['quote'][:180]}»"
                )
        else:
            lines.append("Теги є, окремого числа з одиницею поруч парсер не взяв.")
    conflicts = [card for card in cards if card["conflict_with"]]
    if conflicts:
        lines.extend(["", "## Конфлікти чисел", ""])
        lines.append("Обидві картки лишаються `unverified`. У FACTS така пара не потрапить, доки одну не затвердять, а іншу не відхилять.")
        lines.append("")
        seen = set()
        for card in conflicts:
            key = tuple(sorted([card["id"], *card["conflict_with"]]))
            if key in seen:
                continue
            seen.add(key)
            lines.append(
                f"- **{card['subject']}**, {card['claim'].get('name')}: {claim_label(card)} "
                f"({card['source']['path']}, сторінка {card['source']['page']}). "
                f"Суперечить: {', '.join(card['conflict_with'])}."
            )
    mentions = log.get("lubnymash_pages") or []
    if mentions:
        lines.extend(
            [
                "",
                "## Рядок, який OCR побачив і який не став карткою",
                "",
                "На сторінках "
                + ", ".join(str(page) for page in mentions)
                + " повторюється «ЛУБНИМАШ». Окремого поля виробника в картці немає, "
                "і колонка може бути постачальником, а не паспортом серії МСВУ. "
                "У твердження це не записано.",
                "",
            ]
        )
    lines.extend(["", "## Дірки відомих вузлів", ""])
    known_subjects = set(NODE_OF)
    known = [c for c in gaps if c["subject"] in known_subjects]
    rest = [c for c in gaps if c["subject"] not in known_subjects]
    grouped = defaultdict(list)
    for card in known:
        grouped[card["subject"]].append(card)
    if not known:
        lines.append("Для відомих вузлів відкритих дірок не лишилось.")
    for subject in sorted(grouped):
        node = NODE_OF[subject]
        lines.append(f"### {subject} ({node})")
        lines.append("")
        for card in grouped[subject]:
            lines.append(f"- {card['claim']['field']}: {card['claim']['why_needed']}")
        lines.append("")
    lines.extend(["## Вузли, яких у каталозі немає", ""])
    lines.append("Їх не будувати, доки не з'явиться картка з цього PDF або з паспорта.")
    lines.append("")
    for card in rest:
        if card["claim"]["field"] == "scale":
            continue
        lines.append(f"- **{card['subject']}.** {card['claim']['why_needed']}")
    scale = [c for c in rest if c["claim"]["field"] == "scale"]
    if scale:
        lines.extend(["", "## Масштаб", "", f"- {scale[0]['claim']['why_needed']}"])
    if log.get("scale_mentions"):
        lines.extend(["", "Рядки, де OCR побачив слово про масштаб (картку scale з них не зроблено):", ""])
        for item in log["scale_mentions"][:30]:
            lines.append(f"- сторінка {item['page']}: «{item['line'][:180]}»")
    lines.extend(["", "## Числа без тега", ""])
    if not log["unbound_numbers"]:
        lines.append("Чисел з розпізнаною одиницею поза тегом немає.")
    else:
        per_page = defaultdict(int)
        for item in log["unbound_numbers"]:
            per_page[item["page"]] += 1
        for page in sorted(per_page):
            lines.append(f"- сторінка {page}: {per_page[page]}")
        lines.append("")
        lines.append("Приклади:")
        lines.append("")
        shown = defaultdict(int)
        for item in log["unbound_numbers"]:
            if shown[item["page"]] >= 12:
                continue
            shown[item["page"]] += 1
            unit = item.get("unit") or "без одиниці"
            lines.append(
                f"- сторінка {item['page']}, {item['text']} ({unit}), {item['reason']}: "
                f"«{item['line'][:160]}»"
            )
    lines.extend(
        [
            "",
            f"Окремо пораховано числа без одиниці і без тега: {log['unbound_no_unit_count']}. "
            "Вони не стали картками.",
            "",
            "## Що не прочиталось",
            "",
        ]
    )
    page_rows = log.get("pages") or []
    quiet = [row for row in page_rows if row.get("words", 0) == 0]
    if quiet:
        for row in quiet:
            lines.append(f"- сторінка {row['page']}: 0 слів. {'; '.join(row.get('errors') or [])}")
    else:
        lines.append("Порожніх сторінок OCR немає. Слова є на кожній сторінці, навіть якщо частина з них шум креслення.")
    if log["rejected_tokens"]:
        lines.append("")
        lines.append(f"Відхилених токенів: {len(log['rejected_tokens'])}. Повний список у `parse_log.json`.")
    if log.get("errors"):
        lines.extend(["", "## Помилки прогону", ""])
        for error in log["errors"]:
            lines.append(f"- {error}")
    lines.extend(
        [
            "",
            "## Звідки не брали числа",
            "",
            "- `FINAL_DXF_PERFECT_V7/` у цьому зрізі не читався.",
            "- `D:\\ELEVATOR_REFERENCES\\` не є обмірами.",
            "- Нарізки `Технологія 06.06.24_Images\\` не подавались в OCR.",
            "",
        ]
    )
    return "\n".join(lines)


def self_check() -> None:
    sample = dumps({"value": Decimal("21.422"), "power": Decimal("19.6"), "tiny": Decimal("0.18")})
    if "__decimal__" in sample or "21.422" not in sample or "19.6" not in sample or "0.18" not in sample:
        raise RuntimeError("запис десяткових чисел зламаний")
    catalog = {
        "equipment": {
            "silos": [
                {
                    "tag": "МСВУ 220.13.В12",
                    "description": "x",
                    "diameter": 22000,
                    "height": 21422,
                    "volume": 6381,
                    "material": "x",
                    "quantity": 2,
                    "notes": "x",
                }
            ]
        },
        "totals": {},
    }
    built = catalog_cards(catalog, "2026-09-23")
    diameter = next(card for card in built if card["claim"].get("name") == "diameter")
    if canonical_value(diameter["claim"]["value"]) != "22" or diameter["claim"]["unit"] != "m":
        raise RuntimeError("діаметр каталогу не зійшовся з 22 м")
    if not diameter["notes"].startswith(CATALOG_NOTE):
        raise RuntimeError("примітка каталогу інша")
    if diameter["status"] != "unverified" or diameter["source"]["page"] is not None:
        raise RuntimeError("картка каталогу має лишатися unverified без сторінки")
    height = next(card for card in built if card["claim"].get("name") == "height")
    if canonical_value(height["claim"]["value"]) != "21.422":
        raise RuntimeError("висота силоса не 21.422 м")

    tsv = "\n".join(
        [
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
            "5\t1\t1\t1\t1\t1\t10\t10\t50\t20\t90\tМСВУ",
            "5\t1\t1\t1\t1\t2\t70\t10\t120\t20\t90\t220.13.В12",
            "5\t1\t1\t1\t1\t3\t200\t10\t70\t20\t90\tдіаметр",
            "5\t1\t1\t1\t1\t4\t280\t10\t30\t20\t90\t22",
            "5\t1\t1\t1\t1\t5\t320\t10\t20\t20\t90\tм",
            "5\t1\t1\t1\t2\t1\t10\t40\t70\t20\t90\tН-100",
            "5\t1\t1\t1\t2\t2\t90\t40\t40\t20\t90\t100",
            "5\t1\t1\t1\t2\t3\t140\t40\t50\t20\t92\tт/год",
            "5\t1\t2\t1\t1\t1\t10\t80\t40\t20\t88\t1500",
            "5\t1\t2\t1\t1\t2\t60\t80\t30\t20\t88\tмм",
        ]
    )
    lines = parse_tsv(tsv)
    ocr_cards, unbound, _rejected, hits, _no_unit = bind_page(8, lines, "2026-09-23")
    named = {
        (card["subject"], card["kind"], card["claim"].get("name")): card
        for card in ocr_cards
        if card["kind"] != "node"
    }
    silo = named[("МСВУ 220.13.В12", "dimension", "diameter")]
    if canonical_value(silo["claim"]["value"]) != "22" or silo["claim"]["unit"] != "m":
        raise RuntimeError("OCR не зв'язав діаметр 22 м із МСВУ")
    if silo["source"]["bbox"] is None:
        raise RuntimeError("OCR-картка без рамки")
    capacity = named[("Н-100", "capacity", "capacity")]
    if canonical_value(capacity["claim"]["value"]) != "100":
        raise RuntimeError("OCR не зв'язав 100 т/год із Н-100")
    if not any(item["reason"] == "no_subject" and item["unit"] == "mm" for item in unbound):
        raise RuntimeError("число без тега мало лишитися неприв'язаним")
    if not any(hit["subject"] == "МСВУ 220.13.В12" for hit in hits):
        raise RuntimeError("тег МСВУ не зафіксований")
    above = "\n".join(
        [
            "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext",
            "5\t1\t1\t1\t1\t1\t10\t10\t40\t18\t90\tD=22,0",
            "5\t1\t1\t1\t1\t2\t60\t10\t20\t18\t90\tм",
            "5\t1\t1\t1\t1\t3\t90\t10\t30\t18\t90\tV=6381",
            "5\t1\t1\t1\t1\t4\t130\t10\t30\t18\t90\tмз",
            "5\t1\t1\t1\t2\t1\t10\t40\t140\t18\t90\tМСВУ",
            "5\t1\t1\t1\t2\t2\t160\t40\t120\t18\t92\t220.13.В12",
            "5\t1\t1\t1\t3\t1\t10\t70\t80\t18\t90\tН=21,422",
            "5\t1\t1\t1\t3\t2\t100\t70\t20\t18\t90\tм",
            "5\t1\t3\t1\t1\t1\t10\t200\t160\t18\t90\tУ13-ТЗА-400",
        ]
    )
    extra, _unbound, _rejected, extra_hits, _no_unit = bind_page(8, parse_tsv(above), "2026-09-23")
    extra_named = {
        (card["subject"], card["claim"].get("name"), canonical_value(card["claim"]["value"]) if "value" in card["claim"] else ""): card
        for card in extra
        if card["kind"] != "node"
    }
    if ("МСВУ 220.13.В12", "diameter", "22") not in extra_named:
        raise RuntimeError("рядок над тегом не дав діаметр 22 м")
    if ("МСВУ 220.13.В12", "volume", "6381") not in extra_named:
        raise RuntimeError("мз не прочитано як об'єм 6381 м³")
    if ("МСВУ 220.13.В12", "height", "21.422") not in extra_named:
        raise RuntimeError("рядок під тегом не дав висоту 21.422 м")
    if not any(hit["subject"] == "У13-ТЭА-400" for hit in extra_hits):
        raise RuntimeError("У13-ТЗА-400 не зведено до У13-ТЭА-400")

    store = {}
    for card in built + ocr_cards:
        add_card(store, card)
    first_len = len(store)
    for card in built:
        add_card(store, card)
    if len(store) != first_len:
        raise RuntimeError("повтор картки створив дубль")
    finalized = assign_ids(store)
    apply_conflicts(finalized)
    if any(card["status"] != "unverified" for card in finalized):
        raise RuntimeError("self-check побачив статус, відмінний від unverified")
    left = make_card(
        "МСВУ 220.13.В12",
        "dimension",
        {"name": "diameter", "value": json_num(dec(22)), "unit": "m", "qualifier": "x"},
        source_block("local", CATALOG_NAME, None, "a", None, "2026-09-23"),
        CATALOG_NOTE,
    )
    right = make_card(
        "МСВУ 220.13.В12",
        "dimension",
        {"name": "diameter", "value": json_num(dec("22.5")), "unit": "m", "qualifier": "x"},
        source_block("local", PDF_NAME, 8, "b", [1, 2, 3, 4], "2026-09-23"),
        "ocr",
    )
    conflict_store = {}
    add_card(conflict_store, left)
    add_card(conflict_store, right)
    conflict_cards = assign_ids(conflict_store)
    apply_conflicts(conflict_cards)
    if any(not card["conflict_with"] for card in conflict_cards):
        raise RuntimeError("конфлікт різних діаметрів не записаний")
    gaps = gap_cards(built, "2026-09-23")
    silo_gaps = {card["claim"]["field"] for card in gaps if card["subject"] == "МСВУ 220.13.В12"}
    for field in ("bottom_type", "cone_angle", "corrugation_pitch", "sheet_thickness", "bolt_pattern", "roof_slope", "belt_count"):
        if field not in silo_gaps:
            raise RuntimeError(f"немає дірки силоса: {field}")
    closed = list(built)
    closed.append(
        make_card(
            "МСВУ 220.13.В12",
            "dimension",
            {"name": "sheet_thickness", "value": json_num(dec("1.5")), "unit": "mm", "qualifier": "x"},
            source_block("local", PDF_NAME, 8, "товщина 1.5 мм", [1, 1, 2, 2], "2026-09-23"),
            "ocr",
        )
    )
    after = gap_cards(closed, "2026-09-23")
    if any(card["subject"] == "МСВУ 220.13.В12" and card["claim"]["field"] == "sheet_thickness" for card in after):
        raise RuntimeError("закрите OCR поле лишилось у дірках")


def find_tesseract() -> Path | None:
    candidates = []
    found = shutil.which("tesseract")
    if found:
        candidates.append(Path(found))
    local = os.environ.get("LOCALAPPDATA", "")
    # Спочатку копія в ASCII-шляху: Tesseract 5.5 падає на кирилиці в шляху до exe.
    candidates.extend(
        [
            INBOX / ".tools" / "Tesseract-OCR" / "tesseract.exe",
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(local) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
            Path(local) / "Tesseract-OCR" / "tesseract.exe",
        ]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _traineddata_ok(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 100_000:
        return False
    return not path.read_bytes()[:40].startswith(b"version https://git-lfs")


def prepare_tessdata(exe: Path) -> Path:
    stock = INBOX / ".tools" / "tessdata"
    beside = exe.parent / "tessdata"
    target = beside if beside.is_dir() else stock
    target.mkdir(parents=True, exist_ok=True)
    for lang in ("eng", "ukr", "rus"):
        dst = target / f"{lang}.traineddata"
        if _traineddata_ok(dst):
            continue
        src = stock / f"{lang}.traineddata"
        if not _traineddata_ok(src):
            raise RuntimeError(f"немає мовного пакета {lang} для Tesseract")
        shutil.copyfile(src, dst)
    missing = [lang for lang in ("eng", "ukr", "rus") if not _traineddata_ok(target / f"{lang}.traineddata")]
    if missing:
        raise RuntimeError("немає мовних пакетів Tesseract: " + ", ".join(missing))
    return target


def tesseract_version(exe: Path) -> str:
    proc = subprocess.run(
        [str(exe), "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else ""


def tesseract_langs(exe: Path, tessdata: Path) -> list:
    proc = subprocess.run(
        [str(exe), "--tessdata-dir", str(tessdata), "--list-langs"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    langs = []
    for line in text.splitlines():
        token = line.strip()
        if not token or token.lower().startswith("list of"):
            continue
        if re.fullmatch(r"[a-z0-9_]+", token):
            langs.append(token)
    return sorted(set(langs))


def ensure_dirs() -> None:
    for folder in (
        INBOX / "raw" / "pdf_pages",
        INBOX / "raw" / "ocr",
        INBOX / "records",
        INBOX / "reports",
    ):
        folder.mkdir(parents=True, exist_ok=True)


def write_log(payload: dict) -> None:
    ensure_dirs()
    atomic_write(INBOX / "reports" / "parse_log.json", dumps(payload))


def render_pages(doc, pdf_hash: str) -> tuple[bool, list]:
    folder = INBOX / "raw" / "pdf_pages"
    marker = folder / "_source.sha256"
    errors = []
    complete = all(
        (folder / f"page_{page:02d}.png").is_file() and (folder / f"page_{page:02d}.png").stat().st_size > 1000
        for page in range(1, EXPECTED_PAGES + 1)
    )
    same = marker.is_file() and marker.read_text(encoding="utf-8").strip() == pdf_hash
    if complete and same:
        return True, errors
    for index, page in enumerate(doc, start=1):
        target = folder / f"page_{index:02d}.png"
        if same and target.is_file() and target.stat().st_size > 1000:
            continue
        try:
            pixmap = page.get_pixmap(dpi=RENDER_DPI, alpha=False)
            pixmap.save(str(target))
            print(f"render {index}/{EXPECTED_PAGES} {target.name} {pixmap.width}x{pixmap.height}", flush=True)
        except Exception as exc:  # noqa: BLE001 — помилка сторінки має лишитись у логу, не валити весь процес мовчки
            errors.append(f"сторінка {index}: рендер не записано: {exc}")
            print(f"render fail {index}: {exc}", flush=True)
    if not errors and all((folder / f"page_{page:02d}.png").is_file() for page in range(1, EXPECTED_PAGES + 1)):
        marker.write_text(pdf_hash + "\n", encoding="utf-8", newline="\n")
    return False, errors


def run_tesseract(exe: Path, tessdata: Path, image: Path, out_base: Path, psm: int) -> tuple[int, str]:
    cmd = [
        str(exe),
        str(image),
        str(out_base),
        "--tessdata-dir",
        str(tessdata),
        "-l",
        "ukr+rus+eng",
        "--dpi",
        "300",
        "--oem",
        "1",
        "--psm",
        str(psm),
        "-c",
        "preserve_interword_spaces=1",
        "-c",
        "tessedit_create_tsv=1",
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=900,
    )
    err = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()
    return proc.returncode, err[:2000]


def alpha_count(lines: list) -> int:
    return sum(1 for line in lines for word in line.words if any(ch.isalpha() for ch in word.text))


def ocr_pages(exe: Path, tessdata: Path, pdf_hash: str) -> tuple[list, list]:
    folder = INBOX / "raw" / "ocr"
    marker = folder / "_manifest.json"
    manifest = {"pdf_sha256": pdf_hash, "settings": SETTINGS_ID}
    cached = False
    if marker.is_file():
        try:
            previous = json.loads(marker.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previous = {}
        cached = previous == manifest and all(
            (folder / f"page_{page:02d}.tsv").is_file() and (folder / f"page_{page:02d}.txt").is_file()
            for page in range(1, EXPECTED_PAGES + 1)
        )
    pages = []
    errors = []
    if cached:
        for page in range(1, EXPECTED_PAGES + 1):
            tsv_path = folder / f"page_{page:02d}.tsv"
            text = tsv_path.read_text(encoding="utf-8", errors="replace")
            lines = parse_tsv(text)
            words = sum(len(line.words) for line in lines)
            pages.append(
                {
                    "page": page,
                    "png": f"inbox/raw/pdf_pages/page_{page:02d}.png",
                    "tsv": f"inbox/raw/ocr/page_{page:02d}.tsv",
                    "words": words,
                    "alpha_words": alpha_count(lines),
                    "psm": None,
                    "ocr_skipped": True,
                    "errors": [],
                }
            )
        return pages, errors

    for page in range(1, EXPECTED_PAGES + 1):
        image = INBOX / "raw" / "pdf_pages" / f"page_{page:02d}.png"
        record = {
            "page": page,
            "png": f"inbox/raw/pdf_pages/page_{page:02d}.png",
            "tsv": f"inbox/raw/ocr/page_{page:02d}.tsv",
            "words": 0,
            "alpha_words": 0,
            "psm": None,
            "ocr_skipped": False,
            "errors": [],
        }
        if not image.is_file():
            record["errors"].append("немає PNG")
            errors.append(f"сторінка {page}: немає PNG")
            pages.append(record)
            continue
        try:
            chosen = ocr_choose(exe, tessdata, image, page)
        except subprocess.TimeoutExpired:
            record["errors"].append("OCR перевищив 900 с")
            errors.append(f"сторінка {page}: таймаут OCR")
            pages.append(record)
            continue
        except Exception as exc:  # noqa: BLE001
            record["errors"].append(str(exc))
            errors.append(f"сторінка {page}: {exc}")
            pages.append(record)
            continue
        tsv_path = folder / f"page_{page:02d}.tsv"
        txt_path = folder / f"page_{page:02d}.txt"
        atomic_write(tsv_path, chosen["tsv"])
        lines = parse_tsv(chosen["tsv"])
        txt = "\n".join(line.text for line in lines)
        atomic_write(txt_path, txt + ("\n" if txt else ""))
        record["words"] = sum(len(line.words) for line in lines)
        record["alpha_words"] = alpha_count(lines)
        record["psm"] = chosen["psm"]
        if chosen["error"]:
            record["errors"].append(chosen["error"])
        print(
            f"ocr {page}/{EXPECTED_PAGES} psm={chosen['psm']} words={record['words']}",
            flush=True,
        )
        pages.append(record)
    if not errors:
        atomic_write(marker, dumps(manifest))
    return pages, errors


def ocr_choose(exe: Path, tessdata: Path, image: Path, page: int) -> dict:
    with tempfile.TemporaryDirectory(prefix="slice1-ocr-") as tmp:
        base11 = Path(tmp) / "psm11"
        code, err = run_tesseract(exe, tessdata, image, base11, 11)
        tsv11 = base11.with_suffix(".tsv")
        text11 = tsv11.read_text(encoding="utf-8", errors="replace") if tsv11.is_file() else ""
        lines11 = parse_tsv(text11) if text11 else []
        hits11 = sum(len(find_tags(line)) for line in lines11)
        alpha11 = alpha_count(lines11)
        use_psm = 11
        text = text11
        error = None if code == 0 else f"psm 11 код {code}: {err}"
        if hits11 == 0 or alpha11 < 12:
            base6 = Path(tmp) / "psm6"
            code6, err6 = run_tesseract(exe, tessdata, image, base6, 6)
            tsv6 = base6.with_suffix(".tsv")
            text6 = tsv6.read_text(encoding="utf-8", errors="replace") if tsv6.is_file() else ""
            lines6 = parse_tsv(text6) if text6 else []
            hits6 = sum(len(find_tags(line)) for line in lines6)
            alpha6 = alpha_count(lines6)
            if hits6 > hits11 or (hits6 == hits11 and alpha6 > alpha11):
                use_psm = 6
                text = text6
                error = None if code6 == 0 else f"psm 6 код {code6}: {err6}"
        if not text:
            raise RuntimeError(error or "OCR не повернув TSV")
        return {"psm": use_psm, "tsv": text, "error": error}


def load_ocr_lines(page: int) -> list:
    path = INBOX / "raw" / "ocr" / f"page_{page:02d}.tsv"
    if not path.is_file():
        return []
    return parse_tsv(path.read_text(encoding="utf-8", errors="replace"))


def word_count(lines: list) -> int:
    return sum(len(line.words) for line in lines)


def collect_scale_mentions(page: int, lines: list) -> list:
    mentions = []
    for line in lines:
        folded = line.text.lower()
        homo = line.text.translate(HOMO).lower()
        if "масштаб" in folded or "масштаб" in homo or "scale" in folded:
            mentions.append({"page": page, "line": line.text[:240]})
    return mentions


def write_records(cards: list) -> None:
    folder = INBOX / "records"
    folder.mkdir(parents=True, exist_ok=True)
    ids = set()
    for card in cards:
        if card["status"] != "unverified":
            raise RuntimeError(f"відмова писати картку {card.get('id')} зі статусом {card['status']}")
        ids.add(card["id"])
        # Поле id за контрактом стоїть першим.
        ordered = {
            "id": card["id"],
            "subject": card["subject"],
            "kind": card["kind"],
            "claim": card["claim"],
            "source": card["source"],
            "status": card["status"],
            "conflict_with": card["conflict_with"],
            "notes": card["notes"],
            "seen_in": card["seen_in"],
        }
        atomic_write(folder / f"{card['id']}.json", dumps(ordered))
    for path in folder.glob("rec_*.json"):
        if path.stem in ids:
            continue
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if previous.get("status") == "unverified":
            path.unlink()


def main() -> int:
    ensure_venv()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    self_check()
    import fitz

    from datetime import date

    retrieved_at = date.today().isoformat()
    ensure_dirs()
    facts = ROOT / "FACTS.json"
    site = ROOT / "SITE.json"
    facts_before = facts.exists()
    site_before = site.exists()
    log = {
        "generated_at": retrieved_at,
        "pdf": {"path": PDF_NAME, "sha256": None, "page_count": None},
        "render": {"dpi": RENDER_DPI, "skipped_existing": False},
        "ocr": {
            "engine": "tesseract",
            "version": None,
            "langs": [],
            "oem": 1,
            "psm_policy": "11, fallback 6 if no tag or fewer than 12 letter-words",
            "tessdata": "tessdata_fast 4.1.0",
        },
        "binding_rule": BINDING_RULE,
        "pages": [],
        "tag_hits": [],
        "unbound_numbers": [],
        "unbound_no_unit_count": 0,
        "rejected_tokens": [],
        "scale_mentions": [],
        "lubnymash_pages": [],
        "unused_sources": [],
        "errors": [],
        "catalog_cards": 0,
        "ocr_cards": 0,
        "gap_cards": 0,
    }
    images = ROOT / "Технологія 06.06.24_Images"
    if images.exists():
        log["unused_sources"].append(
            "Технологія 06.06.24_Images\\ — нарізки BMP не є входом SLICE-1"
        )

    exe = find_tesseract()
    if exe is None:
        log["errors"].append(
            "Tesseract не знайдено. Потрібен Tesseract 5 з мовами ukr, rus, eng. "
            "OCR не замінювався ручним читанням."
        )
        write_log(log)
        print("SLICE1 FAIL tesseract-missing", flush=True)
        return 1
    version = tesseract_version(exe)
    log["ocr"]["version"] = version
    log["ocr"]["executable"] = str(exe)
    if not re.search(r"tesseract\s+v?5\.", version, re.IGNORECASE):
        log["errors"].append(f"потрібен Tesseract 5, отримано: {version or 'порожньо'}")
        write_log(log)
        print("SLICE1 FAIL tesseract-version", flush=True)
        return 1
    try:
        tessdata = prepare_tessdata(exe)
    except RuntimeError as exc:
        log["errors"].append(str(exc))
        write_log(log)
        print("SLICE1 FAIL tessdata", flush=True)
        return 1
    langs = tesseract_langs(exe, tessdata)
    log["ocr"]["langs"] = langs
    missing_langs = [lang for lang in ("ukr", "rus", "eng") if lang not in langs]
    if missing_langs:
        log["errors"].append("Tesseract не бачить мови: " + ", ".join(missing_langs))
        write_log(log)
        print("SLICE1 FAIL langs", flush=True)
        return 1

    pdf_path = ROOT / PDF_NAME
    if not pdf_path.is_file():
        log["errors"].append(f"немає файлу {PDF_NAME}")
        write_log(log)
        return 1
    pdf_hash = sha256_file(pdf_path)
    log["pdf"]["sha256"] = pdf_hash
    doc = fitz.open(pdf_path)
    try:
        log["pdf"]["page_count"] = doc.page_count
        if doc.page_count != EXPECTED_PAGES:
            log["errors"].append(
                f"очікувалось {EXPECTED_PAGES} сторінок, у PDF {doc.page_count}. Картки не записані."
            )
            write_log(log)
            print("SLICE1 FAIL page-count", flush=True)
            return 2
        skipped, render_errors = render_pages(doc, pdf_hash)
        log["render"]["skipped_existing"] = skipped
        log["errors"].extend(render_errors)
    finally:
        doc.close()

    try:
        pages, ocr_errors = ocr_pages(exe, tessdata, pdf_hash)
    except Exception as exc:  # noqa: BLE001
        log["errors"].append(f"OCR зупинився: {exc}")
        write_log(log)
        print("SLICE1 FAIL ocr", flush=True)
        return 1
    log["pages"] = pages
    log["errors"].extend(ocr_errors)

    catalog_path = ROOT / CATALOG_NAME
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    store = {}
    catalog_built = catalog_cards(catalog, retrieved_at)
    assert_required(catalog_built)
    for card in catalog_built:
        add_card(store, card)

    for page in range(1, EXPECTED_PAGES + 1):
        lines = load_ocr_lines(page)
        if not lines:
            continue
        log["scale_mentions"].extend(collect_scale_mentions(page, lines))
        if any("ЛУБНИМАШ" in line.text.upper() or "ЛУБНИМАШ" in line.text.translate(HOMO).upper() for line in lines):
            log["lubnymash_pages"].append(page)
        ocr_cards, unbound, rejected, hits, no_unit = bind_page(page, lines, retrieved_at)
        log["tag_hits"].extend(hits)
        log["unbound_numbers"].extend(unbound)
        log["rejected_tokens"].extend(rejected)
        log["unbound_no_unit_count"] += no_unit
        for card in ocr_cards:
            add_card(store, card)

    pre_gaps = list(store.values())
    for card in gap_cards(pre_gaps, retrieved_at):
        add_card(store, card)
    cards = assign_ids(store)
    apply_conflicts(cards)

    log["catalog_cards"] = sum(1 for card in cards if card["source"]["path"] == CATALOG_NAME)
    log["ocr_cards"] = sum(1 for card in cards if card["source"]["path"] == PDF_NAME)
    log["gap_cards"] = sum(1 for card in cards if card["kind"] == "gap")
    total_words = sum(page.get("words") or 0 for page in pages)
    if total_words == 0:
        log["errors"].append(
            "нуль розпізнаних слів на всіх сторінках. Це поломка OCR, а не відсутність тексту."
        )

    write_records(cards)
    gaps = [card for card in cards if card["kind"] == "gap"]
    gaps_payload = {
        "generated_at": retrieved_at,
        "pdf_sha256": pdf_hash,
        "rule": "Дірка лишається, доки немає картки з тим самим subject і claim.name, що дорівнює field.",
        "gaps": [
            {
                "id": card["id"],
                "subject": card["subject"],
                "node_type": NODE_OF.get(card["subject"]) or card["claim"].get("node_type"),
                "field": card["claim"]["field"],
                "why_needed": card["claim"]["why_needed"],
                "record": f"inbox/records/{card['id']}.json",
            }
            for card in gaps
        ],
    }
    atomic_write(INBOX / "reports" / "gaps.json", dumps(gaps_payload))
    atomic_write(INBOX / "reports" / "gaps.md", render_gaps_md(cards, log))
    write_log(log)

    pngs = list((INBOX / "raw" / "pdf_pages").glob("page_*.png"))
    if len(pngs) != EXPECTED_PAGES:
        log["errors"].append(f"PNG не 12, а {len(pngs)}")
        write_log(log)
    if facts.exists() != facts_before or site.exists() != site_before:
        print("SLICE1 FAIL facts-or-site-created", flush=True)
        return 1
    if any(card["status"] != "unverified" for card in cards):
        print("SLICE1 FAIL status", flush=True)
        return 1
    if log["errors"] or total_words == 0:
        print(
            f"SLICE1 FAIL cards={len(cards)} catalog={log['catalog_cards']} "
            f"ocr={log['ocr_cards']} gaps={log['gap_cards']} words={total_words}",
            flush=True,
        )
        return 1
    print(
        f"SLICE1 OK cards={len(cards)} catalog={log['catalog_cards']} "
        f"ocr={log['ocr_cards']} gaps={log['gap_cards']} words={total_words}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"parse_local: {exc}\n")
        raise SystemExit(1)
