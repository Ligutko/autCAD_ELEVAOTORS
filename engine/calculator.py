"""
CALCULATION ENGINE - Автоматичні розрахунки параметрів елеватора

Розраховує всі параметри на основі мінімального config:
- Довжини конвеєрів
- Висоти норій
- Кількість обладнання
- Специфікацію (BOM)
"""

import math
from typing import Dict, Any


class ElevatorCalculator:
    """Розрахунки для елеватора"""

    def __init__(self):
        # Константи
        self.GRAVITY_ANGLE = 45  # градусів (кут самопливу)
        self.GATES_PER_SILO = 12  # засувок на силос
        self.SUPPORT_SPACING = 24000  # мм (відстань між опорами естакади)

        # Таблиця потужностей норій (висота → потужність кВт)
        self.ELEVATOR_POWER_TABLE = {
            25000: 11,
            30000: 11,
            33000: 15,
            35000: 15,
            40000: 18,
            45000: 22
        }

        # Таблиця типів конвеєрів (продуктивність → тип)
        self.CONVEYOR_TYPES = {
            50: "ТЛ-50K",
            100: "ТЦС-320",
            150: "ТЦС-400",
            200: "ТЦС-500"
        }

    def calculate_all(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Головна функція - розраховує ВСЕ

        Args:
            config: Конфігурація з мінімальними параметрами

        Returns:
            Повний набір розрахованих параметрів
        """
        result = {
            'geometry': self.calculate_geometry(config),
            'equipment': self.calculate_equipment(config),
            'bom': self.calculate_bom(config),
            'validation': self.validate(config)
        }

        return result

    def calculate_geometry(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Розрахунки геометрії"""

        silos = config['silos']
        silos_count = silos['count']
        diameter = silos['diameter']
        spacing = silos.get('spacing', 150)

        # Довжина нижнього конвеєра (між силосами)
        bottom_conveyor_length = (silos_count - 1) * (diameter + spacing)

        # Довжина верхнього конвеєра (над силосами)
        top_conveyor_length = silos_count * diameter + (silos_count - 1) * spacing

        # Висота норій (з урахуванням висоти силосу)
        silo_height = silos.get('height', 35000)
        elevator_height = silo_height + 5000  # +5м над силосом

        # Кількість опор естакади
        supports_count = int(top_conveyor_length / self.SUPPORT_SPACING) + 1

        return {
            'bottom_conveyor_length': round(bottom_conveyor_length, 2),
            'top_conveyor_length': round(top_conveyor_length, 2),
            'elevator_height': round(elevator_height, 2),
            'supports_count': supports_count,
            'total_width': round(top_conveyor_length + diameter, 2),
            'total_height': round(elevator_height + 10000, 2)  # +10м для голови
        }

    def calculate_equipment(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Розрахунки обладнання"""

        silos = config['silos']
        throughput = config.get('throughput', 100)

        # Кількість норій (зазвичай 1 на 2 силоси)
        elevators_count = math.ceil(silos['count'] / 2)

        # Потужність норії
        elevator_height = self.calculate_geometry(config)['elevator_height']
        elevator_power = self._get_elevator_power(elevator_height)

        # Тип конвеєра
        conveyor_type = self._get_conveyor_type(throughput)

        # Кількість засувок
        gates_count = silos['count'] * self.GATES_PER_SILO

        # Кількість вентиляторів
        aeration_fans = silos['count'] * silos.get('aeration_fans', 4)
        roof_fans = silos['count'] * silos.get('roof_fans', 2)

        return {
            'elevators': {
                'count': elevators_count,
                'type': config.get('elevators', {}).get('type', 'У13-УН'),
                'height': elevator_height,
                'power_kw': elevator_power,
                'capacity_tph': throughput // elevators_count
            },
            'conveyors': {
                'type': conveyor_type,
                'top_length': self.calculate_geometry(config)['top_conveyor_length'],
                'bottom_length': self.calculate_geometry(config)['bottom_conveyor_length'],
                'capacity_tph': throughput
            },
            'gates': {
                'count': gates_count,
                'type': config.get('gates', {}).get('type', 'У13-ТЭА'),
                'size': config.get('gates', {}).get('size', '350x350')
            },
            'fans': {
                'aeration': aeration_fans,
                'roof': roof_fans
            }
        }

    def calculate_bom(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Розрахунок специфікації (Bill of Materials)"""

        silos = config['silos']
        geometry = self.calculate_geometry(config)
        equipment = self.calculate_equipment(config)

        # Обчислення об'єму одного силосу (циліндр)
        radius = silos['diameter'] / 2 / 1000  # в метрах
        height = silos['height'] / 1000  # в метрах
        volume_per_silo = math.pi * radius**2 * height
        total_volume = volume_per_silo * silos['count']

        bom = {
            'summary': {
                'total_silos': silos['count'],
                'total_capacity_m3': round(total_volume, 2),
                'total_capacity_tons': round(total_volume * 0.75, 2),  # зерно ~0.75 т/м³
                'throughput_tph': config.get('throughput', 100)
            },
            'silos': {
                'count': silos['count'],
                'type': silos.get('type', f"МСВУ-{silos['diameter']/1000:.0f}.13"),
                'diameter_mm': silos['diameter'],
                'height_mm': silos['height'],
                'capacity_m3_each': round(volume_per_silo, 2)
            },
            'elevators': {
                'count': equipment['elevators']['count'],
                'type': equipment['elevators']['type'],
                'height_mm': equipment['elevators']['height'],
                'power_kw_each': equipment['elevators']['power_kw'],
                'total_power_kw': equipment['elevators']['power_kw'] * equipment['elevators']['count']
            },
            'conveyors': {
                'type_top': equipment['conveyors']['type'],
                'length_top_mm': equipment['conveyors']['top_length'],
                'type_bottom': equipment['conveyors']['type'],
                'length_bottom_mm': equipment['conveyors']['bottom_length']
            },
            'gates': {
                'count': equipment['gates']['count'],
                'type': equipment['gates']['type'],
                'size': equipment['gates']['size']
            },
            'structure': {
                'estacade_length_mm': geometry['top_conveyor_length'],
                'supports_count': geometry['supports_count'],
                'gallery_length_mm': geometry['bottom_conveyor_length']
            },
            'fans': {
                'aeration_11kw': equipment['fans']['aeration'],
                'roof_025kw': equipment['fans']['roof']
            }
        }

        return bom

    def validate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Перевірка правил та обмежень"""

        warnings = []
        errors = []

        silos = config['silos']
        geometry = self.calculate_geometry(config)

        # Перевірка кута самопливу
        # (тут спрощена перевірка, в реальності треба враховувати відстані)

        # Перевірка що силосів не надто багато
        if silos['count'] > 12:
            warnings.append(f"Велика кількість силосів ({silos['count']}). Рекомендовано розділити на модулі.")

        # Перевірка що spacing достатній
        spacing = silos.get('spacing', 150)
        if spacing < 100:
            errors.append(f"Spacing {spacing}мм занадто малий. Мінімум 100мм.")

        # Перевірка що довжина естакади не надто велика
        if geometry['top_conveyor_length'] > 200000:  # 200м
            warnings.append(f"Довжина естакади {geometry['top_conveyor_length']/1000:.1f}м дуже велика.")

        # Перевірка непарної кількості
        if silos['count'] % 2 == 1:
            warnings.append(f"Непарна кількість силосів ({silos['count']}). Один конвеєр буде коротшим.")

        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }

    def _get_elevator_power(self, height_mm: float) -> float:
        """Визначити потужність норії по висоті"""
        height = height_mm

        # Знайти найближчу висоту в таблиці
        for h in sorted(self.ELEVATOR_POWER_TABLE.keys()):
            if height <= h:
                return self.ELEVATOR_POWER_TABLE[h]

        # Якщо вище за всі - взяти максимальну
        return self.ELEVATOR_POWER_TABLE[max(self.ELEVATOR_POWER_TABLE.keys())]

    def _get_conveyor_type(self, throughput: int) -> str:
        """Визначити тип конвеєра по продуктивності"""
        for capacity in sorted(self.CONVEYOR_TYPES.keys()):
            if throughput <= capacity:
                return self.CONVEYOR_TYPES[capacity]

        # Якщо більше за всі
        return self.CONVEYOR_TYPES[max(self.CONVEYOR_TYPES.keys())]


# Тестування
if __name__ == "__main__":
    calc = ElevatorCalculator()

    # Тестовий config
    test_config = {
        'silos': {
            'count': 7,
            'diameter': 22000,
            'height': 35000,
            'type': 'МСВУ-220.13.B12',
            'spacing': 150,
            'aeration_fans': 4,
            'roof_fans': 2
        },
        'throughput': 100
    }

    result = calc.calculate_all(test_config)

    print("="*80)
    print("CALCULATION ENGINE - ТЕСТ")
    print("="*80)

    print("\nГЕОМЕТРІЯ:")
    for key, value in result['geometry'].items():
        print(f"  {key}: {value}")

    print("\nОБЛАДНАННЯ:")
    print(f"  Норії: {result['equipment']['elevators']['count']} шт, {result['equipment']['elevators']['power_kw']} кВт")
    print(f"  Конвеєри: {result['equipment']['conveyors']['type']}")
    print(f"  Засувки: {result['equipment']['gates']['count']} шт")

    print("\nСПЕЦИФІКАЦІЯ:")
    print(f"  Загальна ємність: {result['bom']['summary']['total_capacity_m3']:.0f} м³")
    print(f"  Загальна ємність: {result['bom']['summary']['total_capacity_tons']:.0f} тонн")
    print(f"  Продуктивність: {result['bom']['summary']['throughput_tph']} т/год")

    print("\nВАЛІДАЦІЯ:")
    print(f"  Valid: {result['validation']['valid']}")
    if result['validation']['warnings']:
        for w in result['validation']['warnings']:
            print(f"  WARNING: {w}")
    if result['validation']['errors']:
        for e in result['validation']['errors']:
            print(f"  ERROR: {e}")

    print("\nOK - Calculation Engine працює!")
