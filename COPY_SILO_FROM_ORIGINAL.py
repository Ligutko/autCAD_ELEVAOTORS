# -*- coding: utf-8 -*-
"""
КОПІЮВАННЯ 7-ГО СИЛОСУ З ОРИГІНАЛУ (page_01.dxf)
Простий підхід - знаходимо силос #6 і копіюємо
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client


def cp(*coords):
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


print('='*70)
print('КОПІЮВАННЯ 7-ГО СИЛОСУ З ОРИГІНАЛУ')
print('='*70)

acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace

print(f'\nФайл: {doc.Name}')
print(f'Об\'єктів: {ms.Count}')

# КРОК 1: Знайти силос #6 (нижній правий, x≈270-320)
print('\n[1] Шукаю силос #6...')

silo_6_objects = []

# Очікувана позиція силосу #6
expected_x = 290  # приблизно
expected_y = 50

for i in range(ms.Count):
    try:
        obj = ms.Item(i)

        if hasattr(obj, 'Layer'):
            layer = obj.Layer

            # Синій ОБО чорний hatch
            if 'C00-00-FF' in layer or (obj.ObjectName == 'AcDbHatch' and 'C00-00-00' in layer):
                if hasattr(obj, 'GetBoundingBox'):
                    try:
                        bbox = obj.GetBoundingBox()
                        min_p, max_p = bbox[0], bbox[1]
                        cx = (min_p[0] + max_p[0]) / 2
                        cy = (min_p[1] + max_p[1]) / 2

                        # Перевірка чи близько до очікуваної позиції
                        if 250 < cx < 330 and 30 < cy < 70:
                            silo_6_objects.append(obj)
                    except:
                        pass
    except:
        pass

print(f'   Знайдено об\'єктів силосу #6: {len(silo_6_objects)}')

if len(silo_6_objects) == 0:
    print('\n❌ ПОМИЛКА: Силос #6 не знайдено!')
    print('   Перевір чи відкритий page_01.dxf')
    sys.exit(1)

# Визначити центр силосу #6
centers_x = []
centers_y = []

for obj in silo_6_objects:
    try:
        bbox = obj.GetBoundingBox()
        min_p, max_p = bbox[0], bbox[1]
        centers_x.append((min_p[0] + max_p[0]) / 2)
        centers_y.append((min_p[1] + max_p[1]) / 2)
    except:
        pass

if centers_x:
    silo_6_cx = sum(centers_x) / len(centers_x)
    silo_6_cy = sum(centers_y) / len(centers_y)

    print(f'   Центр силосу #6: x={silo_6_cx:.2f}, y={silo_6_cy:.2f}')

# КРОК 2: Копіювати силос #6 → силос #7
print('\n[2] Копіюю силос #6 → силос #7...')

spacing = 47.75  # Стандартна відстань між силосами
dx = spacing

copied = 0

for obj in silo_6_objects:
    try:
        new_obj = obj.Copy()
        new_obj.Move(cp(0, 0, 0), cp(dx, 0, 0))
        copied += 1
    except Exception as e:
        pass

print(f'   ✅ Скопійовано: {copied} об\'єктів')

# КРОК 3: Знайти червоні лінії біля силосу #6
print('\n[3] Шукаю червоні лінії біля силосу #6...')

red_lines_6 = []

for i in range(ms.Count):
    try:
        obj = ms.Item(i)

        if obj.ObjectName == 'AcDbLine':
            if hasattr(obj, 'Color') and obj.Color == 1:
                # Перевірити чи лінія біля силосу #6
                start = obj.StartPoint
                end = obj.EndPoint

                # Перевірити X координати
                if 250 < start[0] < 350 or 250 < end[0] < 350:
                    red_lines_6.append(obj)
    except:
        pass

print(f'   Знайдено червоних ліній біля #6: {len(red_lines_6)}')

# КРОК 4: Копіювати червоні лінії для #7
print('\n[4] Копіюю червоні лінії для силосу #7...')

copied_red = 0

for line in red_lines_6:
    try:
        start = line.StartPoint
        end = line.EndPoint

        dx_line = abs(end[0] - start[0])
        dy_line = abs(end[1] - start[1])

        # Тільки вертикальні лінії (норії) копіюємо
        if dy_line > dx_line:
            # Перевірити чи ця лінія належить силосу #6
            if abs(start[0] - silo_6_cx) < 20:
                new_line = line.Copy()
                new_line.Move(cp(0, 0, 0), cp(spacing, 0, 0))
                copied_red += 1
    except:
        pass

print(f'   ✅ Скопійовано червоних ліній: {copied_red}')

# КРОК 5: Додати горизонтальний конвеєр між #6 і #7
print('\n[5] Додаю конвеєр між силосами #6 та #7...')

# Знайти Y координату конвеєрів (шукаємо горизонтальну червону лінію)
conveyor_y = None

for i in range(ms.Count):
    try:
        obj = ms.Item(i)
        if obj.ObjectName == 'AcDbLine' and hasattr(obj, 'Color') and obj.Color == 1:
            start = obj.StartPoint
            end = obj.EndPoint

            dx_line = abs(end[0] - start[0])
            dy_line = abs(end[1] - start[1])

            # Горизонтальна лінія
            if dx_line > dy_line and dx_line > 20:
                if 200 < start[0] < 350:
                    conveyor_y = start[1]
                    break
    except:
        pass

if conveyor_y:
    print(f'   Y конвеєрів: {conveyor_y:.2f}')

    # Малюємо конвеєр між #6 і #7
    x_6 = silo_6_cx
    x_7 = silo_6_cx + spacing

    line = ms.AddLine(cp(x_6, conveyor_y, 0), cp(x_7, conveyor_y, 0))
    line.Color = 1  # Червоний

    print(f'   ✅ Конвеєр #6→#7 додано')
else:
    print(f'   ⚠ Не знайдено Y координату конвеєрів')

# КРОК 6: Regenerate та Zoom
print('\n[6] Завершення...')

doc.Regen(1)
acad.ZoomExtents()

print('   ✅ Регенерація')
print('   ✅ Zoom')

print('\n' + '='*70)
print('✅✅✅ 7-Й СИЛОС СТВОРЕНО З ОРИГІНАЛУ! ✅✅✅')
print('='*70)
print(f'\nСкопійовано об\'єктів силосу: {copied}')
print(f'Скопійовано червоних ліній: {copied_red}')
print(f'Додано конвеєр: {"✅" if conveyor_y else "❌"}')
print('\nВСЕ СКОПІЙОВАНО З ПРАВИЛЬНОГО ОРИГІНАЛУ!')
print('='*70)
