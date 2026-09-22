# -*- coding: utf-8 -*-
"""
Створити креслення елеватора в НОВОМУ файлі AutoCAD
"""
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, "D:/autocad project/autocad-mcp")
sys.path.insert(0, "D:/autocad project/grain_elevator_agent")

from autocad_helper import AutoCADHelper

print("=" * 60)
print("🌾 ПІДГОТОВКА ДО СТВОРЕННЯ КРЕСЛЕННЯ")
print("=" * 60)

print("\n📋 ІНСТРУКЦІЯ:\n")
print("1. В AutoCAD натисни: Ctrl+N (створити новий файл)")
print("2. Вибери шаблон: acad.dwt або acadlt.dwt")
print("3. Дочекайся поки відкриється ПОРОЖНЄ креслення")
print("4. Потім тут натисни Enter\n")

input("✅ Готовий? Натисни Enter коли в AutoCAD буде порожнє креслення...")

# Тепер малюємо
from generator_agent import create_test_elevator_scheme

print("\n🚀 Починаю малювати схему елеватора...\n")
success = create_test_elevator_scheme()

if success:
    print("\n" + "=" * 60)
    print("✅ ГОТОВО! Дивись в AutoCAD!")
    print("=" * 60)
    print("\n📝 Що робити далі:")
    print("1. Подивись на схему в AutoCAD")
    print("2. Збережи файл: Ctrl+S")
    print("3. Назва: elevator_scheme.dwg")
    print("\n🎉 Твоє креслення готове!")
else:
    print("\n❌ Щось пішло не так")
