#!/usr/bin/env python
"""
SCHEMA MODIFIER - Модифікує ОРИГІНАЛЬНЕ креслення

Замість створення нового DXF з нуля, цей модуль:
1. Завантажує ОРИГІНАЛЬНИЙ page_01_WITH_GRID.dxf
2. Знаходить 5-й силос (найправіший)
3. Копіює його як 6-й та 7-й силос
4. Подовжує конвеєри
5. Зберігає модифікований файл

Це ПРАВИЛЬНИЙ підхід який зберігає всю деталізацію оригіналу!
"""

import ezdxf
from pathlib import Path
from typing import Dict, List, Tuple, Any


class SchemaModifier:
    """Модифікатор креслень - працює з ОРИГІНАЛЬНИМ файлом"""

    def __init__(self, original_file: str):
        """
        Args:
            original_file: Шлях до оригінального DXF файлу
        """
        self.original_file = original_file
        self.doc = None
        self.msp = None

    def load_original(self) -> bool:
        """Завантажити оригінальне креслення"""
        try:
            print(f"\nLoading original: {self.original_file}")
            self.doc = ezdxf.readfile(self.original_file)
            self.msp = self.doc.modelspace()

            total_entities = len(list(self.msp))
            print(f"  Loaded: {total_entities} entities")

            return True

        except Exception as e:
            print(f"ERROR loading original: {e}")
            return False

    def find_silos(self) -> List[Dict]:
        """
        Знайти всі силоси в оригінальному кресленні

        Returns:
            Список силосів з їх bounds та entities
        """
        # Силоси - синій layer (RGB_000_000_255)
        blue_lines = [
            e for e in self.msp
            if e.dxftype() == 'LINE' and
            hasattr(e.dxf, 'layer') and
            e.dxf.layer == 'RGB_000_000_255'
        ]

        print(f"\nFound {len(blue_lines)} blue lines (silos)")

        # TODO: Групування ліній по окремим силосам
        # Це складніше - потрібно аналізувати топологію

        return []

    def copy_silo(self, silo_entities: List, offset_x: float, offset_y: float):
        """
        Скопіювати силос з offset

        Args:
            silo_entities: Список entities силосу
            offset_x: Зсув по X (мм)
            offset_y: Зсув по Y (мм)
        """
        for entity in silo_entities:
            # Створити копію
            new_entity = entity.copy()

            # Застосувати offset
            if hasattr(new_entity.dxf, 'start'):
                new_entity.dxf.start = (
                    new_entity.dxf.start[0] + offset_x,
                    new_entity.dxf.start[1] + offset_y,
                    new_entity.dxf.start[2]
                )
            if hasattr(new_entity.dxf, 'end'):
                new_entity.dxf.end = (
                    new_entity.dxf.end[0] + offset_x,
                    new_entity.dxf.end[1] + offset_y,
                    new_entity.dxf.end[2]
                )

            # Додати до креслення
            self.msp.add_entity(new_entity)

    def save(self, output_file: str) -> bool:
        """
        Зберегти модифіковане креслення

        Args:
            output_file: Шлях до вихідного файлу

        Returns:
            True якщо успішно
        """
        try:
            print(f"\nSaving modified drawing: {output_file}")
            self.doc.saveas(output_file)
            print(f"  Saved successfully!")
            return True

        except Exception as e:
            print(f"ERROR saving: {e}")
            return False


def main():
    """Тест модифікатора"""
    original = r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01_WITH_GRID.dxf"

    modifier = SchemaModifier(original)

    if not modifier.load_original():
        return

    # Знайти силоси
    silos = modifier.find_silos()

    print(f"\nFound {len(silos)} silos")


if __name__ == "__main__":
    main()
