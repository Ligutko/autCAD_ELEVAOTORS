"""
АНАЛІЗ ЧЕРЕЗ EZDXF - ШВИДКИЙ ТА ЕФЕКТИВНИЙ
===========================================

Витягує ПОВНУ геометрію з DXF файлу без зависання
Використовує ezdxf замість Python COM API
"""

import ezdxf
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def analyze_dxf_complete(dxf_path):
    """
    Повний аналіз DXF файлу через ezdxf

    Returns:
        dict: Повна структура з усіма об'єктами
    """
    print(f"\n{'='*70}")
    print(f"АНАЛІЗ ФАЙЛУ: {Path(dxf_path).name}")
    print(f"{'='*70}\n")

    # Читання DXF
    print("[1] Читання DXF файлу...")
    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Статистика
    all_entities = list(msp)
    print(f"    OK Всього об'єктів: {len(all_entities)}")

    # Рахуємо типи
    entity_types = defaultdict(int)
    for e in all_entities:
        entity_types[e.dxftype()] += 1

    print("\n[2] Типи об'єктів:")
    for etype, count in sorted(entity_types.items(), key=lambda x: -x[1]):
        print(f"    {etype:20s} : {count:6d}")

    # Аналіз по layers
    print("\n[3] Аналіз Layers:")
    layers = defaultdict(list)
    for e in all_entities:
        layer = getattr(e.dxf, 'layer', 'UNKNOWN')
        layers[layer].append(e)

    for layer_name, entities in sorted(layers.items(), key=lambda x: -len(x[1])):
        print(f"    {layer_name:30s} : {len(entities):6d} об'єктів")

    # Аналіз кольорів
    print("\n[4] Аналіз кольорів:")
    colors = defaultdict(list)
    for e in all_entities:
        color = getattr(e.dxf, 'color', None)
        colors[color].append(e)

    for color, entities in sorted(colors.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"    Color {str(color):10s} : {len(entities):6d} об'єктів")

    return {
        'file': str(dxf_path),
        'total_entities': len(all_entities),
        'entity_types': dict(entity_types),
        'layers': {name: len(ents) for name, ents in layers.items()},
        'analysis_timestamp': datetime.now().isoformat()
    }


def extract_silos_geometry(dxf_path):
    """
    Витягує детальну геометрію всіх силосів

    Returns:
        dict: Структура з геометрією кожного силосу
    """
    print(f"\n{'='*70}")
    print(f"ВИТЯГУВАННЯ ГЕОМЕТРІЇ СИЛОСІВ")
    print(f"{'='*70}\n")

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Шукаємо сині об'єкти (силоси)
    print("[1] Пошук синіх об'єктів (силоси)...")

    # Варіанти синього кольору
    blue_layers = ['C00-00-FF', '0', 'C00-00-ff']
    blue_colors = [5, 256]  # 5 = синій, 256 = ByLayer

    blue_entities = []
    for e in msp:
        layer = getattr(e.dxf, 'layer', '')
        color = getattr(e.dxf, 'color', None)

        # Перевірка layer або color
        if any(bl in layer for bl in blue_layers) or color in blue_colors:
            blue_entities.append(e)

    print(f"    OK Знайдено синіх об'єктів: {len(blue_entities)}")

    # Групуємо по типах
    blue_by_type = defaultdict(list)
    for e in blue_entities:
        blue_by_type[e.dxftype()].append(e)

    print("\n[2] Типи синіх об'єктів:")
    for etype, ents in blue_by_type.items():
        print(f"    {etype:20s} : {len(ents):4d}")

    # Витягуємо LWPOLYLINE (основні контури силосів)
    print("\n[3] Аналіз LWPOLYLINE (контури силосів)...")

    polylines = blue_by_type.get('LWPOLYLINE', [])
    print(f"    Всього polylines: {len(polylines)}")

    # Групуємо polylines по позиції (силосам)
    # Використаємо bounding boxes для групування

    silos_groups = group_polylines_by_proximity(polylines)

    print(f"    OK Знайдено груп (силосів): {len(silos_groups)}")

    # Витягуємо геометрію для кожної групи
    silos_geometry = {}

    for i, group in enumerate(silos_groups, 1):
        print(f"\n[4] Силос #{i}:")

        geom = extract_polyline_geometry(group)
        silos_geometry[f"silo_{i}"] = geom

        print(f"    Polylines: {len(geom['polylines'])}")
        print(f"    Bounds: ({geom['bounds']['min_x']:.2f}, {geom['bounds']['min_y']:.2f}) - ({geom['bounds']['max_x']:.2f}, {geom['bounds']['max_y']:.2f})")
        print(f"    Center: ({geom['center']['x']:.2f}, {geom['center']['y']:.2f})")
        print(f"    Width: {geom['dimensions']['width']:.2f}")
        print(f"    Height: {geom['dimensions']['height']:.2f}")

    return silos_geometry


