# -*- coding: utf-8 -*-
"""
МАЛЮЄМО ПРОФЕСІЙНИЙ СИЛОС ЧЕРЕЗ COM API!
"""
import sys
import io
import win32com.client
import pythoncom
import math

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("="*70)
print("МАЛЮЄМО СИЛОС МСВУ ЧЕРЕЗ COM API")
print("="*70)

try:
    # Підключаємося до AutoCAD
    print("\n1. Підключення до AutoCAD...")
    acad = win32com.client.Dispatch("AutoCAD.Application")
    doc = acad.ActiveDocument
    modelSpace = doc.ModelSpace
    print(f"   OK! Документ: {doc.Name}")

    # Параметри силоса
    center_x = 10000  # Зміщуємо вправо щоб не накладався
    center_y = 0
    diameter = 5000
    height = 10000
    equipment_tag = "СИЛОС-ТЕСТ"

    radius = diameter / 2.0
    cone_height = diameter * 0.4  # Конус 40% від діаметра

    print(f"\n2. Параметри силоса:")
    print(f"   Центр: ({center_x}, {center_y})")
    print(f"   Діаметр: {diameter} мм")
    print(f"   Висота: {height} мм")
    print(f"   Тег: {equipment_tag}")

    # МАЛЮЄМО ЦИЛІНДРИЧНУ ЧАСТИНУ (прямокутник)
    print("\n3. Малюю циліндричну частину...")

    # Нижній лівий кут
    p1 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                  [center_x - radius, center_y, 0])
    # Верхній правий кут
    p2 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                  [center_x + radius, center_y + height, 0])

    # Малюємо прямокутник через 4 лінії
    # Нижня горизонталь
    pt1 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x - radius, center_y, 0])
    pt2 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x + radius, center_y, 0])
    modelSpace.AddLine(pt1, pt2)

    # Права вертикаль
    pt3 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x + radius, center_y, 0])
    pt4 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x + radius, center_y + height, 0])
    modelSpace.AddLine(pt3, pt4)

    # Верхня горизонталь
    pt5 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x + radius, center_y + height, 0])
    pt6 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x - radius, center_y + height, 0])
    modelSpace.AddLine(pt5, pt6)

    # Ліва вертикаль
    pt7 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x - radius, center_y + height, 0])
    pt8 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                   [center_x - radius, center_y, 0])
    modelSpace.AddLine(pt7, pt8)

    print("   OK! Циліндр намальовано")

    # МАЛЮЄМО КОНУС ВНИЗУ
    print("\n4. Малюю конічне днище...")

    cone_top_y = center_y - cone_height
    cone_bottom_y = cone_top_y - diameter * 0.3

    # Ліва лінія конуса
    cone_p1 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x - radius, cone_top_y, 0])
    cone_p2 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x, cone_bottom_y, 0])
    modelSpace.AddLine(cone_p1, cone_p2)

    # Права лінія конуса
    cone_p3 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x + radius, cone_top_y, 0])
    cone_p4 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x, cone_bottom_y, 0])
    modelSpace.AddLine(cone_p3, cone_p4)

    # Горизонтальна лінія зверху конуса
    cone_p5 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x - radius, cone_top_y, 0])
    cone_p6 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                       [center_x + radius, cone_top_y, 0])
    modelSpace.AddLine(cone_p5, cone_p6)

    print("   OK! Конус намальовано")

    # МАЛЮЄМО ДУГУ ЗВЕРХУ (КУПОЛ)
    print("\n5. Малюю купол (дуга)...")

    # Центр дуги
    arc_center = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                         [center_x, center_y + height, 0])
    arc_radius = radius
    start_angle = math.pi  # 180 градусів
    end_angle = 0  # 0 градусів

    arc = modelSpace.AddArc(arc_center, arc_radius, start_angle, end_angle)
    print("   OK! Купол намальовано")

    # ДОДАЄМО КОЛО ЗВЕРХУ ТА ЗНИЗУ (для візуалізації)
    print("\n6. Додаю кола для візуалізації...")

    # Коло зверху
    top_circle_center = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                                 [center_x, center_y + height, 0])
    modelSpace.AddCircle(top_circle_center, radius)

    # Коло знизу
    bottom_circle_center = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                                    [center_x, center_y, 0])
    modelSpace.AddCircle(bottom_circle_center, radius)

    print("   OK! Кола додано")

    # ДОДАЄМО ТЕКСТ З ТЕГОМ
    print("\n7. Додаю текст з тегом...")

    text_point = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                         [center_x, center_y + height + 500, 0])
    text_height = 400
    text_obj = modelSpace.AddText(equipment_tag, text_point, text_height)

    # Центруємо текст
    text_obj.Alignment = 10  # acAlignmentMiddleCenter
    text_obj.TextAlignmentPoint = text_point

    print(f"   OK! Текст '{equipment_tag}' додано")

    # ДОДАЄМО ПАРАМЕТРИ
    text_point2 = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
                                          [center_x, center_y + height + 900, 0])
    params_text = f"D={diameter}mm, H={height}mm"
    text_obj2 = modelSpace.AddText(params_text, text_point2, 250)
    text_obj2.Alignment = 10
    text_obj2.TextAlignmentPoint = text_point2

    print(f"   OK! Параметри додано: {params_text}")

    # ZOOM EXTENTS
    print("\n8. ZOOM EXTENTS...")
    acad.ZoomExtents()
    print("   OK!")

    print("\n" + "="*70)
    print("✓ СИЛОС НАМАЛЬОВАНО УСПІШНО!")
    print("="*70)
    print("\nПЕРЕВІР AUTOCAD - має бути ПРОФЕСІЙНИЙ СИЛОС:")
    print("  ✓ Циліндрична частина (прямокутник)")
    print("  ✓ Конічне днище")
    print("  ✓ Купол зверху (дуга)")
    print("  ✓ Кола для візуалізації")
    print("  ✓ Тег обладнання")
    print("  ✓ Технічні параметри")

except Exception as e:
    print(f"\nПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
