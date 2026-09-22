# -*- coding: utf-8 -*-
"""
Базовий клас для P&ID символів
ISO 14617 compliant symbols for process diagrams
"""
import sys
import os
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass

@dataclass
class SymbolParams:
    """Параметри символу"""
    position: Tuple[float, float]  # (x, y)
    rotation: float = 0.0           # градуси
    scale: float = 1.0              # масштаб
    layer: str = "EQP"              # шар
    label: str = ""                 # мітка
    label_height: float = 2.5       # висота тексту

class PIDSymbol:
    """Базовий клас для P&ID символів"""

    def __init__(self, autocad_helper):
        """
        Args:
            autocad_helper: Екземпляр AutoCADHelper
        """
        self.acad = autocad_helper
        self.symbol_type = "BASE"

    def draw(self, params: SymbolParams) -> bool:
        """
        Намалювати символ

        Args:
            params: Параметри символу

        Returns:
            True якщо успішно
        """
        raise NotImplementedError("Subclasses must implement draw()")

    def _draw_label(self, x: float, y: float, text: str, height: float = 2.5):
        """Додати мітку до символу"""
        return self.acad.text(x, y, text, height)

    def _draw_dimension(self, x1: float, y1: float, x2: float, y2: float,
                       dim_x: float, dim_y: float):
        """Додати розмір"""
        cmd = f"(c:create-linear-dim {x1} {y1} {x2} {y2} {dim_x} {dim_y})"
        return self.acad.cmd(cmd, f"Додаю розмір")

    def validate_params(self, params: SymbolParams) -> bool:
        """Валідація параметрів"""
        if params.scale <= 0:
            print(f"⚠️ Неправильний масштаб: {params.scale}")
            return False
        return True

    def get_bounds(self, params: SymbolParams) -> Tuple[float, float, float, float]:
        """
        Отримати межі символу

        Returns:
            (x_min, y_min, x_max, y_max)
        """
        raise NotImplementedError("Subclasses must implement get_bounds()")
