#!/usr/bin/env python
"""
Масштабування через AutoCAD COM API - СПРАВЖНЄ масштабування!

Використовує команду SCALE в AutoCAD
"""

import win32com.client
import pythoncom
import time

try:
    # Підключитися до AutoCAD
    print("Connecting to AutoCAD...")
    acad = win32com.client.Dispatch("AutoCAD.Application")
    acad.Visible = True

    doc = acad.ActiveDocument
    print(f"Active document: {doc.Name}")

    # Отримати modelspace
    msp = doc.ModelSpace

    # Знайти нижні сині лінії (силоси)
    print("\nSearching for lower silos...")

    lower_blue_entities = []

    for entity in msp:
        try:
            # Перевірити чи це лінія
            if entity.EntityName == "AcDbLine":
                # Перевірити layer
                if hasattr(entity, 'Layer') and entity.Layer == 'RGB_000_000_255':
                    # Перевірити Y координату (нижні силоси Y < 200)
                    start_point = entity.StartPoint
                    end_point = entity.EndPoint

                    if start_point[1] < 200 and end_point[1] < 200:
                        lower_blue_entities.append(entity)
        except:
            pass

    print(f"Found {len(lower_blue_entities)} lower blue lines")

    if len(lower_blue_entities) == 0:
        print("ERROR: No lower silos found!")
        exit(1)

    # Розділити на ЛІВИЙ та ПРАВИЙ силос
    xs = []
    for entity in lower_blue_entities:
        xs.append(entity.StartPoint[0])
        xs.append(entity.EndPoint[0])

    mid_x = (min(xs) + max(xs)) / 2

    left_entities = [e for e in lower_blue_entities if e.StartPoint[0] < mid_x and e.EndPoint[0] < mid_x]
    right_entities = [e for e in lower_blue_entities if e.StartPoint[0] > mid_x and e.EndPoint[0] > mid_x]

    print(f"LEFT silo: {len(left_entities)} lines")
    print(f"RIGHT silo: {len(right_entities)} lines")

    # Знайти центри
    xs_left = []
    ys_left = []
    for e in left_entities:
        xs_left.extend([e.StartPoint[0], e.EndPoint[0]])
        ys_left.extend([e.StartPoint[1], e.EndPoint[1]])

    left_center_x = (min(xs_left) + max(xs_left)) / 2
    left_center_y = (min(ys_left) + max(ys_left)) / 2

    xs_right = []
    ys_right = []
    for e in right_entities:
        xs_right.extend([e.StartPoint[0], e.EndPoint[0]])
        ys_right.extend([e.StartPoint[1], e.EndPoint[1]])

    right_center_x = (min(xs_right) + max(xs_right)) / 2
    right_center_y = (min(ys_right) + max(ys_right)) / 2

    print(f"\nLEFT center: ({left_center_x:.1f}, {left_center_y:.1f})")
    print(f"RIGHT center: ({right_center_x:.1f}, {right_center_y:.1f})")

    SCALE_FACTOR = 1.25

    print(f"\nScaling LEFT silo by {SCALE_FACTOR}...")

    # Створити SelectionSet для ЛІВОГО силоса
    try:
        ss_left = doc.SelectionSets.Add(f"LeftSilo_{int(time.time())}")
    except:
        ss_left = doc.SelectionSets.Item(f"LeftSilo_{int(time.time())}")

    # Додати entities до selection set
    # ПРОБЛЕМА: win32com не дозволяє передати Python list
    # Потрібно використати інший підхід

    print("\nWARNING: COM API approach is complex!")
    print("Using direct transformation instead...")

    # Альтернатива: масштабувати кожну лінію вручну
    for entity in left_entities:
        # Отримати точки
        start = entity.StartPoint
        end = entity.EndPoint

        # Масштабувати відносно центру
        new_start_x = left_center_x + (start[0] - left_center_x) * SCALE_FACTOR
        new_start_y = left_center_y + (start[1] - left_center_y) * SCALE_FACTOR

        new_end_x = left_center_x + (end[0] - left_center_x) * SCALE_FACTOR
        new_end_y = left_center_y + (end[1] - left_center_y) * SCALE_FACTOR

        # Встановити нові точки
        entity.StartPoint = (new_start_x, new_start_y, start[2])
        entity.EndPoint = (new_end_x, new_end_y, end[2])

    print(f"Scaled {len(left_entities)} entities in LEFT silo")

    print(f"\nScaling RIGHT silo by {SCALE_FACTOR}...")

    for entity in right_entities:
        start = entity.StartPoint
        end = entity.EndPoint

        new_start_x = right_center_x + (start[0] - right_center_x) * SCALE_FACTOR
        new_start_y = right_center_y + (start[1] - right_center_y) * SCALE_FACTOR

        new_end_x = right_center_x + (end[0] - right_center_x) * SCALE_FACTOR
        new_end_y = right_center_y + (end[1] - right_center_y) * SCALE_FACTOR

        entity.StartPoint = (new_start_x, new_start_y, start[2])
        entity.EndPoint = (new_end_x, new_end_y, end[2])

    print(f"Scaled {len(right_entities)} entities in RIGHT silo")

    # Оновити креслення
    doc.Regen(1)  # acActiveViewport

    print(f"\n{'='*80}")
    print("SUCCESS!")
    print(f"{'='*80}")
    print("\nScaled 2 lower silos in active AutoCAD document")
    print("Check AutoCAD window to see result!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
