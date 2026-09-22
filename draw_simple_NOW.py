# -*- coding: utf-8 -*-
"""
Простий малюнок з паузою для активації AutoCAD
"""
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, "D:/autocad project/autocad-mcp")

from autocad_helper import AutoCADHelper

print("=" * 60)
print("🎨 МАЛЮЮ ПРОСТИЙ ТЕСТ В AUTOCAD")
print("=" * 60)
print()
print("⚠️  ВАЖЛИВО!")
print("1. Зараз КЛІКНИ В ВІКНО AUTOCAD (Drawing1)")
print("2. Дочекайся 5 секунд")
print("3. Скрипт автоматично почне малювати")
print()
print("🕐 Чекаю 5 секунд...")

for i in range(5, 0, -1):
    print(f"   {i}...", end="", flush=True)
    time.sleep(1)
    print("\r", end="")

print("\n🚀 ПОЧИНАЮ!\n")

acad = AutoCADHelper()
if not acad.init():
    print("❌ Помилка підключення")
    input("\nНатисни Enter щоб закрити...")
    sys.exit(1)

print("✅ Підключено до AutoCAD!\n")

# 1. Великий квадрат
print("📦 Малюю КВАДРАТ 100x100...")
acad.line(0, 0, 100, 0)
acad.line(100, 0, 100, 100)
acad.line(100, 100, 0, 100)
acad.line(0, 100, 0, 0)

# 2. Коло
print("\n⭕ Малюю КОЛО радіусом 30...")
acad.circle(50, 50, 30)

# 3. Текст
print("\n📝 Додаю ТЕКСТ 'ПРИВІТ!'...")
acad.text(50, 50, "ПРИВІТ!", 10)

# 4. Діагональна лінія
print("\n📐 Малюю ДІАГОНАЛЬ...")
acad.line(0, 0, 100, 100)

# 5. ZOOM EXTENTS
print("\n🔍 ZOOM EXTENTS...")
acad.zoom_extents()

print("\n" + "=" * 60)
print("✅ ГОТОВО!")
print("=" * 60)
print("\nДивись в AutoCAD Drawing1!")
print("Має бути:")
print("- Квадрат 100x100")
print("- Коло в центрі")
print("- Текст 'ПРИВІТ!'")
print("- Діагональна лінія")

input("\nНатисни Enter щоб закрити...")
