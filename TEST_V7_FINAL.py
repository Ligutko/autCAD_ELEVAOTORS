# -*- coding: utf-8 -*-
"""
ФІНАЛЬНИЙ ТЕСТ - V3 + поворот 180° по осі X
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import fitz
import ezdxf


def transform_v7(x, y, w, h):
    """V3 rotate -90° + додатковий flip 180°"""
    # Спочатку V3: (page_height - y, x)
    x_new, y_new = h - y, x
    # Потім поворот 180° по X = інвертувати X координату
    return (-x_new, y_new)


def convert_with_transform(output_name, transform_func):
    """Конвертувати з заданою трансформацією"""
    print(f"\n{'='*70}")
    print(f"🧪 ТЕСТ: {output_name}")
    print(f"{'='*70}")

    pdf_path = "d:/autocad project/Технологія 06.06.24.pdf"
    output_path = f"d:/autocad project/{output_name}.dxf"

    pdf_doc = fitz.open(pdf_path)
    page = pdf_doc[0]

    page_rect = page.rect
    page_width = page_rect.width
    page_height = page_rect.height

    doc = ezdxf.new('R2010', setup=True)
    msp = doc.modelspace()

    stats = {'lines': 0, 'rects': 0}
    color_layers = {}

    drawings = page.get_drawings()

    for path_dict in drawings:
        color = path_dict.get('color', None)
        rgb_color = None

        if color and len(color) >= 3:
            r, g, b = color[:3]
            rgb_color = (int(r*255), int(g*255), int(b*255))
            layer_name = f"RGB_{rgb_color[0]:03d}_{rgb_color[1]:03d}_{rgb_color[2]:03d}"
        else:
            layer_name = "0"

        if layer_name not in color_layers:
            color_layers[layer_name] = rgb_color
            try:
                layer = doc.layers.add(name=layer_name)
                if rgb_color:
                    layer.color = -1
                    layer.rgb = rgb_color
            except:
                pass

        items = path_dict.get('items', [])

        for item in items:
            item_type = item[0]

            if item_type == 'l' and len(item) >= 3:
                p1, p2 = item[1], item[2]
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

    doc.saveas(output_path)
    pdf_doc.close()

    print(f"✅ {output_path}")
    print(f"   Ліній: {stats['lines']}, Rect: {stats['rects']}")
    print(f"   Кольорових шарів: {len(color_layers)}")

    return output_path


if __name__ == "__main__":
    print("\n" + "🎯"*35)
    print("   ФІНАЛЬНИЙ ТЕСТ - V3 + ПОВОРОТ 180°")
    print("🎯"*35)

    convert_with_transform("TEST_V7_FINAL_rotate180", transform_v7)

    print("\n" + "="*70)
    print("✅ ГОТОВО! Відкрий TEST_V7_FINAL_rotate180.dxf")
    print("="*70)
