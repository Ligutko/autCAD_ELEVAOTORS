#!/usr/bin/env python
"""
ПРАВИЛЬНИЙ спосіб: кластеризувати лінії за їх центрами
"""

import ezdxf
from pathlib import Path
import time
from collections import defaultdict

SCALE_FACTOR = 1.25

input_file = r"d:\autocad project\OUTPUT\page_01_WITH_8_SILOS_v1766707448.dxf"
print(f"Loading: {input_file}")
doc = ezdxf.readfile(input_file)
msp = doc.modelspace()

# Знайти нижні сині лінії
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']
lower_blue = [e for e in blue_lines if e.dxf.start[1] < 200 and e.dxf.end[1] < 200]

print(f"Lower blue lines: {len(lower_blue)}")

# Для кожної лінії обчислити її центр
line_centers = []
for line in lower_blue:
    cx = (line.dxf.start[0] + line.dxf.end[0]) / 2
    cy = (line.dxf.start[1] + line.dxf.end[1]) / 2
    line_centers.append((cx, cy, line))

# Сортувати за X
line_centers.sort(key=lambda item: item[0])

# Простий clustering: якщо gap по X > 250mm то новий кластер
clusters = []
current_cluster = []

for i, (cx, cy, line) in enumerate(line_centers):
    if not current_cluster:
        current_cluster.append((cx, cy, line))
    else:
        prev_cx = current_cluster[-1][0]
        if cx - prev_cx > 40:  # Gap > 40mm - новий кластер
            clusters.append(current_cluster)
            current_cluster = [(cx, cy, line)]
        else:
            current_cluster.append((cx, cy, line))

if current_cluster:
    clusters.append(current_cluster)

print(f"\nFound {len(clusters)} clusters (silos)")

# Показати кластери
for i, cluster in enumerate(clusters):
    xs = [item[0] for item in cluster]
    ys = [item[1] for item in cluster]
    print(f"  Cluster {i+1}: {len(cluster)} lines, X=[{min(xs):.1f}, {max(xs):.1f}], Y=[{min(ys):.1f}, {max(ys):.1f}]")

# Взяти 2 ПЕРШІ кластери (найлівіші)
if len(clusters) < 2:
    print("\nERROR: Found less than 2 silos!")
    exit(1)

selected_clusters = clusters[:2]

print(f"\nSelecting 2 leftmost silos for scaling...")

# Масштабувати кожен кластер
for cluster_idx, cluster in enumerate(selected_clusters):
    print(f"\n{'='*60}")
    print(f"Silo {cluster_idx+1}:")
    print(f"{'='*60}")

    # Витягнути лінії
    silo_lines = [item[2] for item in cluster]

    # Bounds
    xs = []
    ys = []
    for line in silo_lines:
        xs.extend([line.dxf.start[0], line.dxf.end[0]])
        ys.extend([line.dxf.start[1], line.dxf.end[1]])

    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2

    print(f"  Blue lines: {len(silo_lines)}")
    print(f"  Bounds: X=[{x_min:.1f}, {x_max:.1f}], Y=[{y_min:.1f}, {y_max:.1f}]")
    print(f"  Center: ({center_x:.1f}, {center_y:.1f})")

    # Знайти ВСІ entities в bounds
    silo_entities = []

    for entity in msp:
        if hasattr(entity.dxf, 'layer') and entity.dxf.layer == 'GRID':
            continue

        in_bounds = False

        if entity.dxftype() == 'LINE':
            sx, sy = entity.dxf.start[0], entity.dxf.start[1]
            ex, ey = entity.dxf.end[0], entity.dxf.end[1]

            if (x_min <= sx <= x_max and y_min <= sy <= y_max and
                x_min <= ex <= x_max and y_min <= ey <= y_max):
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

    # Масштабувати
    scaled = 0

    for entity in silo_entities:
        if entity.dxftype() == 'LINE':
            x1, y1, z1 = entity.dxf.start
            x2, y2, z2 = entity.dxf.end

            mid_x = (x1 + x2) / 2
            mid_y = (y1 + y2) / 2

            dx = mid_x - center_x
            dy = mid_y - center_y
            new_mid_x = center_x + dx * SCALE_FACTOR
            new_mid_y = center_y + dy * SCALE_FACTOR

            vec_x = x2 - x1
            vec_y = y2 - y1
            new_vec_x = vec_x * SCALE_FACTOR
            new_vec_y = vec_y * SCALE_FACTOR

            new_x1 = new_mid_x - new_vec_x / 2
            new_y1 = new_mid_y - new_vec_y / 2
            new_x2 = new_mid_x + new_vec_x / 2
            new_y2 = new_mid_y + new_vec_y / 2

            entity.dxf.start = (new_x1, new_y1, z1)
            entity.dxf.end = (new_x2, new_y2, z2)
            scaled += 1

        elif entity.dxftype() in ['TEXT', 'MTEXT']:
            if hasattr(entity.dxf, 'insert'):
                x, y, z = entity.dxf.insert
                dx = x - center_x
                dy = y - center_y
                entity.dxf.insert = (center_x + dx * SCALE_FACTOR, center_y + dy * SCALE_FACTOR, z)

                if hasattr(entity.dxf, 'height'):
                    entity.dxf.height *= SCALE_FACTOR
                scaled += 1

        elif entity.dxftype() == 'CIRCLE':
            if hasattr(entity.dxf, 'center'):
                x, y, z = entity.dxf.center
                dx = x - center_x
                dy = y - center_y
                entity.dxf.center = (center_x + dx * SCALE_FACTOR, center_y + dy * SCALE_FACTOR, z)

                if hasattr(entity.dxf, 'radius'):
                    entity.dxf.radius *= SCALE_FACTOR
                scaled += 1

    print(f"  Scaled {scaled} entities")

output_file = f"OUTPUT/page_01_2_SILOS_SCALED_CORRECT_v{int(time.time())}.dxf"
Path(output_file).parent.mkdir(parents=True, exist_ok=True)

print(f"\n{'='*80}")
print(f"Saving: {output_file}")
doc.saveas(output_file)

print(f"{'='*80}")
print("SUCCESS!")
print(f"{'='*80}")
print(f"\nScaled 2 leftmost silos by {SCALE_FACTOR}x")
print(f"\nOpen: {output_file}")
