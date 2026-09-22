# -*- coding: utf-8 -*-
"""
НАЙПРОСТІШИЙ КОНВЕРТЕР - ТІЛЬКИ ЛІНІЇ БЕЗ ЗАЙВОГО
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import fitz
import ezdxf


def simple_convert(pdf_path, page_num, output_path):
    """Найпростіша конвертація - тільки лінії"""
    print(f"Відкриваю PDF...")
    pdf = fitz.open(pdf_path)
    page = pdf[page_num - 1]

    page_height = page.rect.height

    print(f"Створюю DXF...")
    doc = ezdxf.new('R2010')
    msp = doc.modelspace()

    print(f"Витягую вектори...")
    drawings = page.get_drawings()
    print(f"Знайдено: {len(drawings)} шляхів")

    lines_count = 0

    for idx, path in enumerate(drawings):
        if idx % 5000 == 0 and idx > 0:
            print(f"  {idx}/{len(drawings)}...")

        items = path.get('items', [])

        for item in items:
            if item[0] == 'l' and len(item) >= 3:
                p1, p2 = item[1], item[2]
                # Трансформація координат
                x1, y1 = page_height - p1.y, p1.x
                x2, y2 = page_height - p2.y, p2.x

                msp.add_line((x1, y1), (x2, y2))
                lines_count += 1

    print(f"\nЗбереження {lines_count} ліній...")
    doc.saveas(output_path)

    file_size = Path(output_path).stat().st_size / 1024 / 1024
    print(f"✅ Готово: {output_path}")
    print(f"   Розмір: {file_size:.1f} MB")
    print(f"   Ліній: {lines_count}")

    pdf.close()


if __name__ == "__main__":
    pdf_path = "d:/autocad project/Технологія 06.06.24.pdf"
    output_path = "d:/autocad project/TEST_SIMPLE_page01.dxf"

    print("="*70)
    print("ПРОСТИЙ ТЕСТ КОНВЕРТАЦІЇ")
    print("="*70)

    simple_convert(pdf_path, 1, output_path)

    print("\n" + "="*70)
    print("ВІДКРИЙ TEST_SIMPLE_page01.dxf В AUTOCAD!")
    print("="*70)
