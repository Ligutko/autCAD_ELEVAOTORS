#!/usr/bin/env python
"""
ПРАВИЛЬНЕ масштабування силосу - зміна ДОВЖИНИ ліній!

Ключова ідея:
- Для кожної лінії обчислюємо її ВЕКТОР (напрямок і довжину)
- Збільшуємо ДОВЖИНУ вектора на scale_factor
- Зміщуємо відносно центру

Це СПРАВЖНЄ масштабування!
"""

import ezdxf
from pathlib import Path
import time
import math

SCALE_FACTOR = 1.25  # Збільшити на 25%

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

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            x, y = entity.dxf.insert[0], entity.dxf.insert[1]
            if left_x_min <= x <= left_x_max and left_y_min <= y <= left_y_max:
                in_bounds = True

    if in_bounds:
        left_entities.append(entity)

print(f"  Total entities: {len(left_entities)}")

# КЛЮЧОВИЙ МОМЕНТ - ПРАВИЛЬНЕ масштабування ліній
print(f"\nScaling by {SCALE_FACTOR}x...")

scaled_count = 0

for entity in left_entities:
    if entity.dxftype() == 'LINE':
        # Отримати точки
        x1, y1, z1 = entity.dxf.start
        x2, y2, z2 = entity.dxf.end

        # Обчислити СЕРЕДИНУ лінії
        mid_line_x = (x1 + x2) / 2
        mid_line_y = (y1 + y2) / 2

        # Вектор від центру силоса до середини лінії
        dx_to_line = mid_line_x - left_center_x
        dy_to_line = mid_line_y - left_center_y

        # Нова середина лінії (масштабована)
        new_mid_x = left_center_x + dx_to_line * SCALE_FACTOR
        new_mid_y = left_center_y + dy_to_line * SCALE_FACTOR

        # Вектор самої лінії
        line_vec_x = x2 - x1
        line_vec_y = y2 - y1

        # Масштабувати ДОВЖИНУ лінії
        new_line_vec_x = line_vec_x * SCALE_FACTOR
        new_line_vec_y = line_vec_y * SCALE_FACTOR

        # Нові точки
        new_x1 = new_mid_x - new_line_vec_x / 2
        new_y1 = new_mid_y - new_line_vec_y / 2
        new_x2 = new_mid_x + new_line_vec_x / 2
        new_y2 = new_mid_y + new_line_vec_y / 2

        # ВСТАНОВИТИ нові координати
        entity.dxf.start = (new_x1, new_y1, z1)
        entity.dxf.end = (new_x2, new_y2, z2)

        scaled_count += 1

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            x, y, z = entity.dxf.insert

            # Зсув від центру
            dx = x - left_center_x
            dy = y - left_center_y

            # Нова позиція
            new_x = left_center_x + dx * SCALE_FACTOR
            new_y = left_center_y + dy * SCALE_FACTOR

            entity.dxf.insert = (new_x, new_y, z)

            # ВАЖЛИВО: масштабувати висоту тексту!
            if hasattr(entity.dxf, 'height'):
                entity.dxf.height = entity.dxf.height * SCALE_FACTOR

            scaled_count += 1

    elif entity.dxftype() == 'CIRCLE':
        if hasattr(entity.dxf, 'center'):
            x, y, z = entity.dxf.center

            dx = x - left_center_x
            dy = y - left_center_y

            new_x = left_center_x + dx * SCALE_FACTOR
            new_y = left_center_y + dy * SCALE_FACTOR

            entity.dxf.center = (new_x, new_y, z)

            # МАСШТАБУВАТИ радіус!
            if hasattr(entity.dxf, 'radius'):
                entity.dxf.radius = entity.dxf.radius * SCALE_FACTOR

            scaled_count += 1

print(f"Scaled {scaled_count} entities")

# Зберегти
output_file = f"OUTPUT/page_01_BIGGER_SILO_v{int(time.time())}.dxf"
Path(output_file).parent.mkdir(parents=True, exist_ok=True)

print(f"\nSaving: {output_file}")
doc.saveas(output_file)

print(f"\n{'='*80}")
print(f"SUCCESS!")
print(f"{'='*80}")
print(f"\nMade LEFT silo {SCALE_FACTOR}x BIGGER")
print(f"Modified {scaled_count} entities")
print(f"\nOpen in AutoCAD: {output_file}")
