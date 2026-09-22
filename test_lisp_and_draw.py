# -*- coding: utf-8 -*-
"""
ТЕСТ ЗАВАНТАЖЕННЯ LISP ТА МАЛЮВАННЯ СИЛОСА
"""
import sys
import io
import time
import os
import win32gui
import keyboard

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def find_autocad_window():
    windows = []
    def enum_callback(hwnd, result):
        if win32gui.IsWindowVisible(hwnd):
            window_text = win32gui.GetWindowText(hwnd)
            if "autocad" in window_text.lower() and ("drawing" in window_text.lower() or ".dwg" in window_text.lower()):
                result.append((hwnd, window_text))
        return True
    win32gui.EnumWindows(enum_callback, windows)
    return windows[0] if windows else (None, None)

def execute_command(hwnd, command, wait_time=0.5):
    """Виконати команду в AutoCAD"""
    try:
        win32gui.SetForegroundWindow(hwnd)
        time.sleep(0.2)

        keyboard.press_and_release('esc')
        time.sleep(0.2)

        keyboard.write(command)
        time.sleep(0.1)
        keyboard.press_and_release('enter')
        time.sleep(wait_time)

        return True
    except Exception as e:
        print(f"ПОМИЛКА: {e}")
        return False

print("="*70)
print("ТЕСТ ЗАВАНТАЖЕННЯ LISP ТА МАЛЮВАННЯ")
print("="*70)

# Знаходимо AutoCAD
hwnd, title = find_autocad_window()
if not hwnd:
    print("ПОМИЛКА: AutoCAD не знайдено!")
    sys.exit(1)

print(f"\nПідключено до: {title}")
print("="*70)

# Шлях до LISP файлів
lisp_path = "D:/autocad project/autocad-mcp/lisp-code"

# Список LISP файлів для завантаження
lisp_files = [
    "error_handling.lsp",
    "basic_shapes.lsp",
    "drafting_helpers.lsp",
    "industrial_equipment.lsp"
]

print("\nКРОК 1: ЗАВАНТАЖЕННЯ LISP БІБЛІОТЕК")
print("-" * 70)

for filename in lisp_files:
    full_path = os.path.join(lisp_path, filename).replace('\\', '/')

    if not os.path.exists(full_path):
        print(f"ПРОПУЩЕНО: {filename} (файл не знайдено)")
        continue

    print(f"\nЗавантажую: {filename}")
    load_command = f'(load "{full_path}")'

    if execute_command(hwnd, load_command, wait_time=3.0):
        print(f"  OK: {filename} завантажено")
    else:
        print(f"  ПОМИЛКА: Не вдалось завантажити {filename}")

print("\n" + "="*70)
print("КРОК 2: МАЛЮЮ ТЕСТОВИЙ СИЛОС")
print("-" * 70)

print("\nЗараз я намалюю ТЕСТОВИЙ СИЛОС:")
print("  - Позиція: (0, 0)")
print("  - Діаметр: 5000 мм")
print("  - Висота: 10000 мм")
print("  - Тег: ТЕСТ-СИЛОС")
print("\nДивись в AutoCAD! Силос малюється...")

time.sleep(2)

# Команда для малювання силоса
silo_command = '(c:draw-silo 0 0 5000 10000 "ТЕСТ-СИЛОС" "carbon_steel" 50)'

if execute_command(hwnd, silo_command, wait_time=2.0):
    print("\nОК: Команда малювання відправлена!")
    print("\n" + "="*70)
    print("ПЕРЕВІР AUTOCAD - МАЄ БУТИ СИЛОС!")
    print("="*70)
    print("\nЯкщо бачиш силос - ВСЕ ПРАЦЮЄ! ✓")
    print("Якщо немає - подивись на помилки в командному рядку AutoCAD")
else:
    print("\nПОМИЛКА: Не вдалось відправити команду малювання")

print("\n" + "="*70)
print("ТЕСТ ЗАВЕРШЕНО!")
print("="*70)
