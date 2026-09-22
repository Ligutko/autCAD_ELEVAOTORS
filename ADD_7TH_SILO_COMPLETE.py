"""
ДОДАВАННЯ 7-ГО СИЛОСУ З ТРАСАМИ - ПОВНА ВЕРСІЯ
================================================

1. Копіюємо силос #6 (геометрію з JSON)
2. Додаємо ЧЕРВОНУ вертикальну норію
3. Додаємо ЧЕРВОНИЙ горизонтальний конвеєр між #6 та #7
"""

import win32com.client
import json
from pathlib import Path

def cp(*coords):
    """Створення COM-сумісної точки"""
    return win32com.client.VARIANT(
        win32com.client.pythoncom.VT_ARRAY |
        win32com.client.pythoncom.VT_R8,
        coords
    )

print("="*70)
print("    ДОДАВАННЯ 7-ГО СИЛОСУ З ТРАСАМИ")
print("="*70)

# 1. Завантаження геометрії силосу #6
print("\n[1] Завантаження template силосу #6...")
template_path = Path(r"d:\autocad project\ANALYSIS_RESULTS\SILO_6_GEOMETRY.json")

with open(template_path, 'r', encoding='utf-8') as f:
    silo_6_geom = json.load(f)

print(f"    OK Завантажено: {silo_6_geom['total_lines']} ліній")
print(f"    Center: ({silo_6_geom['center']['x']:.2f}, {silo_6_geom['center']['y']:.2f})")
print(f"    Width: {silo_6_geom['dimensions']['width']:.2f} мм")

# 2. Підключення до AutoCAD
print("\n[2] Підключення до AutoCAD...")
acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace
print(f"    OK Підключено: {doc.Name}")

# 3. Розрахунок позиції 7-го силосу
spacing = 47.75  # мм - стандартна відстань між силосами
offset_x = silo_6_geom['dimensions']['width'] + spacing

print(f"\n[3] Розрахунок позиції...")
print(f"    Зміщення по X: {offset_x:.2f} мм")

new_center_x = silo_6_geom['center']['x'] + offset_x
new_center_y = silo_6_geom['center']['y']

print(f"    Новий центр #7: ({new_center_x:.2f}, {new_center_y:.2f})")

# 4. Малювання СИНІХ ліній силосу #7
print(f"\n[4] Малювання силосу #7 ({silo_6_geom['total_lines']} ліній)...")

silo_7_lines = []

for i, line_data in enumerate(silo_6_geom['lines'], 1):
    try:
        # Координати з зміщенням
        new_start_x = line_data['start'][0] + offset_x
        new_start_y = line_data['start'][1]
        new_end_x = line_data['end'][0] + offset_x
        new_end_y = line_data['end'][1]

        # Малюємо лінію
        line = ms.AddLine(
            cp(new_start_x, new_start_y, 0),
            cp(new_end_x, new_end_y, 0)
        )

        # СИНІЙ колір
        line.Color = 5

        silo_7_lines.append(line)

    except Exception as e:
        print(f"    Помилка лінії {i}: {e}")

print(f"    OK Намальовано силос: {len(silo_7_lines)} ліній")

# 5. Завантаження даних про червоні з'єднання
print("\n[5] Аналіз червоних з'єднань з template...")

# Завантажуємо MASTER_TEMPLATE_V2.json щоб знайти червоні лінії силосу #6
master_path = Path(r"d:\autocad project\ANALYSIS_RESULTS\MASTER_TEMPLATE_V2.json")

with open(master_path, 'r', encoding='utf-8') as f:
    master_data = json.load(f)

red_vertical = master_data['red_connections']['vertical_elevators']
red_horizontal = master_data['red_connections']['horizontal_conveyors']

print(f"    Вертикальних (норії): {len(red_vertical)}")
print(f"    Горизонтальних (конвеєри): {len(red_horizontal)}")

# 6. Знаходимо норію силосу #6 (найближчу вертикальну лінію)
print("\n[6] Пошук норії силосу #6...")

# Шукаємо вертикальні лінії близько до центру силосу #6
silo_6_center_x = silo_6_geom['center']['x']
silo_6_elevators = []