def group_polylines_by_proximity(polylines, threshold=50):
    """
    Групує polylines по близькості (один силос)
    """
    if not polylines:
        return []

    # Отримуємо центри всіх polylines
    centers = []
    for pl in polylines:
        bounds = get_polyline_bounds(pl)
        if bounds:
            cx = (bounds['min_x'] + bounds['max_x']) / 2
            cy = (bounds['min_y'] + bounds['max_y']) / 2
            centers.append((cx, cy, pl))

    # Групуємо по X координате (силоси в ряд)
    centers_sorted = sorted(centers, key=lambda x: x[0])

    groups = []
    current_group = [centers_sorted[0][2]]
    current_x = centers_sorted[0][0]

    for cx, cy, pl in centers_sorted[1:]:
        if abs(cx - current_x) < threshold:
            # Той самий силос
            current_group.append(pl)
        else:
            # Новий силос
            groups.append(current_group)
            current_group = [pl]
            current_x = cx

    groups.append(current_group)

    return groups


def get_polyline_bounds(polyline):
    """
    Отримує bounds polyline
    """
    try:
        points = list(polyline.get_points('xy'))
        if not points:
            return None

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        return {
            'min_x': min(xs),
            'max_x': max(xs),
            'min_y': min(ys),
            'max_y': max(ys)
        }
    except:
        return None


def extract_polyline_geometry(polylines):
    """
    Витягує детальну геометрію групи polylines (один силос)
    """
    all_polylines_data = []
    all_xs = []
    all_ys = []

    for pl in polylines:
        try:
            # Точки polyline
            points = list(pl.get_points('xyb'))  # x, y, bulge

            # Конвертуємо в список координат
            coords = []
            bulges = []
            for p in points:
                coords.append([float(p[0]), float(p[1])])
                bulges.append(float(p[2]) if len(p) > 2 else 0.0)
                all_xs.append(float(p[0]))
                all_ys.append(float(p[1]))

            all_polylines_data.append({
                'points': coords,
                'bulges': bulges,
                'closed': pl.closed,
                'layer': pl.dxf.layer,
                'color': getattr(pl.dxf, 'color', None)
            })
        except Exception as e:
            print(f"    \! Помилка витягування polyline: {e}")

    # Bounds та center
    if all_xs and all_ys:
        min_x, max_x = min(all_xs), max(all_xs)
        min_y, max_y = min(all_ys), max(all_ys)
        cx = (min_x + max_x) / 2
        cy = (min_y + max_y) / 2
        width = max_x - min_x
        height = max_y - min_y
    else:
        min_x = max_x = min_y = max_y = cx = cy = width = height = 0

    return {
        'polylines': all_polylines_data,
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
        }
    }


