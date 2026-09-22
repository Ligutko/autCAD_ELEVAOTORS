#!/usr/bin/env python
"""Перевірити НОВИЙ scaled файл"""

import ezdxf

# Завантажити ОРИГІНАЛ
print("Loading ORIGINAL...")
orig = ezdxf.readfile(r"d:\autocad project\page_01_WITH_GRID_AND_SILO_7.dxf")
msp_orig = orig.modelspace()

# Завантажити НОВИЙ МАСШТАБОВАНИЙ
print("Loading NEW SCALED...")
scaled = ezdxf.readfile(r"d:\autocad project\OUTPUT\page_01_BIGGER_SILO_v1766710733.dxf")
msp_scaled = scaled.modelspace()

# Знайти ЛІВИЙ нижній силос в ОРИГІНАЛІ
blue_orig = [
    e for e in msp_orig
    if e.dxftype() == 'LINE'
    and hasattr(e.dxf, 'layer')
    and e.dxf.layer == 'RGB_000_000_255'
    and e.dxf.start[1] < 200
    and e.dxf.start[0] < -300
]

print(f"\nORIGINAL LEFT silo: {len(blue_orig)} blue lines")

orig_line = blue_orig[0]
orig_vec_x = orig_line.dxf.end[0] - orig_line.dxf.start[0]
orig_vec_y = orig_line.dxf.end[1] - orig_line.dxf.start[1]
orig_len = (orig_vec_x**2 + orig_vec_y**2)**0.5

print(f"  Sample line:")
print(f"    start=({orig_line.dxf.start[0]:.2f}, {orig_line.dxf.start[1]:.2f})")
print(f"    end=({orig_line.dxf.end[0]:.2f}, {orig_line.dxf.end[1]:.2f})")
print(f"    vector=({orig_vec_x:.2f}, {orig_vec_y:.2f})")
print(f"    length={orig_len:.2f}")

# Знайти ЛІВИЙ нижній силос в НОВОМУ
blue_scaled = [
    e for e in msp_scaled
    if e.dxftype() == 'LINE'
    and hasattr(e.dxf, 'layer')
    and e.dxf.layer == 'RGB_000_000_255'
    and e.dxf.start[1] < 300  # Більший діапазон
    and e.dxf.start[0] < -200
]

print(f"\nNEW SCALED LEFT silo: {len(blue_scaled)} blue lines")

if len(blue_scaled) > 0:
    scaled_line = blue_scaled[0]
    scaled_vec_x = scaled_line.dxf.end[0] - scaled_line.dxf.start[0]
    scaled_vec_y = scaled_line.dxf.end[1] - scaled_line.dxf.start[1]
    scaled_len = (scaled_vec_x**2 + scaled_vec_y**2)**0.5

    print(f"  Sample line:")
    print(f"    start=({scaled_line.dxf.start[0]:.2f}, {scaled_line.dxf.start[1]:.2f})")
    print(f"    end=({scaled_line.dxf.end[0]:.2f}, {scaled_line.dxf.end[1]:.2f})")
    print(f"    vector=({scaled_vec_x:.2f}, {scaled_vec_y:.2f})")
    print(f"    length={scaled_len:.2f}")

    print(f"\n{'='*60}")
    print("COMPARISON:")
    print(f"{'='*60}")
    print(f"Vector X ratio: {scaled_vec_x/orig_vec_x if orig_vec_x != 0 else 'N/A':.3f} (expected 1.250)")
    print(f"Vector Y ratio: {scaled_vec_y/orig_vec_y if orig_vec_y != 0 else 'N/A':.3f} (expected 1.250)")
    print(f"Length ratio: {scaled_len/orig_len:.3f} (expected 1.250)")

    if abs(scaled_len/orig_len - 1.25) < 0.01:
        print("\nSUCCESS! Scaling worked!")
    else:
        print("\nFAILED! Scaling did not work!")
