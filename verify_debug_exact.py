#!/usr/bin/env python
"""Знайти ТОЧНО ті самі лінії що в DEBUG"""

import ezdxf

doc = ezdxf.readfile(r"d:\autocad project\OUTPUT\page_01_DEBUG_v1766710809.dxf")
msp = doc.modelspace()

# Шукати ТОЧНІ координати з DEBUG
target_lines = [
    ((-124.97, 90.36), (-124.97, 80.91)),  # Line 0
    ((-109.82, 80.91), (-112.07, 76.71)),  # Line 1
    ((-112.07, 76.71), (-123.02, 76.71)),  # Line 2
]

print("Searching for exact lines from DEBUG output...")

for i, (target_start, target_end) in enumerate(target_lines):
    print(f"\nLooking for Line {i}: start={target_start}, end={target_end}")

    found = False
    for entity in msp:
        if entity.dxftype() == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end

            # Перевірити чи це та сама лінія (з точністю 0.1)
            if (abs(start[0] - target_start[0]) < 0.1 and abs(start[1] - target_start[1]) < 0.1 and
                abs(end[0] - target_end[0]) < 0.1 and abs(end[1] - target_end[1]) < 0.1):

                vec_x = end[0] - start[0]
                vec_y = end[1] - start[1]
                length = (vec_x**2 + vec_y**2)**0.5

                print(f"  FOUND!")
                print(f"    Actual: start=({start[0]:.2f}, {start[1]:.2f}), end=({end[0]:.2f}, {end[1]:.2f})")
                print(f"    vector=({vec_x:.2f}, {vec_y:.2f}), length={length:.2f}")
                found = True
                break

    if not found:
        print(f"  NOT FOUND!")

# Тепер перевіримо ОРИГІНАЛЬНІ координати
print(f"\n{'='*60}")
print("COMPARISON WITH ORIGINAL:")
print(f"{'='*60}")

orig = ezdxf.readfile(r"d:\autocad project\page_01_WITH_GRID_AND_SILO_7.dxf")
msp_orig = orig.modelspace()

orig_targets = [
    ((-168.56, 93.60), (-168.56, 86.04)),  # Original Line 0
    ((-156.44, 86.04), (-158.24, 82.68)),  # Original Line 1
    ((-158.24, 82.68), (-167.00, 82.68)),  # Original Line 2
]

for i, (target_start, target_end) in enumerate(orig_targets):
    print(f"\nOriginal Line {i}:")

    for entity in msp_orig:
        if entity.dxftype() == 'LINE':
            start = entity.dxf.start
            end = entity.dxf.end

            if (abs(start[0] - target_start[0]) < 0.1 and abs(start[1] - target_start[1]) < 0.1 and
                abs(end[0] - target_end[0]) < 0.1 and abs(end[1] - target_end[1]) < 0.1):

                vec_x = end[0] - start[0]
                vec_y = end[1] - start[1]
                length = (vec_x**2 + vec_y**2)**0.5

                print(f"  start=({start[0]:.2f}, {start[1]:.2f}), end=({end[0]:.2f}, {end[1]:.2f}), length={length:.2f}")
                break
