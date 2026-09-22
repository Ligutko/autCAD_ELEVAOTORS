#!/usr/bin/env python
"""Перевірити чи масштабування справді спрацювало"""

import ezdxf

# Завантажити ОРИГІНАЛ
print("Loading ORIGINAL...")
orig = ezdxf.readfile(r"d:\autocad project\page_01_WITH_GRID_AND_SILO_7.dxf")
msp_orig = orig.modelspace()

# Завантажити МАСШТАБОВАНИЙ
print("Loading SCALED...")
scaled = ezdxf.readfile(r"d:\autocad project\OUTPUT\page_01_BIGGER_SILO_v1766708510.dxf")
msp_scaled = scaled.modelspace()

# Знайти ЛІВИЙ нижній силос в ОРИГІНАЛІ
blue_orig = [
    e for e in msp_orig
    if e.dxftype() == 'LINE'
    and hasattr(e.dxf, 'layer')
    and e.dxf.layer == 'RGB_000_000_255'
    and e.dxf.start[1] < 200  # Нижні
    and e.dxf.start[0] < -300  # Лівий
]

print(f"\nORIGINAL LEFT silo: {len(blue_orig)} blue lines")

if blue_orig:
    xs_orig = []
    ys_orig = []
    for line in blue_orig:
        xs_orig.extend([line.dxf.start[0], line.dxf.end[0]])
        ys_orig.extend([line.dxf.start[1], line.dxf.end[1]])

    width_orig = max(xs_orig) - min(xs_orig)
    height_orig = max(ys_orig) - min(ys_orig)

    print(f"  Width: {width_orig:.2f}mm")
    print(f"  Height: {height_orig:.2f}mm")

    # Перевірити одну лінію
    sample = blue_orig[0]
    length_orig = ((sample.dxf.end[0] - sample.dxf.start[0])**2 +
                   (sample.dxf.end[1] - sample.dxf.start[1])**2)**0.5
    print(f"  Sample line length: {length_orig:.2f}mm")

# Знайти ЛІВИЙ нижній силос в МАСШТАБОВАНОМУ
blue_scaled = [
    e for e in msp_scaled
    if e.dxftype() == 'LINE'
    and hasattr(e.dxf, 'layer')
    and e.dxf.layer == 'RGB_000_000_255'
    and e.dxf.start[1] < 250  # Трохи більший діапазон бо він збільшився
    and e.dxf.start[0] < -200  # Трохи більший діапазон
]

print(f"\nSCALED LEFT silo: {len(blue_scaled)} blue lines")

if blue_scaled:
    xs_scaled = []
    ys_scaled = []
    for line in blue_scaled:
        xs_scaled.extend([line.dxf.start[0], line.dxf.end[0]])
        ys_scaled.extend([line.dxf.start[1], line.dxf.end[1]])

    width_scaled = max(xs_scaled) - min(xs_scaled)
    height_scaled = max(ys_scaled) - min(ys_scaled)

    print(f"  Width: {width_scaled:.2f}mm")
    print(f"  Height: {height_scaled:.2f}mm")

    # Перевірити одну лінію
    sample = blue_scaled[0]
    length_scaled = ((sample.dxf.end[0] - sample.dxf.start[0])**2 +
                     (sample.dxf.end[1] - sample.dxf.start[1])**2)**0.5
    print(f"  Sample line length: {length_scaled:.2f}mm")

if blue_orig and blue_scaled:
    print(f"\n{'='*60}")
    print("COMPARISON:")
    print(f"{'='*60}")
    print(f"Width ratio: {width_scaled/width_orig:.3f} (expected 1.250)")
    print(f"Height ratio: {height_scaled/height_orig:.3f} (expected 1.250)")
    print(f"Line length ratio: {length_scaled/length_orig:.3f} (expected 1.250)")

    if abs(width_scaled/width_orig - 1.25) < 0.01:
        print("\n✓ МАСШТАБУВАННЯ ПРАЦЮЄ!")
    else:
        print("\n✗ МАСШТАБУВАННЯ НЕ ПРАЦЮЄ!")
