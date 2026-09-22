#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
BUILD REVIT PROJECT FROM CONFIG

Автоматично будує повний Revit BIM проект з JSON конфігурації.

Використання:
    python build_revit_project_from_config.py config_6_silos.json

Або через Claude Code:
    "Claude, build Revit project from config_6_silos.json"

Автор: Claude Code
Дата: 2026-01-01
"""

import sys
import json
from pathlib import Path

# Шлях до MCP server
sys.path.insert(0, str(Path(__file__).parent))

from revit_mcp_server import (
    ping_revit,
    load_family,
    place_family_instance,
    create_sheet,
    list_sheets,
    export_sheets_to_pdf
)

# =============================================================================
# КОНФІГУРАЦІЯ
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
FAMILIES_DIR = PROJECT_ROOT / "revit-mcp" / "families"
CONFIG_DIR = PROJECT_ROOT

# =============================================================================
# BUILDER CLASS
# =============================================================================

class RevitProjectBuilder:
    """
    Будує Revit проект з JSON конфігурації
    """

    def __init__(self, config_path):
        """
        Args:
            config_path: Шлях до JSON конфігурації (config_6_silos.json)
        """
        self.config_path = Path(config_path)

        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        # Завантажити конфігурацію
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.project_name = self.config.get('project_name', 'Grain Elevator')
        self.equipment = self.config.get('equipment', {})

        # Статистика
        self.stats = {
            'families_loaded': [],
            'silos_placed': 0,
            'elevators_placed': 0,
            'conveyors_placed': 0,
            'pipes_placed': 0,
            'sheets_created': 0
        }

    def check_revit_connection(self):
        """Перевірити з'єднання з Revit"""
        print("🔍 Перевіряю з'єднання з Revit...")
        try:
            result = ping_revit()
            print(f"✅ {result}")
            return True
        except Exception as e:
            print(f"❌ ERROR: Revit не відповідає!")
            print(f"   {e}")
            print("\nПеревірте:")
            print("  1. Чи запущений Revit?")
            print("  2. Чи запущений pyRevit Listener?")
            return False

    def load_required_families(self):
        """Завантажити необхідні Families"""
        print("\n📦 Завантажую Families...")

        required_families = [
            ("Silo_MSVU_220.rfa", "Силоси"),
            ("Conveyor_T7.rfa", "Конвеєри"),
            ("Elevator_H100.rfa", "Норії"),
            ("Pipe_Connection.rfa", "Труби")
        ]

        for family_file, description in required_families:
            family_path = FAMILIES_DIR / family_file

            if not family_path.exists():
                print(f"⚠️  УВАГА: {family_file} не знайдено!")
                print(f"   Шлях: {family_path}")
                print(f"   Створіть цю Family вручну або пропустіть {description}")
                continue

            try:
                print(f"   Завантажую {family_file}...", end=" ")
                result = load_family(str(family_path))
                self.stats['families_loaded'].append(result['family_name'])
                print(f"✅ {result['family_name']}")
            except Exception as e:
                print(f"❌ ERROR: {e}")

        print(f"\n✅ Завантажено {len(self.stats['families_loaded'])} Families")

    def place_silos(self):
        """Розмістити силоси"""
        silos = self.equipment.get('silos', [])

        if not silos:
            print("\n⚠️  Немає силосів в конфігурації")
            return

        print(f"\n🏗️  Розміщую {len(silos)} силосів...")

        for i, silo in enumerate(silos, 1):
            try:
                print(f"   [{i}/{len(silos)}] {silo['tag']}...", end=" ")

                result = place_family_instance(
                    family_name="Silo_MSVU_220",
                    symbol_name="Default",  # Або тип з config
                    x=silo['x'],
                    y=silo['y'],
                    z=0,
                    level_name="Level 1",
                    parameters={
                        "Diameter": silo['diameter'],
                        "Height": silo['height'],
                        "Equipment_Tag": silo['tag'],
                        "Material_Type": silo.get('material', 'carbon_steel'),
                        "Volume": silo.get('capacity', 0)
                    }
                )

                self.stats['silos_placed'] += 1
                print(f"✅ ID: {result['instance_id']}")

            except Exception as e:
                print(f"❌ ERROR: {e}")

        print(f"\n✅ Розміщено {self.stats['silos_placed']} силосів")

    def place_elevators(self):
        """Розмістити норії (bucket elevators)"""
        elevators = self.equipment.get('elevators', [])

        if not elevators:
            print("\n⚠️  Немає норій в конфігурації")
            return

        print(f"\n🏗️  Розміщую {len(elevators)} норій...")

        for i, elevator in enumerate(elevators, 1):
            try:
                print(f"   [{i}/{len(elevators)}] {elevator['tag']}...", end=" ")

                result = place_family_instance(
                    family_name="Elevator_H100",
                    symbol_name="Default",
                    x=elevator['x'],
                    y=elevator['y'],
                    z=0,
                    parameters={
                        "Height": elevator['lift_height'],
                        "Bucket_Diameter": elevator['bucket_diameter'],
                        "Capacity": elevator.get('capacity', 100),
                        "Equipment_Tag": elevator['tag']
                    }
                )

                self.stats['elevators_placed'] += 1
                print(f"✅ ID: {result['instance_id']}")

            except Exception as e:
                print(f"❌ ERROR: {e}")

        print(f"\n✅ Розміщено {self.stats['elevators_placed']} норій")

    def place_conveyors(self):
        """Розмістити конвеєри"""
        conveyors = self.equipment.get('conveyors', [])

        if not conveyors:
            print("\n⚠️  Немає конвеєрів в конфігурації")
            return

        print(f"\n🏗️  Розміщую {len(conveyors)} конвеєрів...")

        for i, conveyor in enumerate(conveyors, 1):
            try:
                print(f"   [{i}/{len(conveyors)}] {conveyor['tag']}...", end=" ")

                # Розрахувати довжину
                length = ((conveyor['end_x'] - conveyor['start_x'])**2 +
                         (conveyor['end_y'] - conveyor['start_y'])**2)**0.5

                result = place_family_instance(
                    family_name="Conveyor_T7",
                    symbol_name="Default",
                    x=conveyor['start_x'],
                    y=conveyor['start_y'],
                    z=conveyor.get('start_z', 0),
                    parameters={
                        "Length": length,
                        "Width": conveyor['width'],
                        "Capacity": conveyor.get('capacity', 100),
                        "Equipment_Tag": conveyor['tag']
                    }
                )

                self.stats['conveyors_placed'] += 1
                print(f"✅ ID: {result['instance_id']}")

            except Exception as e:
                print(f"❌ ERROR: {e}")

        print(f"\n✅ Розміщено {self.stats['conveyors_placed']} конвеєрів")

    def place_pipes(self):
        """Розмістити труби"""
        pipes = self.equipment.get('pipes', [])

        if not pipes:
            print("\n⚠️  Немає труб в конфігурації")
            return

        print(f"\n🏗️  Розміщую {len(pipes)} труб...")

        for i, pipe in enumerate(pipes, 1):
            try:
                print(f"   [{i}/{len(pipes)}] {pipe['tag']}...", end=" ")

                # Розрахувати довжину
                length = ((pipe['to_x'] - pipe['from_x'])**2 +
                         (pipe['to_y'] - pipe['from_y'])**2 +
                         (pipe.get('to_z', 0) - pipe.get('from_z', 0))**2)**0.5

                result = place_family_instance(
                    family_name="Pipe_Connection",
                    symbol_name="Default",
                    x=pipe['from_x'],
                    y=pipe['from_y'],
                    z=pipe.get('from_z', 0),
                    parameters={
                        "Diameter": pipe['diameter'],
                        "Length": length,
                        "Tag": pipe['tag']
                    }
                )

                self.stats['pipes_placed'] += 1
                print(f"✅ ID: {result['instance_id']}")

            except Exception as e:
                print(f"❌ ERROR: {e}")

        print(f"\n✅ Розміщено {self.stats['pipes_placed']} труб")

    def create_sheets_layout(self):
        """Створити аркуші креслень"""
        print("\n📄 Створюю аркуші...")

        sheets_to_create = [
            ("А-01", "Схема технологічного процесу"),
            ("А-02", "План розташування обладнання"),
            ("А-03", "Розрізи силосів"),
        ]

        for number, name in sheets_to_create:
            try:
                print(f"   {number}: {name}...", end=" ")

                result = create_sheet(
                    number=number,
                    name=name,
                    titleblock_name="A0 metric"
                )

                self.stats['sheets_created'] += 1
                print(f"✅ ID: {result['sheet_id']}")

            except Exception as e:
                print(f"❌ ERROR: {e}")

        print(f"\n✅ Створено {self.stats['sheets_created']} аркушів")

    def print_summary(self):
        """Вивести підсумок"""
        print("\n" + "=" * 70)
        print("  ПІДСУМОК ПОБУДОВИ ПРОЕКТУ")
        print("=" * 70)
        print(f"\nПроект: {self.project_name}")
        print(f"Конфігурація: {self.config_path.name}")
        print()
        print("Розміщено обладнання:")
        print(f"  • Силоси: {self.stats['silos_placed']}")
        print(f"  • Норії: {self.stats['elevators_placed']}")
        print(f"  • Конвеєри: {self.stats['conveyors_placed']}")
        print(f"  • Труби: {self.stats['pipes_placed']}")
        print()
        print(f"Створено аркушів: {self.stats['sheets_created']}")
        print()
        print("Завантажені Families:")
        for family in self.stats['families_loaded']:
            print(f"  • {family}")
        print()
        print("=" * 70)
        print("\n✅ ПРОЕКТ ГОТОВИЙ! Відкрийте Revit для перегляду.")

    def build(self):
        """Головна функція побудови"""
        print("=" * 70)
        print("  REVIT PROJECT BUILDER")
        print("=" * 70)
        print()

        # 1. Перевірити з'єднання
        if not self.check_revit_connection():
            return False

        # 2. Завантажити Families
        self.load_required_families()

        # 3. Розмістити обладнання
        self.place_silos()
        self.place_elevators()
        self.place_conveyors()
        self.place_pipes()

        # 4. Створити аркуші
        self.create_sheets_layout()

        # 5. Підсумок
        self.print_summary()

        return True


# =============================================================================
# КОМАНДНИЙ РЯДОК
# =============================================================================

def main():
    """Головна функція"""
    if len(sys.argv) < 2:
        print("Usage: python build_revit_project_from_config.py <config.json>")
        print("\nExample:")
        print("  python build_revit_project_from_config.py config_6_silos.json")
        sys.exit(1)

    config_path = sys.argv[1]

    # Якщо не absolute path, шукати в PROJECT_ROOT
    if not Path(config_path).is_absolute():
        config_path = CONFIG_DIR / config_path

    # Створити builder
    builder = RevitProjectBuilder(config_path)

    # Запустити побудову
    success = builder.build()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
