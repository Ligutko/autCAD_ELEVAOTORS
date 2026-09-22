# -*- coding: utf-8 -*-
"""
ПРАВИЛЬНЕ ДОДАВАННЯ 7-ГО СИЛОСУ - КОПІЮВАННЯ #6
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
    print('ПРАВИЛЬНЕ ДОДАВАННЯ 7-ГО СИЛОСУ - КОПІЮВАННЯ')
    print('='*70)

    # КРОК 1: Видалити той шмаття що я намалював
    print('\n[1] Видаляю неправильний 7-й силос...')

    deleted = 0
    to_delete = []

    for i in range(ms.Count):
        try:
            obj = ms.Item(i)
            # Знайти об'єкти поблизу x=353, y=50
            if hasattr(obj, 'GetBoundingBox'):
                try:
                    bbox = obj.GetBoundingBox()
                    min_p, max_p = bbox[0], bbox[1]
                    cx = (min_p[0] + max_p[0]) / 2
                    cy = (min_p[1] + max_p[1]) / 2

                    if 340 < cx < 370 and 40 < cy < 60:
                        to_delete.append(i)
                except:
                    pass
        except:
            pass

    # Видалити з кінця
    for idx in sorted(to_delete, reverse=True):
        try:
            obj = ms.Item(idx)
            obj.Delete()
            deleted += 1
        except:
            pass

    print(f'    Видалено: {deleted} обєктів')

    # КРОК 2: Знайти ВСІ об'єкти силосу #6
    print('\n[2] Шукаю ВСІ обєкти силосу #6...')

    silo_6_objects = []
    silo_6_center_x = 0
    silo_6_center_y = 0
    count = 0

    for i in range(ms.Count):
        try:
            obj = ms.Item(i)
            if hasattr(obj, 'Layer'):
                layer = obj.Layer
                # Синій layer АБО чорний hatch
                if 'C00-00-FF' in layer or (obj.ObjectName == 'AcDbHatch' and 'C00-00-00' in layer):
                    if hasattr(obj, 'GetBoundingBox'):
                        try:
                            bbox = obj.GetBoundingBox()
                            min_p, max_p = bbox[0], bbox[1]
                            cx = (min_p[0] + max_p[0]) / 2
                            cy = (min_p[1] + max_p[1]) / 2

                            # Силос #6 приблизно на x=305, y=50
                            if 280 < cx < 330 and 30 < cy < 70:
                                silo_6_objects.append(obj)
                                silo_6_center_x += cx
                                silo_6_center_y += cy
                                count += 1
                        except:
                            pass
        except:
            pass

    if count > 0:
        silo_6_center_x /= count
        silo_6_center_y /= count

    print(f'    Знайдено: {len(silo_6_objects)} обєктів силосу #6')
    print(f'    Центр #6: x={silo_6_center_x:.2f}, y={silo_6_center_y:.2f}')

    # КРОК 3: КОПІЮВАТИ всі об'єкти силосу #6
    print('\n[3] Копіюю силос #6...')

    # Відстань між силосами
    spacing = 47.75

    # Нова позиція для 7-го
    new_x_7 = silo_6_center_x + spacing
    new_y_7 = silo_6_center_y

    # Вектор переміщення
    dx = new_x_7 - silo_6_center_x
    dy = new_y_7 - silo_6_center_y

    print(f'    Нова позиція #7: x={new_x_7:.2f}, y={new_y_7:.2f}')
    print(f'    Вектор переміщення: dx={dx:.2f}, dy={dy:.2f}')

    copied = 0

    for obj in silo_6_objects:
        try:
            # Скопіювати обєкт
            new_obj = obj.Copy()

            # Перемістити на нову позицію
            new_obj.Move(cp(0, 0, 0), cp(dx, dy, 0))

            copied += 1
        except Exception as e:
            print(f'    Помилка копіювання: {e}')

    print(f'    Скопійовано: {copied} обєктів')

    # КРОК 4: Додати червоні лінії
    print('\n[4] Додаю червоні зєднання...')

    # Знайти мінімальну Y
    min_y = float('inf')
    for i in range(ms.Count):
        try:
            obj = ms.Item(i)
            if hasattr(obj, 'Layer'):
                layer = obj.Layer
                if 'C00-00-FF' in layer:
                    if hasattr(obj, 'GetBoundingBox'):
                        try:
                            bbox = obj.GetBoundingBox()
                            min_y = min(min_y, bbox[0][1])
                        except:
                            pass
        except:
            pass

    conveyor_y = min_y - 5

    # Конвеєр #6→#7
    line1 = ms.AddLine(cp(silo_6_center_x, conveyor_y, 0), cp(new_x_7, conveyor_y, 0))
    line1.Color = 1

    # Норія #7
    line2 = ms.AddLine(cp(new_x_7, min_y, 0), cp(new_x_7, min_y + 50, 0))
    line2.Color = 1

    print(f'    Конвеєр #6→#7 додано')
    print(f'    Норія #7 додана')

    # Regenerate
    doc.Regen(1)
    acad.ZoomExtents()

    print(f'\n{'='*70}')
    print('✅ 7-Й СИЛОС ПРАВИЛЬНО СКОПІЙОВАНО!')
    print(f'{'='*70}')

except Exception as e:
    print(f'\nPOMYLKA: {e}')
    import traceback
    traceback.print_exc()
