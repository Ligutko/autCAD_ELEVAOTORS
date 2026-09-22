#!/usr/bin/env python
"""
DEBUG версія - виводити ЩО робиться з кожною лінією
"""

import ezdxf
from pathlib import Path
import time

SCALE_FACTOR = 1.25

# Завантажити
input_file = r"d:\autocad project\page_01_WITH_GRID_AND_SILO_7.dxf"
print(f"Loading: {input_file}")
doc = ezdxf.readfile(input_file)
msp = doc.modelspace()

# Знайти нижні сині лінії
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']
lower_blue = [e for e in blue_lines if e.dxf.start[1] < 200 and e.dxf.end[1] < 200]

# Розділити на ЛІВИЙ та ПРАВИЙ
xs_all = []
for line in lower_blue:
    xs_all.extend([line.dxf.start[0], line.dxf.end[0]])

mid_x = (min(xs_all) + max(xs_all)) / 2

left_blue = [e for e in lower_blue if e.dxf.start[0] < mid_x and e.dxf.end[0] < mid_x]

# Bounds ЛІВОГО силоса
xs_left = []
ys_left = []
for line in left_blue:
    xs_left.extend([line.dxf.start[0], line.dxf.end[0]])
    ys_left.extend([line.dxf.start[1], line.dxf.end[1]])

left_x_min, left_x_max = min(xs_left), max(xs_left)
left_y_min, left_y_max = min(ys_left), max(ys_left)
left_center_x = (left_x_min + left_x_max) / 2
left_center_y = (left_y_min + left_y_max) / 2

print(f"LEFT silo center: ({left_center_x:.1f}, {left_center_y:.1f})")
print(f"  Blue lines: {len(left_blue)}")

# Знайти ВСІ entities ЛІВОГО силоса
left_entities = []
for entity in msp:
    if hasattr(entity.dxf, 'layer') and entity.dxf.layer == 'GRID':
        continue

    in_bounds = False

    if entity.dxftype() == 'LINE':
        start_x, start_y = entity.dxf.start[0], entity.dxf.start[1]
        end_x, end_y = entity.dxf.end[0], entity.dxf.end[1]
        if (left_x_min <= start_x <= left_x_max and left_y_min <= start_y <= left_y_max and
            left_x_min <= end_x <= left_x_max and left_y_min <= end_y <= left_y_max):
            in_bounds = True

    if in_bounds:
        left_entities.append(entity)

print(f"  Total LINE entities: {len(left_entities)}")

print(f"\nScaling by {SCALE_FACTOR}x...")
print("\nDEBUG: First 3 lines BEFORE and AFTER:")

scaled_count = 0

for i, entity in enumerate(left_entities):
    if entity.dxftype() == 'LINE':
        # BEFORE
        x1_old, y1_old, z1 = entity.dxf.start
        x2_old, y2_old, z2 = entity.dxf.end

        old_vec_x = x2_old - x1_old
        old_vec_y = y2_old - y1_old
        old_len = (old_vec_x**2 + old_vec_y**2)**0.5

        # Обчислити СЕРЕДИНУ лінії
        mid_line_x = (x1_old + x2_old) / 2
        mid_line_y = (y1_old + y2_old) / 2

        # Вектор від центру силоса до середини лінії
        dx_to_line = mid_line_x - left_center_x
        dy_to_line = mid_line_y - left_center_y

        # Нова середина лінії (масштабована)
        new_mid_x = left_center_x + dx_to_line * SCALE_FACTOR
        new_mid_y = left_center_y + dy_to_line * SCALE_FACTOR

        # Вектор самої лінії
        line_vec_x = x2_old - x1_old
        line_vec_y = y2_old - y1_old

        # Масштабувати ДОВЖИНУ лінії
        new_line_vec_x = line_vec_x * SCALE_FACTOR
        new_line_vec_y = line_vec_y * SCALE_FACTOR

        # Нові точки
        new_x1 = new_mid_x - new_line_vec_x / 2
        new_y1 = new_mid_y - new_line_vec_y / 2
        new_x2 = new_mid_x + new_line_vec_x / 2
        new_y2 = new_mid_y + new_line_vec_y / 2

        # DEBUG для перших 3 ліній
        if i < 3:
            print(f"\n  Line {i}:")
            print(f"    BEFORE: start=({x1_old:.2f}, {y1_old:.2f}), end=({x2_old:.2f}, {y2_old:.2f})")
            print(f"      vector=({old_vec_x:.2f}, {old_vec_y:.2f}), length={old_len:.2f}")
            print(f"    CALCULATION:")
            print(f"      old midpoint=({mid_line_x:.2f}, {mid_line_y:.2f})")
            print(f"      new midpoint=({new_mid_x:.2f}, {new_mid_y:.2f})")
            print(f"      new vector=({new_line_vec_x:.2f}, {new_line_vec_y:.2f})")
            print(f"      new length={(new_line_vec_x**2 + new_line_vec_y**2)**0.5:.2f}")
            print(f"    AFTER (calculated): start=({new_x1:.2f}, {new_y1:.2f}), end=({new_x2:.2f}, {new_y2:.2f})")

        # ВСТАНОВИТИ нові координати
        entity.dxf.start = (new_x1, new_y1, z1)
        entity.dxf.end = (new_x2, new_y2, z2)

        # Перевірити ЩО НАСПРАВДІ збережено
        if i < 3:
            actual_start = entity.dxf.start
            actual_end = entity.dxf.end
            actual_vec_x = actual_end[0] - actual_start[0]
            actual_vec_y = actual_end[1] - actual_start[1]
            actual_len = (actual_vec_x**2 + actual_vec_y**2)**0.5
            print(f"    AFTER (actual in memory): start=({actual_start[0]:.2f}, {actual_start[1]:.2f}), end=({actual_end[0]:.2f}, {actual_end[1]:.2f})")
            print(f"      actual vector=({actual_vec_x:.2f}, {actual_vec_y:.2f}), actual length={actual_len:.2f}")

        scaled_count += 1

print(f"\nScaled {scaled_count} line entities")

# Зберегти
output_file = f"OUTPUT/page_01_DEBUG_v{int(time.time())}.dxf"
Path(output_file).parent.mkdir(parents=True, exist_ok=True)

print(f"\nSaving: {output_file}")
doc.saveas(output_file)

print(f"\n{'='*80}")
print(f"DONE! Now check what's ACTUALLY in the saved file...")
print(f"{'='*80}")
