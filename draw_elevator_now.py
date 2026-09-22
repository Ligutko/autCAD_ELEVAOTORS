# -*- coding: utf-8 -*-
"""
Одразу намалювати елеватор (без питань)
"""
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, "D:/autocad project/autocad-mcp")
sys.path.insert(0, "D:/autocad project/grain_elevator_agent")

from generator_agent import create_test_elevator_scheme

print("🌾 МАЛЮЮ СХЕМУ ЕЛЕВАТОРА В AUTOCAD...\n")
success = create_test_elevator_scheme()

if success:
    print("\n✅ ГОТОВО!")
    print("\nТепер в AutoCAD:")
    print("1. Натисни: Z потім E потім Enter")
    print("2. Або введи команду: ZOOM EXTENTS")
    print("\nТи побачиш моє креслення!")
