# -*- coding: utf-8 -*-
"""
АВТОМАТИЧНЕ ВИТЯГУВАННЯ 6 СИЛОСІВ З web_temp.dxf
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import win32com.client
import json

print("="*70)
print("АВТОМАТИЧНЕ ВИТЯГУВАННЯ 6 СИЛОСІВ")
print("="*70)

try:
    acad = win32com.client.Dispatch("AutoCAD.Application")
    doc = acad.ActiveDocument
    ms = doc.ModelSpace

    print(f"\n📄 Документ: {doc.Name}")
    print(f"📊 Об'єктів: {ms.Count}")

    # КРОК 1: Знайти всі СИНІ полілінії
    print("\n[1] ПОШУК СИНІХ ПОЛІЛІНІÏ...")

    blue_polylines = []

    for i in range(ms.Count):
        try:
            obj = ms.Item(i)

            # Синій колір = 5 (ACI)
            is_blue = False

            if hasattr(obj, 'Color') and obj.Color == 5:
                is_blue = True

            # АБО шар з "blue" в назві
            if hasattr(obj, 'Layer'):
                layer_name = obj.Layer.lower()
                if 'blue' in layer_name or '00-00-ff' in layer_name:
                    is_blue = True

            if is_blue and obj.ObjectName in ['AcDbPolyline', 'AcDb2dPolyline', 'AcDbLWPolyline']:
                blue_polylines.append({
                    'object': obj,
                    'index': i
                })

        except:
            pass

    print(f"    ✓ Знайдено синіх полілініЇ: {len(blue_polylines)}")

    # КРОК 2: Витягти bounds кожної полілінії
    print("\n[2] ВИТЯГУВАННЯ ГРАНИЦЬ...")

    polyline_bounds = []

    for idx, pline_info in enumerate(blue_polylines):
        try:
            obj = pline_info['object']

            # Отримати bounding box
            min_point = obj.GetBoundingBox()[0]  # (min_x, min_y, min_z)
            max_point = obj.GetBoundingBox()[1]  # (max_x, max_y, max_z)

            min_x, min_y = min_point[0], min_point[1]
            max_x, max_y = max_point[0], max_point[1]

            width = max_x - min_x
            height = max_y - min_y
            area = width * height

            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2

            polyline_bounds.append({
                'index': pline_info['index'],
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y,
                'width': width,
                'height': height,
                'area': area,
                'center_x': center_x,
                'center_y': center_y
            })

        except Exception as e:
            pass

    print(f"    ✓ Опрацьовано: {len(polyline_bounds)}")

    # КРОК 3: Знайти 6 НАЙБІЛЬШИХ прямокутників
    print("\n[3] ПОШУК 6 СИЛОСІВ (найбільші прямокутники)...")

    # Фільтр: ширина > 50, висота > 50 (силоси достатньо великі)
    candidates = [
        pb for pb in polyline_bounds
        if pb['width'] > 50 and pb['height'] > 50
    ]

    print(f"    • Кандидатів (width>50, height>50): {len(candidates)}")

    # Сортуємо по площі (найбільші = силоси)
    candidates.sort(key=lambda x: x['area'], reverse=True)

    # Топ-6
    top_6 = candidates[:6]

    print(f"    ✓ Топ-6 найбільших:")
    for idx, c in enumerate(top_6, 1):
        print(f"       {idx}. Центр: [{c['center_x']:.1f}, {c['center_y']:.1f}], "
              f"Розмір: {c['width']:.1f}×{c['height']:.1f}, Площа: {c['area']:.0f}")

    # КРОК 4: Сортувати по позиції (зверху-вниз, зліва-направо)
    print("\n[4] СОРТУВАННЯ ПО ПОЗИЦІЇ...")

    # Спочатку по Y (зверху вниз), потім по X (зліва направо)
    top_6.sort(key=lambda x: (-x['center_y'], x['center_x']))

    silos_data = []

    for idx, silo in enumerate(top_6, 1):
        silos_data.append({
            'number': idx,
            'center': {
                'x': round(silo['center_x'], 2),
                'y': round(silo['center_y'], 2)
            },
            'width': round(silo['width'], 2),
            'height': round(silo['height'], 2),
            'bounds': {
                'min_x': round(silo['min_x'], 2),
                'max_x': round(silo['max_x'], 2),
                'min_y': round(silo['min_y'], 2),
                'max_y': round(silo['max_y'], 2)
            }
        })

        print(f"    Силос #{idx}: Центр [{silo['center_x']:.1f}, {silo['center_y']:.1f}]")

    # КРОК 5: Зберегти в JSON
    print("\n[5] ЗБЕРЕЖЕННЯ В JSON...")

    output = {
        'source_file': 'web_temp...dxf',
        'extraction_method': 'automatic',
        'silos_count': len(silos_data),
        'silos': silos_data,
        'metadata': {
            'total_blue_polylines': len(blue_polylines),
            'candidates_found': len(candidates),
            'selected_top': 6
        }
    }

    output_path = "d:/autocad project/extracted_silos_AUTO.json"

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"    ✓ Збережено: {output_path}")

    print(f"\n{'='*70}")
    print("✅ ВИТЯГНУТО 6 СИЛОСІВ АВТОМАТИЧНО!")
    print(f"{'='*70}")

    print("\n📊 РЕЗУЛЬТАТ:")
    for silo in silos_data:
        print(f"   Силос {silo['number']}: "
              f"[{silo['center']['x']}, {silo['center']['y']}] "
              f"{silo['width']}×{silo['height']}")

except Exception as e:
    print(f"\n❌ ПОМИЛКА: {e}")
    import traceback
    traceback.print_exc()
