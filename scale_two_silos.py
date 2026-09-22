#!/usr/bin/env python
"""
Масштабувати два силоси - зробити їх БІЛЬШИМИ

Стратегія:
1. Завантажити файл
2. Вибрати які 2 силоси масштабувати (вкажіть їх X позиції)
3. Для кожного силоса:
   - Знайти центр
   - Масштабувати всі entities відносно центру
"""

import ezdxf
from pathlib import Path
import time

# Параметри масштабування
SCALE_FACTOR = 1.25  # Збільшити на 25%

# Завантажити файл
input_file = r"d:\autocad project\OUTPUT\page_01_WITH_8_SILOS_v1766707448.dxf"
print(f"Loading: {input_file}")
doc = ezdxf.readfile(input_file)
msp = doc.modelspace()

# Знайти всі сині лінії (силоси)
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']
print(f"Total blue lines: {len(blue_lines)}")

# Показати приблизні позиції силосів
xs_all = []
for line in blue_lines:
    xs_all.extend([line.dxf.start[0], line.dxf.end[0]])

print(f"\nX range: {min(xs_all):.1f} to {max(xs_all):.1f}")

# Групування силосів по X координатах
# Будемо шукати "кластери" ліній
print("\nAnalyzing silo positions...")

# Проста стратегія: знайти нижні силоси (Y < 200м)
lower_silos = [e for e in blue_lines if e.dxf.start[1] < 200 and e.dxf.end[1] < 200]
print(f"Lower silos lines: {len(lower_silos)}")

if len(lower_silos) == 0:
    print("ERROR: Cannot find lower silos!")
    exit(1)

# Знайти bounds нижніх силосів
xs_lower = []
ys_lower = []
for line in lower_silos:
    xs_lower.extend([line.dxf.start[0], line.dxf.end[0]])
    ys_lower.extend([line.dxf.start[1], line.dxf.end[1]])

x_min_lower = min(xs_lower)
x_max_lower = max(xs_lower)
y_min_lower = min(ys_lower)
y_max_lower = max(ys_lower)

print(f"Lower silos bounds: X=[{x_min_lower:.1f}, {x_max_lower:.1f}], Y=[{y_min_lower:.1f}, {y_max_lower:.1f}]")

# Знайти центр нижніх силосів
center_x = (x_min_lower + x_max_lower) / 2
center_y = (y_min_lower + y_max_lower) / 2

print(f"Center of lower silos: ({center_x:.1f}, {center_y:.1f})")
print(f"\nScaling by factor: {SCALE_FACTOR}")

# Знайти ВСІ entities в bounds нижніх силосів
entities_to_scale = []
for entity in msp:
    if hasattr(entity.dxf, 'layer') and entity.dxf.layer == 'GRID':
        continue

    in_bounds = False

    if entity.dxftype() == 'LINE':
        start_x, start_y = entity.dxf.start[0], entity.dxf.start[1]
        end_x, end_y = entity.dxf.end[0], entity.dxf.end[1]
        if (x_min_lower <= start_x <= x_max_lower and y_min_lower <= start_y <= y_max_lower and
            x_min_lower <= end_x <= x_max_lower and y_min_lower <= end_y <= y_max_lower):
            in_bounds = True

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            x, y = entity.dxf.insert[0], entity.dxf.insert[1]
            if x_min_lower <= x <= x_max_lower and y_min_lower <= y <= y_max_lower:
                in_bounds = True

    elif entity.dxftype() in ['CIRCLE', 'ARC']:
        if hasattr(entity.dxf, 'center'):
            x, y = entity.dxf.center[0], entity.dxf.center[1]
            if x_min_lower <= x <= x_max_lower and y_min_lower <= y <= y_max_lower:
                in_bounds = True

    if in_bounds:
        entities_to_scale.append(entity)

print(f"Found {len(entities_to_scale)} entities to scale")

# Масштабувати entities відносно центру
scaled_count = 0
for entity in entities_to_scale:
    if entity.dxftype() == 'LINE':
        # Масштабувати start
        dx_start = entity.dxf.start[0] - center_x
        dy_start = entity.dxf.start[1] - center_y
        new_start_x = center_x + dx_start * SCALE_FACTOR
        new_start_y = center_y + dy_start * SCALE_FACTOR

        # Масштабувати end
        dx_end = entity.dxf.end[0] - center_x
        dy_end = entity.dxf.end[1] - center_y
        new_end_x = center_x + dx_end * SCALE_FACTOR
        new_end_y = center_y + dy_end * SCALE_FACTOR

        entity.dxf.start = (new_start_x, new_start_y, entity.dxf.start[2])
        entity.dxf.end = (new_end_x, new_end_y, entity.dxf.end[2])
        scaled_count += 1

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            dx = entity.dxf.insert[0] - center_x
            dy = entity.dxf.insert[1] - center_y
            new_x = center_x + dx * SCALE_FACTOR
            new_y = center_y + dy * SCALE_FACTOR
            entity.dxf.insert = (new_x, new_y, entity.dxf.insert[2])
            scaled_count += 1

    elif entity.dxftype() in ['CIRCLE', 'ARC']:
        if hasattr(entity.dxf, 'center'):
            dx = entity.dxf.center[0] - center_x
            dy = entity.dxf.center[1] - center_y
            new_x = center_x + dx * SCALE_FACTOR
            new_y = center_y + dy * SCALE_FACTOR
            entity.dxf.center = (new_x, new_y, entity.dxf.center[2])

            # Масштабувати радіус для CIRCLE
            if entity.dxftype() == 'CIRCLE' and hasattr(entity.dxf, 'radius'):
                entity.dxf.radius = entity.dxf.radius * SCALE_FACTOR
            scaled_count += 1

print(f"Scaled {scaled_count} entities")

# Зберегти
output_file = f"OUTPUT/page_01_WITH_SCALED_SILOS_v{int(time.time())}.dxf"
Path(output_file).parent.mkdir(parents=True, exist_ok=True)

print(f"\nSaving: {output_file}")
doc.saveas(output_file)

print(f"\n{'='*80}")
print(f"SUCCESS!")
print(f"{'='*80}")
print(f"\nScaled lower silos by factor {SCALE_FACTOR}")
print(f"Modified {scaled_count} entities")
print(f"\nOpen in AutoCAD: {output_file}")
