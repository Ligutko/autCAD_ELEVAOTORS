#!/usr/bin/env python
"""Debug - перевірити координати ліній ДО та ПІСЛЯ"""

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

print(f"\nORIGINAL: First 5 lines:")
for i, line in enumerate(blue_orig[:5]):
    start = line.dxf.start
    end = line.dxf.end
    length = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
    print(f"  Line {i}: start=({start[0]:.2f}, {start[1]:.2f}), end=({end[0]:.2f}, {end[1]:.2f}), length={length:.2f}")

# Знайти ЛІВИЙ нижній силос в МАСШТАБОВАНОМУ
blue_scaled = [
    e for e in msp_scaled
    if e.dxftype() == 'LINE'
    and hasattr(e.dxf, 'layer')
    and e.dxf.layer == 'RGB_000_000_255'
    and e.dxf.start[1] < 250  # Трохи більший діапазон
    and e.dxf.start[0] < -200  # Трохи більший діапазон
]

print(f"\nSCALED: First 5 lines:")
for i, line in enumerate(blue_scaled[:5]):
    start = line.dxf.start
    end = line.dxf.end
    length = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
    print(f"  Line {i}: start=({start[0]:.2f}, {start[1]:.2f}), end=({end[0]:.2f}, {end[1]:.2f}), length={length:.2f}")

# Порівняти РІЗНИЦЮ в векторах
if len(blue_orig) > 0 and len(blue_scaled) > 0:
    orig_line = blue_orig[0]
    scaled_line = blue_scaled[0]

    orig_vec_x = orig_line.dxf.end[0] - orig_line.dxf.start[0]
    orig_vec_y = orig_line.dxf.end[1] - orig_line.dxf.start[1]
    orig_len = (orig_vec_x**2 + orig_vec_y**2)**0.5

    scaled_vec_x = scaled_line.dxf.end[0] - scaled_line.dxf.start[0]
    scaled_vec_y = scaled_line.dxf.end[1] - scaled_line.dxf.start[1]
    scaled_len = (scaled_vec_x**2 + scaled_vec_y**2)**0.5

    print(f"\nCOMPARISON of first line:")
    print(f"  ORIG vector: ({orig_vec_x:.2f}, {orig_vec_y:.2f}), length={orig_len:.2f}")
    print(f"  SCALED vector: ({scaled_vec_x:.2f}, {scaled_vec_y:.2f}), length={scaled_len:.2f}")
    print(f"  Vector X ratio: {scaled_vec_x/orig_vec_x if orig_vec_x != 0 else 'N/A'}")
    print(f"  Vector Y ratio: {scaled_vec_y/orig_vec_y if orig_vec_y != 0 else 'N/A'}")
    print(f"  Length ratio: {scaled_len/orig_len:.3f}")