def extract_red_connections(dxf_path):
    """
    Витягує червоні з'єднання (конвеєри та норії)
    """
    print(f"\n{'='*70}")
    print(f"ВИТЯГУВАННЯ ЧЕРВОНИХ З'ЄДНАНЬ")
    print(f"{'='*70}\n")

    doc = ezdxf.readfile(dxf_path)
    msp = doc.modelspace()

    # Шукаємо червоні об'єкти
    print("[1] Пошук червоних об'єктів...")

    red_layers = ['CFF-00-00', 'CFF-00-00']
    red_color = 1  # Червоний

    red_entities = []
    for e in msp:
        layer = getattr(e.dxf, 'layer', '')
        color = getattr(e.dxf, 'color', None)

        if any(rl in layer for rl in red_layers) or color == red_color:
            red_entities.append(e)

    print(f"    OK Знайдено червоних об'єктів: {len(red_entities)}")

    # Групуємо по типах
    red_by_type = defaultdict(list)
    for e in red_entities:
        red_by_type[e.dxftype()].append(e)

    print("\n[2] Типи червоних об'єктів:")
    for etype, ents in red_by_type.items():
        print(f"    {etype:20s} : {len(ents):4d}")

    # Витягуємо лінії
    lines_data = []

    for line in red_by_type.get('LINE', []):
        try:
            start = line.dxf.start
            end = line.dxf.end

            lines_data.append({
                'type': 'LINE',
                'start': [float(start[0]), float(start[1])],
                'end': [float(end[0]), float(end[1])],
                'layer': line.dxf.layer,
                'color': getattr(line.dxf, 'color', None)
            })
        except:
            pass

    # Класифікуємо на горизонтальні та вертикальні
    horizontal = []
    vertical = []

    for line in lines_data:
        dx = abs(line['end'][0] - line['start'][0])
        dy = abs(line['end'][1] - line['start'][1])

        if dx > dy:
            horizontal.append(line)
        else:
            vertical.append(line)

    print(f"\n[3] Класифікація:")
    print(f"    Горизонтальні (конвеєри): {len(horizontal)}")
    print(f"    Вертикальні (норії): {len(vertical)}")

    return {
        'total': len(lines_data),
        'horizontal_conveyors': horizontal,
        'vertical_elevators': vertical
    }


def main():
    """Головна функція"""

    # Шляхи до файлів
    dxf_path = r"d:\autocad project\FINAL_DXF_PERFECT_V7\page_01.dxf"
    output_dir = Path(r"d:\autocad project\ANALYSIS_RESULTS")
    output_dir.mkdir(exist_ok=True)

    print("\n" + "="*70)
    print("    АНАЛІЗ ЧЕРЕЗ EZDXF - ПОВНА СТРУКТУРА")
    print("="*70)

    # 1. Загальний аналіз
    print("\n[ЕТАП 1] ЗАГАЛЬНИЙ АНАЛІЗ")
    general = analyze_dxf_complete(dxf_path)

    # 2. Витягування силосів
    print("\n[ЕТАП 2] ВИТЯГУВАННЯ ГЕОМЕТРІЇ СИЛОСІВ")
    silos = extract_silos_geometry(dxf_path)

    # 3. Витягування червоних з'єднань
    print("\n[ЕТАП 3] ВИТЯГУВАННЯ ЧЕРВОНИХ З'ЄДНАНЬ")
    red_connections = extract_red_connections(dxf_path)

    # Збереження результатів
    print(f"\n{'='*70}")
    print("ЗБЕРЕЖЕННЯ РЕЗУЛЬТАТІВ")
    print(f"{'='*70}\n")

    # Загальна структура
    master_template = {
        'metadata': {
            'source_file': str(dxf_path),
            'analyzed_at': datetime.now().isoformat(),
            'tool': 'ezdxf',
            'version': '1.0'
        },
        'general_statistics': general,
        'silos': silos,
        'red_connections': red_connections
    }

    # Зберігаємо в JSON
    output_file = output_dir / 'MASTER_TEMPLATE.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(master_template, f, indent=2, ensure_ascii=False)

    print(f"OK Збережено: {output_file}")

    # Окремо силос #6 (для копіювання)
    if 'silo_6' in silos:
        silo_6_file = output_dir / 'SILO_6_GEOMETRY.json'
        with open(silo_6_file, 'w', encoding='utf-8') as f:
            json.dump(silos['silo_6'], f, indent=2, ensure_ascii=False)
        print(f"OK Збережено силос #6: {silo_6_file}")

    print("\n" + "="*70)
    print("OKOKOK АНАЛІЗ ЗАВЕРШЕНО УСПІШНО! OKOKOK")
    print("="*70)

    print(f"\nРезультати:")
    print(f"  - Всього об'єктів: {general['total_entities']}")
    print(f"  - Знайдено силосів: {len(silos)}")
    print(f"  - Червоних ліній: {red_connections['total']}")
    print(f"  - Файли збережено в: {output_dir}")


if __name__ == '__main__':
    main()
