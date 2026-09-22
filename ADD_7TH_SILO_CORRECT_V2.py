"""
ДОДАВАННЯ 7-ГО СИЛОСУ - ПРАВИЛЬНА ВЕРСІЯ V2
============================================

Знаходить силос #6 БЕЗПОСЕРЕДНЬО в поточному файлі AutoCAD
і копіює його на правильну позицію
"""

import win32com.client

def cp(*coords):
    return win32com.client.VARIANT(
        win32com.client.pythoncom.VT_ARRAY |
        win32com.client.pythoncom.VT_R8,
        coords
    )

print("="*70)
print("    ДОДАВАННЯ 7-ГО СИЛОСУ - ПРАВИЛЬНА ВЕРСІЯ")
print("="*70)

# Підключення
print("\n[1] Підключення до AutoCAD...")
acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace
print(f"    OK Документ: {doc.Name}")
print(f"    Об'єктів: {ms.Count}")

# Знаходимо ВСІ сині лінії (Color=5 або layer RGB_000_000_255)
print("\n[2] Пошук СИНІХ ліній (силоси)...")

blue_lines = []
for i in range(ms.Count):
    try:
        obj = ms.Item(i)

        # Перевірка: синій колір АБО синій layer
        is_blue = False
        if hasattr(obj, 'Color') and obj.Color == 5:
            is_blue = True
        if hasattr(obj, 'Layer') and 'RGB_000_000_255' in obj.Layer:
            is_blue = True

        if is_blue and 'Line' in obj.EntityName:
            start = obj.StartPoint
            blue_lines.append({
                'obj': obj,
                'index': i,
                'start_x': start[0],
                'start_y': start[1],
                'end_x': obj.EndPoint[0],
                'end_y': obj.EndPoint[1]
            })
    except:
        pass

    if (i % 5000 == 0):
        print(f"    Оброблено: {i}/{ms.Count}")

print(f"    OK Знайдено синіх ліній: {len(blue_lines)}")

# Групуємо по X позиції (силоси стоять в ряд)
print("\n[3] Групування по силосах...")

# Сортуємо по X
blue_lines_sorted = sorted(blue_lines, key=lambda l: l['start_x'])

# Знаходимо групи (відстань між силосами > 30мм)
groups = []
threshold = 30

if blue_lines_sorted:
    current_group = [blue_lines_sorted[0]]
    current_x = blue_lines_sorted[0]['start_x']

    for line in blue_lines_sorted[1:]:
        if abs(line['start_x'] - current_x) < threshold:
            current_group.append(line)
        else:
            groups.append(current_group)
            current_group = [line]
            current_x = line['start_x']

    groups.append(current_group)

print(f"    OK Знайдено груп (силосів): {len(groups)}")

# Показуємо інфо про кожну групу
print("\n[4] Інформація про групи:")
for i, group in enumerate(groups, 1):
    xs = [l['start_x'] for l in group]
    ys = [l['start_y'] for l in group]

    center_x = (min(xs) + max(xs)) / 2
    center_y = (min(ys) + max(ys)) / 2
    width = max(xs) - min(xs)

    print(f"    Група #{i}: {len(group)} ліній, Center=({center_x:.1f}, {center_y:.1f}), Width={width:.1f}")

# Силос #6 - це КРАЙНІЙ ПРАВИЙ з нижнього ряду
# Беремо групу з найбільшою X координатою серед маленьких (width < 200)
bottom_groups = [(i, g) for i, g in enumerate(groups, 1) if len(g) > 10]  # Мінімум 10 ліній

if not bottom_groups:
    print("\n    ПОМИЛКА: Не знайдено груп з достатньою кількістю ліній!")
    exit(1)

# Сортуємо по X (беремо найправіший)
bottom_groups_sorted = sorted(bottom_groups, key=lambda x: max(l['start_x'] for l in x[1]))
silo_6_index, silo_6_group = bottom_groups_sorted[-1]

print(f"\n[5] Силос #6 - це група #{silo_6_index} ({len(silo_6_group)} ліній)")

# Рахуємо параметри силосу #6
xs_6 = [l['start_x'] for l in silo_6_group] + [l['end_x'] for l in silo_6_group]
ys_6 = [l['start_y'] for l in silo_6_group] + [l['end_y'] for l in silo_6_group]

min_x_6 = min(xs_6)
max_x_6 = max(xs_6)
min_y_6 = min(ys_6)
max_y_6 = max(ys_6)
center_x_6 = (min_x_6 + max_x_6) / 2
center_y_6 = (min_y_6 + max_y_6) / 2
width_6 = max_x_6 - min_x_6
height_6 = max_y_6 - min_y_6

print(f"    Center: ({center_x_6:.2f}, {center_y_6:.2f})")
print(f"    Width: {width_6:.2f}, Height: {height_6:.2f}")
print(f"    Bounds: X=[{min_x_6:.2f}, {max_x_6:.2f}], Y=[{min_y_6:.2f}, {max_y_6:.2f}]")

