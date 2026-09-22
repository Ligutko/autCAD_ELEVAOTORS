#!/usr/bin/env python
"""Перевірити що НАСПРАВДІ збережено в DEBUG файлі"""

import ezdxf

# Завантажити DEBUG файл
print("Loading DEBUG file...")
doc = ezdxf.readfile(r"d:\autocad project\OUTPUT\page_01_DEBUG_v1766710809.dxf")
msp = doc.modelspace()

# Знайти перші 3 лінії LEFT силоса (bounds приблизно)
# З DEBUG виводу знаю що перша лінія має бути в районі X=-125, Y=85

lines_found = []

for entity in msp:
    if entity.dxftype() == 'LINE':
        start = entity.dxf.start
        end = entity.dxf.end

        # Знайти лінії поблизу X=-125
        if -130 < start[0] < -120 and 80 < start[1] < 95:
            lines_found.append(entity)

        if len(lines_found) >= 5:
            break

print(f"Found {len(lines_found)} lines near expected position")

for i, line in enumerate(lines_found[:3]):
    start = line.dxf.start
    end = line.dxf.end
    vec_x = end[0] - start[0]
    vec_y = end[1] - start[1]
    length = (vec_x**2 + vec_y**2)**0.5

    print(f"\nLine {i}:")
    print(f"  start=({start[0]:.2f}, {start[1]:.2f})")
    print(f"  end=({end[0]:.2f}, {end[1]:.2f})")
    print(f"  vector=({vec_x:.2f}, {vec_y:.2f})")
    print(f"  length={length:.2f}")

# Порівняти з очікуваннями з DEBUG виводу
print(f"\n{'='*60}")
print("EXPECTED from DEBUG output:")
print(f"{'='*60}")
print("Line 0: start=(-124.97, 90.36), end=(-124.97, 80.91), vector=(0.00, -9.45), length=9.45")
print("Line 1: start=(-109.82, 80.91), end=(-112.07, 76.71), vector=(-2.25, -4.20), length=4.76")
print("Line 2: start=(-112.07, 76.71), end=(-123.02, 76.71), vector=(-10.95, 0.00), length=10.95")
