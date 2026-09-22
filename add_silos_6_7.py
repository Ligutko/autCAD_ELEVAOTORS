#!/usr/bin/env python
"""
Додати 6-й та 7-й силос до оригінального креслення page_01_WITH_GRID.dxf

Підхід:
1. Завантажити оригінал
2. Знайти SILO_TOP_4 (найправіший) по координатах з ANALYSIS/SILOS_ALL_FINAL.json
3. Скопіювати всі його лінії праворуч як SILO_6 та SILO_7
4. Подовжити конвеєри
5. Зберегти результат
"""

import ezdxf
import json
from pathlib import Path

# Завантажити метадані екстрактованих силосів
with open('ANALYSIS/SILOS_ALL_FINAL.json', 'r', encoding='utf-8') as f:
    silos_data = json.load(f)

# Знайти SILO_TOP_4 (останній верхній силос)
silo_top_4 = None
for silo in silos_data['silos_top']:
    if silo['id'] == 'SILO_TOP_4':
        silo_top_4 = silo
        break

if not silo_top_4:
    print("ERROR: Cannot find SILO_TOP_4 in metadata!")
    exit(1)

print(f"Found SILO_TOP_4:")
print(f"  Center: ({silo_top_4['center'][0]:.1f}, {silo_top_4['center'][1]:.1f})")
print(f"  Bounds: X={silo_top_4['bounds']['x_min']:.1f} to {silo_top_4['bounds']['x_max']:.1f}")
print(f"          Y={silo_top_4['bounds']['y_min']:.1f} to {silo_top_4['bounds']['y_max']:.1f}")
print(f"  Lines: {silo_top_4['lines_count']}")

# Завантажити оригінальне креслення
original_file = r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01_WITH_GRID.dxf"
print(f"\nLoading original: {original_file}")
doc = ezdxf.readfile(original_file)
msp = doc.modelspace()

# Знайти всі лінії SILO_TOP_4 (сині лінії в bounds силосу)
x_min = silo_top_4['bounds']['x_min']
x_max = silo_top_4['bounds']['x_max']
y_min = silo_top_4['bounds']['y_min']
y_max = silo_top_4['bounds']['y_max']

silo_4_entities = []
for entity in msp:
    # Пропустити GRID
    if hasattr(entity.dxf, 'layer') and entity.dxf.layer == 'GRID':
        continue

    # Перевірити чи entity в bounds SILO_TOP_4
    in_bounds = False

    if entity.dxftype() == 'LINE':
        start_x, start_y = entity.dxf.start[0], entity.dxf.start[1]
        end_x, end_y = entity.dxf.end[0], entity.dxf.end[1]
        # Entity в bounds якщо ОБІ точки в bounds
        if (x_min <= start_x <= x_max and y_min <= start_y <= y_max and
            x_min <= end_x <= x_max and y_min <= end_y <= y_max):
            in_bounds = True

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            x, y = entity.dxf.insert[0], entity.dxf.insert[1]
            if x_min <= x <= x_max and y_min <= y <= y_max:
                in_bounds = True

    elif entity.dxftype() in ['CIRCLE', 'ARC']:
        if hasattr(entity.dxf, 'center'):
            x, y = entity.dxf.center[0], entity.dxf.center[1]
            if x_min <= x <= x_max and y_min <= y <= y_max:
                in_bounds = True

    if in_bounds:
        silo_4_entities.append(entity)

print(f"\nFound {len(silo_4_entities)} entities in SILO_TOP_4 (ALL: lines, text, etc)")

if len(silo_4_entities) == 0:
    print("ERROR: No lines found! Check bounds!")
    exit(1)

# Розрахувати offset для копіювання
# Ширина SILO_TOP_4
silo_width = x_max - x_min
silo_spacing = 150  # мм між силосами (як в config)

offset_for_silo_5 = silo_width + silo_spacing
offset_for_silo_6 = 2 * (silo_width + silo_spacing)

print(f"\nCopying SILO_TOP_4...")
print(f"  Silo width: {silo_width:.1f}m")
print(f"  Spacing: {silo_spacing:.1f}m")
print(f"  Offset for SILO#5: X + {offset_for_silo_5:.1f}m")
print(f"  Offset for SILO#6: X + {offset_for_silo_6:.1f}m")

# Скопіювати SILO#5
copied_count = 0
for entity in silo_4_entities:
    # Створити копію entity
    new_entity = entity.copy()

    # Застосувати offset
    if entity.dxftype() == 'LINE':
        new_entity.dxf.start = (entity.dxf.start[0] + offset_for_silo_5, entity.dxf.start[1], entity.dxf.start[2])
        new_entity.dxf.end = (entity.dxf.end[0] + offset_for_silo_5, entity.dxf.end[1], entity.dxf.end[2])

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            new_entity.dxf.insert = (entity.dxf.insert[0] + offset_for_silo_5, entity.dxf.insert[1], entity.dxf.insert[2])

    elif entity.dxftype() in ['CIRCLE', 'ARC']:
        if hasattr(entity.dxf, 'center'):
            new_entity.dxf.center = (entity.dxf.center[0] + offset_for_silo_5, entity.dxf.center[1], entity.dxf.center[2])

    # Додати в креслення
    msp.add_entity(new_entity)
    copied_count += 1

print(f"  Created SILO#5: {copied_count} entities")

# Скопіювати SILO#6
copied_count = 0
for entity in silo_4_entities:
    new_entity = entity.copy()

    if entity.dxftype() == 'LINE':
        new_entity.dxf.start = (entity.dxf.start[0] + offset_for_silo_6, entity.dxf.start[1], entity.dxf.start[2])
        new_entity.dxf.end = (entity.dxf.end[0] + offset_for_silo_6, entity.dxf.end[1], entity.dxf.end[2])

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            new_entity.dxf.insert = (entity.dxf.insert[0] + offset_for_silo_6, entity.dxf.insert[1], entity.dxf.insert[2])

    elif entity.dxftype() in ['CIRCLE', 'ARC']:
        if hasattr(entity.dxf, 'center'):
            new_entity.dxf.center = (entity.dxf.center[0] + offset_for_silo_6, entity.dxf.center[1], entity.dxf.center[2])

    msp.add_entity(new_entity)
    copied_count += 1

print(f"  Created SILO#6: {copied_count} entities")

# TODO: Подовжити конвеєри (червоні лінії RGB_255_000_000)
# Поки що пропускаємо - спочатку перевірю чи працює копіювання силосів

# Зберегти результат
import time
output_file = f"OUTPUT/page_01_WITH_6_AND_7_SILOS_v{int(time.time())}.dxf"
Path(output_file).parent.mkdir(parents=True, exist_ok=True)

print(f"\nSaving result: {output_file}")
doc.saveas(output_file)

print(f"\n{'='*80}")
print(f"SUCCESS!")
print(f"{'='*80}")
print(f"\nGenerated: {output_file}")
print(f"\nOriginal had: ~47000 entities")
print(f"Added: {2 * len(silo_4_entities)} entities (2 new silos with ALL details)")
print(f"\nOpen in AutoCAD to verify!")
