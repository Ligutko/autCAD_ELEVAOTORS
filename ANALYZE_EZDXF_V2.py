"""
АНАЛІЗ ЧЕРЕЗ EZDXF V2 - ВИПРАВЛЕНА ВЕРСІЯ
==========================================

Правильний пошук силосів та червоних з'єднань
"""

import ezdxf
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

print("="*70)
print("    АНАЛІЗ ЧЕРЕЗ EZDXF V2")
print("="*70)

# Шлях до файлу
dxf_path = r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01.dxf"
output_dir = Path(r"d:\autocad project\ANALYSIS_RESULTS")
output_dir.mkdir(exist_ok=True)

print(f"\nФайл: {dxf_path}")
print("\n[1] Читання DXF...")

doc = ezdxf.readfile(dxf_path)
msp = doc.modelspace()

all_entities = list(msp)
print(f"    Всього об'єктів: {len(all_entities)}")

# Аналіз layers
print("\n[2] Layers:")
layers_count = defaultdict(int)
for e in all_entities:
    layer = getattr(e.dxf, 'layer', 'UNKNOWN')
    layers_count[layer] += 1

for layer, count in sorted(layers_count.items(), key=lambda x: -x[1])[:10]:
    print(f"    {layer:30s} : {count:6d}")

# Пошук синіх об'єктів (силоси)
print("\n[3] Пошук синіх об'єктів (силоси)...")
print("    Шукаємо в layer: RGB_000_000_255")

blue_entities = []
for e in all_entities:
    layer = getattr(e.dxf, 'layer', '')
    if 'RGB_000_000_255' in layer or '000_000_255' in layer:
        blue_entities.append(e)

print(f"    Знайдено: {len(blue_entities)}")

# Типи синіх об'єктів
blue_types = defaultdict(list)
for e in blue_entities:
    blue_types[e.dxftype()].append(e)

print("\n[4] Типи синіх об'єктів:")
for etype, ents in blue_types.items():
    print(f"    {etype:20s} : {len(ents):4d}")

# Витягуємо LINE (контури силосів)
print("\n[5] Аналіз LINE (контури)...")

blue_lines = blue_types.get('LINE', [])
print(f"    Всього синіх ліній: {len(blue_lines)}")

# Групуємо лінії по позиції (силосам)
# Будемо групувати по X координаті

line_centers = []
for line in blue_lines:
    try:
        start = line.dxf.start
        end = line.dxf.end
        cx = (start[0] + end[0]) / 2
        cy = (start[1] + end[1]) / 2
        line_centers.append((cx, cy, line))
    except:
        pass

print(f"    Обробленo ліній: {len(line_centers)}")

# Сортуємо по X
line_centers_sorted = sorted(line_centers, key=lambda x: x[0])

# Групуємо по X (відстань між силосами > 30мм)
threshold = 30
groups = []
if line_centers_sorted:
    current_group = [line_centers_sorted[0][2]]
    current_x = line_centers_sorted[0][0]

    for cx, cy, line in line_centers_sorted[1:]:
        if abs(cx - current_x) < threshold:
            current_group.append(line)
        else:
            groups.append(current_group)
            current_group = [line]
            current_x = cx

    groups.append(current_group)

print(f"    Знайдено груп (силосів): {len(groups)}")

# Витягуємо геометрію кожного силосу
silos_data = {}

