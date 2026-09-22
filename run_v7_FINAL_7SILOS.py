# -*- coding: utf-8 -*-
"""
V7 FINAL - 7 СИЛОСІВ МСВУ 220.13.В12
Розширення V6 з додаванням 7-го силосу
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import pythoncom

def cp(x, y, z=0):
    """Створити точку VARIANT для AutoCAD"""
    return win32com.client.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, [x, y, z])

def silo(ms, doc, x, y, d, h, num):
    """Намалювати силос (вид збоку)"""
    w = d  # Ширина = діаметр
    hw = w / 2

    # Циліндр (прямокутник)
    ms.AddLine(cp(x-hw, y), cp(x+hw, y))
    ms.AddLine(cp(x+hw, y), cp(x+hw, y+h))
    ms.AddLine(cp(x+hw, y+h), cp(x-hw, y+h))
    ms.AddLine(cp(x-hw, y+h), cp(x-hw, y))

    # Конус знизу (трикутник)
    cone_h = 3000
    ms.AddLine(cp(x-hw, y), cp(x, y-cone_h))
    ms.AddLine(cp(x, y-cone_h), cp(x+hw, y))

    # Купол зверху (дуга)
    dome_h = 2000
    arc = ms.AddArc(cp(x, y+h), dome_h, 0, 3.14159)

    # Мітка
    txt = ms.AddText(str(num), cp(x-1500, y+h/2), 4000)
    txt.Alignment = 4  # Middle center

    txt2 = ms.AddText("МСВУ 220.13.В12", cp(x-hw-1000, y+h+3000), 3000)

    # 7 виходів (стрілки)
    outlet_y = y - cone_h - 1000
    outlets = 7
    spacing = w / (outlets + 1)

    for i in range(1, outlets + 1):
        ox = x - hw + i * spacing
        arrow_x = ox
        arrow_y = outlet_y - 3000

        # Стрілка
        ms.AddLine(cp(ox, outlet_y), cp(arrow_x, arrow_y))
        ms.AddLine(cp(arrow_x, arrow_y), cp(arrow_x-400, arrow_y+1200))
        ms.AddLine(cp(arrow_x, arrow_y), cp(arrow_x+400, arrow_y+1200))

        # Колір стрілки
        if num <= 2:
            # Червоний для силосів 1-2
            ms.Item(ms.Count-1).Color = 1
            ms.Item(ms.Count-2).Color = 1
            ms.Item(ms.Count-3).Color = 1
        else:
            # Синій для силосів 3-7
            ms.Item(ms.Count-1).Color = 5
            ms.Item(ms.Count-2).Color = 5
            ms.Item(ms.Count-3).Color = 5

def noria(ms, doc, x, y, h, tag):
    """Намалювати норію"""
    w = 2000
    hw = w / 2

    # Вертикальна шахта
    ms.AddLine(cp(x-hw, y), cp(x+hw, y))
    ms.AddLine(cp(x+hw, y), cp(x+hw, y+h))
    ms.AddLine(cp(x+hw, y+h), cp(x-hw, y+h))
    ms.AddLine(cp(x-hw, y+h), cp(x-hw, y))

    # Мітка
    txt = ms.AddText(tag, cp(x-1000, y+h/2), 4000)
    txt.Alignment = 4

def conv(ms, doc, x1, y1, x2, y2, w, tag):
    """Намалювати конвеєр зі стрілкою"""
    # Паралельні лінії
    dx = x2 - x1
    dy = y2 - y1
    length = (dx**2 + dy**2)**0.5

    # Перпендикуляр
    px = -dy / length * w / 2
    py = dx / length * w / 2

    ms.AddLine(cp(x1+px, y1+py), cp(x2+px, y2+py))
    ms.AddLine(cp(x1-px, y1-py), cp(x2-px, y2-py))

    # Стрілка напрямку
    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2

    arrow_size = 800
    arrow_x = mx + (dx/length) * arrow_size
    arrow_y = my + (dy/length) * arrow_size

    ms.AddLine(cp(mx, my), cp(arrow_x, arrow_y))
    ms.AddLine(cp(arrow_x, arrow_y), cp(arrow_x-py*1.5, arrow_y-px*1.5))
    ms.AddLine(cp(arrow_x, arrow_y), cp(arrow_x+py*1.5, arrow_y+px*1.5))

    # Мітка
    txt = ms.AddText(tag, cp(mx-2000, my+2000), 3500)
    txt2 = ms.AddText("100 т/год", cp(mx-2000, my-1000), 2500)

def bunker(ms, doc, x, y, w, h, tag):
    """Намалювати бункер"""
    hw = w / 2

    # Прямокутник
    ms.AddLine(cp(x-hw, y), cp(x+hw, y))
    ms.AddLine(cp(x+hw, y), cp(x+hw, y+h))
    ms.AddLine(cp(x+hw, y+h), cp(x-hw, y+h))
    ms.AddLine(cp(x-hw, y+h), cp(x-hw, y))

    # Конус
    cone_h = h * 0.4
    ms.AddLine(cp(x-hw, y), cp(x, y-cone_h))
    ms.AddLine(cp(x, y-cone_h), cp(x+hw, y))

    # Мітка
    txt = ms.AddText(tag, cp(x-1000, y+h/2), 3500)
    txt.Alignment = 4

print("="*70)
print("V7 FINAL - 7 СИЛОСІВ МСВУ 220.13.В12")
print("="*70)

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    print(f"\n✓ З'єднання з AutoCAD")
    print(f"✓ Активний документ: {doc.Name}")

    # Базові координати
    bx, by = 5000, 5000

    print("\n📐 МАЛЮЄМО 7 СИЛОСІВ...")

    # СИЛОС 1 (20м, 21м висота)
    print("  1. Силос №1 (20м)")
    silo(ms, doc, bx+10000, by+30000, 20000, 21000, 1)

    # СИЛОС 2
    print("  2. Силос №2 (20м)")
    silo(ms, doc, bx+30000, by+30000, 20000, 21000, 2)

    # СИЛОС 3 (22м)
    print("  3. Силос №3 (22м)")
    silo(ms, doc, bx+15000, by+15000, 22000, 22000, 3)

    # СИЛОС 4
    print("  4. Силос №4 (22м)")
    silo(ms, doc, bx+37000, by+15000, 22000, 22000, 4)

    # СИЛОС 5
    print("  5. Силос №5 (22м)")
    silo(ms, doc, bx+20000, by+0, 22000, 22000, 5)

    # СИЛОС 6
    print("  6. Силос №6 (22м)")
    silo(ms, doc, bx+42000, by+0, 22000, 22000, 6)

    # СИЛОС 7 - НОВИЙ!
    print("  7. Силос №7 (22м) ← НОВИЙ!")
    silo(ms, doc, bx+64000, by+0, 22000, 22000, 7)

    print("\n🎡 МАЛЮЄМО НОРИЇ...")
    noria(ms, doc, bx+5000, by+5000, 38000, "H1")
    noria(ms, doc, bx-3000, by+5000, 33000, "H3")
    noria(ms, doc, bx+1000, by+43000, 35000, "H4")
    noria(ms, doc, bx+48000, by+5000, 36000, "H5")
    noria(ms, doc, bx+55000, by+5000, 34000, "H6")

    print("\n🚚 МАЛЮЄМО КОНВЕЄРИ...")
    # T7-T16 (з V6)
    conv(ms, doc, bx+3000, by+45000, bx+9000, by+45000, 1500, "T7")
    conv(ms, doc, bx+10000, by+51000, bx+30000, by+51000, 1500, "T8")
    conv(ms, doc, bx+6000, by+43000, bx+20000, by+51000, 1500, "T9")
    conv(ms, doc, bx+20000, by+25000, bx+25000, by+20000, 1500, "T10")
    conv(ms, doc, bx+25000, by+18000, bx+15000, by+36000, 1500, "T11")
    conv(ms, doc, bx+15000, by+36000, bx+37000, by+36000, 1500, "T12")
    conv(ms, doc, bx-2000, by+38000, bx+20000, by+20000, 1500, "T13")
    conv(ms, doc, bx+20000, by+20000, bx+42000, by+20000, 1500, "T14")

    # T15, T16 (з V6)
    conv(ms, doc, bx+42000, by+20000, bx+50000, by+20000, 1500, "T15")
    conv(ms, doc, bx+50000, by+16000, bx+50000, by+0, 1500, "T16")

    # T17 - НОВИЙ! (Силос 6 → Силос 7)
    print("  + T17 (НОВИЙ: Силос 6 → Силос 7)")
    conv(ms, doc, bx+53000, by+11000, bx+64000, by+11000, 1500, "T17")

    # T18 - НОВИЙ! (Силос 7 → Бункер 8.2)
    print("  + T18 (НОВИЙ: Силос 7 → Бункер 8.2)")
    conv(ms, doc, bx+75000, by+11000, bx+75000, by-5000, 1500, "T18")

    print("\n📦 МАЛЮЄМО БУНКЕРИ...")
    bunker(ms, doc, bx+52000, by+16000, 5000, 8000, "8.1")
    bunker(ms, doc, bx+75000, by-8000, 4000, 6000, "8.2")

    # Червона рамка (розширена)
    print("\n🔲 ЧЕРВОНА РАМКА...")
    frame_x1, frame_y1 = bx-10000, by-18000
    frame_x2, frame_y2 = bx+82000, by+80000  # Збільшена для 7 силосів

    frame1 = ms.AddLine(cp(frame_x1, frame_y1), cp(frame_x2, frame_y1))
    frame2 = ms.AddLine(cp(frame_x2, frame_y1), cp(frame_x2, frame_y2))
    frame3 = ms.AddLine(cp(frame_x2, frame_y2), cp(frame_x1, frame_y2))
    frame4 = ms.AddLine(cp(frame_x1, frame_y2), cp(frame_x1, frame_y1))
    frame1.Color = 1
    frame2.Color = 1
    frame3.Color = 1
    frame4.Color = 1
    frame1.Lineweight = 70
    frame2.Lineweight = 70
    frame3.Lineweight = 70
    frame4.Lineweight = 70

    # Легенда
    print("\n📋 ЛЕГЕНДА...")
    leg_x, leg_y = bx+52000, by+65000
    ms.AddText("Умовні позначення:", cp(leg_x, leg_y), 4000)
    ms.AddText("МСВУ - силос металевий", cp(leg_x, leg_y-3000), 2500)
    ms.AddText("H - норія (bucket elevator)", cp(leg_x, leg_y-6000), 2500)
    ms.AddText("T - транспортер (conveyor)", cp(leg_x, leg_y-9000), 2500)
    ms.AddText("Продуктивність: 100 т/год", cp(leg_x, leg_y-12000), 2500)
    ms.AddText("Всього: 7 силосів, 6 норій, 12 конвеєрів", cp(leg_x, leg_y-15000), 2500)

    # Штамп
    print("\n📅 ШТАМП...")
    sx, sy = bx+38000, by-15000
    ms.AddText("Технологічна схема зберігання зерна", cp(sx, sy), 4000)
    ms.AddText("7 силосів МСВУ 220.13.В12", cp(sx, sy-4000), 3000)

    import datetime
    date_str = datetime.datetime.now().strftime("%d.%m.%Y")
    ms.AddText(f"Дата: {date_str}", cp(sx, sy-8000), 2500)

    ms.AddText("🤖 Generated with Claude Code", cp(sx, sy-12000), 2000)

    print(f"\n{'='*70}")
    print("✅ V7 FINAL ЗАВЕРШЕНО!")
    print(f"{'='*70}")
    print("\n📊 СТАТИСТИКА:")
    print("  • Силоси: 7 (додано №7)")
    print("  • Норії: 6")
    print("  • Конвеєри: 12 (додано T17, T18)")
    print("  • Бункери: 2")
    print("  • Стрілки: 49 (7 силосів × 7 виходів)")
    print("\n✨ Система з 7 силосів готова!")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