# Розрахунок зміщення для силосу #7
spacing = 50  # Відстань між силосами
offset_x = width_6 + spacing

print(f"\n[6] Розрахунок позиції силосу #7...")
print(f"    Зміщення по X: {offset_x:.2f} мм")

new_center_x = center_x_6 + offset_x
new_center_y = center_y_6

print(f"    Новий центр: ({new_center_x:.2f}, {new_center_y:.2f})")

# Копіюємо ВСІ лінії силосу #6
print(f"\n[7] Копіювання {len(silo_6_group)} ліній силосу #6...")

copied_lines = []

for i, line_data in enumerate(silo_6_group, 1):
    try:
        obj = line_data['obj']

        # Координати зі зміщенням
        new_start_x = line_data['start_x'] + offset_x
        new_start_y = line_data['start_y']
        new_end_x = line_data['end_x'] + offset_x
        new_end_y = line_data['end_y']

        # Малюємо нову лінію
        new_line = ms.AddLine(
            cp(new_start_x, new_start_y, 0),
            cp(new_end_x, new_end_y, 0)
        )

        # Копіюємо колір
        new_line.Color = obj.Color

        copied_lines.append(new_line)

    except Exception as e:
        print(f"    Помилка лінії {i}: {e}")

print(f"    OK Скопійовано: {len(copied_lines)} ліній")

# Знаходимо ЧЕРВОНІ лінії (норії та конвеєри)
print("\n[8] Пошук ЧЕРВОНИХ ліній (траси)...")

red_lines = []
for i in range(ms.Count):
    try:
        obj = ms.Item(i)

        is_red = False
        if hasattr(obj, 'Color') and obj.Color == 1:
            is_red = True
        if hasattr(obj, 'Layer') and 'RGB_255_000_000' in obj.Layer:
            is_red = True

        if is_red and 'Line' in obj.EntityName:
            start = obj.StartPoint
            end = obj.EndPoint

            dx = abs(end[0] - start[0])
            dy = abs(end[1] - start[1])

            red_lines.append({
                'obj': obj,
                'start_x': start[0],
                'start_y': start[1],
                'end_x': end[0],
                'end_y': end[1],
                'type': 'vertical' if dy > dx else 'horizontal',
                'length': max(dx, dy)
            })
    except:
        pass

vertical_lines = [l for l in red_lines if l['type'] == 'vertical']
horizontal_lines = [l for l in red_lines if l['type'] == 'horizontal']

print(f"    OK Червоних ліній: {len(red_lines)}")
print(f"       Вертикальних (норії): {len(vertical_lines)}")
print(f"       Горизонтальних (конвеєри): {len(horizontal_lines)}")

# Знаходимо норію силосу #6 (вертикальну лінію близько до центру)
print("\n[9] Пошук норії силосу #6...")

silo_6_elevator = None
for v_line in vertical_lines:
    line_x = (v_line['start_x'] + v_line['end_x']) / 2

    # Якщо лінія в межах силосу #6
    if min_x_6 <= line_x <= max_x_6:
        silo_6_elevator = v_line
        break

if silo_6_elevator:
    print(f"    OK Знайдено норію #6")

    # Малюємо норію для силосу #7
    print("\n[10] Малювання норії для силосу #7...")

    new_elevator = ms.AddLine(
        cp(new_center_x, silo_6_elevator['start_y'], 0),
        cp(new_center_x, silo_6_elevator['end_y'], 0)
    )
    new_elevator.Color = 1

    print(f"    OK Норія намальована")
else:
    print("    УВАГА: Норію не знайдено")

# Знаходимо нижній конвеєр
if horizontal_lines:
    lowest_conveyor = min(horizontal_lines, key=lambda l: min(l['start_y'], l['end_y']))
    conveyor_y = lowest_conveyor['start_y']

    print(f"\n[11] Малювання конвеєра між #6 та #7...")
    print(f"    Y конвеєра: {conveyor_y:.2f}")

    new_conveyor = ms.AddLine(
        cp(center_x_6, conveyor_y, 0),
        cp(new_center_x, conveyor_y, 0)
    )
    new_conveyor.Color = 1

    print(f"    OK Конвеєр намальований")

# Regenerate
print("\n[12] Завершення...")
doc.Regen(1)
acad.ZoomExtents()

print("\n" + "="*70)
print("    ГОТОВО! СИЛОС #7 ДОДАНО!")
print("="*70)

print(f"\nРезультат:")
print(f"  - Силос #7: {len(copied_lines)} синіх ліній")
print(f"  - Норія #7: 1 червона лінія")
print(f"  - Конвеєр: 1 червона лінія")
print(f"\nВсього додано: {len(copied_lines) + 2} об'єктів")
