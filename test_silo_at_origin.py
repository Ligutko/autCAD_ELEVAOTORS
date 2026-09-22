# -*- coding: utf-8 -*-
"""
МАЛЮЄМО СИЛОС В ПОЧАТКУ КООРДИНАТ З ПРАВИЛЬНИМ ZOOM
"""
import sys
import io
import win32com.client
import pythoncom
import math

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("="*70)
print("МАЛЮЄМО СИЛОС В ПОЧАТКУ КООРДИНАТ")
print("="*70)

try:
    # Підключаємося до AutoCAD
    print("\n1. Підключення до AutoCAD...")
    acad = win32com.client.Dispatch("AutoCAD.Application")
    doc = acad.ActiveDocument
    modelSpace = doc.ModelSpace
    print(f"   OK! Документ: {doc.Name}")

    # Параметри силоса - починаємо з (0,0)
    center_x = 0
    center_y = 0
    diameter = 5000
    height = 10000
    equipment_tag = "СИЛОС-1"

    radius = diameter / 2.0
    cone_height = diameter * 0.4

    print(f"\n2. Параметри силоса:")
    print(f"   Центр: ({center_x}, {center_y})")
    print(f"   Діаметр: {diameter} мм")
    print(f"   Висота: {height} мм")

    # МАЛЮЄМО ЦИЛІНДРИЧНУ ЧАСТИНУ
    print("\n3. Малюю циліндр (прямокутник)...")

    # Нижня лінія
    pt1 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x - radius, center_y, 0])
    pt2 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x + radius, center_y, 0])
    line1 = modelSpace.AddLine(pt1, pt2)
    print(f"   Лінія 1: ({center_x - radius}, {center_y}) -> ({center_x + radius}, {center_y})")

    # Права лінія
    pt3 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x + radius, center_y, 0])
    pt4 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x + radius, center_y + height, 0])
    line2 = modelSpace.AddLine(pt3, pt4)
    print(f"   Лінія 2: ({center_x + radius}, {center_y}) -> ({center_x + radius}, {center_y + height})")

    # Верхня лінія
    pt5 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x + radius, center_y + height, 0])
    pt6 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x - radius, center_y + height, 0])
    line3 = modelSpace.AddLine(pt5, pt6)
    print(f"   Лінія 3: ({center_x + radius}, {center_y + height}) -> ({center_x - radius}, {center_y + height})")

    # Ліва лінія
    pt7 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x - radius, center_y + height, 0])
    pt8 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x - radius, center_y, 0])
    line4 = modelSpace.AddLine(pt7, pt8)
    print(f"   Лінія 4: ({center_x - radius}, {center_y + height}) -> ({center_x - radius}, {center_y})")

    print("   ✓ Циліндр намальовано (4 лінії)")

    # МАЛЮЄМО КОНІЧНЕ ДНИЩЕ
    print("\n4. Малюю конічне днище...")

    cone_top_y = center_y
    cone_bottom_y = center_y - cone_height

    # Ліва лінія конуса
    cone_p1 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x - radius, cone_top_y, 0])
    cone_p2 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x, cone_bottom_y, 0])
    cone_line1 = modelSpace.AddLine(cone_p1, cone_p2)
    print(f"   Конус ліва: ({center_x - radius}, {cone_top_y}) -> ({center_x}, {cone_bottom_y})")

    # Права лінія конуса
    cone_p3 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x + radius, cone_top_y, 0])
    cone_p4 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x, cone_bottom_y, 0])
    cone_line2 = modelSpace.AddLine(cone_p3, cone_p4)
    print(f"   Конус права: ({center_x + radius}, {cone_top_y}) -> ({center_x}, {cone_bottom_y})")

    print("   ✓ Конус намальовано")

    # МАЛЮЄМО КУПОЛ (дуга)
    print("\n5. Малюю купол зверху...")

    arc_center = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                         [center_x, center_y + height, 0])
    arc_radius = radius
    start_angle = math.pi  # 180°
    end_angle = 0  # 0°

    arc = modelSpace.AddArc(arc_center, arc_radius, start_angle, end_angle)
    print(f"   Дуга: центр ({center_x}, {center_y + height}), радіус {arc_radius}")
    print("   ✓ Купол намальовано")

    # ДОДАЄМО ТЕКСТ
    print("\n6. Додаю текст...")

    text_point = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                         [center_x, center_y + height + 1000, 0])
    text_height = 400
    text_obj = modelSpace.AddText(equipment_tag, text_point, text_height)
    text_obj.Alignment = 10  # Middle Center
    text_obj.TextAlignmentPoint = text_point

    print(f"   ✓ Текст '{equipment_tag}' додано")

    # ZOOM EXTENTS КІЛЬКА РАЗІВ
    print("\n7. ZOOM EXTENTS...")
    acad.ZoomExtents()
    print("   ✓ Перший zoom")

    import time
    time.sleep(0.5)
    acad.ZoomExtents()
    print("   ✓ Другий zoom")

    # Оновлюємо екран
    print("\n8. Оновлюю екран...")
    doc.SendCommand("_REGEN\n")
    print("   ✓ Regen виконано")

    print("\n" + "="*70)
    print("✓✓✓ СИЛОС НАМАЛЬОВАНО УСПІШНО! ✓✓✓")
    print("="*70)
    print("\nПодивись в AutoCAD - має бути силос!")
    print(f"Координати: центр ({center_x}, {center_y})")
    print(f"Розміри: від ({center_x - radius}, {cone_bottom_y}) до ({center_x + radius}, {center_y + height + 1000})")

except Exception as e:
    print(f"\nПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
