#!/usr/bin/env python
"""Знайти ВСІ нижні силоси в файлі з 8 силосами"""

import ezdxf

doc = ezdxf.readfile(r"d:\autocad project\OUTPUT\page_01_WITH_8_SILOS_v1766707448.dxf")
msp = doc.modelspace()

# Знайти ВСІ нижні сині лінії (Y < 200)
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']
lower_blue = [e for e in blue_lines if e.dxf.start[1] < 200 and e.dxf.end[1] < 200]

print(f"Total blue lines: {len(blue_lines)}")
print(f"Lower blue lines (Y < 200): {len(lower_blue)}")

# Знайти унікальні "кластери" силосів по X координатах
xs_all = []
for line in lower_blue:
    xs_all.append(line.dxf.start[0])
    xs_all.append(line.dxf.end[0])

xs_all = sorted(set(xs_all))

print(f"\nX coordinates range: {min(xs_all):.1f} to {max(xs_all):.1f}")

# Спробувати знайти окремі силоси (gap > 100mm означає новий силос)
silos = []
current_silo_xs = []

for i, x in enumerate(xs_all):
    if i == 0:
        current_silo_xs.append(x)
    else:
        if x - xs_all[i-1] > 50:  # Gap > 50mm
            # Новий силос
            if current_silo_xs:
                silos.append((min(current_silo_xs), max(current_silo_xs)))
            current_silo_xs = [x]
        else:
            current_silo_xs.append(x)

# Додати останній силос
if current_silo_xs:
    silos.append((min(current_silo_xs), max(current_silo_xs)))

print(f"\nFound {len(silos)} silos:")

for i, (x_min, x_max) in enumerate(silos):
    # Знайти лінії для цього силоса
    silo_lines = [e for e in lower_blue if x_min <= e.dxf.start[0] <= x_max and x_min <= e.dxf.end[0] <= x_max]

    # Bounds
    ys = []
    for line in silo_lines:
        ys.extend([line.dxf.start[1], line.dxf.end[1]])

    y_min, y_max = min(ys), max(ys)
    width = x_max - x_min
    height = y_max - y_min
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2

    print(f"\nSilo {i+1}:")
    print(f"  X range: [{x_min:.1f}, {x_max:.1f}], width={width:.1f}mm")
    print(f"  Y range: [{y_min:.1f}, {y_max:.1f}], height={height:.1f}mm")
    print(f"  Center: ({center_x:.1f}, {center_y:.1f})")
    print(f"  Blue lines: {len(silo_lines)}")