for i, group in enumerate(groups, 1):
    print(f"\n[СИЛОС #{i}]")

    lines_data = []
    all_xs = []
    all_ys = []

    for line in group:
        try:
            start = line.dxf.start
            end = line.dxf.end

            lines_data.append({
                'start': [float(start[0]), float(start[1])],
                'end': [float(end[0]), float(end[1])],
                'layer': line.dxf.layer
            })

            all_xs.extend([float(start[0]), float(end[0])])
            all_ys.extend([float(start[1]), float(end[1])])
        except:
            pass

    if all_xs and all_ys:
        min_x, max_x = min(all_xs), max(all_xs)
        min_y, max_y = min(all_ys), max(all_ys)
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        width = max_x - min_x
        height = max_y - min_y

        silos_data[f"silo_{i}"] = {
            'lines': lines_data,
            'bounds': {
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y
            },
            'center': {
                'x': cx,
                'y': cy
            },
            'dimensions': {
                'width': width,
                'height': height
            },
            'total_lines': len(lines_data)
        }

        print(f"    Ліній: {len(lines_data)}")
        print(f"    Center: ({cx:.2f}, {cy:.2f})")
        print(f"    Width: {width:.2f}, Height: {height:.2f}")

# Пошук червоних з'єднань
print("\n" + "="*70)
print("[ЧЕРВОНІ З'ЄДНАННЯ]")
print("="*70)

print("\nШукаємо в layer: RGB_255_000_000")

red_entities = []
for e in all_entities:
    layer = getattr(e.dxf, 'layer', '')
    if 'RGB_255_000_000' in layer or '255_000_000' in layer:
        red_entities.append(e)

print(f"\nЗнайдено червоних об'єктів: {len(red_entities)}")

red_types = defaultdict(list)
for e in red_entities:
    red_types[e.dxftype()].append(e)

print("\nТипи червоних об'єктів:")
for etype, ents in red_types.items():
    print(f"    {etype:20s} : {len(ents):4d}")

# Витягуємо червоні лінії
red_lines = red_types.get('LINE', [])
red_lines_data = []

for line in red_lines:
    try:
        start = line.dxf.start
        end = line.dxf.end

        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])

        red_lines_data.append({
            'start': [float(start[0]), float(start[1])],
            'end': [float(end[0]), float(end[1])],
            'type': 'horizontal' if dx > dy else 'vertical',
            'length': max(dx, dy)
        })
    except:
        pass

# Класифікація
horizontal_conveyors = [l for l in red_lines_data if l['type'] == 'horizontal']
vertical_elevators = [l for l in red_lines_data if l['type'] == 'vertical']

print(f"\nГоризонтальні (конвеєри): {len(horizontal_conveyors)}")
print(f"Вертикальні (норії): {len(vertical_elevators)}")

# Збереження
print("\n" + "="*70)
print("ЗБЕРЕЖЕННЯ РЕЗУЛЬТАТІВ")
print("="*70)

master_template = {
    'metadata': {
        'source_file': str(dxf_path),
        'analyzed_at': datetime.now().isoformat(),
        'tool': 'ezdxf_v2',
        'version': '2.0'
    },
    'statistics': {
        'total_entities': len(all_entities),
        'blue_entities': len(blue_entities),
        'red_entities': len(red_entities),
        'silos_found': len(silos_data)
    },
    'silos': silos_data,
    'red_connections': {
        'total': len(red_lines_data),
        'horizontal_conveyors': horizontal_conveyors,
        'vertical_elevators': vertical_elevators
    }
}

# Зберігаємо
output_file = output_dir / 'MASTER_TEMPLATE_V2.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(master_template, f, indent=2, ensure_ascii=False)

print(f"\nОК Збережено: {output_file}")

# Окремо силос #6
if 'silo_6' in silos_data:
    silo_6_file = output_dir / 'SILO_6_GEOMETRY.json'
    with open(silo_6_file, 'w', encoding='utf-8') as f:
        json.dump(silos_data['silo_6'], f, indent=2, ensure_ascii=False)
    print(f"OK Збережено силос #6: {silo_6_file}")

print("\n" + "="*70)
print("АНАЛІЗ ЗАВЕРШЕНО!")
print("="*70)
print(f"\nВсього об'єктів: {len(all_entities)}")
print(f"Знайдено силосів: {len(silos_data)}")
print(f"Червоних ліній: {len(red_lines_data)}")
print(f"  - Конвеєрів: {len(horizontal_conveyors)}")
print(f"  - Норій: {len(vertical_elevators)}")
