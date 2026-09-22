# -*- coding: utf-8 -*-
"""
ПРОСТИЙ малюнок схеми елеватора БЕЗ P&ID символів
Використовує ТІЛЬКИ базові команди AutoCAD
"""
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, "D:/autocad project/autocad-mcp")

from autocad_helper import AutoCADHelper

print("=" * 70)
print("🌾 МАЛЮЮ ПРОСТУ СХЕМУ ЕЛЕВАТОРА")
print("=" * 70)

acad = AutoCADHelper()
if not acad.init():
    print("❌ Помилка підключення до AutoCAD")
    input("\nНатисни Enter...")
    sys.exit(1)

print("\n✅ Підключено до AutoCAD!\n")

# Координати (спрощені)
print("📦 Етап 1/4: Малюю БУНКЕРИ ПРИЙОМУ (H1-H4)...")
for i in range(4):
    x = i * 15.0
    y = 0.0
    # Бункер як трапеція
    acad.line(x, y, x + 4, y)           # Низ
    acad.line(x, y, x + 1, y + 3)       # Ліва стінка
    acad.line(x + 4, y, x + 3, y + 3)   # Права стінка
    acad.line(x + 1, y + 3, x + 3, y + 3)  # Верх
    # Текст
    acad.text(x + 1.5, y + 1.5, f"H{i+1}", 1.0)

print("\n⬆️  Етап 2/4: Малюю НОРІЇ (H5, H6)...")
# Норія H5
acad.rectangle(25, 5, 27, 38)  # Вертикальна шахта
acad.text(25.5, 20, "H5", 1.5)

# Норія H6
acad.rectangle(40, 5, 42, 53)  # Вища шахта
acad.text(40.5, 25, "H6", 1.5)

print("\n🏗️  Етап 3/4: Малюю СИЛОСИ (1-6)...")
silo_positions = [
    (10, 40), (25, 40), (40, 40),
    (55, 40), (70, 40), (85, 40)
]

for i, (x, y) in enumerate(silo_positions):
    # Силос як циліндр + конус
    acad.circle(x, y + 10, 5)  # Верхній циліндр
    acad.circle(x, y + 10, 4)  # Внутрішній циліндр
    # Конусне дно
    acad.line(x - 5, y, x, y - 3)  # Ліва сторона конуса
    acad.line(x + 5, y, x, y - 3)  # Права сторона конуса
    # Позначка
    acad.text(x - 1, y + 10, f"S{i+1}", 1.2)

print("\n🔗 Етап 4/4: Малюю КОНВЕЄРИ...")
# Конвеєри як лінії зі стрілками
conveyors = [
    ("T7",  25, 35, 10, 38),
    ("T8",  25, 35, 25, 38),
    ("T10", 40, 35, 40, 38),
    ("T11", 40, 35, 55, 38),
    ("T12", 40, 35, 70, 38),
    ("T14", 40, 35, 85, 38),
]

for label, x1, y1, x2, y2 in conveyors:
    acad.line(x1, y1, x2, y2)  # Основна лінія
    # Стрілка в кінці
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) > abs(dy):  # Горизонтальна
        acad.line(x2, y2, x2 - 1, y2 + 0.5)
        acad.line(x2, y2, x2 - 1, y2 - 0.5)
    else:  # Вертикальна
        acad.line(x2, y2, x2 + 0.5, y2 - 1)
        acad.line(x2, y2, x2 - 0.5, y2 - 1)
    # Підпис
    acad.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.5, label, 0.8)

# ZOOM EXTENTS
print("\n🔍 ZOOM EXTENTS...")
acad.zoom_extents()

print("\n" + "=" * 70)
print("✅ ГОТОВО! ДИВИСЬ В AUTOCAD!")
print("=" * 70)
print("\nСхема включає:")
print("✓ 4 бункери прийому (H1-H4)")
print("✓ 2 норії (H5, H6)")
print("✓ 6 силосів (S1-S6)")
print("✓ 6 конвеєрів (T7-T14)")

input("\nНатисни Enter щоб закрити...")
