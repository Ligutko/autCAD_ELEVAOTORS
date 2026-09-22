# -*- coding: utf-8 -*-
"""
V7 CORRECTED - ВИПРАВЛЕНІ КООРДИНАТИ (ВЕЛИКИЙ МАСШТАБ)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import pythoncom
import datetime

def cp(x, y, z=0):
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

print("="*70)
print("V7 CORRECTED - ВИПРАВЛЕННЯ МАСШТАБУ")
print("="*70)

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    # ОЧИЩЕННЯ
    print("\n[1] ОЧИЩЕННЯ...")
    while ms.Count > 0:
        try:
            ms.Item(0).Delete()
        except:
            break
    print(f"    ✓ Очищено")

    # НОВІ КООРДИНАТИ - ЗБІЛЬШЕНІ В 15 РАЗІВ!
    bx, by = 0, 0
    SCALE = 15  # Множник масштабу

    print("\n[2] МАЛЮВАННЯ 7 СИЛОСІВ (правильний масштаб)...")

    # Силоси з ВЕЛИКИМИ відстанями
    silos = [
        # Верхній рівень (2 силоси 20м)
        (1, bx+150000, by+450000, 20000, 21000),
        (2, bx+450000, by+450000, 20000, 21000),

        # Середній рівень (2 силоси 22м)
        (3, bx+225000, by+225000, 22000, 22000),
        (4, bx+555000, by+225000, 22000, 22000),

        # Нижній рівень (3 силоси 22м) - ГОРИЗОНТАЛЬНО
        (5, bx+150000, by+0, 22000, 22000),
        (6, bx+400000, by+0, 22000, 22000),
        (7, bx+650000, by+0, 22000, 22000),  # НОВИЙ!
    ]

    for num, x, y, d, h in silos:
        print(f"    Силос #{num}")

        w = d
        hw = w / 2

        # Прямокутник (циліндр)
        ms.AddLine(cp(x-hw, y), cp(x+hw, y))
        ms.AddLine(cp(x+hw, y), cp(x+hw, y+h))
        ms.AddLine(cp(x+hw, y+h), cp(x-hw, y+h))
        ms.AddLine(cp(x-hw, y+h), cp(x-hw, y))

        # Конус
        cone_h = 3000
        ms.AddLine(cp(x-hw, y), cp(x, y-cone_h))
        ms.AddLine(cp(x, y-cone_h), cp(x+hw, y))

        # Купол
        dome_h = 2000
        ms.AddArc(cp(x, y+h), dome_h, 0, 3.14159)

        # Номер (ВЕЛИКИЙ)
        txt = ms.AddText(str(num), cp(x-3000, y+h/2), 8000)
        txt.Alignment = 4

        # Підпис
        ms.AddText("МСВУ 220.13.В12", cp(x-hw-2000, y+h+5000), 5000)

        # Стрілки (7 виходів)
        outlet_y = y - cone_h - 2000
        for i in range(1, 8):
            ox = x - hw + i * (w / 8)
            arr_y = outlet_y - 8000

            a1 = ms.AddLine(cp(ox, outlet_y), cp(ox, arr_y))
            a2 = ms.AddLine(cp(ox, arr_y), cp(ox-800, arr_y+2500))
            a3 = ms.AddLine(cp(ox, arr_y), cp(ox+800, arr_y+2500))

            # Колір
            color = 1 if num <= 2 else 5  # Червоний для 1-2, синій для 3-7
            a1.Color = color
            a2.Color = color
            a3.Color = color

    print("\n[3] НОРИЇ...")

    noriyi = [
        ("H1", bx+75000, by+75000, 38000),
        ("H3", bx-45000, by+75000, 33000),
        ("H4", bx+15000, by+645000, 35000),
        ("H5", bx+720000, by+75000, 36000),
        ("H6", bx+825000, by+75000, 34000),
    ]

    for tag, x, y, h in noriyi:
        print(f"    {tag}")

        w = 3000
        hw = w / 2

        ms.AddLine(cp(x-hw, y), cp(x+hw, y))
        ms.AddLine(cp(x+hw, y), cp(x+hw, y+h))
        ms.AddLine(cp(x+hw, y+h), cp(x-hw, y+h))
        ms.AddLine(cp(x-hw, y+h), cp(x-hw, y))

        txt = ms.AddText(tag, cp(x-2000, y+h/2), 6000)
        txt.Alignment = 4

    print("\n[4] КОНВЕЄРИ...")

    conveyors = [
        ("T7", bx+45000, by+675000, bx+135000, by+675000),
        ("T8", bx+150000, by+765000, bx+450000, by+765000),
        ("T9", bx+90000, by+645000, bx+300000, by+765000),
        ("T10", bx+300000, by+375000, bx+375000, by+300000),
        ("T11", bx+375000, by+270000, bx+225000, by+540000),
        ("T12", bx+225000, by+540000, bx+555000, by+540000),
        ("T13", bx-30000, by+570000, bx+300000, by+300000),
        ("T14", bx+300000, by+300000, bx+630000, by+300000),
        ("T15", bx+630000, by+300000, bx+750000, by+300000),
        ("T16", bx+750000, by+240000, bx+750000, by+0),
        ("T17", bx+530000, by+165000, bx+640000, by+165000),  # НОВИЙ
        ("T18", bx+780000, by+165000, bx+780000, by-75000),   # НОВИЙ
    ]

    for tag, x1, y1, x2, y2 in conveyors:
        print(f"    {tag}")

        w = 2500
        dx = x2 - x1
        dy = y2 - y1
        length = (dx**2 + dy**2)**0.5

        px = -dy / length * w / 2
        py = dx / length * w / 2

        ms.AddLine(cp(x1+px, y1+py), cp(x2+px, y2+py))
        ms.AddLine(cp(x1-px, y1-py), cp(x2-px, y2-py))

        # Стрілка
        mx = (x1 + x2) / 2
        my = (y1 + y2) / 2
        arrow_size = 1500
        arrow_x = mx + (dx/length) * arrow_size
        arrow_y = my + (dy/length) * arrow_size

        ms.AddLine(cp(mx, my), cp(arrow_x, arrow_y))
        ms.AddLine(cp(arrow_x, arrow_y), cp(arrow_x-py*2, arrow_y-px*2))
        ms.AddLine(cp(arrow_x, arrow_y), cp(arrow_x+py*2, arrow_y+px*2))

        ms.AddText(tag, cp(mx-3000, my+3000), 5000)
        ms.AddText("100 т/год", cp(mx-3000, my-2000), 3500)

    print("\n[5] БУНКЕРИ...")

    # Бункер 8.1
    bunk1_x, bunk1_y = bx+780000, by+240000
    ms.AddLine(cp(bunk1_x-2500, bunk1_y), cp(bunk1_x+2500, bunk1_y))
    ms.AddLine(cp(bunk1_x+2500, bunk1_y), cp(bunk1_x+2500, bunk1_y+8000))
    ms.AddLine(cp(bunk1_x+2500, bunk1_y+8000), cp(bunk1_x-2500, bunk1_y+8000))
    ms.AddLine(cp(bunk1_x-2500, bunk1_y+8000), cp(bunk1_x-2500, bunk1_y))
    ms.AddLine(cp(bunk1_x-2500, bunk1_y), cp(bunk1_x, bunk1_y-3000))
    ms.AddLine(cp(bunk1_x, bunk1_y-3000), cp(bunk1_x+2500, bunk1_y))
    ms.AddText("8.1", cp(bunk1_x-1500, bunk1_y+4000), 5000)

    # Бункер 8.2
    bunk2_x, bunk2_y = bx+780000, by-120000
    ms.AddLine(cp(bunk2_x-2000, bunk2_y), cp(bunk2_x+2000, bunk2_y))
    ms.AddLine(cp(bunk2_x+2000, bunk2_y), cp(bunk2_x+2000, bunk2_y+6000))
    ms.AddLine(cp(bunk2_x+2000, bunk2_y+6000), cp(bunk2_x-2000, bunk2_y+6000))
    ms.AddLine(cp(bunk2_x-2000, bunk2_y+6000), cp(bunk2_x-2000, bunk2_y))
    ms.AddLine(cp(bunk2_x-2000, bunk2_y), cp(bunk2_x, bunk2_y-2500))
    ms.AddLine(cp(bunk2_x, bunk2_y-2500), cp(bunk2_x+2000, bunk2_y))
    ms.AddText("8.2", cp(bunk2_x-1500, bunk2_y+3000), 5000)

    print("\n[6] РАМКА...")

    fx1, fy1 = bx-150000, by-270000
    fx2, fy2 = bx+1200000, by+1200000

    f1 = ms.AddLine(cp(fx1, fy1), cp(fx2, fy1))
    f2 = ms.AddLine(cp(fx2, fy1), cp(fx2, fy2))
    f3 = ms.AddLine(cp(fx2, fy2), cp(fx1, fy2))
    f4 = ms.AddLine(cp(fx1, fy2), cp(fx1, fy1))

    for f in [f1, f2, f3, f4]:
        f.Color = 1
        f.Lineweight = 70

    print("\n[7] ЛЕГЕНДА ТА ШТАМП...")

    leg_x = bx+780000
    leg_y = by+975000

    ms.AddText("Умовні позначення:", cp(leg_x, leg_y), 7000)
    ms.AddText("МСВУ - силос металевий", cp(leg_x, leg_y-45000), 4500)
    ms.AddText("H - норія (bucket elevator)", cp(leg_x, leg_y-90000), 4500)
    ms.AddText("T - транспортер (conveyor)", cp(leg_x, leg_y-135000), 4500)
    ms.AddText("Продуктивність: 100 т/год", cp(leg_x, leg_y-180000), 4500)
    ms.AddText("Всього: 7 силосів, 6 норій, 12 конвеєрів", cp(leg_x, leg_y-225000), 4500)

    # Штамп
    sx = bx+570000
    sy = by-225000

    ms.AddText("Технологічна схема зберігання зерна", cp(sx, sy), 7000)
    ms.AddText("7 силосів МСВУ 220.13.В12", cp(sx, sy-60000), 5000)

    date_str = datetime.datetime.now().strftime("%d.%m.%Y")
    ms.AddText(f"Дата: {date_str}", cp(sx, sy-120000), 4000)
    ms.AddText("🤖 Generated with Claude Code", cp(sx, sy-180000), 3500)

    print(f"\n{'='*70}")
    print("✅ ВИПРАВЛЕНО! ПЕРЕВІР ЗАРАЗ!")
    print(f"{'='*70}")
    print(f"\n📊 Об'єктів: {ms.Count}")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
