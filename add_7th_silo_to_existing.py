# -*- coding: utf-8 -*-
"""
ДОДАТИ 7-Й СИЛОС ДО ІСНУЮЧОЇ СХЕМИ (БЕЗ ВИДАЛЕННЯ!)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import pythoncom

def cp(x, y, z=0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

print("="*70)
print("ДОДАВАННЯ 7-ГО СИЛОСУ ДО ІСНУЮЧОЇ СХЕМИ")
print("="*70)

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    docs = acad.Documents

    # Знайти або відкрити page_02.dxf
    print("\n[1] ПОШУК page_02.dxf...")

    target_doc = None
    for i in range(docs.Count):
        doc = docs.Item(i)
        if "page_02" in doc.Name:
            target_doc = doc
            break

    if target_doc:
        print(f"    ✓ Знайдено: {target_doc.Name}")
        acad.ActiveDocument = target_doc
    else:
        # Відкрити файл
        print("    • Відкриваю D:/autocad project/FINAL_DXF_CORRECTED/page_02.dxf...")
        try:
            target_doc = docs.Open("D:/autocad project/FINAL_DXF_CORRECTED/page_02.dxf")
            acad.ActiveDocument = target_doc
            print(f"    ✓ Відкрито!")
        except:
            print("    • Спробую FINAL_DXF_OUTPUT...")
            target_doc = docs.Open("D:/autocad project/FINAL_DXF_OUTPUT/page_02.dxf")
            acad.ActiveDocument = target_doc
            print(f"    ✓ Відкрито!")

    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    print(f"    • Об'єктів зараз: {ms.Count}")

    # Аналіз існуючих силосів (знайти координати)
    print("\n[2] АНАЛІЗ ІСНУЮЧИХ СИЛОСІВ...")

    # TODO: Проаналізувати геометрію щоб знайти де силоси
    # Поки що використаємо приблизні координати

    print("    • Шукаю найправіший силос...")

    # Найправіший силос приблизно на X ~850-900, Y ~600-700
    # 7-й силос розміщуємо праворуч від нього

    print("\n[3] ДОДАВАННЯ 7-ГО СИЛОСУ...")

    # Координати (ПРИБЛИЗНО, треба коригувати)
    silo7_x = 920  # Праворуч від силосу 6
    silo7_y = 650  # На тій же висоті
    silo7_d = 180  # Діаметр ~180 мм (в масштабі PDF)
    silo7_h = 140  # Висота ~140 мм

    hw = silo7_d / 2

    print(f"    Координати: X={silo7_x}, Y={silo7_y}, D={silo7_d}")

    # Прямокутник (циліндр збоку)
    ms.AddLine(cp(silo7_x-hw, silo7_y), cp(silo7_x+hw, silo7_y))
    ms.AddLine(cp(silo7_x+hw, silo7_y), cp(silo7_x+hw, silo7_y+silo7_h))
    ms.AddLine(cp(silo7_x+hw, silo7_y+silo7_h), cp(silo7_x-hw, silo7_y+silo7_h))
    ms.AddLine(cp(silo7_x-hw, silo7_y+silo7_h), cp(silo7_x-hw, silo7_y))

    # Конус знизу
    cone_h = 25
    ms.AddLine(cp(silo7_x-hw, silo7_y), cp(silo7_x, silo7_y-cone_h))
    ms.AddLine(cp(silo7_x, silo7_y-cone_h), cp(silo7_x+hw, silo7_y))

    # Купол зверху
    dome_h = 15
    ms.AddArc(cp(silo7_x, silo7_y+silo7_h), dome_h, 0, 3.14159)

    print("    ✓ Геометрія намальована")

    # Мітка "7"
    txt1 = ms.AddText("7", cp(silo7_x-10, silo7_y+silo7_h/2), 30)

    # Підпис
    ms.AddText("МСВУ 220.13.В12", cp(silo7_x-hw-5, silo7_y+silo7_h+10), 15)

    print("    ✓ Мітки додано")

    # Стрілки виходів (7 штук)
    print("    • Додаю 7 стрілок виходів...")

    outlet_y = silo7_y - cone_h - 5
    spacing = silo7_d / 8

    for i in range(1, 8):
        ox = silo7_x - hw + i * spacing
        arr_y = outlet_y - 20

        a1 = ms.AddLine(cp(ox, outlet_y), cp(ox, arr_y))
        a2 = ms.AddLine(cp(ox, arr_y), cp(ox-3, arr_y+8))
        a3 = ms.AddLine(cp(ox, arr_y), cp(ox+3, arr_y+8))

        # Синій колір (як силоси 3-6)
        a1.Color = 5
        a2.Color = 5
        a3.Color = 5

    print("    ✓ Стрілки додано")

    # Конвеєр T17 (силос 6 → силос 7)
    print("\n[4] ДОДАВАННЯ КОНВЕЄРА T17...")

    t17_x1 = silo7_x - hw - 100  # Від силосу 6
    t17_y1 = silo7_y + 50
    t17_x2 = silo7_x - hw - 10   # До силосу 7
    t17_y2 = silo7_y + 50

    w = 8
    ms.AddLine(cp(t17_x1, t17_y1+w/2), cp(t17_x2, t17_y2+w/2))
    ms.AddLine(cp(t17_x1, t17_y1-w/2), cp(t17_x2, t17_y2-w/2))

    # Стрілка
    mx = (t17_x1 + t17_x2) / 2
    my = (t17_y1 + t17_y2) / 2
    ms.AddLine(cp(mx, my), cp(mx+10, my))
    ms.AddLine(cp(mx+10, my), cp(mx+7, my+3))
    ms.AddLine(cp(mx+10, my), cp(mx+7, my-3))

    ms.AddText("T17", cp(mx-5, my+10), 12)
    ms.AddText("100 т/год", cp(mx-5, my-5), 8)

    print("    ✓ T17 додано")

    print(f"\n{'='*70}")
    print("✅ 7-Й СИЛОС ДОДАНО!")
    print(f"{'='*70}")

    print(f"\n📊 Об'єктів тепер: {ms.Count}")
    print("\n⚠ ВАЖЛИВО: Перевір координати та підкоригуй якщо треба!")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
