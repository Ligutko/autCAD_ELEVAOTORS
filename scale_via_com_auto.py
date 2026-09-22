#!/usr/bin/env python
"""
Масштабування через AutoCAD COM API - АВТОМАТИЧНИЙ вибір нижніх силосів
"""

import win32com.client
import pythoncom

try:
    print("Connecting to AutoCAD...")
    acad = win32com.client.Dispatch("AutoCAD.Application")
    acad.Visible = True

    doc = acad.ActiveDocument
    print(f"Active document: {doc.Name}")

    # Отримати modelspace
    msp = doc.ModelSpace

    # Знайти нижні сині лінії (силоси)
    print("\nSearching for lower silos...")

    lower_blue_lines = []

    for entity in msp:
        try:
            # Перевірити чи це лінія на шарі RGB_000_000_255
            if entity.EntityName == "AcDbLine":
                if hasattr(entity, 'Layer') and entity.Layer == 'RGB_000_000_255':
                    # Перевірити Y координату (нижні силоси Y < 200)
                    start_point = entity.StartPoint
                    end_point = entity.EndPoint

                    if start_point[1] < 200 and end_point[1] < 200:
                        lower_blue_lines.append(entity)
        except:
            pass

    print(f"Found {len(lower_blue_lines)} lower blue lines")

    if len(lower_blue_lines) == 0:
        print("ERROR: No lower silos found!")
        exit(1)

    # Розділити на ЛІВИЙ та ПРАВИЙ силос
    xs = []
    for entity in lower_blue_lines:
        xs.append(entity.StartPoint[0])
        xs.append(entity.EndPoint[0])

    mid_x = (min(xs) + max(xs)) / 2

    left_blue = [e for e in lower_blue_lines if e.StartPoint[0] < mid_x and e.EndPoint[0] < mid_x]
    right_blue = [e for e in lower_blue_lines if e.StartPoint[0] > mid_x and e.EndPoint[0] > mid_x]

    print(f"\nLEFT silo: {len(left_blue)} blue lines")
    print(f"RIGHT silo: {len(right_blue)} blue lines")

    # Знайти центри та bounds для кожного силоса
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

    print(f"\nLEFT center: ({left_center_x:.1f}, {left_center_y:.1f})")
    print(f"RIGHT center: ({right_center_x:.1f}, {right_center_y:.1f})")

    # Знайти ВСІ entities для кожного силоса
    print("\nFinding ALL entities for LEFT silo...")
    left_entities = []

    for entity in msp:
        try:
            # Пропустити GRID
            if hasattr(entity, 'Layer') and entity.Layer == 'GRID':
                continue

            in_bounds = False

            if entity.EntityName == "AcDbLine":
                start = entity.StartPoint
                end = entity.EndPoint
                if (left_x_min <= start[0] <= left_x_max and left_y_min <= start[1] <= left_y_max and
                    left_x_min <= end[0] <= left_x_max and left_y_min <= end[1] <= left_y_max):
                    in_bounds = True

            elif entity.EntityName in ["AcDbText", "AcDbMText"]:
                if hasattr(entity, 'InsertionPoint'):
                    pos = entity.InsertionPoint
                    if left_x_min <= pos[0] <= left_x_max and left_y_min <= pos[1] <= left_y_max:
                        in_bounds = True

            elif entity.EntityName == "AcDbCircle":
                if hasattr(entity, 'Center'):
                    center = entity.Center
                    if left_x_min <= center[0] <= left_x_max and left_y_min <= center[1] <= left_y_max:
                        in_bounds = True

            if in_bounds:
                left_entities.append(entity)
        except:
            pass

    print(f"Found {len(left_entities)} entities in LEFT silo")

    print("\nFinding ALL entities for RIGHT silo...")
    right_entities = []

    for entity in msp:
        try:
            if hasattr(entity, 'Layer') and entity.Layer == 'GRID':
                continue

            in_bounds = False

            if entity.EntityName == "AcDbLine":
                start = entity.StartPoint
                end = entity.EndPoint
                if (right_x_min <= start[0] <= right_x_max and right_y_min <= start[1] <= right_y_max and
                    right_x_min <= end[0] <= right_x_max and right_y_min <= end[1] <= right_y_max):
                    in_bounds = True

            elif entity.EntityName in ["AcDbText", "AcDbMText"]:
                if hasattr(entity, 'InsertionPoint'):
                    pos = entity.InsertionPoint
                    if right_x_min <= pos[0] <= right_x_max and right_y_min <= pos[1] <= right_y_max:
                        in_bounds = True

            elif entity.EntityName == "AcDbCircle":
                if hasattr(entity, 'Center'):
                    center = entity.Center
                    if right_x_min <= center[0] <= right_x_max and right_y_min <= center[1] <= right_y_max:
                        in_bounds = True

            if in_bounds:
                right_entities.append(entity)
        except:
            pass

    print(f"Found {len(right_entities)} entities in RIGHT silo")

    SCALE_FACTOR = 1.25

    print(f"\n{'='*60}")
    print(f"Scaling LEFT silo by {SCALE_FACTOR}x...")
    print(f"{'='*60}")

    # Масштабувати ЛІВИЙ силос
    left_base_point = [left_center_x, left_center_y, 0]
    scaled_left = 0

    for entity in left_entities:
        try:
            entity.ScaleEntity(left_base_point, SCALE_FACTOR)
            scaled_left += 1
        except Exception as e:
            print(f"Warning: Cannot scale entity: {e}")

    print(f"Scaled {scaled_left} entities in LEFT silo")

    print(f"\n{'='*60}")
    print(f"Scaling RIGHT silo by {SCALE_FACTOR}x...")
    print(f"{'='*60}")

    # Масштабувати ПРАВИЙ силос
    right_base_point = [right_center_x, right_center_y, 0]
    scaled_right = 0

    for entity in right_entities:
        try:
            entity.ScaleEntity(right_base_point, SCALE_FACTOR)
            scaled_right += 1
        except Exception as e:
            print(f"Warning: Cannot scale entity: {e}")

    print(f"Scaled {scaled_right} entities in RIGHT silo")

    # Регенерувати
    doc.Regen(1)

    print(f"\n{'='*80}")
    print("SUCCESS!")
    print(f"{'='*80}")
    print(f"\nScaled 2 lower silos by {SCALE_FACTOR}x")
    print(f"LEFT silo: {scaled_left} entities")
    print(f"RIGHT silo: {scaled_right} entities")
    print("\nCheck AutoCAD window to see result!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
