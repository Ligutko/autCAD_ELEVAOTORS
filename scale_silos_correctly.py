#!/usr/bin/env python
"""
ПРАВИЛЬНЕ масштабування 2 нижніх силосів

Проблема попередньої версії: я змінював координати, але НЕ змінював розміри самих об'єктів!

Правильний підхід:
1. Знайти 2 нижні силоси
2. Для КОЖНОГО силоса окремо:
   - Видалити старі entities
   - Створити нові масштабовані entities
"""

import ezdxf
from pathlib import Path
import time

SCALE_FACTOR = 1.25  # Збільшити на 25%

# Завантажити файл
input_file = r"d:\autocad project\page_01_WITH_GRID_AND_SILO_7.dxf"
print(f"Loading: {input_file}")
doc = ezdxf.readfile(input_file)
msp = doc.modelspace()

# Знайти нижні сині лінії
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']
lower_blue = [e for e in blue_lines if e.dxf.start[1] < 200 and e.dxf.end[1] < 200]

print(f"Total blue lines: {len(blue_lines)}")
print(f"Lower blue lines: {len(lower_blue)}")

# Розділити на 2 силоси
xs_all = []
for line in lower_blue:
    xs_all.extend([line.dxf.start[0], line.dxf.end[0]])

mid_x = (min(xs_all) + max(xs_all)) / 2

left_blue = [e for e in lower_blue if e.dxf.start[0] < mid_x and e.dxf.end[0] < mid_x]
right_blue = [e for e in lower_blue if e.dxf.start[0] > mid_x and e.dxf.end[0] > mid_x]

# Bounds для ЛІВОГО силоса
xs_left = []
ys_left = []
for line in left_blue:
    xs_left.extend([line.dxf.start[0], line.dxf.end[0]])
    ys_left.extend([line.dxf.start[1], line.dxf.end[1]])

left_x_min, left_x_max = min(xs_left), max(xs_left)
left_y_min, left_y_max = min(ys_left), max(ys_left)
left_center_x = (left_x_min + left_x_max) / 2
left_center_y = (left_y_min + left_y_max) / 2

print(f"\nLEFT silo: X=[{left_x_min:.1f}, {left_x_max:.1f}], Y=[{left_y_min:.1f}, {left_y_max:.1f}]")
print(f"  Center: ({left_center_x:.1f}, {left_center_y:.1f})")
print(f"  Blue lines: {len(left_blue)}")

# Bounds для ПРАВОГО силоса
xs_right = []
ys_right = []
for line in right_blue:
    xs_right.extend([line.dxf.start[0], line.dxf.end[0]])
    ys_right.extend([line.dxf.start[1], line.dxf.end[1]])

right_x_min, right_x_max = min(xs_right), max(xs_right)
right_y_min, right_y_max = min(ys_right), max(ys_right)
right_center_x = (right_x_min + right_x_max) / 2
right_center_y = (right_y_min + right_y_max) / 2

print(f"\nRIGHT silo: X=[{right_x_min:.1f}, {right_x_max:.1f}], Y=[{right_y_min:.1f}, {right_y_max:.1f}]")
print(f"  Center: ({right_center_x:.1f}, {right_center_y:.1f})")
print(f"  Blue lines: {len(right_blue)}")

# Знайти ВСІ entities для ЛІВОГО силоса
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

# Знайти ВСІ entities для ПРАВОГО силоса
right_entities = []
for entity in msp:
    if hasattr(entity.dxf, 'layer') and entity.dxf.layer == 'GRID':
        continue

    in_bounds = False

    if entity.dxftype() == 'LINE':
        start_x, start_y = entity.dxf.start[0], entity.dxf.start[1]
        end_x, end_y = entity.dxf.end[0], entity.dxf.end[1]
        if (right_x_min <= start_x <= right_x_max and right_y_min <= start_y <= right_y_max and
            right_x_min <= end_x <= right_x_max and right_y_min <= end_y <= right_y_max):
            in_bounds = True

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            x, y = entity.dxf.insert[0], entity.dxf.insert[1]
            if right_x_min <= x <= right_x_max and right_y_min <= y <= right_y_max:
                in_bounds = True

    if in_bounds:
        right_entities.append(entity)

print(f"  Total entities: {len(right_entities)}")

print(f"\nScaling by factor: {SCALE_FACTOR}")

# Функція для масштабування entity
def scale_entity(entity, center_x, center_y, scale):
    """Масштабувати entity відносно центру"""
    if entity.dxftype() == 'LINE':
        # Масштабувати start point
        dx_start = entity.dxf.start[0] - center_x
        dy_start = entity.dxf.start[1] - center_y
        new_start_x = center_x + dx_start * scale
        new_start_y = center_y + dy_start * scale

        # Масштабувати end point
        dx_end = entity.dxf.end[0] - center_x
        dy_end = entity.dxf.end[1] - center_y
        new_end_x = center_x + dx_end * scale
        new_end_y = center_y + dy_end * scale

        entity.dxf.start = (new_start_x, new_start_y, entity.dxf.start[2])
        entity.dxf.end = (new_end_x, new_end_y, entity.dxf.end[2])

    elif entity.dxftype() in ['TEXT', 'MTEXT']:
        if hasattr(entity.dxf, 'insert'):
            dx = entity.dxf.insert[0] - center_x
            dy = entity.dxf.insert[1] - center_y
            new_x = center_x + dx * scale
            new_y = center_y + dy * scale
            entity.dxf.insert = (new_x, new_y, entity.dxf.insert[2])

            # ВАЖЛИВО: масштабувати ВИСОТУ тексту!
            if hasattr(entity.dxf, 'height'):
                entity.dxf.height = entity.dxf.height * scale

    elif entity.dxftype() == 'CIRCLE':
        if hasattr(entity.dxf, 'center'):
            dx = entity.dxf.center[0] - center_x
            dy = entity.dxf.center[1] - center_y
            new_x = center_x + dx * scale
            new_y = center_y + dy * scale
            entity.dxf.center = (new_x, new_y, entity.dxf.center[2])

            # ВАЖЛИВО: масштабувати РАДІУС!
            if hasattr(entity.dxf, 'radius'):
                entity.dxf.radius = entity.dxf.radius * scale

# Масштабувати ЛІВИЙ силос
for entity in left_entities:
    scale_entity(entity, left_center_x, left_center_y, SCALE_FACTOR)

print(f"Scaled LEFT silo: {len(left_entities)} entities")

# Масштабувати ПРАВИЙ силос
for entity in right_entities:
    scale_entity(entity, right_center_x, right_center_y, SCALE_FACTOR)

print(f"Scaled RIGHT silo: {len(right_entities)} entities")

# Зберегти
output_file = f"OUTPUT/page_01_SCALED_CORRECTLY_v{int(time.time())}.dxf"
Path(output_file).parent.mkdir(parents=True, exist_ok=True)

print(f"\nSaving: {output_file}")
doc.saveas(output_file)

print(f"\n{'='*80}")
print(f"SUCCESS!")
print(f"{'='*80}")
print(f"\nScaled 2 lower silos by factor {SCALE_FACTOR}")
print(f"LEFT silo: {len(left_entities)} entities")
print(f"RIGHT silo: {len(right_entities)} entities")
print(f"\nOpen in AutoCAD: {output_file}")
