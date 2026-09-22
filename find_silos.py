#!/usr/bin/env python
"""Знайти окремі силоси в оригінальному кресленні"""

import ezdxf
from collections import defaultdict

# Завантажити оригінал
doc = ezdxf.readfile(r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01_WITH_GRID.dxf")
msp = doc.modelspace()

# Знайти синій layer (силоси)
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']

print(f"Total blue lines (silos): {len(blue_lines)}")

# Збрати всі унікальні X координати
all_xs = set()
for line in blue_lines:
    all_xs.add(round(line.dxf.start[0], 1))
    all_xs.add(round(line.dxf.end[0], 1))

sorted_xs = sorted(list(all_xs))

print(f"\nUnique X coordinates: {len(sorted_xs)}")
print(f"X range: {sorted_xs[0]} to {sorted_xs[-1]}")

# Показати перші 30 координат
print(f"\nFirst 30 X coordinates:")
for x in sorted_xs[:30]:
    count = sum(1 for line in blue_lines if abs(line.dxf.start[0] - x) < 0.1 or abs(line.dxf.end[0] - x) < 0.1)
    print(f"  X={x:7.1f}: {count:3d} lines")

# Знайти кластери (групи близьких X координат)
print(f"\n\nClustering X coordinates (gap > 100m)...")
clusters = []
current_cluster = [sorted_xs[0]]

for x in sorted_xs[1:]:
    if x - current_cluster[-1] < 100:  # Якщо менше 100м різниці - той же силос
        current_cluster.append(x)
    else:
        # Новий силос
        clusters.append(current_cluster)
        current_cluster = [x]

clusters.append(current_cluster)

print(f"\nFound {len(clusters)} silos:")
for i, cluster in enumerate(clusters, 1):
    x_min = min(cluster)
    x_max = max(cluster)
    width = x_max - x_min
    center = (x_min + x_max) / 2

    # Порахувати скільки ліній у цьому силосі
    count = sum(1 for line in blue_lines if x_min - 1 <= line.dxf.start[0] <= x_max + 1 or x_min - 1 <= line.dxf.end[0] <= x_max + 1)

    print(f"  Silo #{i}: center={center:6.1f}m, width={width:5.1f}m, lines={count}")
