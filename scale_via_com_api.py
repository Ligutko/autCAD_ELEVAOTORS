#!/usr/bin/env python
"""
Масштабування через AutoCAD COM API - використання команди SCALE
"""

import win32com.client
import pythoncom

try:
    print("Connecting to AutoCAD...")
    acad = win32com.client.Dispatch("AutoCAD.Application")
    acad.Visible = True

    doc = acad.ActiveDocument
    print(f"Active document: {doc.Name}")

    # Створити SelectionSet
    try:
        doc.SelectionSets.Item("TEMP_SCALE").Delete()
    except:
        pass

    ss = doc.SelectionSets.Add("TEMP_SCALE")

    # Попросити користувача вибрати об'єкти
    print("\n" + "="*60)
    print("УВАГА! Зараз потрібно ВРУЧНУ вибрати об'єкти в AutoCAD!")
    print("="*60)
    print("\n1. Перейдіть в AutoCAD")
    print("2. Виберіть WINDOW (рамкою) всі об'єкти силоса який хочете збільшити")
    print("3. Натисніть Enter коли закінчите")

    # Попросити користувача вибрати
    ss.SelectOnScreen()

    print(f"\nВибрано {ss.Count} об'єктів")

    if ss.Count == 0:
        print("ERROR: Нічого не вибрано!")
        exit(1)

    # Попросити центр масштабування
    print("\nТепер виберіть БАЗОВУ ТОЧКУ для масштабування")
    print("(зазвичай це центр силоса)")

    base_point = doc.Utility.GetPoint(Type="Виберіть базову точку:")

    print(f"Базова точка: ({base_point[0]:.2f}, {base_point[1]:.2f})")

    # Коефіцієнт масштабування
    SCALE_FACTOR = 1.25

    print(f"\nМасштабування з коефіцієнтом {SCALE_FACTOR}...")

    # Застосувати SCALE до кожного об'єкта
    for i in range(ss.Count):
        entity = ss.Item(i)

        # Використати метод ScaleEntity
        try:
            entity.ScaleEntity(base_point, SCALE_FACTOR)
        except Exception as e:
            print(f"Warning: Cannot scale entity {i}: {e}")

    # Очистити selection set
    ss.Delete()

    # Регенерувати
    doc.Regen(1)

    print("\n" + "="*60)
    print("SUCCESS!")
    print("="*60)
    print(f"\nМасштабовано {ss.Count} об'єктів з коефіцієнтом {SCALE_FACTOR}")
    print("\nПеревірте результат в AutoCAD!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
