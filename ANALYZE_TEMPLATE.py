# -*- coding: utf-8 -*-
"""
АНАЛІЗ ЕТАЛОНУ - Витягування точної геометрії силосу з page_01.dxf
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def analyze_silo_template(dxf_path):
    """Проаналізувати один силос і зберегти як еталон"""

    print('='*70)
    print('АНАЛІЗ ЕТАЛОНУ СИЛОСУ')
    print('='*70)

    # Відкрити файл
    acad = win32com.client.Dispatch('AutoCAD.Application')
    docs = acad.Documents

    # Закрити попередній
    try:
        acad.ActiveDocument.Close(False)
    except:
        pass

    print(f'\nВідкриваю: {dxf_path}')
    doc = docs.Open(dxf_path)
    acad.ActiveDocument = doc
    ms = doc.ModelSpace

    print(f'✅ Відкрито')
    print(f'   Об\'єктів: {ms.Count}')

    # Знайти всі СИНІ об'єкти (силоси)
    print('\n[1] Шукаю всі СИНІ об\'єкти...')

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
                                'min_x': min_p[0],
                                'max_x': max_p[0],
                                'min_y': min_p[1],
                                'max_y': max_p[1],
                                'center_x': (min_p[0] + max_p[0]) / 2,
                                'center_y': (min_p[1] + max_p[1]) / 2,
                                'width': max_p[0] - min_p[0],
                                'height': max_p[1] - min_p[1]
                            }

                            blue_objects.append(obj_info)
                        except:
                            pass
        except:
            pass

    print(f'   Знайдено синіх об\'єктів: {len(blue_objects)}')

    # Групувати по силосах (по центрах)
    print('\n[2] Групую по силосах...')

    # Сортувати по Y (зверху вниз) та X (зліва направо)
    blue_objects.sort(key=lambda o: (-o['center_y'], o['center_x']))

    # Кластеризація - знайти групи об'єктів (силоси)
    silos = []
    tolerance = 30  # мм

    for obj in blue_objects:
        # Знайти до якого силосу належить
        found_silo = False

        for silo in silos:
            # Перевірити чи близько до центру силосу
            dist = ((obj['center_x'] - silo['center_x'])**2 +
                   (obj['center_y'] - silo['center_y'])**2)**0.5

            if dist < tolerance:
                silo['objects'].append(obj)
                found_silo = True
                break

        if not found_silo:
            # Новий силос
            silos.append({
                'center_x': obj['center_x'],
                'center_y': obj['center_y'],
                'objects': [obj]
            })

    print(f'   Знайдено силосів: {len(silos)}')

    # Сортувати силоси по позиції
    silos.sort(key=lambda s: (-s['center_y'], s['center_x']))

    # Присвоїти номера
    for idx, silo in enumerate(silos, 1):
        silo['number'] = idx

        # Порахувати bounds силосу
        min_x = min(o['min_x'] for o in silo['objects'])
        max_x = max(o['max_x'] for o in silo['objects'])
        min_y = min(o['min_y'] for o in silo['objects'])
        max_y = max(o['max_y'] for o in silo['objects'])

        silo['bounds'] = {
            'min_x': min_x,
            'max_x': max_x,
            'min_y': min_y,
            'max_y': max_y
        }
        silo['width'] = max_x - min_x
        silo['height'] = max_y - min_y

        print(f'   Силос #{idx}: [{silo["center_x"]:.2f}, {silo["center_y"]:.2f}], '
              f'{silo["width"]:.2f}x{silo["height"]:.2f}мм, '
              f'{len(silo["objects"])} об\'єктів')

    # Вибрати ОДИН силос як еталон (наприклад, #3)
    print('\n[3] Вибираю еталонний силос...')

    # Силоси 3-6 - нижній ряд
    # Візьмемо силос #6 (останній маленький)
    template_silo = None

    for silo in silos:
        if 40 < silo['width'] < 50:  # Шукаємо маленький силос
            template_silo = silo
            break

    if not template_silo:
        # Якщо не знайшли маленький, візьмемо будь-який
        template_silo = silos[0]

    print(f'   Еталон: Силос #{template_silo["number"]}')
    print(f'   Розміри: {template_silo["width"]:.2f}x{template_silo["height"]:.2f}мм')
    print(f'   Об\'єктів: {len(template_silo["objects"])}')

    # Зберегти як еталон
    template_data = {
        'source_file': dxf_path,
        'template_silo': template_silo,
        'all_silos': silos
    }

    output_file = 'd:/autocad project/SILO_TEMPLATE.json'

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(template_data, f, indent=2, ensure_ascii=False)

    print(f'\n✅ Еталон збережено: {output_file}')

    # Аналіз червоних ліній
    print('\n[4] Аналізую червоні з\'єднання...')

    red_lines = []

    for i in range(ms.Count):
        try:
            obj = ms.Item(i)
            if obj.ObjectName == 'AcDbLine':
                if hasattr(obj, 'Color') and obj.Color == 1:  # Червоний
                    start = obj.StartPoint
                    end = obj.EndPoint

                    # Визначити тип: горизонтальна чи вертикальна
                    dx = abs(end[0] - start[0])
                    dy = abs(end[1] - start[1])

                    line_type = 'horizontal' if dx > dy else 'vertical'

                    red_lines.append({
                        'type': line_type,
                        'start_x': start[0],
                        'start_y': start[1],
                        'end_x': end[0],
                        'end_y': end[1],
                        'length': (dx**2 + dy**2)**0.5
                    })
        except:
            pass

    print(f'   Знайдено червоних ліній: {len(red_lines)}')

    horizontal = [l for l in red_lines if l['type'] == 'horizontal']
    vertical = [l for l in red_lines if l['type'] == 'vertical']

    print(f'   Горизонтальних: {len(horizontal)}')
    print(f'   Вертикальних: {len(vertical)}')

    if vertical:
        avg_height = sum(l['length'] for l in vertical) / len(vertical)
        print(f'   Середня висота норії: {avg_height:.2f}мм')

    print('\n' + '='*70)
    print('✅ АНАЛІЗ ЗАВЕРШЕНО!')
    print('='*70)


if __name__ == '__main__':
    dxf_path = 'd:/autocad project/FINAL_DXF_PERFECT_V7/page_01.dxf'
    analyze_silo_template(dxf_path)
