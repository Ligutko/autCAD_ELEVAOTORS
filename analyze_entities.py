#!/usr/bin/env python
"""Проаналізувати ВСІ типи entities в bounds SILO_TOP_4"""

import ezdxf
import json

# Завантажити метадані
with open('ANALYSIS/SILOS_ALL_FINAL.json', 'r', encoding='utf-8') as f:
    silos_data = json.load(f)

silo_top_4 = None
for silo in silos_data['silos_top']:
    if silo['id'] == 'SILO_TOP_4':
        silo_top_4 = silo
        break

x_min = silo_top_4['bounds']['x_min']
x_max = silo_top_4['bounds']['x_max']
y_min = silo_top_4['bounds']['y_min']
y_max = silo_top_4['bounds']['y_max']

print(f"SILO_TOP_4 bounds: X=[{x_min:.1f}, {x_max:.1f}], Y=[{y_min:.1f}, {y_max:.1f}]")

# Завантажити оригінал
doc = ezdxf.readfile(r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01_WITH_GRID.dxf")
msp = doc.modelspace()

# Знайти ВСІ entities в bounds SILO_TOP_4
entities_in_area = []

for entity in msp:
    # Пропустити GRID
    if hasattr(entity.dxf, 'layer') and entity.dxf.layer == 'GRID':
        continue

    # Перевірити чи entity в bounds
    in_bounds = False

    if entity.dxftype() == 'LINE':
        start_x, start_y = entity.dxf.start[0], entity.dxf.start[1]
        end_x, end_y = entity.dxf.end[0], entity.dxf.end[1]
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
        entities_in_area.append(entity)

print(f"\nFound {len(entities_in_area)} entities in SILO_TOP_4 area")

# Групувати по типах
types_count = {}
layers_count = {}

for entity in entities_in_area:
    etype = entity.dxftype()
    types_count[etype] = types_count.get(etype, 0) + 1

    if hasattr(entity.dxf, 'layer'):
        layer = entity.dxf.layer
        layers_count[layer] = layers_count.get(layer, 0) + 1

print(f"\nEntity types:")
for etype, count in sorted(types_count.items()):
    print(f"  {etype}: {count}")

print(f"\nLayers:")
for layer, count in sorted(layers_count.items()):
    print(f"  {layer}: {count}")

print(f"\nТепер я знаю ЩО потрібно копіювати!")
print(f"Всього entities для копіювання: {len(entities_in_area)}")
