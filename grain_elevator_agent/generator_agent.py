# -*- coding: utf-8 -*-
"""
Generator Agent - Генерація P&ID схем в AutoCAD
Відповідальний за створення креслень зернового елеватора
"""
import sys
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Додаємо шлях до autocad_helper
sys.path.insert(0, "D:/autocad project/autocad-mcp")
from autocad_helper import AutoCADHelper

# Імпортуємо символи
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pid_symbols.base_symbol import SymbolParams
from pid_symbols.silo import SiloSymbol
from pid_symbols.conveyor import ConveyorSymbol
from pid_symbols.elevator import ElevatorSymbol
from pid_symbols.hopper import HopperSymbol

@dataclass
class SiloSpec:
    """Специфікація силосу"""
    id: str
    type: str
    diameter: float  # мм
    height: float    # мм
    cone_height: float  # мм
    volume: float  # м³
    position: Tuple[float, float]

@dataclass
class ConveyorSpec:
    """Специфікація конвеєра"""
    id: str
    type: str  # "CHAIN" or "BELT"
    start: Tuple[float, float]
    end: Tuple[float, float]
    capacity: float  # т/год
    power: float  # кВт

@dataclass
class ElevatorSpec:
    """Специфікація норії"""
    id: str
    height: float  # мм
    capacity: float  # т/год
    power: float  # кВт
    position: Tuple[float, float]

@dataclass
class HopperSpec:
    """Специфікація бункера"""
    id: str
    width: float  # мм
    height: float  # мм
    capacity: float  # т/год
    position: Tuple[float, float]

class GeneratorAgent:
    """
    Агент для генерації P&ID схем зернового елеватора

    Використовує AutoCAD MCP через autocad_helper.py
    """

    def __init__(self):
        """Ініціалізація агента"""
        self.acad = AutoCADHelper()
        self.initialized = False

        # Збережені специфікації
        self.silos: List[SiloSpec] = []
        self.conveyors: List[ConveyorSpec] = []
        self.elevators: List[ElevatorSpec] = []
        self.hoppers: List[HopperSpec] = []

        # Масштаб креслення
        self.scale = 0.1  # 1:100 масштаб (10м = 1м на кресленні)

    def initialize(self) -> bool:
        """Ініціалізувати з'єднання з AutoCAD"""
        if not self.initialized:
            print("🚀 Ініціалізація Generator Agent...")
            if self.acad.init():
                self.initialized = True
                print("✅ Generator Agent готовий!")
                return True
            else:
                print("❌ Помилка ініціалізації AutoCAD")
                return False
        return True

    def add_silo(self, spec: SiloSpec):
        """Додати силос до схеми"""
        self.silos.append(spec)

    def add_conveyor(self, spec: ConveyorSpec):
        """Додати конвеєр до схеми"""
        self.conveyors.append(spec)

    def add_elevator(self, spec: ElevatorSpec):
        """Додати норію до схеми"""
        self.elevators.append(spec)

    def add_hopper(self, spec: HopperSpec):
        """Додати бункер до схеми"""
        self.hoppers.append(spec)

    def generate_scheme(self) -> bool:
        """
        Згенерувати повну схему елеватора в AutoCAD

        Returns:
            True якщо успішно
        """
        if not self.initialize():
            return False

        print("\n" + "=" * 60)
        print("ГЕНЕРАЦІЯ P&ID СХЕМИ ЗЕРНОВОГО ЕЛЕВАТОРА")
        print("=" * 60 + "\n")

        # 1. Малюємо бункери прийому
        print("📦 Етап 1/4: Бункери прийому")
        for hopper_spec in self.hoppers:
            symbol = HopperSymbol(
                self.acad,
                hopper_spec.width,
                hopper_spec.height,
                hopper_spec.capacity
            )

            params = SymbolParams(
                position=hopper_spec.position,
                scale=self.scale,
                label=hopper_spec.id
            )

            symbol.draw(params)

        # 2. Малюємо норії (елеватори)
        print("\n⬆️  Етап 2/4: Норії (елеватори)")
        for elev_spec in self.elevators:
            symbol = ElevatorSymbol(
                self.acad,
                elev_spec.height,
                elev_spec.capacity,
                elev_spec.power
            )

            params = SymbolParams(
                position=elev_spec.position,
                scale=self.scale,
                label=elev_spec.id
            )

            symbol.draw(params)

        # 3. Малюємо силоси
        print("\n🏗️  Етап 3/4: Силоси")
        for silo_spec in self.silos:
            symbol = SiloSymbol(
                self.acad,
                silo_spec.diameter,
                silo_spec.height,
                silo_spec.cone_height,
                silo_spec.volume
            )

            params = SymbolParams(
                position=silo_spec.position,
                scale=self.scale,
                label=f"Силос {silo_spec.id}"
            )

            symbol.draw(params)

        # 4. Малюємо конвеєри (лінії потоку)
        print("\n🔗 Етап 4/4: Конвеєри")
        for conv_spec in self.conveyors:
            symbol = ConveyorSymbol(
                self.acad,
                conv_spec.type,
                conv_spec.capacity,
                conv_spec.power
            )

            # Формуємо label з координатами кінця
            label_with_coords = f"{conv_spec.id}->{conv_spec.end[0]},{conv_spec.end[1]}"

            params = SymbolParams(
                position=conv_spec.start,
                scale=self.scale,
                label=label_with_coords
            )

            symbol.draw(params)

        # Фінальні штрихи
        print("\n🎨 Фінальні налаштування...")
        self.acad.zoom_extents()
        self.acad.regen()

        print("\n" + "=" * 60)
        print("✅ СХЕМА ЗГЕНЕРОВАНА УСПІШНО!")
        print("=" * 60 + "\n")

        return True