for v_line in red_vertical:
    line_x = (v_line['start'][0] + v_line['end'][0]) / 2

    # Якщо лінія в межах силосу #6 (±50мм від центру)
    if abs(line_x - silo_6_center_x) < 50:
        silo_6_elevators.append(v_line)

if silo_6_elevators:
    # Беремо першу знайдену норію
    ref_elevator = silo_6_elevators[0]

    elevator_height = ref_elevator['length']
    elevator_bottom_y = min(ref_elevator['start'][1], ref_elevator['end'][1])
    elevator_top_y = max(ref_elevator['start'][1], ref_elevator['end'][1])

    print(f"    OK Знайдено норію #6:")
    print(f"       Висота: {elevator_height:.2f} мм")
    print(f"       Y низ: {elevator_bottom_y:.2f}, Y верх: {elevator_top_y:.2f}")

    # 7. Малюємо норію для силосу #7
    print("\n[7] Малювання норії для силосу #7...")

    # Норія по центру нового силосу
    elevator_7_x = new_center_x

    elevator_7 = ms.AddLine(
        cp(elevator_7_x, elevator_bottom_y, 0),
        cp(elevator_7_x, elevator_top_y, 0)
    )
    elevator_7.Color = 1  # ЧЕРВОНИЙ

    print(f"    OK Норія #7: ({elevator_7_x:.2f}, {elevator_bottom_y:.2f}) -> ({elevator_7_x:.2f}, {elevator_top_y:.2f})")
else:
    print("    УВАГА: Норію #6 не знайдено, використую стандартні параметри")

    # Стандартна висота норії
    elevator_height = 50
    elevator_bottom_y = silo_6_geom['bounds']['min_y'] - 5
    elevator_top_y = elevator_bottom_y + elevator_height
    elevator_7_x = new_center_x

    elevator_7 = ms.AddLine(
        cp(elevator_7_x, elevator_bottom_y, 0),
        cp(elevator_7_x, elevator_top_y, 0)
    )
    elevator_7.Color = 1

# 8. Знаходимо горизонтальний конвеєр (найнижчу горизонтальну лінію)
print("\n[8] Пошук горизонтального конвеєра...")

# Шукаємо найнижчу горизонтальну лінію
if red_horizontal:
    lowest_conveyor = min(red_horizontal, key=lambda l: min(l['start'][1], l['end'][1]))
    conveyor_y = lowest_conveyor['start'][1]

    print(f"    OK Знайдено конвеєр на Y = {conveyor_y:.2f}")

    # 9. Малюємо конвеєр між силосом #6 та #7
    print("\n[9] Малювання конвеєра між #6 та #7...")

    # Конвеєр від центру #6 до центру #7
    conveyor_start_x = silo_6_center_x
    conveyor_end_x = new_center_x

    conveyor = ms.AddLine(
        cp(conveyor_start_x, conveyor_y, 0),
        cp(conveyor_end_x, conveyor_y, 0)
    )
    conveyor.Color = 1  # ЧЕРВОНИЙ

    print(f"    OK Конвеєр: ({conveyor_start_x:.2f}, {conveyor_y:.2f}) -> ({conveyor_end_x:.2f}, {conveyor_y:.2f})")
    print(f"    Довжина: {conveyor_end_x - conveyor_start_x:.2f} мм")
else:
    print("    УВАГА: Конвеєри не знайдено, малюю на стандартній позиції")

    conveyor_y = silo_6_geom['bounds']['min_y'] - 10

    conveyor = ms.AddLine(
        cp(silo_6_center_x, conveyor_y, 0),
        cp(new_center_x, conveyor_y, 0)
    )
    conveyor.Color = 1

# 10. Regenerate та Zoom
print("\n[10] Завершення...")
doc.Regen(1)
acad.ZoomExtents()

print("\n" + "="*70)
print("    ГОТОВО! СИЛОС #7 ДОДАНО З ТРАСАМИ!")
print("="*70)

print(f"\nРезультат:")
print(f"  ✓ Силос #7: {len(silo_7_lines)} синіх ліній")
print(f"  ✓ Норія #7: 1 червона вертикальна лінія")
print(f"  ✓ Конвеєр #6→#7: 1 червона горизонтальна лінія")
print(f"\nВсього додано: {len(silo_7_lines) + 2} об'єктів")
print(f"\nПеревір результат в AutoCAD!")
