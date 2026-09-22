# -*- coding: utf-8 -*-
"""
ТЕСТ ТІЛЬКИ ПЕРШОЇ СТОРІНКИ
Швидка перевірка різних трансформацій
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import fitz
import ezdxf


def test_transform(transform_name, transform_func):
    """Тестувати одну трансформацію"""
    print(f"\n{'='*70}")
    print(f"🧪 ТЕСТ: {transform_name}")
    print(f"{'='*70}")

    pdf_path = "d:/autocad project/Технологія 06.06.24.pdf"
    output_path = f"d:/autocad project/TEST_{transform_name}.dxf"

    # Відкрити PDF
    pdf_doc = fitz.open(pdf_path)
    page = pdf_doc[0]  # Перша сторінка

    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height

    # Створити DXF
    doc = ezdxf.new('R2010', setup=True)
    msp = doc.modelspace()

    # Статистика
    stats = {'lines': 0, 'rects': 0}

    # Витягти вектори
    drawings = page.get_drawings()

    # Шари за кольорами
    color_layers = {}

    for path_dict in drawings:
        # Колір
        color = path_dict.get('color', None)
        rgb_color = None

        if color and len(color) >= 3:
            r, g, b = color[:3]
            rgb_color = (int(r*255), int(g*255), int(b*255))
            layer_name = f"RGB_{rgb_color[0]:03d}_{rgb_color[1]:03d}_{rgb_color[2]:03d}"
        else:
            layer_name = "0"

        # Створити шар
        if layer_name not in color_layers:
            color_layers[layer_name] = rgb_color
            try:
                layer = doc.layers.add(name=layer_name)
                if rgb_color:
                    layer.color = -1
                    layer.rgb = rgb_color
            except:
                pass

        # Обробити items
        items = path_dict.get('items', [])

        for item in items:
            item_type = item[0]

            if item_type == 'l' and len(item) >= 3:
                p1, p2 = item[1], item[2]
                # Застосувати трансформацію
                pt1 = transform_func(p1.x, p1.y, page_width, page_height)
                pt2 = transform_func(p2.x, p2.y, page_width, page_height)

                line = msp.add_line(pt1, pt2, dxfattribs={'layer': layer_name})
                if rgb_color:
                    line.rgb = rgb_color
                stats['lines'] += 1

            elif item_type == 're' and len(item) >= 2:
                rect = item[1]
                if hasattr(rect, 'x0'):
                    x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                    points = [
                        transform_func(x0, y0, page_width, page_height),
                        transform_func(x1, y0, page_width, page_height),
                        transform_func(x1, y1, page_width, page_height),
                        transform_func(x0, y1, page_width, page_height)
                    ]
                    poly = msp.add_lwpolyline(points, close=True, dxfattribs={'layer': layer_name})
                    if rgb_color:
                        poly.rgb = rgb_color
                    stats['rects'] += 1

    # Зберегти
    doc.saveas(output_path)
    pdf_doc.close()

    print(f"✅ {output_path}")
    print(f"   Ліній: {stats['lines']}, Rect: {stats['rects']}")
    print(f"   Кольорових шарів: {len(color_layers)}")

    return output_path


# РІЗНІ ТРАНСФОРМАЦІЇ ДЛЯ ТЕСТУ
def transform_1(x, y, w, h):
    """(x, page_height - y) - попередній варіант"""
    return (x, h - y)

def transform_2(x, y, w, h):
    """(page_width - x, page_height - y) - поточний варіант"""
    return (w - x, h - y)

def transform_3(x, y, w, h):
    """(page_height - y, x) - поворот -90°"""
    return (h - y, x)

def transform_4(x, y, w, h):
    """(y, page_width - x) - поворот +90°"""
    return (y, w - x)

def transform_5(x, y, w, h):
    """(page_height - y, page_width - x) - поворот -90° + mirror"""
    return (h - y, w - x)

def transform_6(x, y, w, h):
    """(y, x) - swap XY"""
    return (y, x)


if __name__ == "__main__":
    print("\n" + "🧪"*35)
    print("   ТЕСТ ТРАНСФОРМАЦІЙ - ТІЛЬКИ СТОРІНКА 1")
    print("🧪"*35)

    # Тестуємо всі варіанти
    test_transform("V1_x_flip_y", transform_1)
    test_transform("V2_flip_both", transform_2)
    test_transform("V3_rotate_minus90", transform_3)
    test_transform("V4_rotate_plus90", transform_4)
    test_transform("V5_rotate_mirror", transform_5)
    test_transform("V6_swap_xy", transform_6)

    print("\n" + "="*70)
    print("✅ ГОТОВО!")
    print("="*70)
    print("\nТепер відкрий ЦІ ФАЙЛИ в AutoCAD:")
    print("   TEST_V1_x_flip_y.dxf")
    print("   TEST_V2_flip_both.dxf")
    print("   TEST_V3_rotate_minus90.dxf")
    print("   TEST_V4_rotate_plus90.dxf")
    print("   TEST_V5_rotate_mirror.dxf")
    print("   TEST_V6_swap_xy.dxf")
    print("\nі СКАЖИ МНІ ЯКИЙ З НИХ ПРАВИЛЬНИЙ!")