# Тестова конфігурація для елеватора з документації
def create_test_elevator_scheme():
    """Створити тестову схему елеватора на основі документації"""

    agent = GeneratorAgent()

    # Бункери прийому H1-H4
    for i in range(4):
        agent.add_hopper(HopperSpec(
            id=f"H{i+1}",
            width=4400,
            height=3000,
            capacity=100,
            position=(i * 15.0, 0.0)
        ))

    # Норії H5, H6
    agent.add_elevator(ElevatorSpec(
        id="H5",
        height=33000,
        capacity=100,
        power=22.0,
        position=(25.0, 5.0)
    ))

    agent.add_elevator(ElevatorSpec(
        id="H6",
        height=48700,
        capacity=100,
        power=5.5,
        position=(40.0, 5.0)
    ))

    # Силоси 1-6
    silo_positions = [
        (10.0, 40.0),  # Силос 1
        (25.0, 40.0),  # Силос 2
        (40.0, 40.0),  # Силос 3
        (55.0, 40.0),  # Силос 4
        (70.0, 40.0),  # Силос 5
        (85.0, 40.0),  # Силос 6
    ]

    for i, pos in enumerate(silo_positions):
        agent.add_silo(SiloSpec(
            id=str(i+1),
            type="MCBY_220.13/B12",
            diameter=22000,
            height=21422,
            cone_height=5000,
            volume=6381,
            position=pos
        ))

    # Конвеєри T7-T16
    conveyors = [
        ("T7", "CHAIN", (25.0, 35.0), (10.0, 38.0)),
        ("T8", "CHAIN", (25.0, 35.0), (25.0, 38.0)),
        ("T10", "CHAIN", (40.0, 35.0), (40.0, 38.0)),
        ("T11", "CHAIN", (40.0, 35.0), (55.0, 38.0)),
        ("T12", "CHAIN", (40.0, 35.0), (70.0, 38.0)),
        ("T14", "CHAIN", (40.0, 35.0), (85.0, 38.0)),
    ]

    for conv_id, conv_type, start, end in conveyors:
        agent.add_conveyor(ConveyorSpec(
            id=conv_id,
            type=conv_type,
            start=start,
            end=end,
            capacity=100,
            power=11.0
        ))

    # Генеруємо схему
    return agent.generate_scheme()

if __name__ == "__main__":
    print("🌾 Grain Elevator P&ID Generator Agent")
    print("Створення тестової схеми елеватора...\n")

    success = create_test_elevator_scheme()

    if success:
        print("\n🎉 Схему успішно створено в AutoCAD!")
        print("📂 Перевір AutoCAD для результату")
    else:
        print("\n❌ Помилка при створенні схеми")
