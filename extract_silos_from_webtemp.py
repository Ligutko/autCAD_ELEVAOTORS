# -*- coding: utf-8 -*-
"""
ВИТЯГУВАННЯ СИЛОСІВ з web_temp DXF
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import ezdxf
import json
from collections import defaultdict

print("="*70)
print("ВИТЯГУВАННЯ СИЛОСІВ З web_temp.dxf")
print("="*70)

dxf_path = "d:/autocad project/FINAL_DXF_PERFECT_V7/web_temp_adde8b6cfc43a61f00a8d5a90c2e670a_32945ae7236018cb9c5201d70b32a84c_o.dxf"

doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

# Знайти прямокутники (силоси на схемі)
print("\n[1] ПОШУК ПРЯМОКУТНИКІВ (силоси)...")

polylines = [e for e in msp if e.dxftype() in ['LWPOLYLINE', 'POLYLINE']]
print(f"    Всього полілініій: {len(polylines)}")

def is_rectangle(pline):
    """Перевірка чи полілінія - прямокутник"""
    try:
        if hasattr(pline, 'vertices'):
            vertices = list(pline.vertices)
        elif hasattr(pline, 'get_points'):
            vertices = list(pline.get_points())
        else:
            return False

        # Прямокутник має 4-5 вершин (5-та = перша для замикання)
        if len(vertices) < 4 or len(vertices) > 5:
            return False

        # Перевірка що це прямокутник (4 прямі кути)
        return True

    except:
        return False

def get_bounds(pline):
    """Отримати границі полілінії"""
    try:
        if hasattr(pline, 'vertices'):
            points = [(v.dxf.location.x, v.dxf.location.y) for v in pline.vertices]
        else:
            points = list(pline.get_points())

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        return {
            'min_x': min(xs),
            'max_x': max(xs),
            'min_y': min(ys),
            'max_y': max(ys),
            'width': max(xs) - min(xs),
            'height': max(ys) - min(ys),
            'center_x': (min(xs) + max(xs)) / 2,
            'center_y': (min(ys) + max(ys)) / 2
        }
    except:
        return None

# Шукаємо прямокутники
rectangles = []

for pline in polylines:
    try:
        bounds = get_bounds(pline)

        if bounds and bounds['width'] > 10 and bounds['height'] > 10:
            # Це достатньо великий прямокутник
            rectangles.append({
                'bounds': bounds,
                'layer': pline.dxf.layer if hasattr(pline.dxf, 'layer') else '0'
            })
    except:
        pass

print(f"    Знайдено прямокутників: {len(rectangles)}")

# Сортуємо по Y (зверху вниз) та X (зліва направо)
rectangles.sort(key=lambda r: (-r['bounds']['center_y'], r['bounds']['center_x']))

print("\n[2] КООРДИНАТИ ЗНАЙДЕНИХ ПРЯМОКУТНИКІВ:")

silos_data = []

for idx, rect in enumerate(rectangles[:10], 1):  # Топ-10
    b = rect['bounds']
    print(f"\n    Прямокутник #{idx}:")
    print(f"      Центр: [{b['center_x']:.1f}, {b['center_y']:.1f}]")
    print(f"      Розміри: {b['width']:.1f} × {b['height']:.1f}")
    print(f"      Шар: {rect['layer']}")

    silos_data.append({
        'number': idx,
        'center': [b['center_x'], b['center_y']],
        'width': b['width'],
        'height': b['height'],
        'layer': rect['layer']
    })

# Зберегти в JSON
output = {
    'source_file': 'web_temp...dxf',
    'silos_count': len(silos_data),
    'silos': silos_data
}

output_path = "d:/autocad project/extracted_silos.json"

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n{'='*70}")
print(f"✅ ВИТЯГНУТО {len(silos_data)} СИЛОСІВ!")
print(f"✅ Збережено: {output_path}")
print(f"{'='*70}")
