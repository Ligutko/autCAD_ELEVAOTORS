# -*- coding: utf-8 -*-
"""
ШВИДКИЙ АНАЛІЗ - тільки СИНІ (силоси) + ЧЕРВОНІ (з'єднання)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json

print('='*70)
print('ШВИДКИЙ АНАЛІЗ - СИНІ + ЧЕРВОНІ')
print('='*70)

acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace

print(f'\nФайл: {doc.Name}')
print(f'Всього об\'єктів: {ms.Count}')

blue_objs = []
red_objs = []

print('\n[1] Сканую СИНІ об\'єкти...')

count = 0
for i in range(ms.Count):
    try:
        obj = ms.Item(i)

        # Перевірка синіх
        is_blue = False
        if hasattr(obj, 'Layer'):
            layer = obj.Layer
            if 'C00-00-FF' in layer or '0000FF' in layer:
                is_blue = True

        if is_blue and hasattr(obj, 'GetBoundingBox'):
            try:
                bbox = obj.GetBoundingBox()
                min_p, max_p = bbox[0], bbox[1]

                blue_objs.append({
                    'type': obj.ObjectName,
                    'cx': round((min_p[0] + max_p[0]) / 2, 2),
                    'cy': round((min_p[1] + max_p[1]) / 2, 2),
                    'min_x': round(min_p[0], 2),
                    'max_x': round(max_p[0], 2),
                    'min_y': round(min_p[1], 2),
                    'max_y': round(max_p[1], 2),
                    'w': round(max_p[0] - min_p[0], 2),
                    'h': round(max_p[1] - min_p[1], 2)
                })
                count += 1
            except:
                pass

    except:
        pass

print(f'   ✅ Синіх: {count}')

print('\n[2] Сканую ЧЕРВОНІ лінії...')

count = 0
for i in range(ms.Count):
    try:
        obj = ms.Item(i)

        if obj.ObjectName == 'AcDbLine':
            # Перевірка червоних
            is_red = False

            if hasattr(obj, 'Color') and obj.Color == 1:
                is_red = True
            elif hasattr(obj, 'Layer'):
                layer = obj.Layer
                if 'CFF-00-00' in layer or 'FF0000' in layer:
                    is_red = True

            if is_red:
                try:
                    start = obj.StartPoint
                    end = obj.EndPoint

                    dx = abs(end[0] - start[0])
                    dy = abs(end[1] - start[1])

                    red_objs.append({
                        'start_x': round(start[0], 2),
                        'start_y': round(start[1], 2),
                        'end_x': round(end[0], 2),
                        'end_y': round(end[1], 2),
                        'length': round((dx**2 + dy**2)**0.5, 2),
                        'type': 'horizontal' if dx > dy else 'vertical'
                    })
                    count += 1
                except:
                    pass

    except:
        pass

print(f'   ✅ Червоних: {count}')

# Кластеризація синіх
print('\n[3] Групую силоси...')

silos = []
for obj in blue_objs:
    found = False
    for silo in silos:
        dist = ((obj['cx'] - silo['cx'])**2 + (obj['cy'] - silo['cy'])**2)**0.5
        if dist < 35:
            silo['objs'].append(obj)
            found = True
            break

    if not found:
        silos.append({'cx': obj['cx'], 'cy': obj['cy'], 'objs': [obj]})

silos.sort(key=lambda s: (-s['cy'], s['cx']))

for idx, silo in enumerate(silos, 1):
    silo['num'] = idx

    min_x = min(o['min_x'] for o in silo['objs'])
    max_x = max(o['max_x'] for o in silo['objs'])
    min_y = min(o['min_y'] for o in silo['objs'])
    max_y = max(o['max_y'] for o in silo['objs'])

    silo['w'] = round(max_x - min_x, 2)
    silo['h'] = round(max_y - min_y, 2)

    print(f'   Силос #{idx}: x={silo["cx"]:.2f}, y={silo["cy"]:.2f}, '
          f'{silo["w"]:.2f}x{silo["h"]:.2f}мм, {len(silo["objs"])} об\'єктів')

# Розділити червоні
horizontal = [r for r in red_objs if r['type'] == 'horizontal']
vertical = [r for r in red_objs if r['type'] == 'vertical']

print(f'\n[4] Червоні лінії:')
print(f'   Горизонтальних (конвеєри): {len(horizontal)}')
print(f'   Вертикальних (норії): {len(vertical)}')

# Зберегти
data = {
    'file': doc.Name,
    'silos': silos,
    'red': {
        'horizontal': horizontal,
        'vertical': vertical
    }
}

output = 'd:/autocad project/QUICK_TEMPLATE.json'
with open(output, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f'\n✅ Збережено: {output}')
print('\n' + '='*70)
print('✅ ШВИДКИЙ АНАЛІЗ ЗАВЕРШЕНО!')
print('='*70)
