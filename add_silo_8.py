#!/usr/bin/env python
"""
Додати 8-й силос до page_01_WITH_GRID_AND_SILO_7.dxf

Стратегія:
1. Завантажити page_01_WITH_GRID_AND_SILO_7.dxf (там вже є 7 силосів)
2. Знайти 7-й силос (новий, X > 126м)
3. Скопіювати його ще раз праворуч як 8-й силос
"""

import ezdxf
from pathlib import Path
import time

# Завантажити файл де вже є 7 силосів
input_file = r"d:\autocad project\page_01_WITH_GRID_AND_SILO_7.dxf"
print(f"Loading file with 7 silos: {input_file}")
doc = ezdxf.readfile(input_file)
msp = doc.modelspace()

# Знайти сині лінії (силоси)
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']
print(f"Total blue lines: {len(blue_lines)}")

# Знайти 7-й силос - він має X > 126м
# З аналізу: ORIGINAL max X = 126.3м, WITH_7 max X = 276.3м
# Тобто 7-й силос має X в діапазоні [126, 276]

silo_7_lines = []
for line in blue_lines:
    start_x = line.dxf.start[0]
    end_x = line.dxf.end[0]

    # Якщо ОБІ точки мають X > 126, то це 7-й силос
    if start_x > 126 and end_x > 126:
        silo_7_lines.append(line)

print(f"\nFound SILO_7: {len(silo_7_lines)} blue lines")

if len(silo_7_lines) == 0:
    print("ERROR: Cannot find SILO_7!")
    exit(1)

# Знайти bounds SILO_7
xs = []
ys = []
for line in silo_7_lines:
    xs.extend([line.dxf.start[0], line.dxf.end[0]])
    ys.extend([line.dxf.start[1], line.dxf.end[1]])

x_min_7 = min(xs)
x_max_7 = max(xs)
y_min_7 = min(ys)
y_max_7 = max(ys)

print(f"SILO_7 bounds: X=[{x_min_7:.1f}, {x_max_7:.1f}], Y=[{y_min_7:.1f}, {y_max_7:.1f}]")

# Знайти ВСІ entities в bounds SILO_7 (не тільки сині лінії!)
silo_7_entities = []
for entity in msp:
    if hasattr(entity.dxf, 'layer') and entity.dxf.layer == 'GRID':
        continue

    in_bounds = False

    if entity.dxftype() == 'LINE':
        start_x, start_y = entity.dxf.start[0], entity.dxf.start[1]
        end_x, end_y = entity.dxf.end[0], entity.dxf.end[1]
        if (x_min_7 <= start_x <= x_max_7 and y_min_7 <= start_y <= y_max_7 and
            x_min_7 <= end_x <= x_max_7 and y_min_7 <= end_y <= y_max_7):
            in_bounds = True

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            x, y = entity.dxf.insert[0], entity.dxf.insert[1]
            if x_min_7 <= x <= x_max_7 and y_min_7 <= y <= y_max_7:
                in_bounds = True

    elif entity.dxftype() in ['CIRCLE', 'ARC']:
        if hasattr(entity.dxf, 'center'):
            x, y = entity.dxf.center[0], entity.dxf.center[1]
            if x_min_7 <= x <= x_max_7 and y_min_7 <= y <= y_max_7:
                in_bounds = True

    if in_bounds:
        silo_7_entities.append(entity)

print(f"Found {len(silo_7_entities)} entities in SILO_7 (all types)")

# Розрахувати offset для SILO_8
# Width SILO_7
silo_7_width = x_max_7 - x_min_7
spacing = 150  # мм

offset_for_silo_8 = silo_7_width + spacing

print(f"\nCopying SILO_7 as SILO_8...")
print(f"  SILO_7 width: {silo_7_width:.1f}m")
print(f"  Offset: X + {offset_for_silo_8:.1f}m")

# Скопіювати SILO_8
copied = 0
for entity in silo_7_entities:
    new_entity = entity.copy()

    if entity.dxftype() == 'LINE':
        new_entity.dxf.start = (entity.dxf.start[0] + offset_for_silo_8, entity.dxf.start[1], entity.dxf.start[2])
        new_entity.dxf.end = (entity.dxf.end[0] + offset_for_silo_8, entity.dxf.end[1], entity.dxf.end[2])

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            new_entity.dxf.insert = (entity.dxf.insert[0] + offset_for_silo_8, entity.dxf.insert[1], entity.dxf.insert[2])

    elif entity.dxftype() in ['CIRCLE', 'ARC']:
        if hasattr(entity.dxf, 'center'):
            new_entity.dxf.center = (entity.dxf.center[0] + offset_for_silo_8, entity.dxf.center[1], entity.dxf.center[2])

    msp.add_entity(new_entity)
    copied += 1

print(f"  Created SILO_8: {copied} entities")

# Зберегти
output_file = f"OUTPUT/page_01_WITH_8_SILOS_v{int(time.time())}.dxf"
Path(output_file).parent.mkdir(parents=True, exist_ok=True)

print(f"\nSaving: {output_file}")
doc.saveas(output_file)

print(f"\n{'='*80}")
print(f"SUCCESS!")
print(f"{'='*80}")
print(f"\nCreated file with 8 silos!")
print(f"Added {copied} entities for SILO_8")
print(f"\nOpen in AutoCAD: {output_file}")
