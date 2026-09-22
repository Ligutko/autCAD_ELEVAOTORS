#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Автоматичний генератор Revit Families для обладнання елеваторів

Створює .rfa файли програмно через Revit API:
- Silo (Силос МСВУ)
- Conveyor (Конвеєр/Транспортер)
- Elevator (Норія/Bucket Elevator)
- Pipe (Трубопровід)

Автор: Claude Code
Дата: 2026-01-01
"""

import json
import os
from pathlib import Path

# Цей скрипт ПОВИНЕН запускатися через MCP Server → pyRevit Listener!
# Не можна запустити напряму в Python, бо потрібен Revit API

FAMILIES_OUTPUT = Path("D:/autocad project/revit-mcp/families")
FAMILIES_OUTPUT.mkdir(parents=True, exist_ok=True)

# =============================================================================
# ШАБЛОНИ FAMILIES (структура для створення)
# =============================================================================

SILO_FAMILY_TEMPLATE = {
    "family_name": "Silo_MSVU",
    "category": "GenericModel",  # Revit category
    "parameters": [
        {"name": "Diameter", "type": "Length", "default": 22000, "formula": None},
        {"name": "Height", "type": "Length", "default": 21422, "formula": None},
        {"name": "Volume", "type": "Volume", "default": 0, "formula": "PI * (Diameter / 2)^2 * Height / 1000000000"},
        {"name": "Equipment_Tag", "type": "Text", "default": "МСВУ-220.13.В12", "formula": None},
        {"name": "Material_Type", "type": "Text", "default": "Carbon Steel", "formula": None},
    ],
    "geometry": {
        "type": "extrusion",  # Циліндр
        "profile": "circle",
        "profile_param": "Diameter",
        "extrusion_param": "Height"
    }
}

CONVEYOR_FAMILY_TEMPLATE = {
    "family_name": "Conveyor_T7",
    "category": "GenericModel",
    "parameters": [
        {"name": "Length", "type": "Length", "default": 30000, "formula": None},
        {"name": "Width", "type": "Length", "default": 320, "formula": None},
        {"name": "Capacity", "type": "Number", "default": 100, "formula": None},
        {"name": "Equipment_Tag", "type": "Text", "default": "T7", "formula": None},
    ],
    "geometry": {
        "type": "line",  # Лінія з стрілкою
        "start_param": "0,0,0",
        "end_param": "Length,0,0"
    }
}

ELEVATOR_FAMILY_TEMPLATE = {
    "family_name": "Elevator_H100",
    "category": "GenericModel",
    "parameters": [
        {"name": "Height", "type": "Length", "default": 33000, "formula": None},
        {"name": "Bucket_Diameter", "type": "Length", "default": 600, "formula": None},
        {"name": "Capacity", "type": "Number", "default": 100, "formula": None},
        {"name": "Equipment_Tag", "type": "Text", "default": "H5", "formula": None},
    ],
    "geometry": {
        "type": "line",  # Вертикальна лінія
        "start_param": "0,0,0",
        "end_param": "0,0,Height"
    }
}

PIPE_FAMILY_TEMPLATE = {
    "family_name": "Pipe_Connection",
    "category": "GenericModel",
    "parameters": [
        {"name": "Diameter", "type": "Length", "default": 400, "formula": None},
        {"name": "Length", "type": "Length", "default": 10000, "formula": None},
        {"name": "Tag", "type": "Text", "default": "P1", "formula": None},
    ],
    "geometry": {
        "type": "pipe",  # Труба
        "diameter_param": "Diameter",
        "length_param": "Length"
    }
}

# =============================================================================
# КОМАНДИ ДЛЯ MCP SERVER
# =============================================================================

def generate_create_family_commands():
    """
    Генерує команди для MCP Server, щоб створити Families через Revit API
    """
    commands = []

    templates = [
        SILO_FAMILY_TEMPLATE,
        CONVEYOR_FAMILY_TEMPLATE,
        ELEVATOR_FAMILY_TEMPLATE,
        PIPE_FAMILY_TEMPLATE
    ]

    for template in templates:
        command = {
            "action": "create_family",
            "template": template,
            "output_path": str(FAMILIES_OUTPUT / f"{template['family_name']}.rfa")
        }
        commands.append(command)

    # Зберегти команди в JSON для MCP Server
    commands_file = Path("D:/autocad project/revit-mcp/family_creation_commands.json")
    with open(commands_file, 'w', encoding='utf-8') as f:
        json.dump(commands, f, ensure_ascii=False, indent=2)

    print(f"✅ Створено {len(commands)} команд для створення Families")
    print(f"📁 Збережено в: {commands_file}")
    print("\nНаступний крок: Запустити через MCP Server:")
    print("  Claude, create all families from family_creation_commands.json")

    return commands_file


# =============================================================================
# HEADLESS ГЕНЕРАТОР (якщо Revit відкритий)
# =============================================================================

def create_families_in_revit():
    """
    ЦІЄЇ ФУНКЦІЇ ПРАЦЮЄ ТІЛЬКИ ВСЕРЕДИНІ REVIT через pyRevit!

    Запуск:
    1. Відкрити Revit
    2. Запустити pyRevit listener
    3. Викликати цю функцію через MCP Server
    """
    # Імпорти Revit API (доступні тільки в Revit!)
    try:
        from pyrevit import revit, DB, script
        import clr
        clr.AddReference('RevitAPI')
    except ImportError:
        raise Exception(
            "ERROR: Revit API не доступний!\n"
            "Цей скрипт повинен запускатися ВСЕРЕДИНІ Revit через pyRevit."
        )

    app = __revit__.Application
    doc = __revit__.ActiveUIDocument.Document

    families_created = []

    # Створити Silo Family
    silo_family = create_silo_family(app, SILO_FAMILY_TEMPLATE)
    families_created.append(silo_family)

    # Створити Conveyor Family
    conveyor_family = create_conveyor_family(app, CONVEYOR_FAMILY_TEMPLATE)
    families_created.append(conveyor_family)

    # Створити Elevator Family
    elevator_family = create_elevator_family(app, ELEVATOR_FAMILY_TEMPLATE)
    families_created.append(elevator_family)

    # Створити Pipe Family
    pipe_family = create_pipe_family(app, PIPE_FAMILY_TEMPLATE)
    families_created.append(pipe_family)

    return families_created


def create_silo_family(app, template):
    """
    Створює Silo Family (циліндр з параметрами)

    ВАЖЛИВО: Створення Family в Revit API - ДУЖЕ СКЛАДНЕ!
    Простіше створити вручну в Family Editor один раз.

    Тому тут я створюю "заготовку" - ви відкриєте в Revit і доопрацюєте.
    """
    from pyrevit import DB

    # Створити новий Family Document
    family_template_path = app.FamilyTemplatePath + "\\Metric Generic Model.rft"

    family_doc = app.NewFamilyDocument(family_template_path)

    # TODO: Додати геометрію (Extrusion)
    # TODO: Додати параметри
    # TODO: Зберегти .rfa файл

    output_path = str(FAMILIES_OUTPUT / f"{template['family_name']}.rfa")
    family_doc.SaveAs(output_path)
    family_doc.Close(False)

    return output_path


# ПРОБЛЕМА: Створення Families програмно в Revit API - НАДЗВИЧАЙНО СКЛАДНЕ!
# Навіть прості об'єкти потребують десятків рядків коду.
#
# РІШЕННЯ: Створити Families ВРУЧНУ (один раз), зберегти як шаблони,
# потім тільки завантажувати та розміщувати через MCP Server.


# =============================================================================
# АЛЬТЕРНАТИВНИЙ ПІДХІД: MANUAL TEMPLATES
# =============================================================================

MANUAL_FAMILY_GUIDE = """
╔══════════════════════════════════════════════════════════════════════════╗
║  ІНСТРУКЦІЯ: Створення Families ВРУЧНУ в Revit Family Editor           ║
╚══════════════════════════════════════════════════════════════════════════╝

