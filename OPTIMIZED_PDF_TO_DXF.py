# -*- coding: utf-8 -*-
"""
ОПТИМІЗОВАНИЙ КОНВЕРТЕР PDF → DXF
З правильним форматом для AutoCAD
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import fitz  # PyMuPDF
import ezdxf
from ezdxf import colors


class OptimizedPDFtoDXFConverter:
    """Оптимізований конвертер з правильним форматом DXF"""

    def __init__(self, pdf_path, output_dir="OPTIMIZED_DXF"):
        self.pdf_path = Path(pdf_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def convert_page(self, page_num):
        """Конвертувати одну сторінку PDF в DXF"""
        print(f"\n{'='*70}")
        print(f"📄 СТОРІНКА {page_num}")
        print(f"{'='*70}")

        # Відкрити PDF
        pdf_doc = fitz.open(self.pdf_path)
        page = pdf_doc[page_num - 1]

        # Отримати розміри сторінки
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height

        print(f"   Розмір сторінки: {page_width:.1f} x {page_height:.1f} pt")

        # Створити DXF документ R2010 (AutoCAD 2010)
        doc = ezdxf.new('R2010', setup=True)
        msp = doc.modelspace()

        # Налаштувати документ
        doc.header['$INSUNITS'] = 4  # Міліметри
        doc.header['$MEASUREMENT'] = 1  # Метрична система

        # Функція трансформації координат
        def transform_point(x, y):
            # Поворот на -90° для правильної орієнтації
            return (page_height - y, x)

        # Статистика
        stats = {
            'lines': 0,
            'paths': 0,
            'skipped': 0
        }

        # Витягти векторні об'єкти
        drawings = page.get_drawings()
        stats['paths'] = len(drawings)
        print(f"   Знайдено векторних шляхів: {len(drawings)}")

        # Створити базовий шар
        if '0' not in doc.layers:
            doc.layers.add(name='0')

        # Обробити кожен векторний шлях
        for idx, path_dict in enumerate(drawings, 1):
            if idx % 5000 == 0:
                print(f"   Оброблено: {idx}/{len(drawings)}")

            # Визначити колір
            color = path_dict.get('color', None)
            if color and len(color) >= 3:
                r, g, b = color[:3]
                # AutoCAD color index (спрощено)
                color_idx = 7  # білий по замовчуванню
            else:
                color_idx = 7

            # Обробити items
            items = path_dict.get('items', [])

            for item in items:
                try:
                    item_type = item[0]

                    if item_type == 'l':  # Лінія
                        if len(item) >= 3:
                            p1, p2 = item[1], item[2]
                            pt1 = transform_point(p1.x, p1.y)
                            pt2 = transform_point(p2.x, p2.y)

                            # Додати лінію
                            line = msp.add_line(pt1, pt2)
                            line.dxf.color = color_idx
                            stats['lines'] += 1

                    elif item_type == 're':  # Прямокутник
                        if len(item) >= 2:
                            rect = item[1]
                            if hasattr(rect, 'x0'):
                                x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                                points = [
                                    transform_point(x0, y0),
                                    transform_point(x1, y0),
                                    transform_point(x1, y1),
                                    transform_point(x0, y1)
                                ]
                                poly = msp.add_lwpolyline(points, close=True)
                                poly.dxf.color = color_idx
                                stats['lines'] += 1

                except Exception as e:
                    stats['skipped'] += 1
                    continue

        # Зберегти DXF
        filename = f"page_{page_num:02d}.dxf"
        filepath = self.output_dir / filename

        # Зберегти з мінімальними заголовками
        doc.saveas(filepath)

        pdf_doc.close()

        # Статистика
        print(f"\n✅ ЗБЕРЕЖЕНО: {filepath.name}")
        print(f"   Розмір файлу: {filepath.stat().st_size / 1024 / 1024:.1f} MB")
        print(f"   Векторних шляхів: {stats['paths']}")
        print(f"   Створено ліній: {stats['lines']}")
        print(f"   Пропущено: {stats['skipped']}")

        return filepath, stats

    def convert_all_pages(self):
        """Конвертувати всі сторінки"""
        print("\n" + "🔥"*35)
        print("   ОПТИМІЗОВАНА КОНВЕРТАЦІЯ PDF → DXF")
        print("🔥"*35)

        pdf_doc = fitz.open(self.pdf_path)
        total_pages = len(pdf_doc)
        pdf_doc.close()

        print(f"\n📂 PDF: {self.pdf_path.name}")
        print(f"📄 Сторінок: {total_pages}")

        dxf_files = []
        for page_num in range(1, total_pages + 1):
            filepath, stats = self.convert_page(page_num)
            dxf_files.append(filepath)

        print("\n" + "="*70)
        print(f"✅ Створено {len(dxf_files)} DXF файлів")
        print("="*70)

        return dxf_files


def main():
    """Головна функція"""
    pdf_path = "d:/autocad project/Технологія 06.06.24.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ PDF не знайдено: {pdf_path}")
        return

    converter = OptimizedPDFtoDXFConverter(pdf_path)

    # Спочатку конвертуємо тільки ПЕРШУ сторінку для тесту
    print("\n⚡ ТЕСТ: Конвертуємо ПЕРШУ сторінку...")
    converter.convert_page(1)

    print("\n" + "="*70)
    print("✅ ТЕСТ ЗАВЕРШЕНО!")
    print("="*70)
    print("\nТепер відкрий page_01.dxf в AutoCAD для перевірки!")
    print("Якщо працює - запусти converter.convert_all_pages()")


if __name__ == "__main__":
    main()
