# -*- coding: utf-8 -*-
"""
Створити НОВЕ креслення елеватора
"""
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, "D:/autocad project/autocad-mcp")
sys.path.insert(0, "D:/autocad project/grain_elevator_agent")

from autocad_helper import AutoCADHelper
from generator_agent import create_test_elevator_scheme

print("=" * 60)
print("🌾 СТВОРЕННЯ НОВОГО КРЕСЛЕННЯ ЕЛЕВАТОРА")
print("=" * 60)

# Ініціалізація
acad = AutoCADHelper()
if not acad.init():
    print("❌ Помилка підключення до AutoCAD")
    sys.exit(1)

# Запитуємо користувача
print("\n⚠️  УВАГА!")
print("Це створить нову схему в поточному кресленні.")
print("\nРекомендую:")
print("1. Відкрити НОВЕ креслення в AutoCAD (Ctrl+N)")
print("2. Потім запустити цей скрипт")
print("\nАбо зберегти поточне креслення перед продовженням!")

input("\n✅ Натисни Enter щоб продовжити...")

# Очищаємо (опціонально)
print("\n🧹 Хочеш очистити поточне креслення?")
print("1 - ТАК, очистити все")
print("2 - НІ, малювати поверх")
choice = input("Вибір (1 або 2): ").strip()

if choice == "1":
    print("⚠️  Видаляю всі об'єкти...")
    acad.cmd('(command "._erase" "_all" "")', "Очищення креслення")

# Генеруємо схему
print("\n🚀 Генерую схему елеватора...\n")
success = create_test_elevator_scheme()

if success:
    print("\n✅ ГОТОВО!")
    print("\n📝 Що робити далі:")
    print("1. Перевір AutoCAD - там має бути схема")
    print("2. Збережи: Ctrl+S або File → Save As")
    print("3. Назва файлу: elevator_scheme.dwg")
else:
    print("\n❌ Помилка при створенні")
