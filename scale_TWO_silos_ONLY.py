#!/usr/bin/env python
"""
Масштабувати ТІЛЬКИ 2 конкретні силоси - найлівіші з нижнього ряду
ТОЧНО визначити їх bounds і масштабувати ТІЛЬКИ ці entities!
"""

import ezdxf
from pathlib import Path
import time

SCALE_FACTOR = 1.25

# Завантажити
input_file = r"d:\autocad project\OUTPUT\page_01_WITH_8_SILOS_v1766707448.dxf"
print(f"Loading: {input_file}")
doc = ezdxf.readfile(input_file)
msp = doc.modelspace()

# Знайти нижні сині лінії
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']
lower_blue = [e for e in blue_lines if e.dxf.start[1] < 200 and e.dxf.end[1] < 200]

print(f"Lower blue lines: {len(lower_blue)}")

# Знайти 2 НАЙЛІВІШІ групи ліній (кожна група = один силос)
# Стратегія: сортувати за X, групувати з невеликим gap (діаметр силоса ~220mm)

xs_centers = []
for line in lower_blue:
    center_x = (line.dxf.start[0] + line.dxf.end[0]) / 2
    xs_centers.append(center_x)

# Знайти 2 найлівіші X координати
xs_unique = sorted(set(xs_centers))

# Групувати: якщо різниця > 250mm то це новий силос
silos = []
current_group = []

for x in xs_unique:
    if not current_group:
        current_group.append(x)
    else:
        if x - current_group[-1] > 250:  # Новий силос
            if current_group:
                silos.append((min(current_group), max(current_group)))
            current_group = [x]
        else:
            current_group.append(x)

if current_group:
    silos.append((min(current_group), max(current_group)))

print(f"\nFound {len(silos)} distinct silos")

# Взяти 2 НАЙЛІВІШІ
silos = sorted(silos, key=lambda s: s[0])[:2]

print(f"\nSelecting 2 LEFTMOST silos:")
for i, (x_min, x_max) in enumerate(silos):
    print(f"  Silo {i+1}: X range [{x_min:.1f}, {x_max:.1f}]")

# Для КОЖНОГО з 2 силосів - знайти entities і масштабувати
for silo_idx, (x_min_range, x_max_range) in enumerate(silos):
    print(f"\n{'='*60}")
    print(f"Processing Silo {silo_idx+1}...")
    print(f"{'='*60}")

    # Знайти сині лінії цього силоса
    silo_blue = []
    for line in lower_blue:
        center_x = (line.dxf.start[0] + line.dxf.end[0]) / 2
        if x_min_range <= center_x <= x_max_range:
            silo_blue.append(line)

    print(f"  Blue lines: {len(silo_blue)}")

    # Знайти ТОЧНІ bounds цього силоса
    xs = []
    ys = []
    for line in silo_blue:
        xs.extend([line.dxf.start[0], line.dxf.end[0]])
        ys.extend([line.dxf.start[1], line.dxf.end[1]])

    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2

    print(f"  Bounds: X=[{x_min:.1f}, {x_max:.1f}], Y=[{y_min:.1f}, {y_max:.1f}]")
    print(f"  Center: ({center_x:.1f}, {center_y:.1f})")

    # Знайти ВСІ entities в цих bounds
    silo_entities = []

    for entity in msp:
        # Пропустити GRID
        if hasattr(entity.dxf, 'layer') and entity.dxf.layer == 'GRID':
            continue

        in_bounds = False

        if entity.dxftype() == 'LINE':
            start_x, start_y = entity.dxf.start[0], entity.dxf.start[1]
            end_x, end_y = entity.dxf.end[0], entity.dxf.end[1]

            # СТРОГА перевірка - ОБІ точки мають бути в bounds
            if (x_min <= start_x <= x_max and y_min <= start_y <= y_max and
                x_min <= end_x <= x_max and y_min <= end_y <= y_max):
                in_bounds = True

        elif entity.dxftype() in ['TEXT', 'MTEXT']:
            if hasattr(entity.dxf, 'insert'):
                px, py = entity.dxf.insert[0], entity.dxf.insert[1]
                if x_min <= px <= x_max and y_min <= py <= y_max:
                    in_bounds = True

        elif entity.dxftype() == 'CIRCLE':
            if hasattr(entity.dxf, 'center'):
                px, py = entity.dxf.center[0], entity.dxf.center[1]
                if x_min <= px <= x_max and y_min <= py <= y_max:
                    in_bounds = True

        if in_bounds:
            silo_entities.append(entity)

    print(f"  Total entities: {len(silo_entities)}")

    # МАСШТАБУВАТИ цей силос
    scaled_count = 0

    for entity in silo_entities:
        if entity.dxftype() == 'LINE':
            x1, y1, z1 = entity.dxf.start
            x2, y2, z2 = entity.dxf.end

            # Середина лінії
            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            # Масштабувати позицію середини
            dx = mid_x - center_x
            dy = mid_y - center_y
            new_mid_x = center_x + dx * SCALE_FACTOR
            new_mid_y = center_y + dy * SCALE_FACTOR

            # Масштабувати вектор лінії
            vec_x = x2 - x1
            vec_y = y2 - y1
            new_vec_x = vec_x * SCALE_FACTOR
            new_vec_y = vec_y * SCALE_FACTOR

            # Нові точки
            new_x1 = new_mid_x - new_vec_x / 2
            new_y1 = new_mid_y - new_vec_y / 2
            new_x2 = new_mid_x + new_vec_x / 2
            new_y2 = new_mid_y + new_vec_y / 2

            entity.dxf.start = (new_x1, new_y1, z1)
            entity.dxf.end = (new_x2, new_y2, z2)
            scaled_count += 1

        elif entity.dxftype() in ['TEXT', 'MTEXT']:
            if hasattr(entity.dxf, 'insert'):
                x, y, z = entity.dxf.insert
                dx = x - center_x
                dy = y - center_y
                new_x = center_x + dx * SCALE_FACTOR
                new_y = center_y + dy * SCALE_FACTOR
                entity.dxf.insert = (new_x, new_y, z)

                if hasattr(entity.dxf, 'height'):
                    entity.dxf.height *= SCALE_FACTOR

                scaled_count += 1

        elif entity.dxftype() == 'CIRCLE':
            if hasattr(entity.dxf, 'center'):
                x, y, z = entity.dxf.center
                dx = x - center_x
                dy = y - center_y
                new_x = center_x + dx * SCALE_FACTOR
                new_y = center_y + dy * SCALE_FACTOR
                entity.dxf.center = (new_x, new_y, z)

                if hasattr(entity.dxf, 'radius'):
                    entity.dxf.radius *= SCALE_FACTOR

                scaled_count += 1

    print(f"  Scaled {scaled_count} entities")

# Зберегти
output_file = f"OUTPUT/page_01_2_SILOS_SCALED_v{int(time.time())}.dxf"
Path(output_file).parent.mkdir(parents=True, exist_ok=True)

print(f"\n{'='*80}")
print(f"Saving: {output_file}")
doc.saveas(output_file)

print(f"{'='*80}")
print("DONE!")
print(f"{'='*80}")
print(f"\nScaled 2 leftmost silos by {SCALE_FACTOR}x")
print(f"\nOpen in AutoCAD: {output_file}")
