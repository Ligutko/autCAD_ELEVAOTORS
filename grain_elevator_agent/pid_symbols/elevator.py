# -*- coding: utf-8 -*-
"""
Символ норії (елеватора) для P&ID діаграм
"""
import math
from typing import Tuple
from .base_symbol import PIDSymbol, SymbolParams

class ElevatorSymbol(PIDSymbol):
    """
    Норія (ковшовий елеватор)

    Параметри:
    - height: Висота підйому (мм)
    - capacity: Продуктивність (т/год)
    - power: Потужність двигуна (кВт)
    """

    def __init__(self, autocad_helper, height: float, capacity: float, power: float):
        super().__init__(autocad_helper)
        self.symbol_type = "ELEVATOR_BUCKET"
        self.height = height
        self.capacity = capacity
        self.power = power

    def draw(self, params: SymbolParams) -> bool:
        """Намалювати норію"""
        if not self.validate_params(params):
            return False

        x, y = params.position
        scale = params.scale

        # Висота в метрах для креслення
        h = self.height * scale / 1000.0
        width = 1.5  # Ширина норії

        print(f"⬆️  Малюю норію {params.label} висотою {self.height}мм")

        # Вертикальний корпус (дві паралельні лінії)
        x1 = x - width/2
        x2 = x + width/2

        self.acad.line(x1, y, x1, y + h)
        self.acad.line(x2, y, x2, y + h)

        # Нижня частина (прийом)
        self.acad.line(x1, y, x2, y)

        # Верхня частина (вивантаження)
        self.acad.line(x1, y + h, x2, y + h)

        # Головний привід зверху (коло)
        drive_r = width * 0.6
        self.acad.circle(x, y + h, drive_r)

        # Натяжний барабан знизу (коло)
        self.acad.circle(x, y, drive_r * 0.8)

        # Ковші (маленькі прямокутники вздовж лінії)
        bucket_count = max(3, int(h / 5.0))
        bucket_w = width * 0.3
        bucket_h = 0.4

        for i in range(bucket_count):
            by = y + (h / bucket_count) * i
            # Ковш справа (вгору)
            self.acad.rectangle(x2 - bucket_w, by, x2, by + bucket_h)

        # Аспірація (патрубок знизу)
        asp_size = 0.5
        self.acad.rectangle(x1 - asp_size, y, x1, y + asp_size)
        self._draw_label(x1 - asp_size - 0.5, y, "ASP", params.label_height * 0.6)

        # Мітки
        # Номер та тип
        label_x = x + width/2 + 0.5
        self._draw_label(label_x, y + h/2, params.label, params.label_height)

        # Продуктивність
        cap_label = f"{self.capacity:.0f}т/г"
        self._draw_label(label_x, y + h/2 - 2.0, cap_label, params.label_height * 0.8)

        # Висота
        height_label = f"H={self.height/1000:.1f}м"
        self._draw_label(label_x, y + h/2 - 4.0, height_label, params.label_height * 0.7)

        print(f"   ✅ Норія {params.label} створена")
        return True

    def get_bounds(self, params: SymbolParams) -> Tuple[float, float, float, float]:
        """Межі символу"""
        x, y = params.position
        scale = params.scale
        h = self.height * scale / 1000.0
        width = 1.5

        return (
            x - width - 2.0,
            y - 1.0,
            x + width + 5.0,
            y + h + 1.0
        )
