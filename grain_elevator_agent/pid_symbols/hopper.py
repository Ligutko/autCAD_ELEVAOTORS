# -*- coding: utf-8 -*-
"""
Символ бункера прийому для P&ID діаграм
"""
from typing import Tuple
from .base_symbol import PIDSymbol, SymbolParams

class HopperSymbol(PIDSymbol):
    """
    Бункер прийому

    Параметри:
    - width: Ширина (мм)
    - height: Висота (мм)
    - capacity: Продуктивність (т/год)
    """

    def __init__(self, autocad_helper, width: float, height: float, capacity: float):
        super().__init__(autocad_helper)
        self.symbol_type = "HOPPER_RECEPTION"
        self.width = width
        self.height = height
        self.capacity = capacity

    def draw(self, params: SymbolParams) -> bool:
        """Намалювати бункер"""
        if not self.validate_params(params):
            return False

        x, y = params.position
        scale = params.scale

        # Розміри в метрах
        w = self.width * scale / 1000.0
        h = self.height * scale / 1000.0

        print(f"📦 Малюю бункер {params.label} {self.width}x{self.height}мм")

        # Бункер - трапеція (45° стінки)
        # Верхня частина (прийом)
        top_w = w
        top_y = y + h

        # Нижня частина (вузька)
        bottom_w = w * 0.3
        bottom_y = y

        # Координати вершин
        x1_top = x - top_w/2
        x2_top = x + top_w/2

        x1_bottom = x - bottom_w/2
        x2_bottom = x + bottom_w/2

        # Малюємо трапецію
        # Верх
        self.acad.line(x1_top, top_y, x2_top, top_y)
        # Ліва стінка
        self.acad.line(x1_top, top_y, x1_bottom, bottom_y)
        # Права стінка
        self.acad.line(x2_top, top_y, x2_bottom, bottom_y)
        # Дно (вузьке)
        self.acad.line(x1_bottom, bottom_y, x2_bottom, bottom_y)

        # Решітка зверху (захисна)
        grid_count = 3
        for i in range(1, grid_count):
            gx = x1_top + (top_w / grid_count) * i
            self.acad.line(gx, top_y - 0.2, gx, top_y + 0.2)

        # Аспірація (патрубок збоку)
        asp_size = 0.5
        asp_x = x2_top + 0.2
        asp_y = top_y - h * 0.3
        self.acad.rectangle(asp_x, asp_y, asp_x + asp_size, asp_y + asp_size)
        self._draw_label(asp_x, asp_y + asp_size + 0.2, "350x350", params.label_height * 0.5)

        # Вібропідживач знизу
        vibro_w = bottom_w * 1.5
        vibro_h = 0.3
        self.acad.rectangle(x - vibro_w/2, bottom_y - vibro_h,
                          x + vibro_w/2, bottom_y)

        # Мітки
        # Номер бункера
        label_x = x1_top - 0.5
        self._draw_label(label_x, top_y + 0.5, params.label, params.label_height)

        # Продуктивність
        cap_label = f"{self.capacity:.0f}т/г"
        self._draw_label(label_x, top_y - 1.0, cap_label, params.label_height * 0.8)

        print(f"   ✅ Бункер {params.label} створено")
        return True

    def get_bounds(self, params: SymbolParams) -> Tuple[float, float, float, float]:
        """Межі символу"""
        x, y = params.position
        scale = params.scale
        w = self.width * scale / 1000.0
        h = self.height * scale / 1000.0

        return (
            x - w/2 - 2.0,
            y - 0.5,
            x + w/2 + 2.0,
            y + h + 2.0
        )
