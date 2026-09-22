#!/usr/bin/env python
"""
HYBRID підхід: ezdxf знаходить bounds, COM API масштабує
"""

import ezdxf
import win32com.client

# КРОК 1: Швидко знайти bounds через ezdxf
print("STEP 1: Finding silo bounds with ezdxf...")

input_file = r"d:\autocad project\OUTPUT\page_01_WITH_8_SILOS_v1766707448.dxf"
doc = ezdxf.readfile(input_file)
msp = doc.modelspace()

# Знайти нижні сині лінії
blue_lines = [e for e in msp if e.dxftype() == 'LINE' and hasattr(e.dxf, 'layer') and e.dxf.layer == 'RGB_000_000_255']
lower_blue = [e for e in blue_lines if e.dxf.start[1] < 200 and e.dxf.end[1] < 200]

print(f"Found {len(lower_blue)} lower blue lines")

# Розділити на 2 силоси
xs_all = []
for line in lower_blue:
    xs_all.extend([line.dxf.start[0], line.dxf.end[0]])

mid_x = (min(xs_all) + max(xs_all)) / 2

left_blue = [e for e in lower_blue if e.dxf.start[0] < mid_x and e.dxf.end[0] < mid_x]
right_blue = [e for e in lower_blue if e.dxf.start[0] > mid_x and e.dxf.end[0] > mid_x]

# Bounds для ЛІВОГО
xs_left = []
ys_left = []
for line in left_blue:
    xs_left.extend([line.dxf.start[0], line.dxf.end[0]])
    ys_left.extend([line.dxf.start[1], line.dxf.end[1]])

left_x_min, left_x_max = min(xs_left), max(xs_left)
left_y_min, left_y_max = min(ys_left), max(ys_left)
left_center_x = (left_x_min + left_x_max) / 2
left_center_y = (left_y_min + left_y_max) / 2

# Bounds для ПРАВОГО
xs_right = []
ys_right = []
for line in right_blue:
    xs_right.extend([line.dxf.start[0], line.dxf.end[0]])
    ys_right.extend([line.dxf.start[1], line.dxf.end[1]])

right_x_min, right_x_max = min(xs_right), max(xs_right)
right_y_min, right_y_max = min(ys_right), max(ys_right)
right_center_x = (right_x_min + right_x_max) / 2
right_center_y = (right_y_min + right_y_max) / 2

print(f"\nLEFT silo:")
print(f"  Bounds: X=[{left_x_min:.1f}, {left_x_max:.1f}], Y=[{left_y_min:.1f}, {left_y_max:.1f}]")
print(f"  Center: ({left_center_x:.1f}, {left_center_y:.1f})")
print(f"  Blue lines: {len(left_blue)}")

print(f"\nRIGHT silo:")
print(f"  Bounds: X=[{right_x_min:.1f}, {right_x_max:.1f}], Y=[{right_y_min:.1f}, {right_y_max:.1f}]")
print(f"  Center: ({right_center_x:.1f}, {right_center_y:.1f})")
print(f"  Blue lines: {len(right_blue)}")

# КРОК 2: Масштабувати через COM API
print("\nSTEP 2: Scaling through AutoCAD COM API...")

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    acad.Visible = True

    doc_acad = acad.ActiveDocument
    print(f"Active document: {doc_acad.Name}")

    msp_acad = doc_acad.ModelSpace

    SCALE_FACTOR = 1.25

    # Масштабувати ЛІВИЙ силос
    print(f"\nScaling LEFT silo by {SCALE_FACTOR}x...")
    left_base = [left_center_x, left_center_y, 0]
    scaled_left = 0

    for entity in msp_acad:
        try:
            # Перевірити чи це лінія в bounds ЛІВОГО силоса
            if entity.EntityName == "AcDbLine":
                if hasattr(entity, 'Layer') and entity.Layer == 'RGB_000_000_255':
                    start = entity.StartPoint
                    end = entity.EndPoint

                    # Перевірити чи в bounds
                    if (left_x_min <= start[0] <= left_x_max and left_y_min <= start[1] <= left_y_max and
                        left_x_min <= end[0] <= left_x_max and left_y_min <= end[1] <= left_y_max):
                        entity.ScaleEntity(left_base, SCALE_FACTOR)
                        scaled_left += 1
        except:
            pass

    print(f"Scaled {scaled_left} lines in LEFT silo")

    # Масштабувати ПРАВИЙ силос
    print(f"\nScaling RIGHT silo by {SCALE_FACTOR}x...")
    right_base = [right_center_x, right_center_y, 0]
    scaled_right = 0

    for entity in msp_acad:
        try:
            if entity.EntityName == "AcDbLine":
                if hasattr(entity, 'Layer') and entity.Layer == 'RGB_000_000_255':
                    start = entity.StartPoint
                    end = entity.EndPoint

                    if (right_x_min <= start[0] <= right_x_max and right_y_min <= start[1] <= right_y_max and
                        right_x_min <= end[0] <= right_x_max and right_y_min <= end[1] <= right_y_max):
                        entity.ScaleEntity(right_base, SCALE_FACTOR)
                        scaled_right += 1
        except:
            pass

    print(f"Scaled {scaled_right} lines in RIGHT silo")

    # Регенерувати
    doc_acad.Regen(1)

    print(f"\n{'='*80}")
    print("SUCCESS!")
    print(f"{'='*80}")
    print(f"\nScaled 2 lower silos by {SCALE_FACTOR}x")
    print(f"LEFT: {scaled_left} lines, RIGHT: {scaled_right} lines")
    print("\nCheck AutoCAD to see the result!")

except Exception as e:
    print(f"\nERROR in COM API: {e}")
    import traceback
    traceback.print_exc()
