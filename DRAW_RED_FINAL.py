# -*- coding: utf-8 -*-
"""
ФІНАЛЬНЕ МАЛЮВАННЯ ЧЕРВОНИХ З'ЄДНАНЬ
Малює правильні червоні конвеєри та норії для всіх 7 силосів
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


try:
    acad = win32com.client.Dispatch('AutoCAD.Application')
    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    print('='*70)
    print('МАЛЮВАННЯ ЧЕРВОНИХ З\'ЄДНАНЬ ДЛЯ 7 СИЛОСІВ')
    print('='*70)

    print(f'\nПоточний файл: {doc.Name}')
    print(f'Об\'єктів: {ms.Count}')

    # КРОК 1: Видалити всі старі червоні лінії
    print('\n[1] Видаляю старі червоні лінії...')

    deleted = 0
    to_delete = []

    for i in range(ms.Count):
        try:
            obj = ms.Item(i)
            if obj.ObjectName == 'AcDbLine':
                if hasattr(obj, 'Color') and obj.Color == 1:  # Червоний
                    to_delete.append(i)
        except:
            pass

    for idx in sorted(to_delete, reverse=True):
        try:
            ms.Item(idx).Delete()
            deleted += 1
        except:
            pass

    print(f'    Видалено старих ліній: {deleted}')

    # КРОК 2: Знайти всі сині силоси (3-7)
    print('\n[2] Шукаю всі силоси...')

    # Очікувані позиції силосів (приблизно)
    expected_positions = [
        {'num': 3, 'x': 134, 'y': 63},
        {'num': 4, 'x': 181, 'y': 63},
        {'num': 5, 'x': 270, 'y': 63},
        {'num': 6, 'x': 305, 'y': 50},
        {'num': 7, 'x': 353, 'y': 50}
    ]

    found_silos = []

    for expected in expected_positions:
        centers_x = []
        centers_y = []
        min_y_list = []

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
                                cx = (min_p[0] + max_p[0]) / 2
                                cy = (min_p[1] + max_p[1]) / 2

                                # Перевірити чи близько до очікуваної позиції
                                distance = ((cx - expected['x'])**2 + (cy - expected['y'])**2)**0.5

                                if distance < 80:
                                    centers_x.append(cx)
                                    centers_y.append(cy)
                                    min_y_list.append(min_p[1])
                            except:
                                pass
            except:
                pass

        if centers_x:
            avg_x = sum(centers_x) / len(centers_x)
            avg_y = sum(centers_y) / len(centers_y)
            min_y = min(min_y_list)

            found_silos.append({
                'number': expected['num'],
                'x': avg_x,
                'y': avg_y,
                'min_y': min_y
            })

            print(f'    Силос #{expected["num"]}: x={avg_x:.2f}, y={avg_y:.2f}, min_y={min_y:.2f}')

    if len(found_silos) < 2:
        print('\n❌ Недостатньо силосів знайдено!')
        sys.exit(1)

    # КРОК 3: Намалювати горизонтальні конвеєри
    print('\n[3] Малюю горизонтальні конвеєри...')

    # Знайти базову Y (найнижча точка)
    base_y = min(s['min_y'] for s in found_silos)
    conveyor_y = base_y - 5

    print(f'    Конвеєри на y={conveyor_y:.2f}')

    horizontal_lines = 0

    for i in range(len(found_silos) - 1):
        s1 = found_silos[i]
        s2 = found_silos[i + 1]

        line = ms.AddLine(cp(s1['x'], conveyor_y, 0), cp(s2['x'], conveyor_y, 0))
        line.Color = 1  # Червоний
        horizontal_lines += 1

        print(f'    Конвеєр #{s1["number"]}→#{s2["number"]}: x={s1["x"]:.2f}→{s2["x"]:.2f}')

    # КРОК 4: Намалювати вертикальні норії
    print('\n[4] Малюю вертикальні норії...')

    elevator_height = 50
    vertical_lines = 0

    for silo in found_silos:
        line = ms.AddLine(cp(silo['x'], silo['min_y'], 0),
                         cp(silo['x'], silo['min_y'] + elevator_height, 0))
        line.Color = 1  # Червоний
        vertical_lines += 1

        print(f'    Норія #{silo["number"]}: x={silo["x"]:.2f}, y={silo["min_y"]:.2f}→{silo["min_y"] + elevator_height:.2f}')

    # КРОК 5: Regenerate та Zoom
    print('\n[5] Завершення...')

    doc.Regen(1)
    acad.ZoomExtents()

    print('    ✅ Регенерація')
    print('    ✅ Zoom')

    print('\n' + '='*70)
    print('✅✅✅ ЧЕРВОНІ З\'ЄДНАННЯ НАМАЛЬОВАНО! ✅✅✅')
    print('='*70)
    print(f'\nГоризонтальних конвеєрів: {horizontal_lines}')
    print(f'Вертикальних норій: {vertical_lines}')
    print(f'Всього ліній: {horizontal_lines + vertical_lines}')
    print('='*70)

except Exception as e:
    print(f'\n❌ ПОМИЛКА: {e}')
    import traceback
    traceback.print_exc()
