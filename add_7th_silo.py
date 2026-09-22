# -*- coding: utf-8 -*-
"""
ДОДАТИ 7-Й СИЛОС (маленький, масштаб 0.8)
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json


def cp(*coords):
    """Create COM-compatible coordinate array"""
    return win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8, coords)


try:
    acad = win32com.client.Dispatch('AutoCAD.Application')
    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    print('='*70)
    print('ДОДАВАННЯ 7-ГО СИЛОСУ (маленький)')
    print('='*70)

    # Завантажити базові дані
    with open('d:/autocad project/extracted_silos_REAL_ORIGINAL.json', 'r', encoding='utf-8') as f:
        silos_data = json.load(f)
    base_silos = silos_data['silos']

    # Базова ширина
    base_width = base_silos[0]['width']  # 58.76

    print(f'\nБазова ширина: {base_width:.2f} мм')

    # 7-й силос буде ПІСЛЯ силосу #6
    # Силос #6 знаходиться приблизно на x=317.82
    # Відстань між силосами ≈47мм

    silo_6 = base_silos[5]  # Силос #6

    # Параметри 7-го силосу
    scale_7 = 0.8  # МАЛЕНЬКИЙ (як #5 та #6)
    width_7 = base_width * scale_7
    spacing = 47.75  # Стандартна відстань

    x_7 = silo_6['center']['x'] + spacing
    y_7 = silo_6['center']['y']

    print(f'\n7-й СИЛОС:')
    print(f'  Позиція: x={x_7:.2f}, y={y_7:.2f}')
    print(f'  Масштаб: {scale_7}')
    print(f'  Очікувана ширина: {width_7:.2f} мм')

    # Знайти силос #6 в поточному кресленні (після масштабування)
    print(f'\nШукаю поточну позицію силосу #6...')

    min_x_6 = float('inf')
    max_x_6 = float('-inf')
    centers_x = []
    centers_y = []

    for i in range(ms.Count):
        try:
            obj = ms.Item(i)
            if hasattr(obj, 'Layer'):
                layer = obj.Layer
                if 'C00-00-FF' in layer:
                    if hasattr(obj, 'GetBoundingBox'):
                        try:
                            bbox = obj.GetBoundingBox()
                            min_p, max_p = bbox[0], bbox[1]
                            cx = (min_p[0] + max_p[0]) / 2
                            cy = (min_p[1] + max_p[1]) / 2

                            # Перевірити чи це силос #6 (приблизно x=317, y=63)
                            if 280 < cx < 350 and 40 < cy < 80:
                                min_x_6 = min(min_x_6, min_p[0])
                                max_x_6 = max(max_x_6, max_p[0])
                                centers_x.append(cx)
                                centers_y.append(cy)
                        except:
                            pass
        except:
            pass

    if len(centers_x) > 0:
        current_x_6 = sum(centers_x) / len(centers_x)
        current_y_6 = sum(centers_y) / len(centers_y)
        current_width_6 = max_x_6 - min_x_6

        print(f'  Силос #6: x={current_x_6:.2f}, y={current_y_6:.2f}, width={current_width_6:.2f}')

        # Позиція 7-го силосу
        new_x_7 = current_x_6 + spacing
        new_y_7 = current_y_6

        print(f'\nМалюю 7-й силос на x={new_x_7:.2f}, y={new_y_7:.2f}...')

        # Намалювати простий синій прямокутник (силос)
        half_width = width_7 / 2
        half_height = 38 / 2  # Приблизна висота

        # Координати прямокутника
        p1 = cp(new_x_7 - half_width, new_y_7 - half_height, 0)
        p2 = cp(new_x_7 + half_width, new_y_7 - half_height, 0)
        p3 = cp(new_x_7 + half_width, new_y_7 + half_height, 0)
        p4 = cp(new_x_7 - half_width, new_y_7 + half_height, 0)

        # Створити полілінію (LightWeightPolyline - тільки 2D координати!)
        points = win32com.client.VARIANT(win32com.client.pythoncom.VT_ARRAY | win32com.client.pythoncom.VT_R8,
                                        [new_x_7 - half_width, new_y_7 - half_height,
                                         new_x_7 + half_width, new_y_7 - half_height,
                                         new_x_7 + half_width, new_y_7 + half_height,
                                         new_x_7 - half_width, new_y_7 + half_height,
                                         new_x_7 - half_width, new_y_7 - half_height])

        pline = ms.AddLightWeightPolyline(points)
        pline.Color = 5  # Синій (ACI color 5)
        pline.ConstantWidth = 0.5  # Товщина лінії

        print(f'  ✅ Силос намальовано!')

        # Додати текст "МСВУ 220.13 В/2"
        text_obj = ms.AddText("МСВУ 220.13 В/2", cp(new_x_7 - 15, new_y_7, 0), 3)
        text_obj.Color = 7  # Білий

        print(f'  ✅ Текст додано!')

        # Regenerate
        doc.Regen(1)
        acad.ZoomExtents()

        print(f'\n{'='*70}')
        print('✅ 7-Й СИЛОС ДОДАНО!')
        print(f'{'='*70}')

    else:
        print('\n❌ Силос #6 не знайдено!')

except Exception as e:
    print(f'\nPOMYLKA: {e}')
    import traceback
    traceback.print_exc()
