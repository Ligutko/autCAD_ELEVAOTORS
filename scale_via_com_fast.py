#!/usr/bin/env python
"""
Масштабування через AutoCAD COM API - ШВИДКА версія
Використовує SelectByPolygon для швидкого вибору
"""

import win32com.client
import pythoncom
import time

try:
    print("Connecting to AutoCAD...")
    acad = win32com.client.Dispatch("AutoCAD.Application")
    acad.Visible = True

    doc = acad.ActiveDocument
    print(f"Active document: {doc.Name}")

    msp = doc.ModelSpace

    # Знайти тільки нижні сині лінії (для визначення bounds)
    print("\nQuick search for lower silos bounds...")

    lower_blue_lines = []
    count = 0

    for entity in msp:
        count += 1
        if count % 10000 == 0:
            print(f"  Processed {count} entities...")

        try:
            if entity.EntityName == "AcDbLine":
                if hasattr(entity, 'Layer') and entity.Layer == 'RGB_000_000_255':
                    start_point = entity.StartPoint
                    end_point = entity.EndPoint

                    if start_point[1] < 200 and end_point[1] < 200:
                        lower_blue_lines.append(entity)
        except:
            pass

    print(f"Total entities in drawing: {count}")
    print(f"Found {len(lower_blue_lines)} lower blue lines")

    if len(lower_blue_lines) == 0:
        print("ERROR: No lower silos found!")
        exit(1)

    # Розділити на ЛІВИЙ та ПРАВИЙ
    xs = []
    for entity in lower_blue_lines:
        xs.append(entity.StartPoint[0])
        xs.append(entity.EndPoint[0])

    mid_x = (min(xs) + max(xs)) / 2

    left_blue = [e for e in lower_blue_lines if e.StartPoint[0] < mid_x]
    right_blue = [e for e in lower_blue_lines if e.StartPoint[0] > mid_x]

    # Bounds
    xs_left = []
    ys_left = []
    for e in left_blue:
        xs_left.extend([e.StartPoint[0], e.EndPoint[0]])
        ys_left.extend([e.StartPoint[1], e.EndPoint[1]])

    left_x_min, left_x_max = min(xs_left), max(xs_left)
    left_y_min, left_y_max = min(ys_left), max(ys_left)
    left_center_x = (left_x_min + left_x_max) / 2
    left_center_y = (left_y_min + left_y_max) / 2

    xs_right = []
    ys_right = []
    for e in right_blue:
        xs_right.extend([e.StartPoint[0], e.EndPoint[0]])
        ys_right.extend([e.StartPoint[1], e.EndPoint[1]])

    right_x_min, right_x_max = min(xs_right), max(xs_right)
    right_y_min, right_y_max = min(ys_right), max(ys_right)
    right_center_x = (right_x_min + right_x_max) / 2
    right_center_y = (right_y_min + right_y_max) / 2

    print(f"\nLEFT silo: X=[{left_x_min:.1f}, {left_x_max:.1f}], Y=[{left_y_min:.1f}, {left_y_max:.1f}]")
    print(f"  Center: ({left_center_x:.1f}, {left_center_y:.1f})")
    print(f"  Blue lines: {len(left_blue)}")

    print(f"\nRIGHT silo: X=[{right_x_min:.1f}, {right_x_max:.1f}], Y=[{right_y_min:.1f}, {right_y_max:.1f}]")
    print(f"  Center: ({right_center_x:.1f}, {right_center_y:.1f})")
    print(f"  Blue lines: {len(right_blue)}")

    SCALE_FACTOR = 1.25

    # ВАЖЛИВО: Масштабуємо тільки СИНІ лінії (структура силоса)
    # Інші entities (текст, розміри) можуть не підтримувати ScaleEntity

    print(f"\n{'='*60}")
    print(f"Scaling LEFT silo BLUE LINES by {SCALE_FACTOR}x...")
    print(f"{'='*60}")

    left_base_point = [left_center_x, left_center_y, 0]
    scaled_left = 0

    for entity in left_blue:
        try:
            entity.ScaleEntity(left_base_point, SCALE_FACTOR)
            scaled_left += 1
        except Exception as e:
            print(f"Warning: {e}")

    print(f"Scaled {scaled_left} blue lines in LEFT silo")

    print(f"\n{'='*60}")
    print(f"Scaling RIGHT silo BLUE LINES by {SCALE_FACTOR}x...")
    print(f"{'='*60}")

    right_base_point = [right_center_x, right_center_y, 0]
    scaled_right = 0

    for entity in right_blue:
        try:
            entity.ScaleEntity(right_base_point, SCALE_FACTOR)
            scaled_right += 1
        except Exception as e:
            print(f"Warning: {e}")

    print(f"Scaled {scaled_right} blue lines in RIGHT silo")

    # Регенерувати
    print("\nRegenerating drawing...")
    doc.Regen(1)

    print(f"\n{'='*80}")
    print("SUCCESS!")
    print(f"{'='*80}")
    print(f"\nScaled BLUE STRUCTURE of 2 lower silos by {SCALE_FACTOR}x")
    print(f"LEFT silo: {scaled_left} blue lines")
    print(f"RIGHT silo: {scaled_right} blue lines")
    print("\nNOTE: Text and dimensions were NOT scaled (may need manual adjustment)")
    print("\nCheck AutoCAD window to see result!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
