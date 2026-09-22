# -*- coding: utf-8 -*-
"""
ТЕСТ COM API - ПРЯМИЙ ДОСТУП ДО AUTOCAD БЕЗ КЛАВІАТУРИ!
"""
import sys
import io
import win32com.client
import pythoncom

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("="*70)
print("ТЕСТ COM API - ПРЯМИЙ ДОСТУП ДО AUTOCAD")
print("="*70)

try:
    # Підключаємося до AutoCAD через COM
    print("\n1. Підключаюсь до AutoCAD через COM API...")
    acad = win32com.client.Dispatch("AutoCAD.Application")

    print(f"   OK! Версія: {acad.Version}")
    print(f"   Назва: {acad.Name}")

    # Отримуємо активний документ
    doc = acad.ActiveDocument
    print(f"\n2. Активний документ: {doc.Name}")

    # Отримуємо ModelSpace
    modelSpace = doc.ModelSpace
    print("   OK! ModelSpace отримано")

    # МАЛЮЄМО ЛІНІЮ
    print("\n3. Малюю ЛІНІЮ від (0,0) до (5000,5000)...")
    startPoint = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [0, 0, 0])
    endPoint = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [5000, 5000, 0])
    line = modelSpace.AddLine(startPoint, endPoint)
    print("   OK! Лінія намальована!")

    # МАЛЮЄМО КОЛО
    print("\n4. Малюю КОЛО з центром (2500,2500), радіус 1500...")
    centerPoint = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [2500, 2500, 0])
    radius = 1500
    circle = modelSpace.AddCircle(centerPoint, radius)
    print("   OK! Коло намальовано!")

    # МАЛЮЄМО ТЕКСТ
    print("\n5. Додаю ТЕКСТ 'COM API WORKS!' в точці (1000,1000)...")
    textPoint = win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [1000, 1000, 0])
    textHeight = 500
    text = modelSpace.AddText("COM API WORKS!", textPoint, textHeight)
    print("   OK! Текст додано!")

    # ZOOM EXTENTS
    print("\n6. Роблю ZOOM EXTENTS...")
    acad.ZoomExtents()
    print("   OK! Zoom виконано!")

    # Оновлюємо екран
    doc.Regen(win32com.client.constants.acAllViewports)

    print("\n" + "="*70)
    print("УСПІХ! ВСЕ НАМАЛЬОВАНО ЧЕРЕЗ COM API!")
    print("="*70)
    print("\nПЕРЕВІР AUTOCAD - має бути:")
    print("  - Діагональна лінія")
    print("  - Коло в центрі")
    print("  - Текст 'COM API WORKS!'")
    print("\nЦей метод працює БЕЗ клавіатури - набагато надійніше!")

except Exception as e:
    print(f"\nПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
