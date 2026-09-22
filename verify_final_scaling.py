#!/usr/bin/env python
"""Перевірити фінальне масштабування 2 нижніх силосів"""

import ezdxf

# Завантажити ОРИГІНАЛ
print("Loading ORIGINAL (8 silos)...")
orig = ezdxf.readfile(r"d:\autocad project\OUTPUT\page_01_WITH_8_SILOS_v1766707448.dxf")
msp_orig = orig.modelspace()

# Завантажити МАСШТАБОВАНИЙ
print("Loading SCALED (2 lower silos scaled)...")
scaled = ezdxf.readfile(r"d:\autocad project\OUTPUT\page_01_WITH_8_SILOS_SCALED_v1766710927.dxf")
msp_scaled = scaled.modelspace()

# Знайти нижні сині лінії в ОРИГІНАЛІ
blue_orig = [
    e for e in msp_orig
    if e.dxftype() == 'LINE'
    and hasattr(e.dxf, 'layer')
    and e.dxf.layer == 'RGB_000_000_255'
    and e.dxf.start[1] < 200
]

# Розділити на ЛІВИЙ та ПРАВИЙ
xs_all = []
for line in blue_orig:
    xs_all.extend([line.dxf.start[0], line.dxf.end[0]])

mid_x = (min(xs_all) + max(xs_all)) / 2

left_orig = [e for e in blue_orig if e.dxf.start[0] < mid_x and e.dxf.end[0] < mid_x]

print(f"\nORIGINAL LEFT silo: {len(left_orig)} blue lines")

if left_orig:
    # Перевірити перші 3 лінії
    sample_orig = []
    for i, line in enumerate(left_orig[:3]):
        vec_x = line.dxf.end[0] - line.dxf.start[0]
        vec_y = line.dxf.end[1] - line.dxf.start[1]
        length = (vec_x**2 + vec_y**2)**0.5
        sample_orig.append((line.dxf.start, line.dxf.end, length))
        print(f"  Line {i}: start=({line.dxf.start[0]:.2f}, {line.dxf.start[1]:.2f}), length={length:.2f}")

# Знайти нижні сині лінії в МАСШТАБОВАНОМУ
blue_scaled = [
    e for e in msp_scaled
    if e.dxftype() == 'LINE'
    and hasattr(e.dxf, 'layer')
    and e.dxf.layer == 'RGB_000_000_255'
    and e.dxf.start[1] < 300  # Більший діапазон бо масштабовані
]

# Розділити
xs_all_scaled = []
for line in blue_scaled:
    xs_all_scaled.extend([line.dxf.start[0], line.dxf.end[0]])

mid_x_scaled = (min(xs_all_scaled) + max(xs_all_scaled)) / 2

left_scaled = [e for e in blue_scaled if e.dxf.start[0] < mid_x_scaled and e.dxf.end[0] < mid_x_scaled]

print(f"\nSCALED LEFT silo: {len(left_scaled)} blue lines")

if left_scaled:
    # Перевірити перші 3 лінії
    sample_scaled = []
    for i, line in enumerate(left_scaled[:3]):
        vec_x = line.dxf.end[0] - line.dxf.start[0]
        vec_y = line.dxf.end[1] - line.dxf.start[1]
        length = (vec_x**2 + vec_y**2)**0.5
        sample_scaled.append((line.dxf.start, line.dxf.end, length))
        print(f"  Line {i}: start=({line.dxf.start[0]:.2f}, {line.dxf.start[1]:.2f}), length={length:.2f}")

# ПОРІВНЯННЯ
if sample_orig and sample_scaled:
    print(f"\n{'='*60}")
    print("COMPARISON:")
    print(f"{'='*60}")

    for i in range(min(3, len(sample_orig), len(sample_scaled))):
        _, _, orig_len = sample_orig[i]
        _, _, scaled_len = sample_scaled[i]

        ratio = scaled_len / orig_len if orig_len > 0 else 0

        print(f"\nLine {i}:")
        print(f"  Original length: {orig_len:.2f}mm")
        print(f"  Scaled length: {scaled_len:.2f}mm")
        print(f"  Ratio: {ratio:.3f} (expected 1.250)")

        if abs(ratio - 1.25) < 0.01:
            print(f"  Result: OK!")
        else:
            print(f"  Result: FAILED!")

# Загальна перевірка bounds
xs_left_orig = []
ys_left_orig = []
for line in left_orig:
    xs_left_orig.extend([line.dxf.start[0], line.dxf.end[0]])
    ys_left_orig.extend([line.dxf.start[1], line.dxf.end[1]])

width_orig = max(xs_left_orig) - min(xs_left_orig)
height_orig = max(ys_left_orig) - min(ys_left_orig)

xs_left_scaled = []
ys_left_scaled = []
for line in left_scaled:
    xs_left_scaled.extend([line.dxf.start[0], line.dxf.end[0]])
    ys_left_scaled.extend([line.dxf.start[1], line.dxf.end[1]])

width_scaled = max(xs_left_scaled) - min(xs_left_scaled)
height_scaled = max(ys_left_scaled) - min(ys_left_scaled)

print(f"\n{'='*60}")
print("OVERALL BOUNDS:")
print(f"{'='*60}")
print(f"Original width: {width_orig:.2f}mm, height: {height_orig:.2f}mm")
print(f"Scaled width: {width_scaled:.2f}mm, height: {height_scaled:.2f}mm")
print(f"Width ratio: {width_scaled/width_orig:.3f}")
print(f"Height ratio: {height_scaled/height_orig:.3f}")

if abs(width_scaled/width_orig - 1.25) < 0.05 and abs(height_scaled/height_orig - 1.25) < 0.05:
    print(f"\n*** SUCCESS! SCALING WORKED! ***")
else:
    print(f"\n*** FAILED! ***")
