"""
МАЛЮВАННЯ 7-ГО СИЛОСУ З TEMPLATE
===================================

Використовує витягнуту геометрію силосу #6 з JSON
Малює точну копію з зміщенням вправо
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
print("    МАЛЮВАННЯ 7-ГО СИЛОСУ З TEMPLATE")
print("="*70)

# Завантаження геометрії силосу #6
template_path = Path(r"d:\autocad project\ANALYSIS_RESULTS\SILO_6_GEOMETRY.json")

print(f"\n[1] Завантаження template...")
print(f"    Файл: {template_path}")

with open(template_path, 'r', encoding='utf-8') as f:
    silo_6_geom = json.load(f)

print(f"    OK Завантажено")
print(f"    Ліній: {silo_6_geom['total_lines']}")
print(f"    Center: ({silo_6_geom['center']['x']:.2f}, {silo_6_geom['center']['y']:.2f})")
print(f"    Width: {silo_6_geom['dimensions']['width']:.2f}")
print(f"    Height: {silo_6_geom['dimensions']['height']:.2f}")

# Підключення до AutoCAD
print("\n[2] Підключення до AutoCAD...")

try:
    acad = win32com.client.Dispatch('AutoCAD.Application')
    doc = acad.ActiveDocument
    ms = doc.ModelSpace
    print(f"    OK Підключено")
    print(f"    Документ: {doc.Name}")
except Exception as e:
    print(f"    ПОМИЛКА: {e}")
    exit(1)

# Розрахунок зміщення для 7-го силосу
# Відстань між силосами (приблизно)
spacing = 47.75  # мм - середня відстань між силосами

# Зміщення = ширина силосу + spacing
offset_x = silo_6_geom['dimensions']['width'] + spacing

print(f"\n[3] Розрахунок позиції 7-го силосу...")
print(f"    Зміщення по X: {offset_x:.2f} мм")

new_center_x = silo_6_geom['center']['x'] + offset_x
new_center_y = silo_6_geom['center']['y']

print(f"    Новий центр: ({new_center_x:.2f}, {new_center_y:.2f})")

# Малювання ліній 7-го силосу
print(f"\n[4] Малювання {silo_6_geom['total_lines']} ліній...")

created_lines = []

for i, line_data in enumerate(silo_6_geom['lines'], 1):
    try:
        # Витягуємо координати
        start_x = line_data['start'][0]
        start_y = line_data['start'][1]
        end_x = line_data['end'][0]
        end_y = line_data['end'][1]

        # Застосовуємо зміщення
        new_start_x = start_x + offset_x
        new_start_y = start_y
        new_end_x = end_x + offset_x
        new_end_y = end_y

        # Малюємо лінію
        start_point = cp(new_start_x, new_start_y, 0)
        end_point = cp(new_end_x, new_end_y, 0)

        line = ms.AddLine(start_point, end_point)

        # Встановлюємо колір (синій)
        line.Color = 5  # 5 = синій

        created_lines.append(line)

        if i % 5 == 0:
            print(f"    Намальовано: {i}/{silo_6_geom['total_lines']}")

    except Exception as e:
        print(f"    Помилка при малюванні лінії {i}: {e}")

print(f"    OK Намальовано всіх ліній: {len(created_lines)}")

# Regenerate
print("\n[5] Regenerate та Zoom...")
try:
    doc.Regen(1)  # acActiveViewport
    acad.ZoomExtents()
    print("    OK")
except Exception as e:
    print(f"    Помилка: {e}")

print("\n" + "="*70)
print("    ГОТОВО! 7-Й СИЛОС НАМАЛЬОВАНИЙ!")
print("="*70)

print(f"\nРезультат:")
print(f"  - Намальовано ліній: {len(created_lines)}")
print(f"  - Позиція центру: ({new_center_x:.2f}, {new_center_y:.2f})")
print(f"  - Колір: СИНІЙ (Color = 5)")
print(f"\nПеревірте результат в AutoCAD!")
