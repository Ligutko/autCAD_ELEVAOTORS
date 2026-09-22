# -*- coding: utf-8 -*-
"""
КОМПАКТНИЙ КОНВЕРТЕР PDF → DWG
Створює бінарні DWG файли (компактніші ніж DXF)
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import fitz  # PyMuPDF
import ezdxf


class CompactPDFtoDWGConverter:
    """Конвертер в компактний DWG формат"""

    def __init__(self, pdf_path, output_dir="COMPACT_DWG"):
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def convert_page(self, page_num, save_as_dwg=True):
        """Конвертувати сторінку в DWG"""
        print(f"\n{'='*70}")
        print(f"📄 СТОРІНКА {page_num}")
        print(f"{'='*70}")

        pdf_doc = fitz.open(self.pdf_path)
        page = pdf_doc[page_num - 1]

        page_rect = page.rect
        page_height = page_rect.height

        # Створити документ
        doc = ezdxf.new('R2010', setup=True)
        msp = doc.modelspace()

        def transform_point(x, y):
            return (page_height - y, x)

        stats = {'lines': 0, 'rects': 0, 'total': 0}

        # Витягти об'єкти
        drawings = page.get_drawings()
        print(f"   Обробка {len(drawings)} об'єктів...")

        for idx, path_dict in enumerate(drawings, 1):
            if idx % 10000 == 0:
                print(f"   {idx}/{len(drawings)}...")

            items = path_dict.get('items', [])

            for item in items:
                try:
                    item_type = item[0]

                    if item_type == 'l' and len(item) >= 3:
                        p1, p2 = item[1], item[2]
                        msp.add_line(
                            transform_point(p1.x, p1.y),
                            transform_point(p2.x, p2.y)
                        )
                        stats['lines'] += 1

                    elif item_type == 're' and len(item) >= 2:
                        rect = item[1]
                        if hasattr(rect, 'x0'):
                            x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                            points = [
                                transform_point(x0, y0),
                                transform_point(x1, y0),
                                transform_point(x1, y1),
                                transform_point(x0, y1)
                            ]
                            msp.add_lwpolyline(points, close=True)
                            stats['rects'] += 1
                except:
                    continue

        stats['total'] = stats['lines'] + stats['rects']

        # Зберегти
        if save_as_dwg:
            filename = f"page_{page_num:02d}.dwg"
            filepath = self.output_dir / filename
            try:
                doc.saveas(filepath)
                print(f"✅ DWG: {filepath.name} ({filepath.stat().st_size / 1024 / 1024:.1f} MB)")
            except Exception as e:
                print(f"⚠️  DWG помилка: {e}")
                # Fallback to DXF
                filename = f"page_{page_num:02d}.dxf"
                filepath = self.output_dir / filename
                doc.saveas(filepath)
                print(f"✅ DXF (fallback): {filepath.name}")
        else:
            filename = f"page_{page_num:02d}.dxf"
            filepath = self.output_dir / filename
            doc.saveas(filepath)
            print(f"✅ DXF: {filepath.name}")

        pdf_doc.close()

        print(f"   Об'єктів: {stats['total']} (ліній: {stats['lines']}, rect: {stats['rects']})")

        return filepath, stats


def main():
    pdf_path = "d:/autocad project/Технологія 06.06.24.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ PDF не знайдено")
        return

    converter = CompactPDFtoDWGConverter(pdf_path)

    print("\n🔥 ТЕСТ: Конвертуємо першу сторінку в DXF...")
    converter.convert_page(1, save_as_dwg=False)

    print("\n" + "="*70)
    print("Перевір цей файл в AutoCAD!")
    print("="*70)


if __name__ == "__main__":
    main()
