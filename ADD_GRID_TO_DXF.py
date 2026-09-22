# -*- coding: utf-8 -*-
"""
ДОДАТИ КООРДИНАТНУ СІТКУ ДО DXF
Для зручності аналізу позицій обладнання
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import ezdxf


def add_grid_to_dxf(dxf_path, grid_step=1000, grid_color=8):
    """
    Додати координатну сітку до існуючого DXF файлу

    Args:
        dxf_path: Шлях до DXF файлу
        grid_step: Крок сітки в мм (за замовчуванням 1000мм = 1м)
        grid_color: Колір сітки (8 = сірий)
    """
    print(f"\n{'='*70}")
    print(f"📐 Додаю сітку до: {Path(dxf_path).name}")
    print(f"{'='*70}")

    # Відкрити DXF
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Створити шар для сітки
    if "GRID" not in doc.layers:
        grid_layer = doc.layers.add(name="GRID")
        grid_layer.color = grid_color
        grid_layer.dxf.lineweight = 0  # Тонка лінія

    # Знайти межі креслення
    min_x, min_y = float('inf'), float('inf')
    max_x, max_y = float('-inf'), float('-inf')

    for entity in msp:
        if entity.dxftype() == 'LINE':
            min_x = min(min_x, entity.dxf.start[0], entity.dxf.end[0])
            max_x = max(max_x, entity.dxf.start[0], entity.dxf.end[0])
            min_y = min(min_y, entity.dxf.start[1], entity.dxf.end[1])
            max_y = max(max_y, entity.dxf.start[1], entity.dxf.end[1])

    print(f"   Межі креслення:")
    print(f"   X: {min_x:.0f} до {max_x:.0f}")
    print(f"   Y: {min_y:.0f} до {max_y:.0f}")

    # Розширити межі на 10%
    margin = grid_step * 2
    min_x = int(min_x / grid_step) * grid_step - margin
    max_x = int(max_x / grid_step) * grid_step + margin
    min_y = int(min_y / grid_step) * grid_step - margin
    max_y = int(max_y / grid_step) * grid_step + margin

    grid_lines = 0

    # Вертикальні лінії сітки
    x = min_x
    while x <= max_x:
        msp.add_line(
            (x, min_y),
            (x, max_y),
            dxfattribs={
                'layer': 'GRID',
                'color': grid_color,
                'lineweight': 0
            }
        )
        # Додати мітку координати
        msp.add_text(
            f"{int(x)}",
            dxfattribs={
                'layer': 'GRID',
                'height': grid_step * 0.05,
                'insert': (x, min_y - grid_step * 0.2),
                'color': grid_color
            }
        )
        grid_lines += 1
        x += grid_step

    # Горизонтальні лінії сітки
    y = min_y
    while y <= max_y:
        msp.add_line(
            (min_x, y),
            (max_x, y),
            dxfattribs={
                'layer': 'GRID',
                'color': grid_color,
                'lineweight': 0
            }
        )
        # Додати мітку координати
        msp.add_text(
            f"{int(y)}",
            dxfattribs={
                'layer': 'GRID',
                'height': grid_step * 0.05,
                'insert': (min_x - grid_step * 0.3, y),
                'color': grid_color
            }
        )
        grid_lines += 1
        y += grid_step

    # Зберегти
    output_path = str(dxf_path).replace('.dxf', '_WITH_GRID.dxf')
    doc.saveas(output_path)

    print(f"\n✅ Додано {grid_lines} ліній сітки")
    print(f"   Крок сітки: {grid_step} мм")
    print(f"   Збережено: {Path(output_path).name}")

    return output_path


def process_all_pages(source_dir="FINAL_DXF_PERFECT_V7", grid_step=1000):
    """Додати сітку до всіх сторінок"""
    source_path = Path(source_dir)

    print("\n" + "📐"*35)
    print("   ДОДАЮ КООРДИНАТНУ СІТКУ ДО ВСІХ СТОРІНОК")
    print("📐"*35)

    dxf_files = sorted(source_path.glob("page_*.dxf"))

    if not dxf_files:
        print(f"\n❌ Файли не знайдено в: {source_path}")
        return

    print(f"\n📂 Знайдено {len(dxf_files)} файлів")
    print(f"   Крок сітки: {grid_step} мм\n")

    output_files = []

    for dxf_file in dxf_files:
        output = add_grid_to_dxf(str(dxf_file), grid_step=grid_step)
        output_files.append(output)

    print("\n" + "="*70)
    print("🎉 ГОТОВО!")
    print("="*70)
    print(f"\n✅ Оброблено {len(output_files)} файлів")
    print("\nФайли з сіткою:")
    for i, f in enumerate(output_files, 1):
        print(f"   {i:2d}. {Path(f).name}")

    return output_files


if __name__ == "__main__":
    # Параметри
    SOURCE_DIR = "d:/autocad project/FINAL_DXF_PERFECT_V7"
    GRID_STEP = 1000  # 1 метр

    print("\n" + "🎯"*35)
    print("   ДОДАВАННЯ КООРДИНАТНОЇ СІТКИ")
    print("🎯"*35)
    print(f"\n📂 Директорія: {SOURCE_DIR}")
    print(f"📐 Крок сітки: {GRID_STEP} мм")

    process_all_pages(SOURCE_DIR, GRID_STEP)

    print("\n💡 ПІДКАЗКА:")
    print("   В AutoCAD можеш вимкнути/увімкнути сітку через шар 'GRID'")
    print("   Команда: LAYER -> знайти GRID -> вимкнути/увімкнути")
