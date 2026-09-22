#!/usr/bin/env python
"""Перевірити як розташовані силоси - по X чи по Y"""

import ezdxf

doc = ezdxf.readfile(r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01_WITH_GRID.dxf")
msp = doc.modelspace()

blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']

print(f"Total blue lines: {len(blue_lines)}")

# Порівняти розкид по X та по Y
xs = [line.dxf.start[0] for line in blue_lines]
ys = [line.dxf.start[1] for line in blue_lines]

x_range = max(xs) - min(xs)
y_range = max(ys) - min(ys)

print(f"\nX range: {min(xs):.1f} to {max(xs):.1f} (span = {x_range:.1f}m)")
print(f"Y range: {min(ys):.1f} to {max(ys):.1f} (span = {y_range:.1f}m)")

# Спробувати знайти окремі силоси по ОБОХ координатах
# Використаємо метод: знайдемо всі "центри мас" ліній

from collections import defaultdict

# Групування по Y (вертикальні рівні)
y_tolerance = 10  # 10м толеранс
y_groups = defaultdict(list)

for line in blue_lines:
    y = line.dxf.start[1]
    # Знайти найближчу групу
    found = False
    for group_y in y_groups.keys():
        if abs(y - group_y) < y_tolerance:
            y_groups[group_y].append(line)
            found = True
            break
    if not found:
        y_groups[y].append(line)

print(f"\n\nY groups (levels) found: {len(y_groups)}")
sorted_y = sorted(y_groups.keys())
for i, y in enumerate(sorted_y[:10], 1):  # Показати перші 10
    print(f"  Level #{i}: Y={y:6.1f}m, {len(y_groups[y])} lines")

# ВАЖЛИВО: Можливо це SIDE VIEW (вид збоку)?
# Тоді силоси стоять ОДИН ЗА ОДНИМ по Y, а не поруч по X

print(f"\n\nChecking if this is SIDE VIEW...")
print(f"If Y range ({y_range:.1f}m) >> X range ({x_range:.1f}m) => SIDE VIEW (silos stacked vertically)")
print(f"If X range ({x_range:.1f}m) >> Y range ({y_range:.1f}m) => TOP VIEW (silos side by side)")

if y_range > x_range:
    print(f"\n=> This looks like SIDE VIEW (силоси нарисовані один над одним)")
else:
    print(f"\n=> This looks like TOP VIEW (силоси нарисовані поруч)")
