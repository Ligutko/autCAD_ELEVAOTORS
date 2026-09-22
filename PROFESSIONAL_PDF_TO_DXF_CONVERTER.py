# -*- coding: utf-8 -*-
"""
🔥 ПРОФЕСІЙНИЙ ВЕКТОРНИЙ КОНВЕРТЕР PDF → DXF 🔥
Витягує всі векторні примітиви з PDF аналогічно до онлайн-сервісів
Використовує перевірений підхід з Point objects
"""
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import fitz  # PyMuPDF
import ezdxf


class ProfessionalPDFtoDXFConverter:
    """Професійний конвертер PDF → DXF з повною векторною екстракцією"""

    def __init__(self, pdf_path, output_dir="FINAL_DXF_PERFECT_V7"):
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

        # Отримати розміри сторінки для трансформації координат
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height

        # Створити DXF документ
        doc = ezdxf.new('R2010', setup=True)
        msp = doc.modelspace()

        # Функція для трансформації координат PDF → AutoCAD
        def transform_point(x, y):
            # PDF: (0,0) верхній лівий кут, Y вниз
            # AutoCAD: (0,0) нижній лівий кут, Y вгору
            # ✅ V7 ПРАВИЛЬНА: Rotate -90° + Flip X (поворот 180°)
            x_new = page_height - y
            y_new = x
            return (-x_new, y_new)

        # Функція для тексту - така сама трансформація як і для ліній
        def transform_text_point(x, y):
            # Використати ту саму трансформацію що і для геометрії
            x_new = page_height - y
            y_new = x
            return (-x_new, y_new)

        # Статистика
        stats = {
            'lines': 0,
            'curves': 0,
            'rects': 0,
            'quads': 0,
            'texts': 0,
            'total_paths': 0
        }

        # Витягти векторні об'єкти
        drawings = page.get_drawings()
        stats['total_paths'] = len(drawings)
        print(f"   Знайдено векторних шляхів: {len(drawings)}")

        # Створити шари за кольорами
        color_layers = {}

        # Обробити кожен векторний шлях
        for idx, path_dict in enumerate(drawings, 1):
            if idx % 1000 == 0:
                print(f"   Оброблено: {idx}/{len(drawings)}")

            # Визначити колір і створити шар
            color = path_dict.get('color', None)
            rgb_color = None

            if color and len(color) >= 3:
                r, g, b = color[:3]
                # Конвертувати в RGB (0-255)
                rgb_color = (int(r*255), int(g*255), int(b*255))
                layer_name = f"RGB_{rgb_color[0]:03d}_{rgb_color[1]:03d}_{rgb_color[2]:03d}"
            else:
                layer_name = "0"
                rgb_color = None

            # Створити шар якщо не існує
            if layer_name not in color_layers:
                color_layers[layer_name] = rgb_color
                try:
                    layer = doc.layers.add(name=layer_name)
                    # Встановити True Color для шару
                    if rgb_color:
                        layer.color = -1  # -1 означає True Color
                        layer.rgb = rgb_color
                except:
                    pass

            # Обробити items (елементи шляху)
            items = path_dict.get('items', [])

            for item in items:
                item_type = item[0]  # 'l', 'c', 're', 'qu'

                if item_type == 'l':  # LINE - ЛІНІЯ
                    if len(item) >= 3:
                        p1, p2 = item[1], item[2]
                        # Трансформувати координати
                        pt1 = transform_point(p1.x, p1.y)
                        pt2 = transform_point(p2.x, p2.y)

                        # Створити лінію з кольором
                        line = msp.add_line(pt1, pt2, dxfattribs={'layer': layer_name})
                        # Встановити True Color якщо є
                        if rgb_color:
                            line.rgb = rgb_color

                        stats['lines'] += 1

                elif item_type == 'c':  # CURVE - КРИВА БЕЗЬЄ
                    if len(item) >= 5:
                        # Трансформувати всі точки кривої
                        points = [transform_point(p.x, p.y) for p in item[1:5]]
                        if len(points) >= 2:
                            poly = msp.add_lwpolyline(points, dxfattribs={'layer': layer_name})
                            if rgb_color:
                                poly.rgb = rgb_color
                            stats['curves'] += 1

                elif item_type == 're':  # RECTANGLE - ПРЯМОКУТНИК
                    if len(item) >= 2:
                        rect = item[1]
                        # ✅ ПРАВИЛЬНО: Rect має x0, y0, x1, y1
                        if hasattr(rect, 'x0'):
                            x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                            # Трансформувати всі 4 кути
                            points = [
                                transform_point(x0, y0),
                                transform_point(x1, y0),
                                transform_point(x1, y1),
                                transform_point(x0, y1)
                            ]
                            poly = msp.add_lwpolyline(points, close=True, dxfattribs={'layer': layer_name})
                            if rgb_color:
                                poly.rgb = rgb_color
                            stats['rects'] += 1

                elif item_type == 'qu':  # QUAD - ЧОТИРИКУТНИК
                    if len(item) >= 5:
                        # Трансформувати всі точки чотирикутника
                        points = [transform_point(p.x, p.y) for p in item[1:5]]
                        poly = msp.add_lwpolyline(points, close=True, dxfattribs={'layer': layer_name})
                        if rgb_color:
                            poly.rgb = rgb_color
                        stats['quads'] += 1

        # Витягти текст
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:  # text block
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            bbox = span.get("bbox", [0, 0, 0, 0])
                            size = span.get("size", 2.5)

                            # Трансформувати позицію тексту
                            text_pos = transform_text_point(bbox[0], bbox[1])

                            # Додати текст без rotation - трансформація вже правильна
                            msp.add_text(
                                text,
                                dxfattribs={
                                    'layer': 'TEXT',
                                    'height': size * 0.7,
                                    'insert': text_pos,
                                    'rotation': 0  # Без додаткового повороту
                                }
                            )
                            stats['texts'] += 1

        # Зберегти DXF
        filename = f"page_{page_num:02d}.dxf"
        filepath = self.output_dir / filename
        doc.saveas(filepath)

        pdf_doc.close()

        # Вивести статистику
        print(f"\n✅ ЗБЕРЕЖЕНО: {filepath.name}")
        print(f"\n📊 СТАТИСТИКА:")
        print(f"   Векторних шляхів:  {stats['total_paths']}")
        print(f"   Ліній:             {stats['lines']}")
        print(f"   Кривих:            {stats['curves']}")
        print(f"   Прямокутників:     {stats['rects']}")
        print(f"   Чотирикутників:    {stats['quads']}")
        print(f"   Текстів:           {stats['texts']}")
        print(f"   Кольорових шарів:  {len(color_layers)}")

        total_objects = stats['lines'] + stats['curves'] + stats['rects'] + stats['quads'] + stats['texts']
        print(f"   📦 ВСЬОГО ОБ'ЄКТІВ: {total_objects}")

        return filepath, stats

    def convert_all_pages(self):
        """Конвертувати всі сторінки PDF"""
        print("\n" + "🔥"*35)
        print("   ПРОФЕСІЙНА ВЕКТОРНА КОНВЕРТАЦІЯ PDF → DXF")
        print("🔥"*35)

        pdf_doc = fitz.open(self.pdf_path)
        total_pages = len(pdf_doc)
        pdf_doc.close()

        print(f"\n📂 PDF файл: {self.pdf_path.name}")
        print(f"📄 Сторінок: {total_pages}")
        print(f"📂 Вихідна директорія: {self.output_dir.absolute()}")

        dxf_files = []
        total_stats = {
            'lines': 0,
            'curves': 0,
            'rects': 0,
            'quads': 0,
            'texts': 0,
            'total_paths': 0
        }

        # Конвертувати кожну сторінку
        for page_num in range(1, total_pages + 1):
            filepath, stats = self.convert_page(page_num)
            dxf_files.append(filepath)

            # Накопичити загальну статистику
            for key in total_stats:
                total_stats[key] += stats.get(key, 0)

        # Фінальний звіт
        print("\n" + "="*70)
        print("🎉 КОНВЕРТАЦІЯ ЗАВЕРШЕНА!")
        print("="*70)
        print(f"\n📦 Створено {len(dxf_files)} DXF файлів:")
        for i, dxf_file in enumerate(dxf_files, 1):
            print(f"   {i:2d}. {dxf_file.name}")

        print(f"\n📊 ЗАГАЛЬНА СТАТИСТИКА (всі {total_pages} сторінок):")
        print(f"   Векторних шляхів:  {total_stats['total_paths']}")
        print(f"   Ліній:             {total_stats['lines']}")
        print(f"   Кривих:            {total_stats['curves']}")
        print(f"   Прямокутників:     {total_stats['rects']}")
        print(f"   Чотирикутників:    {total_stats['quads']}")
        print(f"   Текстів:           {total_stats['texts']}")

        grand_total = (total_stats['lines'] + total_stats['curves'] +
                      total_stats['rects'] + total_stats['quads'] +
                      total_stats['texts'])
        print(f"\n   🏆 ВСЬОГО ОБ'ЄКТІВ: {grand_total}")

        return dxf_files


def main():
    """Головна функція"""
    pdf_path = "d:/autocad project/Технологія 06.06.24.pdf"

    if not Path(pdf_path).exists():
        print(f"❌ PDF не знайдено: {pdf_path}")
        input("\nEnter...")
        return

    print("\n" + "🎨"*35)
    print("   ПРОФЕСІЙНИЙ КОНВЕРТЕР PDF → DXF")
    print("   Якість як у онлайн-сервісів!")
    print("🎨"*35)

    converter = ProfessionalPDFtoDXFConverter(pdf_path)

    # Конвертувати всі сторінки
    dxf_files = converter.convert_all_pages()

    print("\n" + "="*70)
    print("✅ ГОТОВО!")
    print("="*70)
    print(f"\n📂 Всі файли збережено в: {converter.output_dir.absolute()}")
    print("\n🚀 Тепер можеш відкривати їх в AutoCAD!")

    input("\n\nНатисни Enter для виходу...")


if __name__ == "__main__":
    main()
