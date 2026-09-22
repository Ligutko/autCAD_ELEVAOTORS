# -*- coding: utf-8 -*-
"""
АНАЛІЗ ПОТОЧНОГО ВІДКРИТОГО ФАЙЛУ (page_01.dxf)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


print('='*70)
print('АНАЛІЗ ЕТАЛОНУ - page_01.dxf')
print('='*70)

acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace

print(f'\nПоточний файл: {doc.Name}')
print(f'Об\'єктів: {ms.Count}')

# КРОК 1: Знайти всі СИНІ об'єкти
print('\n[1] Шукаю всі СИНІ об\'єкти (силоси)...')

blue_objects = []

for i in range(ms.Count):
    try:
        obj = ms.Item(i)
        if hasattr(obj, 'Layer'):
            layer = obj.Layer
            if 'C00-00-FF' in layer:  # Синій
                if hasattr(obj, 'GetBoundingBox'):
                    try:
                        bbox = obj.GetBoundingBox()
                        min_p, max_p = bbox[0], bbox[1]

                        obj_info = {
                            'index': i,
                            'type': obj.ObjectName,
                            'layer': layer,
                            'min_x': round(min_p[0], 2),
                            'max_x': round(max_p[0], 2),
                            'min_y': round(min_p[1], 2),
                            'max_y': round(max_p[1], 2),
                            'center_x': round((min_p[0] + max_p[0]) / 2, 2),
                            'center_y': round((min_p[1] + max_p[1]) / 2, 2),
                            'width': round(max_p[0] - min_p[0], 2),
                            'height': round(max_p[1] - min_p[1], 2)
                        }

                        blue_objects.append(obj_info)
                    except:
                        pass
    except:
        pass

print(f'   Знайдено синіх об\'єктів: {len(blue_objects)}')

# КРОК 2: Кластеризація по силосах
print('\n[2] Групую по силосах...')

# Сортувати
blue_objects.sort(key=lambda o: (-o['center_y'], o['center_x']))

silos = []
tolerance = 35

for obj in blue_objects:
    found = False

    for silo in silos:
        dist = ((obj['center_x'] - silo['center_x'])**2 +
               (obj['center_y'] - silo['center_y'])**2)**0.5

        if dist < tolerance:
            silo['objects'].append(obj)
            found = True
            break

    if not found:
        silos.append({
            'center_x': obj['center_x'],
            'center_y': obj['center_y'],
            'objects': [obj]
        })

# Сортувати силоси (зверху-вниз, зліва-направо)
silos.sort(key=lambda s: (-s['center_y'], s['center_x']))

# Присвоїти номера
for idx, silo in enumerate(silos, 1):
    silo['number'] = idx

    # Bounds
    min_x = min(o['min_x'] for o in silo['objects'])
    max_x = max(o['max_x'] for o in silo['objects'])
    min_y = min(o['min_y'] for o in silo['objects'])
    max_y = max(o['max_y'] for o in silo['objects'])

    silo['bounds'] = {
        'min_x': round(min_x, 2),
        'max_x': round(max_x, 2),
        'min_y': round(min_y, 2),
        'max_y': round(max_y, 2)
    }
    silo['width'] = round(max_x - min_x, 2)
    silo['height'] = round(max_y - min_y, 2)

    print(f'   Силос #{idx}: x={silo["center_x"]:.2f}, y={silo["center_y"]:.2f}, '
          f'{silo["width"]:.2f}x{silo["height"]:.2f}мм, {len(silo["objects"])} об\'єктів')

# КРОК 3: Визначити еталонний силос (маленький #6)
print('\n[3] Визначаю еталонний силос...')

# Нижні силоси (3-6) - маленькі
bottom_silos = [s for s in silos if s['number'] >= 3]

if bottom_silos:
    template_silo = bottom_silos[-1]  # Останній = #6

    print(f'   ✅ Еталон: Силос #{template_silo["number"]}')
    print(f'   Розміри: {template_silo["width"]:.2f} x {template_silo["height"]:.2f} мм')
    print(f'   Центр: [{template_silo["center_x"]:.2f}, {template_silo["center_y"]:.2f}]')
    print(f'   Об\'єктів: {len(template_silo["objects"])}')

    # Показати типи об'єктів
    obj_types = {}
    for obj in template_silo['objects']:
        obj_type = obj['type']
        obj_types[obj_type] = obj_types.get(obj_type, 0) + 1

    print(f'   Типи об\'єктів:')
    for obj_type, count in obj_types.items():
        print(f'     - {obj_type}: {count}')

# КРОК 4: Аналіз червоних ліній
print('\n[4] Аналізую червоні з\'єднання...')

red_lines = []

for i in range(ms.Count):
    try:
        obj = ms.Item(i)
        if obj.ObjectName == 'AcDbLine':
            if hasattr(obj, 'Color') and obj.Color == 1:
                start = obj.StartPoint
                end = obj.EndPoint

                dx = abs(end[0] - start[0])
                dy = abs(end[1] - start[1])

                line_type = 'horizontal' if dx > dy else 'vertical'

                red_lines.append({
                    'type': line_type,
                    'start_x': round(start[0], 2),
                    'start_y': round(start[1], 2),
                    'end_x': round(end[0], 2),
                    'end_y': round(end[1], 2),
                    'length': round((dx**2 + dy**2)**0.5, 2)
                })
    except:
        pass

horizontal = [l for l in red_lines if l['type'] == 'horizontal']
vertical = [l for l in red_lines if l['type'] == 'vertical']

print(f'   Всього червоних ліній: {len(red_lines)}')
print(f'   Горизонтальних (конвеєри): {len(horizontal)}')
print(f'   Вертикальних (норії): {len(vertical)}')

if vertical:
    avg_height = sum(l['length'] for l in vertical) / len(vertical)
    print(f'   Середня висота норії: {avg_height:.2f} мм')

if horizontal:
    # Знайти Y конвеєрів
    conveyor_y_values = [l['start_y'] for l in horizontal] + [l['end_y'] for l in horizontal]
    avg_conveyor_y = sum(conveyor_y_values) / len(conveyor_y_values)
    print(f'   Y конвеєрів: ~{avg_conveyor_y:.2f} мм')

# КРОК 5: Зберегти еталон
print('\n[5] Зберігаю еталон...')

template_data = {
    'source_file': 'page_01.dxf',
    'total_silos': len(silos),
    'silos': silos,
    'template_silo': template_silo if bottom_silos else None,
    'red_lines': {
        'total': len(red_lines),
        'horizontal': len(horizontal),
        'vertical': len(vertical),
        'avg_elevator_height': round(sum(l['length'] for l in vertical) / len(vertical), 2) if vertical else 0,
        'conveyor_y': round(avg_conveyor_y, 2) if horizontal else 0
    }
}

output_file = 'd:/autocad project/SILO_TEMPLATE.json'

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(template_data, f, indent=2, ensure_ascii=False)

print(f'   ✅ Збережено: {output_file}')

print('\n' + '='*70)
print('✅✅✅ АНАЛІЗ ЗАВЕРШЕНО! ✅✅✅')
print('='*70)
print(f'\nВсього силосів: {len(silos)}')
print(f'Еталонний силос: #{template_silo["number"] if bottom_silos else "N/A"}')
print(f'Червоних ліній: {len(red_lines)}')
print('='*70)
