# -*- coding: utf-8 -*-
"""
ПОВНИЙ АНАЛІЗ page_01.dxf
Витягує ВСІ елементи: СИНІ, ЧЕРВОНІ, ЗЕЛЕНІ, ЧОРНІ
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json

print('='*70)
print('ПОВНИЙ АНАЛІЗ ОРИГІНАЛУ - ВСІ КОЛЬОРИ')
print('='*70)

acad = win32com.client.Dispatch('AutoCAD.Application')
doc = acad.ActiveDocument
ms = doc.ModelSpace

print(f'\nФайл: {doc.Name}')
print(f'Всього об\'єктів: {ms.Count}')

# Структура для збереження
all_elements = {
    'blue': [],    # Сині - силоси (C00-00-FF)
    'red': [],     # Червоні - з'єднання (CFF-00-00)
    'green': [],   # Зелені (якщо є)
    'black': [],   # Чорні (hatches)
    'other': []
}

print('\n[1] Сканую ВСІ об\'єкти...')

for i in range(ms.Count):
    if i % 500 == 0:
        print(f'    Прогрес: {i}/{ms.Count}...')

    try:
        obj = ms.Item(i)
        obj_type = obj.ObjectName

        # Базова інформація
        obj_info = {
            'index': i,
            'type': obj_type
        }

        # Layer
        if hasattr(obj, 'Layer'):
            obj_info['layer'] = obj.Layer

        # Color
        if hasattr(obj, 'Color'):
            obj_info['color'] = obj.Color

        # Bounding box
        if hasattr(obj, 'GetBoundingBox'):
            try:
                bbox = obj.GetBoundingBox()
                min_p, max_p = bbox[0], bbox[1]

                obj_info['bounds'] = {
                    'min_x': round(min_p[0], 2),
                    'min_y': round(min_p[1], 2),
                    'max_x': round(max_p[0], 2),
                    'max_y': round(max_p[1], 2)
                }
                obj_info['center_x'] = round((min_p[0] + max_p[0]) / 2, 2)
                obj_info['center_y'] = round((min_p[1] + max_p[1]) / 2, 2)
                obj_info['width'] = round(max_p[0] - min_p[0], 2)
                obj_info['height'] = round(max_p[1] - min_p[1], 2)
            except:
                pass

        # Для ліній - координати
        if obj_type == 'AcDbLine':
            try:
                start = obj.StartPoint
                end = obj.EndPoint
                obj_info['start'] = {
                    'x': round(start[0], 2),
                    'y': round(start[1], 2)
                }
                obj_info['end'] = {
                    'x': round(end[0], 2),
                    'y': round(end[1], 2)
                }
                obj_info['length'] = round(((end[0]-start[0])**2 + (end[1]-start[1])**2)**0.5, 2)

                # Тип лінії
                dx = abs(end[0] - start[0])
                dy = abs(end[1] - start[1])
                obj_info['line_type'] = 'horizontal' if dx > dy else 'vertical'
            except:
                pass

        # Визначити категорію по кольору
        category = 'other'

        if 'layer' in obj_info:
            layer = obj_info['layer']

            # Синій (силоси)
            if 'C00-00-FF' in layer or 'C0000FF' in layer or '0000FF' in layer:
                category = 'blue'

            # Червоний (з'єднання)
            elif 'CFF-00-00' in layer or 'CFF0000' in layer or 'FF0000' in layer:
                category = 'red'

            # Зелений
            elif 'C00-FF-00' in layer or 'C00FF00' in layer or '00FF00' in layer:
                category = 'green'

            # Чорний (hatches)
            elif 'C00-00-00' in layer or 'C000000' in layer or '000000' in layer:
                if obj_type == 'AcDbHatch':
                    category = 'black'

        # Також по Color
        if 'color' in obj_info:
            color = obj_info['color']
            if color == 1:  # Червоний
                category = 'red'
            elif color == 5:  # Синій
                category = 'blue'
            elif color == 3:  # Зелений
                category = 'green'

        all_elements[category].append(obj_info)

    except Exception as e:
        pass

print(f'    ✅ Сканування завершено!')

print('\n[2] Статистика по кольорах:')
print(f'    СИНІ (силоси):      {len(all_elements["blue"])}')
print(f'    ЧЕРВОНІ (з\'єднання): {len(all_elements["red"])}')
print(f'    ЗЕЛЕНІ:             {len(all_elements["green"])}')
print(f'    ЧОРНІ (hatches):    {len(all_elements["black"])}')
print(f'    ІНШІ:               {len(all_elements["other"])}')

# Аналіз синіх (силоси)
print('\n[3] Аналіз СИНІХ об\'єктів (силоси)...')

blue_objects = all_elements['blue']

# Кластеризація
silos = []
tolerance = 35

for obj in blue_objects:
    if 'center_x' not in obj:
        continue

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

# Сортувати силоси
silos.sort(key=lambda s: (-s['center_y'], s['center_x']))

for idx, silo in enumerate(silos, 1):
    silo['number'] = idx

    # Bounds
    objs_with_bounds = [o for o in silo['objects'] if 'bounds' in o]
    if objs_with_bounds:
        min_x = min(o['bounds']['min_x'] for o in objs_with_bounds)
        max_x = max(o['bounds']['max_x'] for o in objs_with_bounds)
        min_y = min(o['bounds']['min_y'] for o in objs_with_bounds)
        max_y = max(o['bounds']['max_y'] for o in objs_with_bounds)

        silo['bounds'] = {
            'min_x': round(min_x, 2),
            'max_x': round(max_x, 2),
            'min_y': round(min_y, 2),
            'max_y': round(max_y, 2)
        }
        silo['width'] = round(max_x - min_x, 2)
        silo['height'] = round(max_y - min_y, 2)

    print(f'    Силос #{idx}: x={silo["center_x"]:.2f}, y={silo["center_y"]:.2f}, '
          f'{silo.get("width", 0):.2f}x{silo.get("height", 0):.2f}мм, '
          f'{len(silo["objects"])} об\'єктів')

# Аналіз червоних (з'єднання)
print('\n[4] Аналіз ЧЕРВОНИХ об\'єктів (з\'єднання)...')

red_objects = all_elements['red']
red_lines = [obj for obj in red_objects if obj['type'] == 'AcDbLine' and 'start' in obj]

horizontal_lines = [l for l in red_lines if l.get('line_type') == 'horizontal']
vertical_lines = [l for l in red_lines if l.get('line_type') == 'vertical']

print(f'    Всього червоних ліній: {len(red_lines)}')
print(f'    Горизонтальних (конвеєри): {len(horizontal_lines)}')
print(f'    Вертикальних (норії): {len(vertical_lines)}')

if horizontal_lines:
    print(f'\n    Горизонтальні конвеєри:')
    for idx, line in enumerate(horizontal_lines, 1):
        print(f'      #{idx}: x={line["start"]["x"]:.2f}→{line["end"]["x"]:.2f}, '
              f'y={line["start"]["y"]:.2f}, довжина={line["length"]:.2f}мм')

if vertical_lines:
    print(f'\n    Вертикальні норії:')
    for idx, line in enumerate(vertical_lines, 1):
        print(f'      #{idx}: x={line["start"]["x"]:.2f}, '
              f'y={line["start"]["y"]:.2f}→{line["end"]["y"]:.2f}, '
              f'висота={line["length"]:.2f}мм')

# Зберегти ВСЕ
print('\n[5] Зберігаю повний аналіз...')

complete_data = {
    'source_file': doc.Name,
    'total_objects': ms.Count,
    'statistics': {
        'blue': len(all_elements['blue']),
        'red': len(all_elements['red']),
        'green': len(all_elements['green']),
        'black': len(all_elements['black']),
        'other': len(all_elements['other'])
    },
    'silos': silos,
    'red_connections': {
        'all_lines': red_lines,
        'horizontal': horizontal_lines,
        'vertical': vertical_lines
    },
    'all_elements': all_elements
}

output_file = 'd:/autocad project/COMPLETE_TEMPLATE.json'

with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(complete_data, f, indent=2, ensure_ascii=False)

print(f'    ✅ Збережено: {output_file}')

print('\n' + '='*70)
print('✅✅✅ ПОВНИЙ АНАЛІЗ ЗАВЕРШЕНО! ✅✅✅')
print('='*70)
print(f'\nСилосів: {len(silos)}')
print(f'Червоних ліній: {len(red_lines)}')
print(f'  - Конвеєрів: {len(horizontal_lines)}')
print(f'  - Норій: {len(vertical_lines)}')
print('\nВСЕ ЗАФІКСОВАНО З ОРИГІНАЛУ!')
print('='*70)
