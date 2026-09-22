# -*- coding: utf-8 -*-
"""
Простий тест - намалювати квадрат, коло і текст
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, "D:/autocad project/autocad-mcp")

from autocad_helper import AutoCADHelper

print("🎨 Малюю ТЕСТОВІ ОБ'ЄКТИ в Drawing1...\n")

acad = AutoCADHelper()
if not acad.init():
    print("❌ Помилка підключення")
    sys.exit(1)

print("✅ Підключено до AutoCAD!")

# 1. Великий квадрат по центру
print("📦 Малюю великий КВАДРАТ...")
acad.line(0, 0, 100, 0)
acad.line(100, 0, 100, 100)
acad.line(100, 100, 0, 100)
acad.line(0, 100, 0, 0)

# 2. Велике коло
print("⭕ Малюю КОЛО...")
acad.circle(50, 50, 30)

# 3. Текст
print("📝 Пишу ТЕКСТ...")
acad.text(50, 50, "ПРИВІТ!", 10)

# 4. ZOOM EXTENTS
print("🔍 ZOOM EXTENTS...")
acad.zoom_extents()

print("\n✅ ГОТОВО! Дивись в AutoCAD!")
print("Має бути: квадрат, коло і текст ПРИВІТ!")
