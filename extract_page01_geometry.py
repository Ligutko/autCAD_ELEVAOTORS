# -*- coding: utf-8 -*-
"""
ВИТЯГУВАННЯ ГЕОМЕТРІЇ З page_01.dxf ДЛЯ РЕФЕРЕНСА
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import os
import json

try:
    import ezdxf
except ImportError:
    print("Встановлюю ezdxf...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "ezdxf"], check=True)
    import ezdxf

print("="*70)
print("ВИТЯГУВАННЯ ГЕОМЕТРІЇ З page_01.dxf")
print("="*70)

dxf_path = "D:/autocad project/FINAL_DXF_CORRECTED/page_01.dxf"

if not os.path.exists(dxf_path):
    # Спробувати альтернативний шлях
    dxf_path = "D:/autocad project/FINAL_DXF_OUTPUT/page_01.dxf"

print(f"\nФайл: {dxf_path}")

doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

print(f"Всього об'єктів: {len(list(msp))}")

# Аналіз ліній для пошуку ПРЯМОКУТНИКІВ (силоси у вигляді side view)
print("\n" + "="*70)
print("АНАЛІЗ ГЕОМЕТРІЇ")
print("="*70)

lines = [e for e in msp if e.dxftype() == 'LINE']
circles = [e for e in msp if e.dxftype() == 'CIRCLE']
polylines = [e for e in msp if e.dxftype() in ['LWPOLYLINE', 'POLYLINE']]

print(f"\nЛінії: {len(lines)}")
print(f"Кола: {len(circles)}")
print(f"Полілінії: {len(polylines)}")

# Пошук ПРЯМОКУТНИКІВ (4 лінії, що формують квадрат)
print("\n" + "="*70)
print("ПОШУК ПРЯМОКУТНИКІВ (СИЛОСИ)")
print("="*70)

# Групуємо лінії по X та Y координатам
horizontal_lines = []
vertical_lines = []

for line in lines:
    x1, y1 = line.dxf.start.x, line.dxf.start.y
    x2, y2 = line.dxf.end.x, line.dxf.end.y

    # Горизонтальна (Y однаковий)
    if abs(y1 - y2) < 1:
        horizontal_lines.append({
            'x1': min(x1, x2), 'x2': max(x1, x2),
            'y': (y1 + y2) / 2,
            'length': abs(x2 - x1)
        })
    # Вертикальна (X однаковий)
    elif abs(x1 - x2) < 1:
        vertical_lines.append({
            'y1': min(y1, y2), 'y2': max(y1, y2),
            'x': (x1 + x2) / 2,
            'length': abs(y2 - y1)
        })

print(f"Горизонтальних ліній: {len(horizontal_lines)}")
print(f"Вертикальних ліній: {len(vertical_lines)}")

# Знаходимо найбільші прямокутники (силоси зазвичай великі)
# Фільтр: довжина > 15000 (силоси діаметр 20-22м)
large_horizontal = [l for l in horizontal_lines if l['length'] > 15000]
large_vertical = [l for l in vertical_lines if l['length'] > 15000]

print(f"\nВеликі горизонтальні (>15000): {len(large_horizontal)}")
print(f"Великі вертикальні (>15000): {len(large_vertical)}")

# Виводимо топ-20 найбільших ліній
print("\n📏 ТОП-20 НАЙБІЛЬШИХ ГОРИЗОНТАЛЬНИХ ЛІНІЙ:")
for idx, l in enumerate(sorted(large_horizontal, key=lambda x: x['length'], reverse=True)[:20], 1):
    print(f"{idx}. Y={l['y']:.0f}, X: {l['x1']:.0f} → {l['x2']:.0f}, Довжина: {l['length']:.0f}")

print("\n📏 ТОП-20 НАЙБІЛЬШИХ ВЕРТИКАЛЬНИХ ЛІНІЙ:")
for idx, l in enumerate(sorted(large_vertical, key=lambda x: x['length'], reverse=True)[:20], 1):
    print(f"{idx}. X={l['x']:.0f}, Y: {l['y1']:.0f} → {l['y2']:.0f}, Довжина: {l['length']:.0f}")

# Пошук КЛАСТЕРІВ прямокутників
print("\n" + "="*70)
print("ПОШУК КЛАСТЕРІВ (ГРУПИ СИЛОСІВ)")
print("="*70)

# Групуємо прямокутники по близькості
def find_rectangles(h_lines, v_lines, tolerance=100):
    """Знайти прямокутники з 4 ліній"""
    rectangles = []

    # Сортуємо горизонтальні по Y
    h_sorted = sorted(h_lines, key=lambda x: x['y'])

    for i in range(len(h_sorted)):
        for j in range(i+1, len(h_sorted)):
            h1, h2 = h_sorted[i], h_sorted[j]

            # Перевіряємо чи близькі X координати
            if abs(h1['x1'] - h2['x1']) < tolerance and abs(h1['x2'] - h2['x2']) < tolerance:
                # Знайшли 2 паралельні горизонталі
                # Тепер шукаємо 2 вертикалі
                width = h1['length']
                height = abs(h2['y'] - h1['y'])
                x_left = (h1['x1'] + h2['x1']) / 2
                x_right = (h1['x2'] + h2['x2']) / 2
                y_bottom = min(h1['y'], h2['y'])
                y_top = max(h1['y'], h2['y'])

                # Перевіряємо наявність вертикальних ліній
                left_v = [v for v in v_lines if abs(v['x'] - x_left) < tolerance
                          and v['y1'] <= y_bottom + tolerance and v['y2'] >= y_top - tolerance]
                right_v = [v for v in v_lines if abs(v['x'] - x_right) < tolerance
                           and v['y1'] <= y_bottom + tolerance and v['y2'] >= y_top - tolerance]

                if left_v and right_v and width > 15000 and height > 15000:
                    rectangles.append({
                        'x': (x_left + x_right) / 2,
                        'y': (y_bottom + y_top) / 2,
                        'width': width,
                        'height': height,
                        'x_left': x_left,
                        'x_right': x_right,
                        'y_bottom': y_bottom,
                        'y_top': y_top
                    })

    return rectangles

rectangles = find_rectangles(large_horizontal, large_vertical)

print(f"\n✓ ЗНАЙДЕНО ПРЯМОКУТНИКІВ: {len(rectangles)}")

if rectangles:
    print("\n📐 КООРДИНАТИ ПРЯМОКУТНИКІВ (потенційні силоси):")
    for idx, r in enumerate(sorted(rectangles, key=lambda x: x['y'], reverse=True), 1):
        print(f"\n{idx}. ПРЯМОКУТНИК:")
        print(f"   Центр: ({r['x']:.0f}, {r['y']:.0f})")
        print(f"   Розміри: {r['width']:.0f} × {r['height']:.0f} мм")
        print(f"   X: {r['x_left']:.0f} → {r['x_right']:.0f}")
        print(f"   Y: {r['y_bottom']:.0f} → {r['y_top']:.0f}")

# Збереження результатів
output = {
    'rectangles': rectangles,
    'stats': {
        'total_lines': len(lines),
        'horizontal': len(horizontal_lines),
        'vertical': len(vertical_lines),
        'large_horizontal': len(large_horizontal),
        'large_vertical': len(large_vertical),
        'rectangles_found': len(rectangles)
    }
}

output_file = "d:/autocad project/page01_geometry.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n{'='*70}")
print(f"✅ ГЕОМЕТРІЯ ЗБЕРЕЖЕНА: {output_file}")
print(f"{'='*70}")
