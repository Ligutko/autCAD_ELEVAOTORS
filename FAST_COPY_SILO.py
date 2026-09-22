# -*- coding: utf-8 -*-
"""
ШВИДКЕ КОПІЮВАННЯ - без сканування всіх 47000 об'єктів
Використовує SelectionSet для швидкого пошуку
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client


def cp(*coords):
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


print('='*70)
print('ШВИДКЕ КОПІЮВАННЯ СИЛОСУ #6')
print('='*70)

acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace

print(f'\nФайл: {doc.Name}')
print(f'Всього об\'єктів: {ms.Count}')

# МЕТОД 1: Використати SelectByBox для вибірки тільки в області силосу #6
print('\n[1] Вибираю область силосу #6...')

# Очікувана область силосу #6 (приблизно)
min_point = cp(250, 30, 0)
max_point = cp(330, 70, 0)

# Створити selection set
try:
    ss = doc.SelectionSets.Add('TempSS')
except:
    # Якщо вже існує, видалити і створити знову
    try:
        doc.SelectionSets.Item('TempSS').Delete()
    except:
        pass
    ss = doc.SelectionSets.Add('TempSS')

# Вибрати об'єкти в рамці
ss.Select(5, min_point, max_point)  # 5 = acSelectionSetWindow

print(f'   Вибрано в області: {ss.Count} об\'єктів')

# Фільтрувати тільки сині
silo_objects = []

for i in range(ss.Count):
    obj = ss.Item(i)
    try:
        if hasattr(obj, 'Layer'):
            layer = obj.Layer
            if 'C00-00-FF' in layer or 'C00-00-00' in layer:
                silo_objects.append(obj)
    except:
        pass

print(f'   Синіх/чорних об\'єктів: {len(silo_objects)}')

ss.Delete()

if len(silo_objects) == 0:
    print('\n❌ Силос #6 не знайдено в цій області!')
    sys.exit(1)

# КОПІЮВАННЯ
print('\n[2] Копіюю силос #6 → #7...')

spacing = 47.75
copied = 0

for obj in silo_objects:
    try:
        new_obj = obj.Copy()
        new_obj.Move(cp(0, 0, 0), cp(spacing, 0, 0))
        copied += 1
    except:
        pass

print(f'   ✅ Скопійовано: {copied} об\'єктів')

# ЧЕРВОНІ ЛІНІЇ - теж через SelectionSet
print('\n[3] Копіюю червоні лінії...')

min_red = cp(250, 0, 0)
max_red = cp(350, 100, 0)

try:
    ss_red = doc.SelectionSets.Add('RedSS')
except:
    try:
        doc.SelectionSets.Item('RedSS').Delete()
    except:
        pass
    ss_red = doc.SelectionSets.Add('RedSS')

ss_red.Select(5, min_red, max_red)

copied_red = 0

for i in range(ss_red.Count):
    obj = ss_red.Item(i)
    try:
        if obj.ObjectName == 'AcDbLine' and hasattr(obj, 'Color') and obj.Color == 1:
            # Вертикальні лінії (норії)
            start = obj.StartPoint
            end = obj.EndPoint

            dy = abs(end[1] - start[1])
            dx = abs(end[0] - start[0])

            if dy > dx and dy > 20:
                new_line = obj.Copy()
                new_line.Move(cp(0, 0, 0), cp(spacing, 0, 0))
                copied_red += 1
    except:
        pass

ss_red.Delete()

print(f'   ✅ Скопійовано червоних ліній: {copied_red}')

# Regenerate
print('\n[4] Завершення...')
doc.Regen(1)
acad.ZoomExtents()

print('\n' + '='*70)
print('✅✅✅ ГОТОВО! ✅✅✅')
print('='*70)
print(f'\nОб\'єктів силосу: {copied}')
print(f'Червоних ліній: {copied_red}')
print('='*70)
