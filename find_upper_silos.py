#!/usr/bin/env python
"""Знайти ВЕРХНІ силоси"""

import ezdxf

doc = ezdxf.readfile(r"d:\autocad project\OUTPUT\page_01_WITH_8_SILOS_v1766707448.dxf")
msp = doc.modelspace()

# Знайти ВСІ сині лінії
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']

# Нижні (Y < 200)
lower_blue = [e for e in blue_lines if e.dxf.start[1] < 200 and e.dxf.end[1] < 200]

# Верхні (Y >= 200)
upper_blue = [e for e in blue_lines if e.dxf.start[1] >= 200 and e.dxf.end[1] >= 200]

print(f"Total blue lines: {len(blue_lines)}")
print(f"Lower blue lines (Y < 200): {len(lower_blue)}")
print(f"Upper blue lines (Y >= 200): {len(upper_blue)}")

# Розібрати ВЕРХНІ силоси
xs_upper = []
for line in upper_blue:
    xs_upper.extend([line.dxf.start[0], line.dxf.end[0]])

if xs_upper:
    print(f"\nUPPER silos X range: {min(xs_upper):.1f} to {max(xs_upper):.1f}")

    # Clustering
    xs_unique = sorted(set(xs_upper))
    silos_upper = []
    current_silo_xs = []

    for i, x in enumerate(xs_unique):
        if i == 0:
            current_silo_xs.append(x)
        else:
            if x - xs_unique[i-1] > 50:
                if current_silo_xs:
                    silos_upper.append((min(current_silo_xs), max(current_silo_xs)))
                current_silo_xs = [x]
            else:
                current_silo_xs.append(x)

    if current_silo_xs:
        silos_upper.append((min(current_silo_xs), max(current_silo_xs)))

    print(f"\nFound {len(silos_upper)} UPPER silos:")

    for i, (x_min, x_max) in enumerate(silos_upper):
        silo_lines = [e for e in upper_blue if x_min <= e.dxf.start[0] <= x_max and x_min <= e.dxf.end[0] <= x_max]

        ys = []
        for line in silo_lines:
            ys.extend([line.dxf.start[1], line.dxf.end[1]])

        y_min, y_max = min(ys), max(ys)
        width = x_max - x_min
        height = y_max - y_min
        center_x = (x_min + x_max) / 2
        center_y = (y_min + y_max) / 2

        print(f"\nUpper Silo {i+1}:")
        print(f"  X range: [{x_min:.1f}, {x_max:.1f}], width={width:.1f}mm")
        print(f"  Y range: [{y_min:.1f}, {y_max:.1f}], height={height:.1f}mm")
        print(f"  Center: ({center_x:.1f}, {center_y:.1f})")
        print(f"  Blue lines: {len(silo_lines)}")

# Аналогічно для НИЖНІХ
print(f"\n{'='*60}")
print("LOWER silos (detailed):")
print(f"{'='*60}")

xs_lower = []
for line in lower_blue:
    xs_lower.extend([line.dxf.start[0], line.dxf.end[0]])

xs_unique_lower = sorted(set(xs_lower))
silos_lower = []
current_silo_xs = []

for i, x in enumerate(xs_unique_lower):
    if i == 0:
        current_silo_xs.append(x)
    else:
        if x - xs_unique_lower[i-1] > 20:  # Ще менший gap
            if current_silo_xs:
                silos_lower.append((min(current_silo_xs), max(current_silo_xs)))
            current_silo_xs = [x]
        else:
            current_silo_xs.append(x)

if current_silo_xs:
    silos_lower.append((min(current_silo_xs), max(current_silo_xs)))

print(f"\nFound {len(silos_lower)} LOWER silos (gap=20mm):")

for i, (x_min, x_max) in enumerate(silos_lower):
    silo_lines = [e for e in lower_blue if x_min <= e.dxf.start[0] <= x_max and x_min <= e.dxf.end[0] <= x_max]

    ys = []
    for line in silo_lines:
        ys.extend([line.dxf.start[1], line.dxf.end[1]])

    y_min, y_max = min(ys), max(ys)
    width = x_max - x_min
    height = y_max - y_min
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2

    print(f"\nLower Silo {i+1}:")
    print(f"  X range: [{x_min:.1f}, {x_max:.1f}], width={width:.1f}mm")
    print(f"  Y range: [{y_min:.1f}, {y_max:.1f}], height={height:.1f}mm")
    print(f"  Center: ({center_x:.1f}, {center_y:.1f})")
    print(f"  Blue lines: {len(silo_lines)}")