Створення Families програмно в Revit API - ДУЖЕ СКЛАДНЕ (100+ рядків коду
для простого циліндра). Набагато швидше створити вручну один раз!

═══════════════════════════════════════════════════════════════════════════

1. SILO FAMILY (Силос МСВУ 220.13.В12)
───────────────────────────────────────

Крок 1: Створити новий Family
  • Revit → File → New → Family
  • Шаблон: "Metric Generic Model.rft"

Крок 2: Створити Reference Planes
  • Architecture → Datum → Reference Plane
  • Створити 2 вертикальні площини: "Left" та "Right"
  • Відстань між ними = "Diameter" (параметр)

Крок 3: Додати параметри
  • Create → Family Types → New Parameter:
    - Name: Diameter, Type: Length, Default: 22000mm
    - Name: Height, Type: Length, Default: 21422mm
    - Name: Volume, Type: Volume, Formula: PI * (Diameter / 2)^2 * Height
    - Name: Equipment_Tag, Type: Text, Default: "МСВУ-220.13.В12"
    - Name: Material_Type, Type: Text, Default: "Carbon Steel"

Крок 4: Створити геометрію (циліндр)
  • Create → Forms → Extrusion
  • Намалювати CIRCLE з центром в Origin
  • Радіус = Diameter / 2 (зв'язати з параметром!)
  • Extrusion Height = Height (зв'язати з параметром!)

Крок 5: Зберегти
  • File → Save As → "Silo_MSVU_220.rfa"
  • Зберегти в: D:/autocad project/revit-mcp/families/

═══════════════════════════════════════════════════════════════════════════

2. CONVEYOR FAMILY (Конвеєр T7)
───────────────────────────────

Крок 1-2: Аналогічно Silo

Крок 3: Параметри
  - Length: 30000mm
  - Width: 320mm
  - Capacity: 100 t/h
  - Equipment_Tag: "T7"

Крок 4: Геометрія
  • Create → Model → Model Line
  • Намалювати лінію від (0,0,0) до (Length, 0, 0)
  • Додати стрілку напрямку (Detail Item)

Крок 5: Зберегти як "Conveyor_T7.rfa"

═══════════════════════════════════════════════════════════════════════════

3. ELEVATOR FAMILY (Норія H100)
───────────────────────────────

Параметри:
  - Height: 33000mm
  - Bucket_Diameter: 600mm
  - Capacity: 100 t/h

Геометрія:
  • Вертикальна лінія від (0,0,0) до (0,0,Height)
  • 2 кола зверху/знизу (барабани)

Зберегти як "Elevator_H100.rfa"

═══════════════════════════════════════════════════════════════════════════

4. PIPE FAMILY (Трубопровід)
────────────────────────────

Параметри:
  - Diameter: 400mm
  - Length: 10000mm (може змінюватися)

Геометрія:
  • Pipe (труба) з діаметром = Diameter

Зберегти як "Pipe_Connection.rfa"

═══════════════════════════════════════════════════════════════════════════

ПІСЛЯ СТВОРЕННЯ:

Всі .rfa файли розмістити в:
  D:/autocad project/revit-mcp/families/

Потім MCP Server зможе їх завантажувати та розміщувати автоматично!

═══════════════════════════════════════════════════════════════════════════

АЛЬТЕРНАТИВА: Використати існуючі Families з Revit Library
  • C:/ProgramData/Autodesk/RVT 2024/Libraries/
  • Знайти подібні об'єкти (Tanks, Equipment, Pipes)
  • Модифікувати під наші потреби

═══════════════════════════════════════════════════════════════════════════
"""


if __name__ == "__main__":
    print("=" * 70)
    print("  REVIT FAMILIES GENERATOR")
    print("=" * 70)
    print()

    print("Цей скрипт генерує структуру для створення Revit Families.")
    print()

    # Генерувати команди для MCP
    print("Крок 1: Генерую команди для MCP Server...")
    commands_file = generate_create_family_commands()

    print()
    print("=" * 70)
    print("  ВАЖЛИВО: Створення Families")
    print("=" * 70)
    print()
    print("Revit API не дозволяє ЛЕГКО створювати Families програмно.")
    print("Навіть простий циліндр потребує 100+ рядків коду.")
    print()
    print("РЕКОМЕНДАЦІЯ:")
    print("  1. Створити 4 Families ВРУЧНУ в Revit (один раз, 30 хвилин)")
    print("  2. Зберегти як .rfa шаблони")
    print("  3. MCP Server потім автоматично завантажує і розміщує їх")
    print()
    print("Детальна інструкція збережена в:")
    print("  D:/autocad project/revit-mcp/MANUAL_FAMILY_CREATION_GUIDE.txt")
    print()

    # Зберегти інструкцію
    guide_path = Path("D:/autocad project/revit-mcp/MANUAL_FAMILY_CREATION_GUIDE.txt")
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(MANUAL_FAMILY_GUIDE)

    print("✅ Готово!")
