#!/usr/bin/env python
"""Проаналізувати розподіл X координат центрів ліній"""

import ezdxf

doc = ezdxf.readfile(r"d:\autocad project\OUTPUT\page_01_WITH_8_SILOS_v1766707448.dxf")
msp = doc.modelspace()

blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']
lower_blue = [e for e in blue_lines if e.dxf.start[1] < 200]

# Обчислити центри
centers_x = []
for line in lower_blue:
    cx = (line.dxf.start[0] + line.dxf.end[0]) / 2
    centers_x.append(cx)

centers_x_sorted = sorted(centers_x)

print(f"Total lower lines: {len(centers_x)}")
print(f"X range: {min(centers_x):.1f} to {max(centers_x):.1f}")

# Показати розподіл: перші 20 і останні 20
print(f"\nFirst 20 X centers:")
for i, x in enumerate(centers_x_sorted[:20]):
    print(f"  {i+1}: {x:.2f}")

print(f"\nLast 20 X centers:")
for i, x in enumerate(centers_x_sorted[-20:]):
    print(f"  {len(centers_x)-19+i}: {x:.2f}")

# Знайти GAPS
print(f"\nLargest gaps:")
gaps = []
for i in range(1, len(centers_x_sorted)):
    gap = centers_x_sorted[i] - centers_x_sorted[i-1]
    gaps.append((gap, i, centers_x_sorted[i-1], centers_x_sorted[i]))

gaps.sort(reverse=True)

for i, (gap, idx, x_before, x_after) in enumerate(gaps[:10]):
    print(f"  Gap {i+1}: {gap:.2f}mm at index {idx}, X: {x_before:.1f} -> {x_after:.1f}")
