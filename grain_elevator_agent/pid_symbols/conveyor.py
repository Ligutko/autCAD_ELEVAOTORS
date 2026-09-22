# -*- coding: utf-8 -*-
"""
Символи конвеєрів для P&ID діаграм
Типи: Chain (ланцюговий), Belt (стрічковий)
"""
import math
from typing import Tuple, List
from .base_symbol import PIDSymbol, SymbolParams

class ConveyorSymbol(PIDSymbol):
    """
    Конвеєр (ланцюговий або стрічковий)

    Параметри:
    - conveyor_type: "CHAIN" або "BELT"
    - start_point: (x, y) початок
    - end_point: (x, y) кінець
    - capacity: Продуктивність (т/год)
    - power: Потужність двигуна (кВт)
    """

    def __init__(self, autocad_helper, conveyor_type: str, capacity: float, power: float):
        super().__init__(autocad_helper)
        self.conveyor_type = conveyor_type  # "CHAIN" or "BELT"
        self.capacity = capacity
        self.power = power
        self.symbol_type = f"CONVEYOR_{conveyor_type}"

    def draw(self, params: SymbolParams) -> bool:
        """Намалювати конвеєр"""
        if not self.validate_params(params):
            return False

        # Для конвеєра position - це початок, а потрібна кінцева точка
        # Передаємо через label як "x1,y1,x2,y2"
        try:
            coords = params.label.split("->")
            start_label, end_coords = coords[0], coords[1]

            x1, y1 = params.position
            x2, y2 = map(float, end_coords.strip().split(","))
        except:
            print(f"⚠️ Неправильний формат координат конвеєра: {params.label}")
            return False

        print(f"🔗 Малюю конвеєр {self.conveyor_type} від ({x1},{y1}) до ({x2},{y2})")

        # Головна лінія конвеєра
        self.acad.line(x1, y1, x2, y2)

        # Напрямок потоку (стрілка)
        self._draw_arrow(x1, y1, x2, y2)

        # Мітка типу конвеєра
        mid_x = (x1 + x2) / 2.0
        mid_y = (y1 + y2) / 2.0

        # Зміщуємо мітку вбік від лінії
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx**2 + dy**2)

        if length > 0:
            # Перпендикуляр
            offset_x = -dy / length * 2.0
            offset_y = dx / length * 2.0

            label_x = mid_x + offset_x
            label_y = mid_y + offset_y
        else:
            label_x = mid_x + 2.0
            label_y = mid_y + 2.0

        # Формуємо мітку
        label_text = f"{start_label} {self.capacity:.0f}т/г"
        self._draw_label(label_x, label_y, label_text, params.label_height)

        # Додаємо символ типу конвеєра
        if self.conveyor_type == "CHAIN":
            self._draw_chain_symbol(mid_x, mid_y)
        elif self.conveyor_type == "BELT":
            self._draw_belt_symbol(mid_x, mid_y)

        print(f"   ✅ Конвеєр {start_label} створено")
        return True

    def _draw_arrow(self, x1: float, y1: float, x2: float, y2: float):
        """Малює стрілку напрямку потоку"""
        dx = x2 - x1
        dy = y2 - y1
        length = math.sqrt(dx**2 + dy**2)

        if length == 0:
            return

        # Нормалізовані вектори
        ux = dx / length
        uy = dy / length

        # Точка стрілки (75% від початку)
        arrow_x = x1 + dx * 0.75
        arrow_y = y1 + dy * 0.75

        # Розмір стрілки
        arrow_size = min(length * 0.1, 2.0)

        # Крила стрілки
        perp_x = -uy
        perp_y = ux

        wing1_x = arrow_x - ux * arrow_size + perp_x * arrow_size * 0.5
        wing1_y = arrow_y - uy * arrow_size + perp_y * arrow_size * 0.5

        wing2_x = arrow_x - ux * arrow_size - perp_x * arrow_size * 0.5
        wing2_y = arrow_y - uy * arrow_size - perp_y * arrow_size * 0.5

        # Малюємо стрілку
        self.acad.line(wing1_x, wing1_y, arrow_x, arrow_y)
        self.acad.line(wing2_x, wing2_y, arrow_x, arrow_y)

    def _draw_chain_symbol(self, x: float, y: float):
        """Малює символ ланцюгового конвеєра (ланки)"""
        size = 0.5
        # Прямокутник як символ ланки
        self.acad.rectangle(x - size, y - size/2, x + size, y + size/2)

    def _draw_belt_symbol(self, x: float, y: float):
        """Малює символ стрічкового конвеєра (паралельні лінії)"""
        offset = 0.3
        length = 1.0
        self.acad.line(x - length/2, y - offset, x + length/2, y - offset)
        self.acad.line(x - length/2, y + offset, x + length/2, y + offset)

    def get_bounds(self, params: SymbolParams) -> Tuple[float, float, float, float]:
        """Межі символу"""
        try:
            coords = params.label.split("->")
            end_coords = coords[1]
            x1, y1 = params.position
            x2, y2 = map(float, end_coords.strip().split(","))

            return (
                min(x1, x2) - 3.0,
                min(y1, y2) - 3.0,
                max(x1, x2) + 3.0,
                max(y1, y2) + 3.0
            )
        except:
            return (0, 0, 0, 0)
