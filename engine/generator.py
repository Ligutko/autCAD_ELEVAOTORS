"""
SCHEMA GENERATOR - Генерація DXF креслень з config

Підтримує ДВА режими:
1. AUTO - автоматичні розрахунки (мінімум параметрів)
2. MANUAL - всі параметри задані вручну (професійне ТЗ)
"""

import ezdxf
import json
from pathlib import Path
from typing import Dict, Any, List
from calculator import ElevatorCalculator


class SchemaGenerator:
    """Генератор схем елеваторів"""

    def __init__(self):
        self.calculator = ElevatorCalculator()
        self.templates = {}
        self.doc = None
        self.msp = None

        # Кольори layers
        self.COLORS = {
            'silos': 5,        # Синій
            'elevators': 1,    # Червоний
            'conveyors': 1,    # Червоний
            'structure': 7,    # Білий/Чорний
            'text': 7          # Білий/Чорний
        }

    def load_templates(self, templates_dir: str = "ANALYSIS"):
        """Завантажити шаблони компонентів з JSON"""
        base_path = Path(templates_dir)

        try:
            # Завантажити силоси
            with open(base_path / "SILOS_ALL_FINAL.json", 'r', encoding='utf-8') as f:
                self.templates['silos'] = json.load(f)

            # Завантажити норії
            with open(base_path / "ELEVATORS_LIBRARY_V2.json", 'r', encoding='utf-8') as f:
                self.templates['elevators'] = json.load(f)

            # Завантажити конвеєри
            with open(base_path / "CONVEYORS_LIBRARY.json", 'r', encoding='utf-8') as f:
                self.templates['conveyors'] = json.load(f)

            print(f"OK Templates loaded: {len(self.templates)} types")
            return True

        except Exception as e:
            print(f"ERROR loading templates: {e}")
            return False

    def generate(self, config: Dict[str, Any], output_file: str) -> bool:
        """
        Головна функція генерації

        Args:
            config: Конфігурація проекту
            output_file: Шлях до вихідного DXF файлу

        Returns:
            True якщо успішно
        """
        mode = config.get('project', {}).get('mode', 'AUTO')

        print(f"="*80)
        print(f"SCHEMA GENERATOR - Mode: {mode}")
        print(f"="*80)

        # Створити новий DXF
        self.doc = ezdxf.new('R2018')
        self.msp = self.doc.modelspace()

        # Створити layers
        self._create_layers()

        if mode == 'AUTO':
            return self._generate_auto(config, output_file)
        elif mode == 'MANUAL':
            return self._generate_manual(config, output_file)
        else:
            print(f"ERROR: Unknown mode '{mode}'")
            return False

    def _generate_auto(self, config: Dict[str, Any], output_file: str) -> bool:
        """Автоматична генерація з розрахунками"""

        print("\nMode: AUTO - calculating parameters...")

        # 1. Розрахувати всі параметри
        calculated = self.calculator.calculate_all(config)

        print(f"  Silos: {config['silos']['count']}")
        print(f"  Conveyors: {calculated['geometry']['top_conveyor_length']/1000:.1f}m")
        print(f"  Elevators: {calculated['equipment']['elevators']['count']} x {calculated['equipment']['elevators']['power_kw']}kW")

        # Перевірити validation
        if not calculated['validation']['valid']:
            print("\nERROR: Validation failed!")
            for err in calculated['validation']['errors']:
                print(f"  - {err}")
            return False

        if calculated['validation']['warnings']:
            print("\nWARNINGS:")
            for warn in calculated['validation']['warnings']:
                print(f"  ! {warn}")

        # 2. Завантажити шаблон силосу
        if not self.templates:
            print("\nLoading templates...")
            if not self.load_templates():
                print("ERROR: Cannot load templates!")
                return False

        # Взяти ВЕРХНІЙ силос як шаблон (він ПОВНИЙ з усіма деталями!)
        # silos_bottom має тільки 20 ліній - це неповний шаблон
        # silos_top має 108-144 лінії - це РЕАЛЬНЕ професійне креслення
        silo_template = self.templates['silos']['silos_top'][0]

        print(f"\nUsing REAL template: {silo_template['id']}")
        print(f"  Template has {silo_template['lines_count']} lines (FULL professional drawing)")

        # 3. Малювати силоси
        print(f"\nDrawing {config['silos']['count']} silos...")

        silos_count = config['silos']['count']
        default_diameter = config['silos']['diameter']
        default_height = config['silos']['height']
        spacing = config['silos'].get('spacing', 150)

        # Custom розміри для окремих силосів
        custom_sizes = {}
        if 'custom_sizes' in config['silos']:
            for custom in config['silos']['custom_sizes']:
                custom_sizes[custom['number']] = custom

        current_x = 0

        for i in range(silos_count):
            silo_number = i + 1

            # Перевірити чи є custom розмір
            if silo_number in custom_sizes:
                silo_diameter = custom_sizes[silo_number].get('diameter', default_diameter)
                silo_height = custom_sizes[silo_number].get('height', default_height)
                print(f"  Silo #{silo_number} at X={current_x/1000:.1f}m (CUSTOM: {silo_diameter/1000:.0f}m x {silo_height/1000:.0f}m)")
            else:
                silo_diameter = default_diameter
                silo_height = default_height
                print(f"  Silo #{silo_number} at X={current_x/1000:.1f}m")

            self._draw_silo_from_template(
                silo_template,
                offset_x=current_x,
                offset_y=0,
                number=silo_number,
                scale_x=silo_diameter / default_diameter,
                scale_y=silo_height / default_height
            )

            # Наступна позиція
            current_x += silo_diameter + spacing

        # 4. Малювати конвеєри
        print(f"\nDrawing conveyors...")

        # Верхній конвеєр (над силосами) - від 0 до current_x (кінець останнього силосу)
        top_conveyor_length = current_x
        self._draw_conveyor(
            start_x=0,
            start_y=40000,  # Над силосами
            length=top_conveyor_length,
            conveyor_id="T9",
            level="top"
        )
        print(f"  Conveyor T9: {top_conveyor_length/1000:.1f}m (auto-adjusted)")

        # Нижній конвеєр (під силосами)
        bottom_conveyor_length = current_x - default_diameter
        self._draw_conveyor(
            start_x=default_diameter/2,
            start_y=-5000,  # Під силосами
            length=bottom_conveyor_length,
            conveyor_id="T13",
            level="bottom"
        )
        print(f"  Conveyor T13: {bottom_conveyor_length/1000:.1f}m (auto-adjusted)")

        # 5. Малювати норії
        print(f"\nDrawing {calculated['equipment']['elevators']['count']} elevators...")

        elevators_count = calculated['equipment']['elevators']['count']
        elevator_height = calculated['equipment']['elevators']['height']

        # Розподілити норії рівномірно по довжині
        total_length = current_x  # Загальна довжина
        for i in range(elevators_count):
            # Позиція рівномірно розподілена
            x_pos = (i + 0.5) * (total_length / elevators_count)
            y_pos = 0

            self._draw_elevator(
                x=x_pos,
                y_bottom=y_pos - 1000,
                height=elevator_height,
                elevator_id=f"H{i+1}"
            )

            print(f"  Elevator H{i+1} at X={x_pos/1000:.1f}m, height={elevator_height/1000:.1f}m")

        # 6. Додати текстові мітки
        self._add_title_block(config, calculated)

        # 7. Зберегти DXF
        print(f"\nSaving DXF: {output_file}")
        self.doc.saveas(output_file)

        print(f"\n{'='*80}")
        print(f"SUCCESS! Schema generated: {output_file}")
        print(f"{'='*80}")

        return True

    def _generate_manual(self, config: Dict[str, Any], output_file: str) -> bool:
        """Ручна генерація (всі параметри задані)"""

        print("\nMode: MANUAL - using provided parameters...")

        # TODO: Реалізувати MANUAL режим
        print("MANUAL mode - coming soon!")

        return False

    def _create_layers(self):
        """Створити layers для кольорів"""
        layers_def = {
            'RGB_000_000_255': self.COLORS['silos'],      # Синій - силоси
            'RGB_255_000_000': self.COLORS['elevators'],  # Червоний - норії/конвеєри
            'RGB_000_000_000': self.COLORS['structure'],  # Структура
            '0': 256  # Default ByLayer
        }

        for layer_name, color in layers_def.items():
            if layer_name not in self.doc.layers:
                layer = self.doc.layers.add(layer_name)
                layer.color = color

    def _draw_silo_from_template(self, template: Dict, offset_x: float, offset_y: float, number: int, scale_x: float = 1.0, scale_y: float = 1.0):
        """Намалювати силос з шаблону зі зміщенням та масштабуванням"""

        lines = template['geometry']['lines']

        # Знайти центр шаблону для масштабування
        template_center_x = template['center'][0]
        template_center_y = template['center'][1]

        for line_data in lines:
            start = line_data['start']
            end = line_data['end']

            # Масштабувати відносно центру шаблону
            scaled_start_x = template_center_x + (start[0] - template_center_x) * scale_x
            scaled_start_y = template_center_y + (start[1] - template_center_y) * scale_y

            scaled_end_x = template_center_x + (end[0] - template_center_x) * scale_x
            scaled_end_y = template_center_y + (end[1] - template_center_y) * scale_y

            # Застосувати offset
            new_start = (scaled_start_x + offset_x, scaled_start_y + offset_y, start[2])
            new_end = (scaled_end_x + offset_x, scaled_end_y + offset_y, end[2])

            # Намалювати лінію
            new_line = self.msp.add_line(new_start, new_end)
            new_line.dxf.layer = 'RGB_000_000_255'  # Синій

    def _draw_conveyor(self, start_x: float, start_y: float, length: float, conveyor_id: str, level: str):
        """Намалювати конвеєр (горизонтальна лінія)"""

        # Головна лінія конвеєра
        line = self.msp.add_line(
            (start_x, start_y, 0),
            (start_x + length, start_y, 0)
        )
        line.dxf.layer = 'RGB_255_000_000'  # Червоний

        # Додаткові лінії (контур)
        offset = 500  # 500мм ширина

        line2 = self.msp.add_line(
            (start_x, start_y + offset, 0),
            (start_x + length, start_y + offset, 0)
        )
        line2.dxf.layer = 'RGB_255_000_000'

        line3 = self.msp.add_line(
            (start_x, start_y - offset, 0),
            (start_x + length, start_y - offset, 0)
        )
        line3.dxf.layer = 'RGB_255_000_000'

        # Текстова мітка
        text = self.msp.add_text(
            conveyor_id,
            dxfattribs={
                'layer': '0',
                'height': 800
            }
        )
        text.set_placement((start_x + length/2, start_y + 1500, 0))

    def _draw_elevator(self, x: float, y_bottom: float, height: float, elevator_id: str):
        """Намалювати норію (вертикальна лінія)"""

        # Головна вертикальна лінія
        line = self.msp.add_line(
            (x, y_bottom, 0),
            (x, y_bottom + height, 0)
        )
        line.dxf.layer = 'RGB_255_000_000'  # Червоний

        # Контур (2 лінії по боках)
        offset = 300

        line2 = self.msp.add_line(
            (x + offset, y_bottom, 0),
            (x + offset, y_bottom + height, 0)
        )
        line2.dxf.layer = 'RGB_255_000_000'

        line3 = self.msp.add_line(
            (x - offset, y_bottom, 0),
            (x - offset, y_bottom + height, 0)
        )
        line3.dxf.layer = 'RGB_255_000_000'

        # Текстова мітка
        text = self.msp.add_text(
            elevator_id,
            dxfattribs={
                'layer': '0',
                'height': 800
            }
        )
        text.set_placement((x + 1500, y_bottom + height/2, 0))

    def _add_title_block(self, config: Dict, calculated: Dict):
        """Додати текстовий блок з інформацією"""

        project_name = config.get('project', {}).get('name', 'Elevator Project')

        # Заголовок
        title = self.msp.add_text(
            project_name,
            dxfattribs={
                'layer': '0',
                'height': 2000
            }
        )
        title.set_placement((-50000, 50000, 0))

        # Параметри
        info_lines = [
            f"Silos: {config['silos']['count']} x {config['silos']['diameter']/1000:.0f}m",
            f"Capacity: {calculated['bom']['summary']['total_capacity_tons']:.0f} tons",
            f"Throughput: {config.get('throughput', 100)} t/h",
            f"Elevators: {calculated['equipment']['elevators']['count']} x {calculated['equipment']['elevators']['power_kw']}kW"
        ]

        y_pos = 45000
        for line in info_lines:
            text = self.msp.add_text(
                line,
                dxfattribs={
                    'layer': '0',
                    'height': 1000
                }
            )
            text.set_placement((-50000, y_pos, 0))
            y_pos -= 1500


# Тестування
if __name__ == "__main__":
    import sys

    # Завантажити config
    config_file = "configs/example_7silos_auto.json"

    if len(sys.argv) > 1:
        config_file = sys.argv[1]

    print(f"Loading config: {config_file}")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Створити генератор
    generator = SchemaGenerator()

    # Згенерувати схему
    output_file = "OUTPUT/elevator_generated.dxf"

    success = generator.generate(config, output_file)

    if success:
        print(f"\nSUCCESS! Open in AutoCAD: {output_file}")
    else:
        print("\nFAILED!")
        sys.exit(1)
