# -*- coding: utf-8 -*-
"""
PDF to AutoCAD Converter
Перетворює кожну сторінку PDF елеватора в окремий DXF/DWG файл
"""
import sys
import io
import os
from pathlib import Path

# Fix encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, "D:/autocad project/autocad-mcp")

import ezdxf
from ezdxf.enums import TextEntityAlignment
from autocad_helper import AutoCADHelper

class PDFToAutoCADConverter:
    """Конвертер PDF технологічних схем елеватора в AutoCAD"""

    def __init__(self, output_dir="autocad_drawings"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.acad = None

    def create_page_data(self):
        """Створити дані для кожної сторінки PDF на основі аналізу"""
        # ВАЖЛИВО: Координати в метрах для правильного масштабу!
        # Діаметр силоса = 22м, тому відстань між центрами мінімум 24-25м

        pages = {
            1: {
                "name": "Схема_технологічного_процесу",
                "title": "Схема технологічного процесу",
                "equipment": [
                    # Силоси МСВУ 220.13.В12 (2 ряди по 3 силоси)
                    # Верхній ряд (Черга 1)
                    {"type": "silo", "tag": "МСВУ-1", "x": 0, "y": 25, "diameter": 22000, "height": 21422},
                    {"type": "silo", "tag": "МСВУ-2", "x": 25, "y": 25, "diameter": 22000, "height": 21422},

                    # Нижній ряд (Черги 2 та 3)
                    {"type": "silo", "tag": "МСВУ-3", "x": 0, "y": 0, "diameter": 22000, "height": 21422},
                    {"type": "silo", "tag": "МСВУ-4", "x": 25, "y": 0, "diameter": 22000, "height": 21422},
                    {"type": "silo", "tag": "МСВУ-5", "x": 50, "y": 0, "diameter": 22000, "height": 21422},
                    {"type": "silo", "tag": "МСВУ-6", "x": 75, "y": 0, "diameter": 22000, "height": 21422},

                    # Норії (вертикальний транспорт) - зліва від силосів
                    {"type": "elevator", "tag": "H1", "x": -20, "y": 40, "height": 33000, "capacity": 100},
                    {"type": "elevator", "tag": "H3", "x": -15, "y": 40, "height": 33000, "capacity": 100},
                    {"type": "elevator", "tag": "H4", "x": -10, "y": 40, "height": 33000, "capacity": 100},
                    {"type": "elevator", "tag": "H5", "x": 30, "y": 40, "height": 33000, "capacity": 100},
                    {"type": "elevator", "tag": "H6", "x": 70, "y": 40, "height": 32500, "capacity": 100},

                    # Транспортери (горизонтальні лінії)
                    {"type": "conveyor", "tag": "T7", "x1": 0, "y1": 35, "x2": 30, "y2": 35, "capacity": 100},
                    {"type": "conveyor", "tag": "T8", "x1": 0, "y1": 37, "x2": 25, "y2": 37, "capacity": 100},
                    {"type": "conveyor", "tag": "T9", "x1": 0, "y1": -5, "x2": 20, "y2": -5, "capacity": 100},
                    {"type": "conveyor", "tag": "T10", "x1": 30, "y1": 30, "x2": 50, "y2": 30, "capacity": 100},
                    {"type": "conveyor", "tag": "T11", "x1": 50, "y1": -5, "x2": 70, "y2": -5, "capacity": 100},
                    {"type": "conveyor", "tag": "T12", "x1": 0, "y1": -10, "x2": 20, "y2": -10, "capacity": 100},
                ]
            },
            2: {
                "name": "План_розміщення_відм_0.000",
                "title": "План розміщення технологічного обладнання на відм. ±0.000 м",
                "equipment": []  # Буде заповнено з детального креслення
            },
            3: {
                "name": "План_розміщення_естакади",
                "title": "План розміщення технологічного обладнання на естакадах",
                "equipment": []
            },
            4: {
                "name": "Напрям_транспортування_НА_силоса",
                "title": "Напрям транспортування на силоса",
                "equipment": []
            },
            5: {
                "name": "Напрям_транспортування_ВІД_силосів",
                "title": "Напрям транспортування від силосів",
                "equipment": []
            },
            6: {
                "name": "Фасад_силосів",
                "title": "Фасад силосів",
                "equipment": []
            },
            7: {
                "name": "Загальний_вид",
                "title": "Загальний вид елеватора",
                "equipment": []
            }
        }
        return pages

    def create_dxf_for_page(self, page_num, page_data):
        """Створити DXF файл для конкретної сторінки"""
        print(f"\n{'='*70}")
        print(f"📄 Створюю DXF для сторінки {page_num}: {page_data['title']}")
        print(f"{'='*70}")

        # Створити новий DXF документ (AutoCAD 2010)
        doc = ezdxf.new('R2010', setup=True)
        msp = doc.modelspace()

        # Додати шари
        doc.layers.add(name="EQUIPMENT", color=1)  # Червоний
        doc.layers.add(name="TEXT", color=3)       # Зелений
        doc.layers.add(name="DIMENSIONS", color=4) # Блакитний
        doc.layers.add(name="SILOS", color=2)      # Жовтий
        doc.layers.add(name="CONVEYORS", color=6)  # Пурпурний

        # Додати заголовок
        msp.add_text(
            page_data['title'],
            dxfattribs={
                'layer': 'TEXT',
                'height': 3,
                'insert': (-20, 50),
                'style': 'OpenSans'
            }
        )

        # Додати обладнання
        equipment_count = len(page_data.get('equipment', []))
        print(f"   Обладнання до малювання: {equipment_count} одиниць")

        for idx, item in enumerate(page_data.get('equipment', []), 1):
            eq_type = item['type']

            if eq_type == 'silo':
                self._draw_silo_dxf(msp, item)
                print(f"   ✓ [{idx}/{equipment_count}] Силос {item['tag']} - D={item['diameter']/1000}м")

            elif eq_type == 'elevator':
                self._draw_elevator_dxf(msp, item)
                print(f"   ✓ [{idx}/{equipment_count}] Норія {item['tag']} - H={item['height']/1000}м")

            elif eq_type == 'conveyor':
                self._draw_conveyor_dxf(msp, item)
                length = ((item['x2']-item['x1'])**2 + (item['y2']-item['y1'])**2)**0.5
                print(f"   ✓ [{idx}/{equipment_count}] Транспортер {item['tag']} - L={length:.1f}м")

        # Зберегти DXF
        filename = f"{page_data['name']}_page{page_num}.dxf"
        filepath = self.output_dir / filename
        doc.saveas(filepath)

        print(f"\n✅ DXF збережено: {filepath}")
        return filepath

    def _draw_silo_dxf(self, msp, silo):
        """Намалювати силос у DXF"""
        x, y = silo['x'], silo['y']
        radius = silo['diameter'] / 2000  # мм -> м, потім радіус

        # Коло силосу
        msp.add_circle(
            center=(x, y),
            radius=radius,
            dxfattribs={'layer': 'SILOS'}
        )

        # Позначення
        msp.add_text(
            silo['tag'],
            dxfattribs={
                'layer': 'TEXT',
                'height': 2.5,
                'insert': (x, y)
            }
        ).set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)

        # Характеристики
        info = f"D={silo['diameter']/1000}м\nH={silo['height']/1000}м"
        msp.add_text(
            info,
            dxfattribs={
                'layer': 'TEXT',
                'height': 1.5,
                'insert': (x, y - radius - 3)
            }
        ).set_placement((x, y - radius - 3), align=TextEntityAlignment.TOP_CENTER)

    def _draw_elevator_dxf(self, msp, elevator):
        """Намалювати норію (bucket elevator) у DXF"""
        x, y = elevator['x'], elevator['y']
        height = elevator['height'] / 1000  # мм -> м
        width = 4  # ширина норії

        # Прямокутник норії
        msp.add_lwpolyline(
            [(x-width/2, y), (x+width/2, y), (x+width/2, y+height), (x-width/2, y+height)],
            close=True,
            dxfattribs={'layer': 'EQUIPMENT'}
        )

        # Стрілка вгору (напрям руху)
        arrow_y = y + height/2
        msp.add_line(
            (x, arrow_y), (x, arrow_y + 5),
            dxfattribs={'layer': 'EQUIPMENT'}
        )
        # Кінчик стрілки
        msp.add_line((x, arrow_y + 5), (x-1, arrow_y + 3), dxfattribs={'layer': 'EQUIPMENT'})
        msp.add_line((x, arrow_y + 5), (x+1, arrow_y + 3), dxfattribs={'layer': 'EQUIPMENT'})

        # Текст
        msp.add_text(
            f"{elevator['tag']}\n{elevator['capacity']} т/год",
            dxfattribs={
                'layer': 'TEXT',
                'height': 1.8,
                'insert': (x + width/2 + 2, y + height/2)
            }
        )

    def _draw_conveyor_dxf(self, msp, conveyor):
        """Намалювати транспортер (конвеєр) у DXF"""
        x1, y1 = conveyor['x1'], conveyor['y1']
        x2, y2 = conveyor['x2'], conveyor['y2']

        # Лінія транспортера (подвійна для об'єму)
        offset = 0.5
        dx = y2 - y1
        dy = x2 - x1
        length = (dx**2 + dy**2)**0.5

        if length > 0:
            dx_norm = dx / length * offset
            dy_norm = dy / length * offset

            # Дві паралельні лінії
            msp.add_line(
                (x1 - dy_norm, y1 + dx_norm),
                (x2 - dy_norm, y2 + dx_norm),
                dxfattribs={'layer': 'CONVEYORS'}
            )
            msp.add_line(
                (x1 + dy_norm, y1 - dx_norm),
                (x2 + dy_norm, y2 - dx_norm),
                dxfattribs={'layer': 'CONVEYORS'}
            )

        # Стрілка напрямку
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        arrow_len = 3

        if length > 0:
            arrow_dx = (x2 - x1) / length * arrow_len
            arrow_dy = (y2 - y1) / length * arrow_len

            msp.add_line(
                (mid_x, mid_y),
                (mid_x + arrow_dx, mid_y + arrow_dy),
                dxfattribs={'layer': 'CONVEYORS', 'color': 1}
            )

        # Текст
        msp.add_text(
            conveyor['tag'],
            dxfattribs={
                'layer': 'TEXT',
                'height': 2.0,
                'insert': (mid_x, mid_y + 2)
            }
        )

    def convert_all_pages(self):
        """Перетворити всі сторінки PDF"""
        print("\n" + "="*70)
        print("🚀 PDF TO AUTOCAD CONVERTER")
        print("="*70)
        print(f"📂 Вихідна директорія: {self.output_dir.absolute()}")

        pages = self.create_page_data()
        dxf_files = []

        for page_num, page_data in pages.items():
            dxf_file = self.create_dxf_for_page(page_num, page_data)
            dxf_files.append(dxf_file)

        print("\n" + "="*70)
        print(f"✅ ГОТОВО! Створено {len(dxf_files)} DXF файлів:")
        print("="*70)

        for i, dxf_file in enumerate(dxf_files, 1):
            print(f"   {i}. {dxf_file.name}")

        return dxf_files

    def import_to_autocad(self, dxf_files):
        """Імпортувати DXF файли в AutoCAD"""
        print("\n" + "="*70)
        print("📥 ІМПОРТ В AUTOCAD")
        print("="*70)

        # Ініціалізація AutoCAD Helper
        self.acad = AutoCADHelper()
        if not self.acad.init():
            print("❌ Не вдалося підключитися до AutoCAD!")
            return False

        print("\n✅ AutoCAD підключено!")
        print("\nІмпортую DXF файли...\n")

        for idx, dxf_file in enumerate(dxf_files, 1):
            print(f"[{idx}/{len(dxf_files)}] Імпортую {dxf_file.name}...")

            # Створити новий документ для кожної сторінки
            # (або можна імпортувати в поточний)
            dxf_path = str(dxf_file.absolute()).replace("\\", "/")

            # Команда імпорту DXF
            success = self.acad.cmd(
                f'(command "._dxfin" "{dxf_path}")',
                f"Імпорт {dxf_file.name}"
            )

            if success:
                print(f"   ✅ Успішно імпортовано!")
                # Zoom extents
                self.acad.zoom_extents()
            else:
                print(f"   ⚠️  Помилка імпорту")

        print("\n" + "="*70)
        print("✅ ІМПОРТ ЗАВЕРШЕНО!")
        print("="*70)

        return True


def main():
    """Головна функція"""
    print("\n" + "🎨"*35)
    print("   КОНВЕРТЕР PDF ЕЛЕВАТОРА → AUTOCAD DXF/DWG")
    print("🎨"*35)

    converter = PDFToAutoCADConverter(output_dir="autocad_drawings")

    # Крок 1: Створити DXF файли
    dxf_files = converter.convert_all_pages()

    # Крок 2: Запитати користувача чи імпортувати в AutoCAD
    print("\n" + "="*70)
    choice = input("\n📥 Бажаєте імпортувати файли в AutoCAD зараз? (y/n): ")

    if choice.lower() in ['y', 'yes', 'так', 'т']:
        converter.import_to_autocad(dxf_files)
    else:
        print("\n✅ DXF файли створено!")
        print("   Ви можете відкрити їх пізніше в AutoCAD вручну.")

    print("\n" + "="*70)
    print("🎉 РОБОТА ЗАВЕРШЕНА!")
    print("="*70)
    input("\nНатисніть Enter для виходу...")


if __name__ == "__main__":
    main()
