#!/usr/bin/env python
"""Проаналізувати оригінальне креслення page_01_WITH_GRID.dxf"""

import ezdxf
from pathlib import Path

# Завантажити оригінал
original_file = r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01_WITH_GRID.dxf"
doc = ezdxf.readfile(original_file)
msp = doc.modelspace()

# Знайти синій layer (силоси)
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']

print(f"Original file: {original_file}")
print(f"Total entities: {len(list(msp))}")
print(f"Blue lines (silos): {len(blue_lines)}")

if blue_lines:
    xs = [e.dxf.start[0] for e in blue_lines]
    ys = [e.dxf.start[1] for e in blue_lines]

    print(f"\nSilos location:")
    print(f"  X range: {min(xs):.1f} to {max(xs):.1f}")
    print(f"  Y range: {min(ys):.1f} to {max(ys):.1f}")

    # Групувати по X координатах (знайти окремі силоси)
    print(f"\nAnalyzing silo positions...")

    # Округлити X до найближчих 10000 (групування силосів)
    x_groups = {}
    for line in blue_lines:
        x = line.dxf.start[0]
        # Округлити до найближчих 50000 мм (приблизна ширина силосу)
        bucket = round(x / 50000) * 50000
        if bucket not in x_groups:
            x_groups[bucket] = []
        x_groups[bucket].append(line)

    print(f"\nFound {len(x_groups)} silo groups:")
    for bucket in sorted(x_groups.keys()):
        print(f"  Group at X~{bucket/1000:.0f}m: {len(x_groups[bucket])} lines")
