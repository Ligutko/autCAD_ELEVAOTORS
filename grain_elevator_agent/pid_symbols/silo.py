# -*- coding: utf-8 -*-
"""
Символ силосу для P&ID діаграм
Тип: MCBY з конічним дном
"""
import math
from typing import Tuple
from .base_symbol import PIDSymbol, SymbolParams

class SiloSymbol(PIDSymbol):
    """
    Силос з конічним дном (MCBY type)

    Параметри:
    - diameter: Діаметр силосу (мм)
    - height: Висота циліндричної частини (мм)
    - cone_height: Висота конусу (мм)
    - volume: Об'єм (м³) - для мітки
    """

    def __init__(self, autocad_helper, diameter: float, height: float,
                 cone_height: float, volume: float):
        super().__init__(autocad_helper)
        self.symbol_type = "SILO_CONICAL"
        self.diameter = diameter
        self.height = height
        self.cone_height = cone_height
        self.volume = volume

    def draw(self, params: SymbolParams) -> bool:
        """Намалювати силос з конічним дном"""
        if not self.validate_params(params):
            return False

        x, y = params.position
        scale = params.scale
        rotation = params.rotation

        # Масштабовані розміри (переводимо в метри для зручності)
        d = self.diameter * scale / 1000.0  # діаметр в м
        h = self.height * scale / 1000.0    # висота в м
        ch = self.cone_height * scale / 1000.0  # висота конуса

        r = d / 2.0  # радіус

        # 1. Циліндрична частина (прямокутник)
        x1, y1 = x - r, y
        x2, y2 = x + r, y + h

        print(f"🏗️  Малюю силос діаметром {self.diameter}мм в ({x},{y})")

        # Вертикальні лінії циліндра
        self.acad.line(x1, y1, x1, y2)
        self.acad.line(x2, y1, x2, y2)

        # Верхня кришка (дуга або лінія)
        self.acad.line(x1, y2, x2, y2)

        # 2. Конічне дно
        # Точка вершини конуса
        cone_x = x
        cone_y = y - ch

        # Лінії конуса
        self.acad.line(x1, y1, cone_x, cone_y)
        self.acad.line(x2, y1, cone_x, cone_y)

        # 3. Позначки аерації (30% покриття дна)
        # Малюємо пунктирну лінію на рівні ~1/3 конуса
        aeration_y = y - ch * 0.7
        aeration_x1 = x - r * 0.3
        aeration_x2 = x + r * 0.3
        self.acad.line(aeration_x1, aeration_y, aeration_x2, aeration_y)

        # 4. Додаємо мітки
        # Мітка типу та номеру
        label_y = y + h + 1.0
        self._draw_label(x - r, label_y, params.label, params.label_height)

        # Мітка об'єму
        vol_label = f"V={self.volume:.0f} м³"
        self._draw_label(x - r, label_y - 3.0, vol_label, params.label_height * 0.8)

        # Мітка діаметру
        dim_label = f"Ø{self.diameter/1000:.1f}м"
        self._draw_label(x - r, y + h/2, dim_label, params.label_height * 0.7)

        # 5. Вихідний патрубок (засувка внизу)
        gate_w = 0.5
        gate_h = 0.3
        gate_x1 = cone_x - gate_w/2
        gate_y = cone_y - gate_h
        self.acad.rectangle(gate_x1, gate_y, gate_x1 + gate_w, gate_y + gate_h)

        print(f"   ✅ Силос {params.label} створено")
        return True

    def get_bounds(self, params: SymbolParams) -> Tuple[float, float, float, float]:
        """Межі символу"""
        x, y = params.position
        scale = params.scale

        d = self.diameter * scale / 1000.0
        h = self.height * scale / 1000.0
        ch = self.cone_height * scale / 1000.0
        r = d / 2.0

        return (
            x - r,               # x_min
            y - ch,              # y_min
            x + r,               # x_max
            y + h + 3.0          # y_max (з міткою)
        )
